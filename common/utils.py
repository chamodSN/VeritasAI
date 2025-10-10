import os
from pdfminer.high_level import extract_text
from docx import Document
from common.config import Config


def load_document(file_path: str) -> str:
    """Load text from PDF or DOCX files."""
    ext = os.path.splitext(file_path)[1].lower()
    if ext == '.pdf':
        return extract_text(file_path)
    elif ext == '.docx':
        doc = Document(file_path)
        return '\n'.join([para.text for para in doc.paragraphs])
    else:
        raise ValueError("Unsupported file format")


def get_all_documents() -> list:
    """Get list of all documents in data path."""
    return [os.path.join(Config.DATA_PATH, f) for f in os.listdir(Config.DATA_PATH) if f.endswith(('.pdf', '.docx'))]
