try:
    import magic
except Exception:
    magic = None
import PyPDF2
from docx import Document as DocxDocument
from io import BytesIO
from typing import Tuple


def detect_file_type(content: bytes, filename: str) -> str:
    """
    Detect file type using python-magic and filename extension.
    """
    if magic is not None:
        try:
            mime_type = magic.from_buffer(content, mime=True)
            
            if mime_type == "application/pdf":
                return "pdf"
            elif mime_type in ["application/vnd.openxmlformats-officedocument.wordprocessingml.document", 
                              "application/msword"]:
                return "docx"
            elif mime_type.startswith("text/"):
                return "txt"
        except Exception:
            pass

    # Fallback to filename extension
    ext = filename.lower()
    if ext.endswith('.pdf'):
        return "pdf"
    elif ext.endswith(('.docx', '.doc')):
        return "docx"
    elif ext.endswith(('.txt', '.md', '.markdown')):
        return "txt"
    else:
        return "unknown"


def extract_text_from_pdf(content: bytes) -> Tuple[str, bool]:
    """
    Extract text from PDF content.
    Returns (text, success)
    """
    try:
        pdf_file = BytesIO(content)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        
        text = "\n".join(page.extract_text() or "" for page in pdf_reader.pages)
        
        return text.strip(), True
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        return "", False


def extract_pages_from_pdf(content: bytes) -> Tuple[list[str], bool]:
    """Extract PDF text as one string per page so page metadata is retained."""
    try:
        pdf_reader = PyPDF2.PdfReader(BytesIO(content))
        return [page.extract_text() or "" for page in pdf_reader.pages], True
    except Exception as e:
        print(f"Error extracting PDF pages: {e}")
        return [], False


def extract_document_pages(content: bytes, filename: str) -> Tuple[list[tuple[int | None, str]], bool, str]:
    """Return page-numbered text for PDFs and one logical page for other formats."""
    file_type = detect_file_type(content, filename)
    if file_type == "pdf":
        pages, success = extract_pages_from_pdf(content)
        return [(index + 1, text) for index, text in enumerate(pages)], success, file_type

    text, success, file_type = process_document(content, filename)
    return [(None, text)] if success else [], success, file_type


def extract_text_from_docx(content: bytes) -> Tuple[str, bool]:
    """
    Extract text from DOCX content.
    Returns (text, success)
    """
    try:
        docx_file = BytesIO(content)
        doc = DocxDocument(docx_file)
        
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        
        return text.strip(), True
    except Exception as e:
        print(f"Error extracting text from DOCX: {e}")
        return "", False


def extract_text_from_txt(content: bytes) -> Tuple[str, bool]:
    """
    Extract text from plain text content.
    Returns (text, success)
    """
    try:
        text = content.decode('utf-8')
        return text, True
    except UnicodeDecodeError:
        encodings = ['latin-1', 'cp1252', 'iso-8859-1']
        for encoding in encodings:
            try:
                text = content.decode(encoding)
                return text, True
            except Exception:
                continue
        return "", False


def process_document(content: bytes, filename: str) -> Tuple[str, bool, str]:
    """
    Process document content and extract text.
    Returns (text, success, file_type)
    """
    file_type = detect_file_type(content, filename)
    
    if file_type == "pdf":
        text, success = extract_text_from_pdf(content)
    elif file_type == "docx":
        text, success = extract_text_from_docx(content)
    elif file_type == "txt":
        text, success = extract_text_from_txt(content)
    else:
        return "", False, file_type
    
    return text, success, file_type