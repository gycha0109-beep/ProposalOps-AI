#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


PPTX_TEXT_TAG = "{http://schemas.openxmlformats.org/drawingml/2006/main}t"
SLIDE_RE = re.compile(r"slide(\d+)\.xml$")
SUPPORTED_EXTENSIONS = {".pptx", ".pdf"}


def normalize_text(parts: list[str]) -> str:
    cleaned = []
    for value in parts:
        text = re.sub(r"\s+", " ", str(value or "")).strip()
        if text:
            cleaned.append(text)
    return "\n".join(cleaned).strip()


def infer_title(raw_text: str, fallback: str) -> str:
    for line in raw_text.splitlines():
        line = line.strip()
        if line:
            return line[:160]
    return fallback


def make_record(
    *,
    proposal_id: str,
    file_name: str,
    page: int,
    raw_text: str,
    source_type: str,
    sensitivity: str,
    source_format: str,
) -> dict:
    raw_text = raw_text.strip()
    return {
        "proposal_id": proposal_id,
        "page": page,
        "title": infer_title(raw_text, f"Page {page}"),
        "raw_text": raw_text,
        "source": {
            "file_name": file_name,
            "page": page,
            "source_type": source_type,
        },
        "sensitivity": sensitivity,
        "extraction": {
            "format": source_format,
            "text_chars": len(raw_text),
            "empty": not bool(raw_text),
        },
    }


def _slide_number(name: str) -> int | None:
    match = SLIDE_RE.search(name)
    return int(match.group(1)) if match else None


def _extract_xml_text(payload: bytes) -> list[str]:
    root = ET.fromstring(payload)
    return [
        node.text or ""
        for node in root.iter(PPTX_TEXT_TAG)
        if (node.text or "").strip()
    ]


def extract_pptx(
    path: Path,
    *,
    proposal_id: str,
    source_type: str,
    sensitivity: str,
) -> list[dict]:
    records = []
    with zipfile.ZipFile(path) as archive:
        slide_names = []
        for name in archive.namelist():
            if name.startswith("ppt/slides/") and _slide_number(name) is not None:
                slide_names.append(name)
        slide_names.sort(key=lambda value: _slide_number(value) or 0)

        for name in slide_names:
            page = _slide_number(name)
            if page is None:
                continue
            parts = _extract_xml_text(archive.read(name))

            note_name = f"ppt/notesSlides/notesSlide{page}.xml"
            if note_name in archive.namelist():
                note_parts = _extract_xml_text(archive.read(note_name))
                if note_parts:
                    parts.append("Speaker Notes")
                    parts.extend(note_parts)

            raw_text = normalize_text(parts)
            records.append(
                make_record(
                    proposal_id=proposal_id,
                    file_name=path.name,
                    page=page,
                    raw_text=raw_text,
                    source_type=source_type,
                    sensitivity=sensitivity,
                    source_format="pptx",
                )
            )

    return records


def extract_pdf(
    path: Path,
    *,
    proposal_id: str,
    source_type: str,
    sensitivity: str,
) -> list[dict]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError(
            "PDF extraction requires pypdf. Install with: pip install -r requirements-extraction.txt"
        ) from exc

    reader = PdfReader(str(path))
    records = []
    for index, page_obj in enumerate(reader.pages, start=1):
        raw_text = normalize_text([(page_obj.extract_text() or "")])
        records.append(
            make_record(
                proposal_id=proposal_id,
                file_name=path.name,
                page=index,
                raw_text=raw_text,
                source_type=source_type,
                sensitivity=sensitivity,
                source_format="pdf",
            )
        )
    return records


def extract_source(
    path: Path,
    *,
    proposal_id: str,
    source_type: str,
    sensitivity: str,
) -> list[dict]:
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported source format: {suffix}. Supported: {sorted(SUPPORTED_EXTENSIONS)}"
        )
    if suffix == ".pptx":
        return extract_pptx(
            path,
            proposal_id=proposal_id,
            source_type=source_type,
            sensitivity=sensitivity,
        )
    return extract_pdf(
        path,
        proposal_id=proposal_id,
        source_type=source_type,
        sensitivity=sensitivity,
    )


def validate_records(records: list[dict], *, expected_file_name: str) -> list[str]:
    errors = []
    if not records:
        errors.append("NO_PAGES")
        return errors

    pages = [record.get("page") for record in records]
    if pages != list(range(1, len(records) + 1)):
        errors.append(f"NON_SEQUENTIAL_PAGES:{pages}")

    for record in records:
        page = record.get("page")
        if not record.get("proposal_id"):
            errors.append(f"MISSING_PROPOSAL_ID:{page}")
        if not isinstance(record.get("raw_text"), str):
            errors.append(f"INVALID_RAW_TEXT:{page}")
        source = record.get("source") or {}
        if source.get("file_name") != expected_file_name:
            errors.append(f"SOURCE_FILE_MISMATCH:{page}")
        if source.get("page") != page:
            errors.append(f"SOURCE_PAGE_MISMATCH:{page}")
        extraction = record.get("extraction") or {}
        if extraction.get("text_chars") != len(record.get("raw_text") or ""):
            errors.append(f"TEXT_CHAR_MISMATCH:{page}")
    return errors


def write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")


def default_proposal_id(path: Path) -> str:
    stem = re.sub(r"[^A-Za-z0-9]+", "-", path.stem.upper()).strip("-")
    return f"PROP-{stem or 'SOURCE'}"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract page-level text/provenance from PPTX or PDF proposal sources."
    )
    parser.add_argument("source")
    parser.add_argument("--proposal-id")
    parser.add_argument("--source-type", default="customer_source")
    parser.add_argument(
        "--sensitivity",
        choices=("public_demo", "internal", "confidential"),
        default="internal",
    )
    parser.add_argument("--out", required=True)
    parser.add_argument("--allow-empty-pages", action="store_true")
    args = parser.parse_args()

    source = Path(args.source)
    if not source.is_file():
        raise SystemExit(f"Source file does not exist: {source}")

    proposal_id = args.proposal_id or default_proposal_id(source)
    try:
        records = extract_source(
            source,
            proposal_id=proposal_id,
            source_type=args.source_type,
            sensitivity=args.sensitivity,
        )
    except Exception as exc:
        raise SystemExit(str(exc)) from exc

    errors = validate_records(records, expected_file_name=source.name)
    if not args.allow_empty_pages:
        for record in records:
            if (record.get("extraction") or {}).get("empty"):
                errors.append(f"EMPTY_PAGE:{record.get('page')}")

    if errors:
        print(
            json.dumps(
                {
                    "status": "FAIL",
                    "source": str(source),
                    "errors": errors,
                },
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )
        raise SystemExit(3)

    out = Path(args.out)
    write_jsonl(out, records)
    print(
        json.dumps(
            {
                "status": "PASS",
                "source": str(source),
                "format": source.suffix.lower().lstrip("."),
                "proposal_id": proposal_id,
                "pages": len(records),
                "nonempty_pages": sum(
                    1 for record in records if not record["extraction"]["empty"]
                ),
                "output": str(out),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
