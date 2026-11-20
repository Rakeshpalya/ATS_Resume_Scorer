import io
import re
from typing import Tuple, List, Optional
import pdfplumber
import pypdf
try:
    import docx
except ImportError:
    docx = None

from backend.utils.file_utils import validate_file_metadata

def extract_hyperlinks_from_pypdf(reader: pypdf.PdfReader) -> List[str]:
    """Extracts URIs from PDF page annotations (/Annots -> /Subtype /Link)."""
    links: List[str] = []
    try:
        for page in reader.pages:
            if "/Annots" in page:
                annots = page["/Annots"]
                if annots:
                    for annot_ref in annots:
                        try:
                            annot = annot_ref.get_object() if hasattr(annot_ref, "get_object") else annot_ref
                            if annot and annot.get("/Subtype") == "/Link":
                                action = annot.get("/A")
                                if action and hasattr(action, "get_object"):
                                    action = action.get_object()
                                if action and action.get("/S") == "/URI":
                                    uri = action.get("/URI")
                                    if uri and str(uri) not in links:
                                        links.append(str(uri))
                        except Exception:
                            continue
    except Exception:
        pass
    return links

def parse_pdf_bytes(content: bytes) -> str:
    """Parses PDF content using pdfplumber with PyPDF2 fallback and link extraction."""
    extracted_text = ""
    # 1. Primary extractor: pdfplumber
    try:
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            pages_text = []
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    pages_text.append(text)
            if pages_text:
                extracted_text = "\n\n".join(pages_text).strip()
    except Exception:
        extracted_text = ""

    # 2. Fallback to pypdf / PyPDF2 if pdfplumber yields empty text
    reader: Optional[pypdf.PdfReader] = None
    try:
        reader = pypdf.PdfReader(io.BytesIO(content))
        if not extracted_text:
            pages_text = []
            for page in reader.pages:
                txt = page.extract_text()
                if txt:
                    pages_text.append(txt)
            extracted_text = "\n\n".join(pages_text).strip()
    except Exception:
        pass

    # 3. Extract embedded hyperlinks (e.g. LinkedIn, GitHub badges)
    if reader is not None:
        links = extract_hyperlinks_from_pypdf(reader)
        if links:
            extracted_text += "\n\n[Extracted Links]:\n" + "\n".join(links)

    return extracted_text.strip()

def parse_docx_bytes(content: bytes) -> str:
    """Parses DOCX content extracting all paragraphs and table contents."""
    if docx is None:
        raise RuntimeError("python-docx is not installed.")

    doc = docx.Document(io.BytesIO(content))
    paragraphs: List[str] = []

    # Paragraphs
    for p in doc.paragraphs:
        txt = p.text.strip()
        if txt:
            paragraphs.append(txt)

    # Tables
    for table in doc.tables:
        for row in table.rows:
            row_cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if row_cells:
                paragraphs.append(" | ".join(row_cells))

    return "\n\n".join(paragraphs).strip()

def parse_resume_file(filename: str, content: bytes) -> Tuple[str, str]:
    """Validates and extracts raw text from a PDF or DOCX resume file."""
    valid, msg = validate_file_metadata(filename, len(content), content)
    if not valid:
        raise ValueError(msg)

    ext = filename.lower()
    if ext.endswith(".pdf"):
        raw_text = parse_pdf_bytes(content)
    elif ext.endswith(".docx"):
        raw_text = parse_docx_bytes(content)
    else:
        raise ValueError(f"Unsupported file format for {filename}")

    if not raw_text.strip():
        raise ValueError("Could not extract any readable text from the uploaded file.")

    return raw_text, ext
