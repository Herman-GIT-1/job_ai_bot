from database import get_resume, set_resume, CLI_CHAT_ID

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


def save_resume(text: str, chat_id: int) -> None:
    set_resume(chat_id, text)


def load_resume(chat_id: int = CLI_CHAT_ID) -> str:
    text = get_resume(chat_id)
    if text is None:
        raise FileNotFoundError(f"Резюме для chat_id={chat_id} не найдено в БД.")
    return text


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
