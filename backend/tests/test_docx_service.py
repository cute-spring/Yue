import logging
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pytest
from docx import Document
from docx.oxml import OxmlElement

from app.services import doc_retrieval
from app.services.docx_service import docx_service


def _write_sample_docx(path: Path) -> None:
    document = Document()
    document.add_heading("Overview", level=1)
    document.add_paragraph("A plain paragraph.")
    document.add_paragraph("First checklist item", style="List Bullet")
    table = document.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "Product"
    table.cell(0, 1).text = "Amount"
    table.cell(1, 0).text = "苹果"
    table.cell(1, 1).text = "100"
    document.add_paragraph("Closing note.")
    document.save(path)


def _write_merged_table_docx(path: Path) -> None:
    document = Document()
    table = document.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "Merged heading"
    table.cell(0, 0).merge(table.cell(0, 1))
    table.cell(1, 0).text = "Product"
    table.cell(1, 1).text = "Amount"
    document.save(path)


def _write_malformed_xml_docx(path: Path) -> None:
    _write_sample_docx(path)
    with ZipFile(path) as archive:
        members = {name: archive.read(name) for name in archive.namelist()}
    members["word/document.xml"] = b"<w:document>"
    with ZipFile(path, "w", compression=ZIP_DEFLATED) as archive:
        for name, content in members.items():
            archive.writestr(name, content)


def test_extract_blocks_preserves_document_order_stable_locators_and_audit(tmp_path: Path, caplog):
    caplog.set_level(logging.INFO)
    path = tmp_path / "sample.docx"
    _write_sample_docx(path)

    result = docx_service.extract_blocks(
        "sample.docx",
        root_dir=str(tmp_path),
        allow_roots=[str(tmp_path)],
    )

    assert result["ok"] is True
    assert [block["block_id"] for block in result["blocks"]] == [
        "p-0001",
        "p-0002",
        "p-0003",
        "table-0004",
        "p-0005",
    ]
    assert [block["kind"] for block in result["blocks"]] == [
        "heading",
        "paragraph",
        "list_item",
        "table",
        "paragraph",
    ]
    assert result["blocks"][0]["level"] == 1
    assert result["blocks"][1]["locator"] == {
        "block_id": "p-0002",
        "kind": "paragraph",
        "source_index": 2,
        "heading_path": ["Overview"],
    }
    assert result["blocks"][2]["text"] == "First checklist item"
    assert result["blocks"][3]["rows"][1][0] == {
        "text": "苹果",
        "locator": {
            "block_id": "table-0004",
            "kind": "table_cell",
            "source_index": 4,
            "heading_path": ["Overview"],
            "row": 2,
            "column": 1,
        },
    }
    assert result["fidelity_warnings"] == []
    assert any("[DocxAudit]" in message for message in caplog.messages)


def test_extract_blocks_reports_merged_table_ranges(tmp_path: Path):
    path = tmp_path / "merged.docx"
    _write_merged_table_docx(path)

    result = docx_service.extract_blocks(
        "merged.docx",
        root_dir=str(tmp_path),
        allow_roots=[str(tmp_path)],
    )

    assert result["ok"] is True
    assert result["blocks"][0]["merged_cells"] == [
        {
            "start": {"row": 1, "column": 1},
            "end": {"row": 1, "column": 2},
        }
    ]


def test_extract_blocks_reports_unsupported_body_content_as_a_fidelity_warning(tmp_path: Path):
    path = tmp_path / "unsupported.docx"
    document = Document()
    document.add_paragraph("Readable")
    document.element.body.append(OxmlElement("w:altChunk"))
    document.save(path)

    result = docx_service.extract_blocks(
        "unsupported.docx",
        root_dir=str(tmp_path),
        allow_roots=[str(tmp_path)],
    )

    assert result["ok"] is True
    assert result["fidelity_warnings"] == [
        {"code": "UNSUPPORTED_BODY_ELEMENT", "element": "altChunk"}
    ]


def test_extract_blocks_rejects_paths_outside_allowed_roots(tmp_path: Path):
    with pytest.raises(doc_retrieval.DocAccessError):
        docx_service.extract_blocks(
            "/etc/passwd",
            root_dir=str(tmp_path),
            allow_roots=[str(tmp_path)],
        )


def test_extract_blocks_enforces_docx_extension_and_deny_roots(tmp_path: Path, caplog):
    caplog.set_level(logging.INFO)
    (tmp_path / "not-docx.txt").write_text("plain text", encoding="utf-8")

    with pytest.raises(doc_retrieval.DocAccessError, match="File extension is not allowed"):
        docx_service.extract_blocks(
            "not-docx.txt",
            root_dir=str(tmp_path),
            allow_roots=[str(tmp_path)],
        )

    sample_path = tmp_path / "sample.docx"
    _write_sample_docx(sample_path)
    with pytest.raises(doc_retrieval.DocAccessError, match="denied"):
        docx_service.extract_blocks(
            "sample.docx",
            root_dir=str(tmp_path),
            allow_roots=[str(tmp_path)],
            deny_roots=[str(tmp_path)],
        )
    assert any("DOCX_ACCESS_DENIED" in message for message in caplog.messages)


def test_extract_blocks_rejects_ambiguous_relative_paths(tmp_path: Path):
    first_root = tmp_path / "first"
    second_root = tmp_path / "second"
    first_root.mkdir()
    second_root.mkdir()
    _write_sample_docx(first_root / "same.docx")
    _write_sample_docx(second_root / "same.docx")

    with pytest.raises(doc_retrieval.DocAccessError, match="Ambiguous relative path"):
        docx_service.extract_blocks(
            "same.docx",
            allow_roots=[str(first_root), str(second_root)],
        )


def test_extract_blocks_reports_malformed_docx_without_parser_traceback(tmp_path: Path):
    (tmp_path / "broken.docx").write_bytes(b"not a DOCX package")

    result = docx_service.extract_blocks(
        "broken.docx",
        root_dir=str(tmp_path),
        allow_roots=[str(tmp_path)],
    )

    assert result == {
        "ok": False,
        "error_code": "DOCX_PARSE_FAILED",
        "message": "The file is not a readable DOCX package.",
        "fidelity_warnings": [],
    }


def test_extract_blocks_normalizes_malformed_ooxml_xml(tmp_path: Path):
    path = tmp_path / "broken-xml.docx"
    _write_malformed_xml_docx(path)

    result = docx_service.extract_blocks(
        "broken-xml.docx",
        root_dir=str(tmp_path),
        allow_roots=[str(tmp_path)],
    )

    assert result == {
        "ok": False,
        "error_code": "DOCX_PARSE_FAILED",
        "message": "The file is not a readable DOCX package.",
        "fidelity_warnings": [],
    }
