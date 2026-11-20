import os
from typing import Tuple

try:
    import magic
except ImportError:
    magic = None

ALLOWED_EXTENSIONS = {".pdf", ".docx"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

def validate_file_metadata(filename: str, file_size: int, content: bytes) -> Tuple[bool, str]:
    """Validates file extension, size, and magic bytes/MIME."""
    if file_size > MAX_FILE_SIZE:
        return False, f"File size exceeds limit of 5 MB ({file_size / (1024 * 1024):.2f} MB)."

    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return False, f"Unsupported file extension '{ext}'. Only .pdf and .docx are supported."

    # Inspect magic MIME type if available, fallback to header signature check
    if magic is not None:
        try:
            mime = magic.from_buffer(content, mime=True)
            valid_mimes = {
                "application/pdf",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "application/zip",
                "application/octet-stream"
            }
            if mime not in valid_mimes:
                return False, f"Invalid file MIME type: {mime}"
        except Exception:
            pass

    # Header signature checks
    if ext == ".pdf":
        if not content.startswith(b"%PDF-"):
            return False, "File does not appear to be a valid PDF document."
    elif ext == ".docx":
        # DOCX is a zip file starting with PK\x03\x04
        if not content.startswith(b"PK\x03\x04"):
            return False, "File does not appear to be a valid DOCX document."

    return True, "Valid"
