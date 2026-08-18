"""
Agent: pdf_ocr_agent
--------------------
The Archivist Agent (PDFs). Processes complex PDFs, scanned documents, and extracts text.
Implements safety logic to search massive PDFs without blowing out the context window.
"""

import os
import json

try:
    import pypdf
except ImportError:
    pypdf = None

try:
    import PyPDF2
except ImportError:
    PyPDF2 = None

def _get_pdf_reader(file_obj):
    if pypdf is not None:
        return pypdf.PdfReader(file_obj)
    if PyPDF2 is not None:
        return PyPDF2.PdfReader(file_obj)
    raise ImportError("No PDF reader installed. Run: pip install pypdf")

DESCRIPTION = (
    "The Archivist Agent for Documents. Use this to extract text from PDFs or run OCR on scanned documents. "
    "Crucially, it can search massive 500-page PDFs for specific keywords so you don't have to read the whole file."
)

PARAMETERS = {
    "action": {
        "type": "string",
        "required": True,
        "description": "Must be one of: 'extract_text', 'search_pdf', 'run_ocr'.",
    },
    "file_path": {
        "type": "string",
        "required": True,
        "description": "The absolute path to the PDF or image file.",
    },
    "keyword": {
        "type": "string",
        "required": False,
        "description": "The keyword to search for (required for search_pdf).",
    },
    "page_num": {
        "type": "integer",
        "required": False,
        "description": "Specific page number to extract (1-indexed). Defaults to first 5 pages if omitted in extract_text.",
    }
}

def pdf_ocr_agent(
    action: str, 
    file_path: str, 
    keyword: str = "", 
    page_num: int = 0
) -> dict:
    """Processes PDF documents."""
    action = action.lower().strip()
    
    if not os.path.exists(file_path):
        return {"error": f"File not found at {file_path}"}
        
    if pypdf is None and PyPDF2 is None and action in ["extract_text", "search_pdf"]:
        return {"error": "pypdf is not installed. Please run `pip install pypdf` to use PDF features."}

    if action == "extract_text":
        try:
            with open(file_path, "rb") as f:
                reader = _get_pdf_reader(f)
                total_pages = len(reader.pages)
                
                text = ""
                if page_num > 0:
                    if page_num > total_pages:
                        return {"error": f"Page {page_num} out of bounds. Document only has {total_pages} pages."}
                    text = reader.pages[page_num - 1].extract_text() or ""
                else:
                    # EDGE CASE: Don't extract a 500 page book at once.
                    max_pages = min(total_pages, 5)
                    for i in range(max_pages):
                        page_text = reader.pages[i].extract_text()
                        if page_text:
                            text += f"\n--- Page {i+1} ---\n{page_text}"
                            
                return {
                    "success": True, 
                    "total_pages": total_pages,
                    "extracted_text": text,
                    "warning": "Only first 5 pages extracted to save context. Use 'search_pdf' for massive docs." if page_num == 0 and total_pages > 5 else None
                }
        except Exception as e:
            return {"error": f"Failed to extract PDF text: {str(e)}"}
            
    elif action == "search_pdf":
        if not keyword:
            return {"error": "search_pdf requires a 'keyword'."}
            
        try:
            with open(file_path, "rb") as f:
                reader = _get_pdf_reader(f)
                total_pages = len(reader.pages)
                
                matches = []
                for i in range(total_pages):
                    text = reader.pages[i].extract_text()
                    if text and keyword.lower() in text.lower():
                        idx = text.lower().find(keyword.lower())
                        start = max(0, idx - 100)
                        end = min(len(text), idx + 100)
                        snippet = text[start:end].replace('\n', ' ')
                        matches.append({"page": i + 1, "snippet": f"...{snippet}..."})
                        
                if not matches:
                    return {"success": True, "message": f"Keyword '{keyword}' not found in PDF."}
                    
                return {
                    "success": True,
                    "total_matches": len(matches),
                    "matches": matches[:10]
                }
        except Exception as e:
            return {"error": f"Failed to search PDF: {str(e)}"}
            
    elif action == "run_ocr":
        # In a real system, this would call Tesseract or transfer to the Vision Agent.
        return {
            "success": True, 
            "message": "OCR simulation complete. (In production, this routes to vision_agent or tesseract).",
            "instruction": f"If this is an image, consider transferring to 'vision_agent' with path {file_path}"
        }
        
    else:
        return {"error": "Invalid action. Use 'extract_text', 'search_pdf', or 'run_ocr'."}
