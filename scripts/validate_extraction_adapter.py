#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
import zipfile
from pathlib import Path

from extract_proposal_source import extract_source, validate_records


def make_pptx_fixture(path: Path) -> None:
    slide_1 = """<?xml version="1.0" encoding="UTF-8"?>
<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"
       xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
  <p:cSld>
    <p:spTree>
      <p:sp><p:txBody><a:p><a:r><a:t>지역 관광 홍보 전략</a:t></a:r></a:p></p:txBody></p:sp>
      <p:sp><p:txBody><a:p><a:r><a:t>발견에서 저장까지 연결</a:t></a:r></a:p></p:txBody></p:sp>
    </p:spTree>
  </p:cSld>
</p:sld>
"""
    slide_2 = """<?xml version="1.0" encoding="UTF-8"?>
<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"
       xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
  <p:cSld>
    <p:spTree>
      <p:sp><p:txBody><a:p><a:r><a:t>운영정보 검수</a:t></a:r></a:p></p:txBody></p:sp>
    </p:spTree>
  </p:cSld>
</p:sld>
"""
    notes_2 = """<?xml version="1.0" encoding="UTF-8"?>
<p:notes xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"
         xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
  <p:cSld>
    <p:spTree>
      <p:sp><p:txBody><a:p><a:r><a:t>게시 전 변경 가능 정보를 재확인</a:t></a:r></a:p></p:txBody></p:sp>
    </p:spTree>
  </p:cSld>
</p:notes>
"""
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("ppt/slides/slide1.xml", slide_1)
        archive.writestr("ppt/slides/slide2.xml", slide_2)
        archive.writestr("ppt/notesSlides/notesSlide2.xml", notes_2)


def make_pdf_fixture(path: Path) -> None:
    from pypdf import PdfWriter
    from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

    writer = PdfWriter()

    for text in ("Proposal PDF Page One", "Proposal PDF Page Two"):
        page = writer.add_blank_page(width=612, height=792)
        font = DictionaryObject(
            {
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
            }
        )
        font_ref = writer._add_object(font)
        resources = DictionaryObject(
            {
                NameObject("/Font"): DictionaryObject(
                    {
                        NameObject("/F1"): font_ref,
                    }
                )
            }
        )
        page[NameObject("/Resources")] = resources

        stream = DecodedStreamObject()
        stream.set_data(
            f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode("ascii")
        )
        page[NameObject("/Contents")] = writer._add_object(stream)

    with path.open("wb") as handle:
        writer.write(handle)


def assert_records(records: list[dict], *, file_name: str, pages: int) -> None:
    errors = validate_records(records, expected_file_name=file_name)
    if errors:
        raise AssertionError(errors)
    if len(records) != pages:
        raise AssertionError(f"{file_name}: expected {pages} pages, got {len(records)}")
    if any(record["extraction"]["empty"] for record in records):
        raise AssertionError(f"{file_name}: fixture unexpectedly produced an empty page")


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="proposalops-extract-") as temp_dir:
        root = Path(temp_dir)
        pptx_path = root / "proposal-fixture.pptx"
        pdf_path = root / "proposal-fixture.pdf"

        make_pptx_fixture(pptx_path)
        make_pdf_fixture(pdf_path)

        pptx_records = extract_source(
            pptx_path,
            proposal_id="PROP-FIXTURE-PPTX",
            source_type="synthetic_fixture",
            sensitivity="public_demo",
        )
        pdf_records = extract_source(
            pdf_path,
            proposal_id="PROP-FIXTURE-PDF",
            source_type="synthetic_fixture",
            sensitivity="public_demo",
        )

        assert_records(pptx_records, file_name=pptx_path.name, pages=2)
        assert_records(pdf_records, file_name=pdf_path.name, pages=2)

        if "지역 관광 홍보 전략" not in pptx_records[0]["raw_text"]:
            raise AssertionError("PPTX slide text was not extracted.")
        if "Speaker Notes" not in pptx_records[1]["raw_text"]:
            raise AssertionError("PPTX speaker notes marker was not extracted.")
        if "게시 전 변경 가능 정보를 재확인" not in pptx_records[1]["raw_text"]:
            raise AssertionError("PPTX speaker notes content was not extracted.")
        if "Proposal PDF Page One" not in pdf_records[0]["raw_text"]:
            raise AssertionError("PDF page 1 text was not extracted.")
        if "Proposal PDF Page Two" not in pdf_records[1]["raw_text"]:
            raise AssertionError("PDF page 2 text was not extracted.")

        result = {
            "status": "PASS",
            "pptx": {
                "pages": len(pptx_records),
                "speaker_notes": True,
                "source_provenance": True,
            },
            "pdf": {
                "pages": len(pdf_records),
                "text_extraction": True,
                "source_provenance": True,
            },
            "llm_calls": 0,
            "fixture_storage": "runtime-only",
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
