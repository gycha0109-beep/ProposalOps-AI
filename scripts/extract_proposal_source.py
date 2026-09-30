#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import posixpath
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


PPTX_TEXT_TAG = "{http://schemas.openxmlformats.org/drawingml/2006/main}t"
PPTX_SLIDE_ID_TAG = "{http://schemas.openxmlformats.org/presentationml/2006/main}sldId"
PPTX_REL_ID_ATTR = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
OOXML_REL_TAG = "{http://schemas.openxmlformats.org/package/2006/relationships}Relationship"
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


def _normalize_ooxml_target(base_dir: str, target: str) -> str:
    if target.startswith("/"):
        return posixpath.normpath(target.lstrip("/"))
    return posixpath.normpath(posixpath.join(base_dir, target))


def _relationship_map(
    archive: zipfile.ZipFile,
    rel_path: str,
    *,
    base_dir: str,
) -> dict[str, dict]:
    if rel_path not in archive.namelist():
        return {}
    root = ET.fromstring(archive.read(rel_path))
    result = {}
    for rel in root.iter(OOXML_REL_TAG):
        rel_id = rel.attrib.get("Id")
        target = rel.attrib.get("Target")
        if not rel_id or not target:
            continue
        result[rel_id] = {
            "target": _normalize_ooxml_target(base_dir, target),
            "type": rel.attrib.get("Type", ""),
        }
    return result


def _ordered_slide_names(archive: zipfile.ZipFile) -> list[str]:
    presentation = "ppt/presentation.xml"
    rels = "ppt/_rels/presentation.xml.rels"
    if presentation in archive.namelist() and rels in archive.namelist():
        relationships = _relationship_map(archive, rels, base_dir="ppt")
        root = ET.fromstring(archive.read(presentation))
        ordered = []
        for slide_id in root.iter(PPTX_SLIDE_ID_TAG):
            rel_id = slide_id.attrib.get(PPTX_REL_ID_ATTR)
            target = (relationships.get(rel_id) or {}).get("target")
            if target and target in archive.namelist():
                ordered.append(target)
        if ordered:
            return ordered

    slide_names = [
        name
        for name in archive.namelist()
        if name.startswith("ppt/slides/") and _slide_number(name) is not None
    ]
    slide_names.sort(key=lambda value: _slide_number(value) or 0)
    return slide_names


def _notes_name_for_slide(
    archive: zipfile.ZipFile,
    slide_name: str,
) -> str | None:
    slide_file = posixpath.basename(slide_name)
    rel_path = f"{posixpath.dirname(slide_name)}/_rels/{slide_file}.rels"
    relationships = _relationship_map(
        archive,
        rel_path,
        base_dir=posixpath.dirname(slide_name),
    )
    for relation in relationships.values():
        if relation.get("type", "").endswith("/notesSlide"):
            target = relation.get("target")
            if target in archive.namelist():
                return target

    native_number = _slide_number(slide_name)
    fallback = (
        f"ppt/notesSlides/notesSlide{native_number}.xml"
        if native_number is not None
        else None
    )
    if fallback and fallback in archive.namelist():
        return fallback
    return None


def extract_pptx(
    path: Path,
    *,
    proposal_id: str,
    source_type: str,
    sensitivity: str,
) -> list[dict]:
    records = []
    with zipfile.ZipFile(path) as archive:
        slide_names = _ordered_slide_names(archive)

        for page, name in enumerate(slide_names, start=1):
            parts = _extract_xml_text(archive.read(name))

            note_name = _notes_name_for_slide(archive, name)
            if note_name:
                note_parts = _extract_xml_text(archive.read(note_name))
                if note_parts:
                    parts.append("Speaker Notes")
                    parts.extend(note_parts)

            raw_text = normalize_text(parts)
            record = make_record(
                proposal_id=proposal_id,
                file_name=path.name,
                page=page,
                raw_text=raw_text,
                source_type=source_type,
                sensitivity=sensitivity,
                source_format="pptx",
            )
            record["extraction"]["native_part"] = name
            if note_name:
                record["extraction"]["notes_part"] = note_name
            records.append(record)

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
