import os

RESUME_PATH = os.path.join(os.path.dirname(__file__), "resume.txt")
MIN_LENGTH = 100


def parse_resume(file_bytes: bytes, filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower()
    if ext == "txt":
        return _parse_txt(file_bytes)
    if ext == "pdf":
        return _parse_pdf(file_bytes)
    if ext == "docx":
        return _parse_docx(file_bytes)
    raise ValueError(f"Неподдерживаемый формат: .{ext}. Используй TXT, PDF или DOCX.")


def save_resume(text: str) -> None:
    with open(RESUME_PATH, "w", encoding="utf-8") as f:
        f.write(text)


def load_resume() -> str:
    with open(RESUME_PATH, encoding="utf-8") as f:
        return f.read()


def validate(text: str) -> None:
    if len(text.strip()) < MIN_LENGTH:
        raise ValueError(f"Резюме слишком короткое (минимум {MIN_LENGTH} символов).")


def _parse_txt(data: bytes) -> str:
    return data.decode("utf-8", errors="replace")


def _parse_pdf(data: bytes) -> str:
    try:
        import pypdf
    except ImportError:
        raise ImportError("Установи pypdf: pip install pypdf")
    import io
    reader = pypdf.PdfReader(io.BytesIO(data))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages)


def _parse_docx(data: bytes) -> str:
    try:
        import docx
    except ImportError:
        raise ImportError("Установи python-docx: pip install python-docx")
    import io
    doc = docx.Document(io.BytesIO(data))
    return "\n".join(p.text for p in doc.paragraphs)
