import os
import pdfplumber
from langchain.docstore.document import Document
import re

HEADING_PATTERN = re.compile(r"^(\d+(\.\d+)*)\s+.+")
FIGURE_PATTERN = re.compile(r"\b(Figure|Fig\.)\b", re.IGNORECASE)


def _is_heading(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False

    if HEADING_PATTERN.match(stripped):
        return True

    # Heuristic: short all-caps lines are often section titles in papers.
    if len(stripped) <= 80 and stripped.isupper() and len(stripped.split()) <= 10:
        return True

    return False


def _split_sections(page_text: str) -> list[tuple[str, str]]:
    lines = [line.strip() for line in page_text.split("\n")]
    sections: list[tuple[str, str]] = []

    current_title = "body"
    current_lines: list[str] = []

    for line in lines:
        if not line:
            if current_lines and current_lines[-1] != "":
                current_lines.append("")
            continue

        if _is_heading(line):
            if current_lines:
                content = "\n".join(current_lines).strip()
                if content:
                    sections.append((current_title, content))
            current_title = line
            current_lines = []
            continue

        current_lines.append(line)

    if current_lines:
        content = "\n".join(current_lines).strip()
        if content:
            sections.append((current_title, content))

    return sections


def _table_to_text(table: list[list[str | None]]) -> str:
    cleaned_rows: list[list[str]] = []
    for row in table:
        cleaned = [str(cell).strip() if cell is not None else "" for cell in row]
        if any(cleaned):
            cleaned_rows.append(cleaned)

    if not cleaned_rows:
        return ""

    # Render as simple pipe-delimited table text for better retrieval.
    return "\n".join(" | ".join(cells) for cells in cleaned_rows)


def extract_pdf_content(pdf_path: str) -> list[Document]:
    """Extract structured LangChain documents from text, tables, and figure captions."""
    source_name = os.path.basename(pdf_path)
    extracted_docs: list[Document] = []

    with pdfplumber.open(pdf_path) as pdf:
        for page_index, page in enumerate(pdf.pages, start=1):
            page_text = page.extract_text() or ""

            if page_text.strip():
                for section_name, section_text in _split_sections(page_text):
                    extracted_docs.append(
                        Document(
                            page_content=section_text,
                            metadata={
                                "source": source_name,
                                "source_path": pdf_path,
                                "page": page_index,
                                "content_type": "section",
                                "section": section_name,
                            },
                        )
                    )

                figure_idx = 0
                for line in page_text.split("\n"):
                    caption = line.strip()
                    if FIGURE_PATTERN.search(caption):
                        figure_idx += 1
                        extracted_docs.append(
                            Document(
                                page_content=caption,
                                metadata={
                                    "source": source_name,
                                    "source_path": pdf_path,
                                    "page": page_index,
                                    "content_type": "figure_caption",
                                    "figure_index": figure_idx,
                                },
                            )
                        )

            table_idx = 0
            for table in page.extract_tables() or []:
                table_text = _table_to_text(table)
                if not table_text:
                    continue

                table_idx += 1
                extracted_docs.append(
                    Document(
                        page_content=table_text,
                        metadata={
                            "source": source_name,
                            "source_path": pdf_path,
                            "page": page_index,
                            "content_type": "table",
                            "table_index": table_idx,
                        },
                    )
                )

    return extracted_docs


def load_all_pdfs(pdf_folder: str) -> list[Document]:
    """
    Loads all PDFs in a folder and returns a list of Document objects.
    """
    documents = []
    for file in os.listdir(pdf_folder):
        if file.lower().endswith(".pdf"):
            full_path = os.path.join(pdf_folder, file)
            try:
                docs = extract_pdf_content(full_path)
                documents.extend(docs)
            except Exception as e:
                print(f"Error processing {file}: {e}")
    return documents