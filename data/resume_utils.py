
import fitz  # PyMuPDF

def extract_resume_text(path: str) -> str:
    """Extract all text from the PDF at `path`."""
    text_pages = []
    with fitz.open(path) as doc:
        for page in doc:
            text_pages.append(page.get_text())
    return "\n".join(text_pages)

