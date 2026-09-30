# Proposal Source Extraction Adapter

## Goal

기존 제안서 PPTX/PDF를 ProposalOps AI의 Proposal Asset 전처리 단계에 넣기 전에,
페이지 단위 raw text와 source provenance를 deterministic하게 추출한다.

이 단계는 **문서 읽기**만 담당한다.

하지 않는 일:

- 전략 의미 추론
- page_type 자동 분류
- reusable pattern 생성
- company fact 판정
- Proposal Asset의 의미 필드 자동 완성

이 분리는 extraction 단계에서 hallucination이 섞이지 않게 하기 위한 것이다.

## Supported formats

- `.pptx`
- text-bearing `.pdf`

PPTX:

- slide text
- matching speaker notes
- slide number
- original file name

PDF:

- page text
- page number
- original file name

PDF extraction uses `pypdf`.

Scanned/image-only PDFs require a separate OCR adapter and are not claimed as supported.

## Output

JSONL, one record per page:

```json
{
  "proposal_id": "PROP-CUSTOMER-001",
  "page": 1,
  "title": "첫 번째 비어 있지 않은 텍스트 줄",
  "raw_text": "page text",
  "source": {
    "file_name": "proposal.pptx",
    "page": 1,
    "source_type": "customer_source"
  },
  "sensitivity": "internal",
  "extraction": {
    "format": "pptx",
    "text_chars": 123,
    "empty": false
  }
}
```

이 출력은 `data/taxonomy/proposal-taxonomy.yaml`의 full Proposal Asset으로 semantic enrichment하기 전 staging record다.

## Usage

Install PDF dependency:

```bash
python -m pip install -r requirements-extraction.txt
```

PPTX:

```bash
python scripts/extract_proposal_source.py proposal.pptx \
  --proposal-id PROP-CUSTOMER-001 \
  --source-type customer_source \
  --sensitivity confidential \
  --out extracted/proposal.jsonl
```

PDF:

```bash
python scripts/extract_proposal_source.py proposal.pdf \
  --proposal-id PROP-CUSTOMER-002 \
  --source-type customer_source \
  --sensitivity confidential \
  --out extracted/proposal.jsonl
```

By default, an empty page is a blocking validation error.
Use `--allow-empty-pages` only when blank pages are intentional.

## Deterministic validation

The adapter checks:

- source file exists
- supported extension
- sequential pages
- proposal_id present
- raw_text is a string
- source file/page provenance matches
- recorded character count matches actual text
- empty pages blocked by default

No LLM call is used.

## CI evidence

Workflow:

`.github/workflows/proposal-source-extraction.yml`

Self-test:

`scripts/validate_extraction_adapter.py`

The CI test creates runtime-only fixtures:

- synthetic PPTX: 2 slides + speaker notes
- synthetic PDF: 2 text pages

It verifies:

- page count
- slide text extraction
- speaker notes extraction
- PDF text extraction
- source provenance
- sequential pages

Fixtures are not committed as fake customer files.

## Boundary

This adapter closes the previous portfolio gap of having only Markdown synthetic source documents.

What is still outside the current scope:

- OCR for scanned/image-only PDFs
- layout/table/image semantic reconstruction
- automatic Proposal Asset semantic classification from raw extracted pages
- real customer confidential source validation

Those should be added only when actual source files and handling requirements are available.
