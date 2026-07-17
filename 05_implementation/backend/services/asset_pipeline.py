"""
Asset Intelligence Pipeline for Sage v4.
Handles file upload, type detection, text extraction, and preparation for knowledge extraction.
"""
import os
import mimetypes
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Tuple

class AssetPipeline:
    """Pipeline for processing uploaded assets into extractable knowledge."""
    
    def __init__(self, upload_dir: str = "uploads"):
        self.upload_dir = upload_dir
        os.makedirs(upload_dir, exist_ok=True)
    
    def detect_file_type(self, file_path: str) -> Dict[str, str]:
        """Detect file type using extension, MIME type, and magic numbers.
        
        Returns dict with: asset_type, mime_type, extension
        """
        path = Path(file_path)
        extension = path.suffix.lower()
        
        # MIME type detection
        mime_type, _ = mimetypes.guess_type(file_path)
        mime_type = mime_type or "application/octet-stream"
        
        # Map to internal asset types
        asset_type_map = {
            # Images
            ".png": "image",
            ".jpg": "image",
            ".jpeg": "image",
            ".gif": "image",
            ".webp": "image",
            ".svg": "image",
            # Documents
            ".pdf": "pdf",
            ".docx": "docx",
            ".doc": "docx",
            ".txt": "text",
            ".md": "markdown",
            ".markdown": "markdown",
            # Presentations
            ".pptx": "presentation",
            ".ppt": "presentation",
            # Audio
            ".mp3": "audio",
            ".wav": "audio",
            ".m4a": "audio",
            ".ogg": "audio",
            # Video
            ".mp4": "video",
            ".mov": "video",
            ".avi": "video",
            ".mkv": "video",
            # Code
            ".py": "code",
            ".js": "code",
            ".ts": "code",
            ".jsx": "code",
            ".tsx": "code",
            ".html": "code",
            ".css": "code",
            ".json": "code",
            ".yaml": "code",
            ".yml": "code",
        }
        
        asset_type = asset_type_map.get(extension, "unknown")
        
        # Refine based on MIME type
        if mime_type:
            if mime_type.startswith("image/"):
                asset_type = "image"
            elif mime_type == "application/pdf":
                asset_type = "pdf"
            elif mime_type in ["text/plain", "text/markdown"]:
                asset_type = "text" if extension != ".md" else "markdown"
            elif mime_type.startswith("audio/"):
                asset_type = "audio"
            elif mime_type.startswith("video/"):
                asset_type = "video"
        
        return {
            "asset_type": asset_type,
            "mime_type": mime_type,
            "extension": extension,
            "filename": path.name
        }
    
    def save_upload(self, file_content: bytes, original_filename: str) -> str:
        """Save uploaded file to disk and return file path."""
        file_id = str(uuid.uuid4())
        extension = Path(original_filename).suffix
        safe_name = f"{file_id}{extension}"
        file_path = os.path.join(self.upload_dir, safe_name)
        
        with open(file_path, "wb") as f:
            f.write(file_content)
        
        return file_path
    
    def extract_text(self, file_path: str, asset_type: str) -> Dict[str, any]:
        """Extract text content from file based on type.
        
        Returns dict with: text, chunks, metadata, success, error
        """
        result = {
            "text": "",
            "chunks": [],
            "metadata": {},
            "success": False,
            "error": None
        }
        
        try:
            if asset_type == "pdf":
                result = self._extract_pdf(file_path)
            elif asset_type == "image":
                result = self._extract_image(file_path)
            elif asset_type in ["text", "markdown", "code"]:
                result = self._extract_text_file(file_path)
            elif asset_type == "docx":
                result = self._extract_docx(file_path)
            elif asset_type == "presentation":
                result = self._extract_presentation(file_path)
            elif asset_type == "audio":
                result = self._extract_audio(file_path)
            elif asset_type == "video":
                result = self._extract_video(file_path)
            else:
                result["error"] = f"Unsupported asset type: {asset_type}"
                
        except Exception as e:
            result["error"] = str(e)
        
        # Generate chunks if text was extracted
        if result["text"] and not result["chunks"]:
            result["chunks"] = self._chunk_text(result["text"])
        
        return result
    
    def _extract_pdf(self, file_path: str) -> Dict:
        """Extract text from PDF using pdfplumber."""
        result = {"text": "", "chunks": [], "metadata": {}, "success": False, "error": None}
        
        try:
            import pdfplumber
            
            text_parts = []
            metadata = {}
            
            with pdfplumber.open(file_path) as pdf:
                # Extract metadata
                if pdf.metadata:
                    metadata = {
                        "title": pdf.metadata.get("Title", ""),
                        "author": pdf.metadata.get("Author", ""),
                        "subject": pdf.metadata.get("Subject", ""),
                        "creator": pdf.metadata.get("Creator", ""),
                        "pages": len(pdf.pages)
                    }
                
                # Extract text from each page
                for i, page in enumerate(pdf.pages):
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(f"--- Page {i+1} ---\n{page_text}")
                
                result["text"] = "\n\n".join(text_parts)
                result["metadata"] = metadata
                result["success"] = True
                
        except ImportError:
            result["error"] = "pdfplumber not installed. Run: pip install pdfplumber"
        except Exception as e:
            result["error"] = f"PDF extraction error: {str(e)}"
        
        return result
    
    def _extract_image(self, file_path: str) -> Dict:
        """Extract text from image using OCR."""
        result = {"text": "", "chunks": [], "metadata": {}, "success": False, "error": None}
        
        try:
            from PIL import Image
            import pytesseract
            
            # Open image
            img = Image.open(file_path)
            
            # Extract metadata
            metadata = {
                "format": img.format,
                "size": f"{img.width}x{img.height}",
                "mode": img.mode
            }
            
            # Extract EXIF data if available
            if hasattr(img, '_getexif') and img._getexif():
                exif = img._getexif()
                metadata["exif"] = {str(k): str(v) for k, v in exif.items()}
            
            # OCR
            text = pytesseract.image_to_string(img)
            
            result["text"] = text
            result["metadata"] = metadata
            result["success"] = True
            
        except ImportError:
            result["error"] = "pytesseract or Pillow not installed. Run: pip install pytesseract Pillow"
        except Exception as e:
            result["error"] = f"OCR error: {str(e)}"
        
        return result
    
    def _extract_text_file(self, file_path: str) -> Dict:
        """Extract text from plain text, markdown, or code files."""
        result = {"text": "", "chunks": [], "metadata": {}, "success": False, "error": None}
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
            
            result["text"] = text
            result["metadata"] = {"lines": text.count("\n") + 1}
            result["success"] = True
            
        except UnicodeDecodeError:
            # Try with different encoding
            try:
                with open(file_path, "r", encoding="latin-1") as f:
                    text = f.read()
                result["text"] = text
                result["success"] = True
            except Exception as e:
                result["error"] = f"Text extraction error: {str(e)}"
        except Exception as e:
            result["error"] = f"Text extraction error: {str(e)}"
        
        return result
    
    def _extract_docx(self, file_path: str) -> Dict:
        """Extract text from DOCX files."""
        result = {"text": "", "chunks": [], "metadata": {}, "success": False, "error": None}
        
        try:
            from docx import Document
            
            doc = Document(file_path)
            
            # Extract text from paragraphs
            text_parts = []
            for para in doc.paragraphs:
                if para.text.strip():
                    text_parts.append(para.text)
            
            # Extract text from tables
            for table in doc.tables:
                for row in table.rows:
                    row_text = " | ".join([cell.text for cell in row.cells])
                    if row_text.strip():
                        text_parts.append(row_text)
            
            result["text"] = "\n\n".join(text_parts)
            result["metadata"] = {"paragraphs": len(doc.paragraphs)}
            result["success"] = True
            
        except ImportError:
            result["error"] = "python-docx not installed. Run: pip install python-docx"
        except Exception as e:
            result["error"] = f"DOCX extraction error: {str(e)}"
        
        return result
    
    def _extract_presentation(self, file_path: str) -> Dict:
        """Extract text from presentations (placeholder)."""
        return {
            "text": "",
            "chunks": [],
            "metadata": {},
            "success": False,
            "error": "Presentation extraction not yet implemented. Convert to PDF first."
        }
    
    def _extract_audio(self, file_path: str) -> Dict:
        """Extract text from audio using speech-to-text (placeholder)."""
        return {
            "text": "",
            "chunks": [],
            "metadata": {},
            "success": False,
            "error": "Audio transcription not yet implemented. Requires Whisper or similar model."
        }
    
    def _extract_video(self, file_path: str) -> Dict:
        """Extract text from video (placeholder)."""
        return {
            "text": "",
            "chunks": [],
            "metadata": {},
            "success": False,
            "error": "Video extraction not yet implemented. Requires frame extraction + OCR + speech recognition."
        }
    
    def _chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 100) -> List[str]:
        """Split text into overlapping chunks for processing."""
        if not text:
            return []
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            # Try to break at sentence boundary
            if end < len(text):
                # Look for sentence end within overlap window
                search_start = max(start + chunk_size - overlap, start)
                search_end = min(end + overlap, len(text))
                segment = text[search_start:search_end]
                
                # Find last sentence boundary
                last_period = segment.rfind(". ")
                if last_period > 0:
                    end = search_start + last_period + 1
            
            chunks.append(text[start:end].strip())
            start = end - overlap if end < len(text) else end
        
        return chunks
    
    def extract_metadata(self, file_path: str) -> Dict[str, any]:
        """Extract file metadata (size, creation date, etc.)."""
        stat = os.stat(file_path)
        return {
            "file_size": stat.st_size,
            "file_size_human": self._human_readable_size(stat.st_size),
            "created_at": stat.st_ctime,
            "modified_at": stat.st_mtime
        }
    
    def _human_readable_size(self, size_bytes: int) -> str:
        """Convert bytes to human readable format."""
        for unit in ["B", "KB", "MB", "GB"]:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"
    
    def process_asset(self, file_content: bytes, original_filename: str) -> Dict[str, any]:
        """Full pipeline: save, detect, extract, chunk.
        
        Returns complete processing result.
        """
        # Save file
        file_path = self.save_upload(file_content, original_filename)
        
        # Detect type
        type_info = self.detect_file_type(file_path)
        
        # Special handling for ChatGPT/Claude JSON exports
        if type_info["asset_type"] == "unknown" and type_info["extension"] == ".json":
            try:
                import json
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Detect ChatGPT format
                if "conversations" in data:
                    type_info["asset_type"] = "chatgpt_export"
                elif "chats" in data or "messages" in data:
                    type_info["asset_type"] = "claude_export"
            except:
                pass
        
        # Extract text
        extraction = self.extract_text(file_path, type_info["asset_type"])
        
        # Get metadata
        metadata = self.extract_metadata(file_path)
        metadata.update(type_info)
        metadata.update(extraction.get("metadata", {}))
        
        return {
            "file_path": file_path,
            "type_info": type_info,
            "extraction": extraction,
            "metadata": metadata,
            "success": extraction["success"],
            "error": extraction["error"]
        }
