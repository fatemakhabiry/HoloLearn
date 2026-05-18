"""
PDF Extractor for HoloLearn
Extracts text content from PDF files.
"""

from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from collections import Counter
import json
import time
import re

import sys
sys.path.append(str(Path(__file__).parent.parent))
from utils.configs import OUTPUT_DIR, LOGS_DIR, MAX_PDF_SIZE
from utils.error_handler import ErrorHandler
from utils.text_cleaner import TextCleaner

try:
    import fitz  # PyMuPDF
    _FITZ_AVAILABLE = True
except ImportError:
    _FITZ_AVAILABLE = False


class PDFExtractor:
    """Extract text from PDF files"""

    def __init__(self):
        if not _FITZ_AVAILABLE:
            raise ImportError(
                "PyMuPDF not installed. Install with: pip install PyMuPDF"
            )

        self.text_cleaner = TextCleaner()
        self.base_output_dir = OUTPUT_DIR
        self.base_logs_dir = LOGS_DIR

        self.base_output_dir.mkdir(parents=True, exist_ok=True)
        self.base_logs_dir.mkdir(parents=True, exist_ok=True)

    def _create_resource_name(self, filename: str) -> str:
        name = Path(filename).stem
        name = name.lower()
        name = re.sub(r'[^\w\s-]', '', name)
        name = re.sub(r'[-\s]+', '_', name)
        name = name.strip('_')
        if len(name) > 50:
            name = name[:50]
        return name or "unnamed_resource"

    def _setup_resource_directories(self, resource_name: str, output_dir_override: Optional[Path] = None) -> tuple:
        if output_dir_override:
            resource_output_dir = Path(output_dir_override)
        else:
            resource_output_dir = self.base_output_dir / resource_name

        resource_logs_dir = self.base_logs_dir / resource_name
        resource_output_dir.mkdir(parents=True, exist_ok=True)
        resource_logs_dir.mkdir(parents=True, exist_ok=True)
        return resource_output_dir, resource_logs_dir

    # ------------------------------------------------------------------ #
    #  Structured extraction helpers                                       #
    # ------------------------------------------------------------------ #

    def _build_sections_from_blocks(self, doc) -> Tuple[List[dict], List[dict]]:
        """
        Detect headings via font-size analysis and group body text into sections.
        Returns (sections, outline).
        """
        all_lines = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            blocks = page.get_text("dict")["blocks"]
            for block in blocks:
                if block.get("type") != 0:
                    continue
                for line in block.get("lines", []):
                    line_text = ""
                    max_size = 0.0
                    is_bold = False
                    for span in line.get("spans", []):
                        line_text += span.get("text", "")
                        size = span.get("size", 12.0)
                        if size > max_size:
                            max_size = size
                        if span.get("flags", 0) & 16:
                            is_bold = True
                    line_text = line_text.strip()
                    if line_text:
                        all_lines.append({
                            "page": page_num + 1,
                            "text": line_text,
                            "size": max_size,
                            "is_bold": is_bold,
                        })

        if not all_lines:
            return [], []

        # Most common (rounded) font size = body size
        body_size = Counter(round(l["size"]) for l in all_lines).most_common(1)[0][0]

        sections: List[dict] = []
        outline: List[dict] = []
        current_title = ""
        current_body: List[str] = []
        current_page = 1

        def _flush(title, body, page):
            if body:
                sections.append({
                    "title": title,
                    "body": " ".join(body),
                    "type": "body" if not title else "section",
                    "source_location": {"page": page},
                })

        for line in all_lines:
            size = line["size"]
            text = line["text"]
            # Headings: notably larger than body, or bold+slightly larger, and short
            is_heading = (
                (size > body_size * 1.15 or (line["is_bold"] and size >= body_size * 1.05))
                and len(text) < 200
            )

            if is_heading:
                _flush(current_title, current_body, current_page)
                current_body = []
                current_title = text
                current_page = line["page"]

                if size > body_size * 1.4:
                    level = 1
                elif size > body_size * 1.2:
                    level = 2
                else:
                    level = 3
                outline.append({"level": level, "title": text, "page": line["page"]})
            else:
                current_body.append(text)

        _flush(current_title, current_body, current_page)
        return sections, outline

    def _extract_tables_structured(self, doc) -> List[dict]:
        """
        Extract tables as structured JSON arrays (requires PyMuPDF ≥ 1.23).
        Falls back gracefully on older versions.
        """
        tables = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            try:
                page_tables = page.find_tables()
                for t in page_tables:
                    data = t.extract()
                    if data:
                        tables.append({"page": page_num + 1, "rows": data})
            except AttributeError:
                # find_tables() not available in this PyMuPDF version
                break
            except Exception:
                pass
        return tables

    def _extract_figure_refs(self, text: str) -> List[str]:
        """Detect figure/table captions and cross-references in extracted text."""
        pattern = (
            r'(?:Figure|Fig\.|Table|Chart|Diagram|Appendix)\s+'
            r'[\dA-Z][\w.]*[.:]\s*[^\n]+'
        )
        return list(dict.fromkeys(  # preserve order, deduplicate
            m.strip() for m in re.findall(pattern, text, re.IGNORECASE)
        ))

    def _compute_quality_score(self, text: str, sections: List[dict]) -> float:
        """Return a 0–1 score reflecting content richness for lecture generation."""
        word_score = min(len(text.split()) / 5000, 1.0)
        structure_score = min(len(sections) / 10, 1.0)
        return round(word_score * 0.6 + structure_score * 0.4, 2)

    # ------------------------------------------------------------------ #
    #  Main extraction                                                     #
    # ------------------------------------------------------------------ #

    def extract(self,
                pdf_path: str,
                resource_id: Optional[str] = None,
                clean_text: bool = True,
                password: Optional[str] = None,
                output_dir: Optional[str] = None) -> Dict[str, Any]:
        """
        Extract text from a PDF file.

        Returns dict with: success, resource_name, resource_id, text_file,
        metadata_file, structured_file, output_dir, logs_dir, extracted_text,
        sections, outline, tables, figure_refs, content_quality_score, metadata.
        """
        start_time = time.time()
        pdf_path = Path(pdf_path)

        resource_name = self._create_resource_name(pdf_path.name)
        override = Path(output_dir) if output_dir else None
        output_dir, logs_dir = self._setup_resource_directories(resource_name, output_dir_override=override)

        error_handler = ErrorHandler(f"pdf_{resource_name}")
        error_handler.log_file = logs_dir / "extraction.log"
        error_handler.logger = error_handler._setup_logger()

        if not pdf_path.exists():
            error_msg = f"PDF file not found: {pdf_path}"
            error_handler.log_error(FileNotFoundError(error_msg), context="Validating PDF file",
                                    metadata={"path": str(pdf_path)})
            return self._create_error_result(resource_name, error_msg, output_dir, pdf_path.name)

        file_size = pdf_path.stat().st_size
        file_size_mb = file_size / (1024 * 1024)

        if file_size_mb > MAX_PDF_SIZE:
            error_msg = f"PDF too large: {file_size_mb:.2f}MB (max: {MAX_PDF_SIZE}MB)"
            error_handler.log_error(ValueError(error_msg), context="Checking PDF size",
                                    metadata={"size_mb": file_size_mb, "max_mb": MAX_PDF_SIZE})
            return self._create_error_result(resource_name, error_msg, output_dir, pdf_path.name, file_size)

        error_handler.log_info(f"Starting PDF extraction: {pdf_path.name}",
                               metadata={"size_mb": f"{file_size_mb:.2f}",
                                         "resource_name": resource_name,
                                         "output_dir": str(output_dir)})

        try:
            doc = fitz.open(pdf_path)

            if doc.is_encrypted:
                if password:
                    if not doc.authenticate(password):
                        raise ValueError("Invalid password for encrypted PDF")
                else:
                    raise ValueError("PDF is encrypted but no password provided")

            # --- flat text (backwards compatible) ---
            extracted_text = ""
            page_count = len(doc)

            for page_num in range(page_count):
                page = doc[page_num]
                page_text = page.get_text()
                if page_text.strip():
                    extracted_text += f"\n--- Page {page_num + 1} ---\n"
                    extracted_text += page_text + "\n"

            # --- structured analysis ---
            sections, outline = self._build_sections_from_blocks(doc)
            tables = self._extract_tables_structured(doc)

            doc.close()

            if clean_text:
                extracted_text = self.text_cleaner.clean_text(
                    extracted_text, remove_urls=False, remove_emails=False, fix_spacing=True
                )
            extracted_text = self.text_cleaner.remove_duplicate_lines(extracted_text)

            figure_refs = self._extract_figure_refs(extracted_text)
            quality_score = self._compute_quality_score(extracted_text, sections)

            processing_time = time.time() - start_time

            metadata = {
                "resource_name": resource_name,
                "resource_id": resource_id or resource_name,
                "filename": pdf_path.name,
                "source_type": "pdf",
                "upload_date": datetime.now().isoformat(),
                "extraction_timestamp": datetime.now().isoformat(),
                "file_size_bytes": file_size,
                "processing_time_seconds": round(processing_time, 2),
                "status": "success",
                "error_message": None,
                "page_count": page_count,
                "character_count": len(extracted_text),
                "section_count": len(sections),
                "table_count": len(tables),
                "figure_ref_count": len(figure_refs),
                "content_quality_score": quality_score,
                "is_encrypted": False,
            }

            # Save flat text
            text_file = output_dir / f"{resource_name}_text.txt"
            text_file.write_text(extracted_text, encoding='utf-8')
            metadata["extracted_text_path"] = str(text_file)

            # Save metadata
            metadata_file = output_dir / f"{resource_name}_metadata.json"
            metadata_file.write_text(json.dumps(metadata, indent=2), encoding='utf-8')

            # Save structured data (sections, outline, tables, figure_refs)
            structured = {
                "sections": sections,
                "outline": outline,
                "tables": tables,
                "figure_refs": figure_refs,
            }
            structured_file = output_dir / f"{resource_name}_structured.json"
            structured_file.write_text(json.dumps(structured, indent=2, ensure_ascii=False), encoding='utf-8')

            error_handler.log_success(f"PDF extracted successfully: {pdf_path.name}",
                                      metadata={"pages": page_count, "sections": len(sections),
                                                "tables": len(tables), "time": f"{processing_time:.2f}s"})

            return {
                "success": True,
                "resource_name": resource_name,
                "resource_id": resource_id or resource_name,
                "text_file": str(text_file),
                "metadata_file": str(metadata_file),
                "structured_file": str(structured_file),
                "output_dir": str(output_dir),
                "logs_dir": str(logs_dir),
                "extracted_text": extracted_text,
                "sections": sections,
                "outline": outline,
                "tables": tables,
                "figure_refs": figure_refs,
                "content_quality_score": quality_score,
                "metadata": metadata,
            }

        except Exception as e:
            processing_time = time.time() - start_time
            error_handler.log_error(e, context=f"Extracting PDF: {pdf_path.name}",
                                    metadata={"resource_name": resource_name})
            return self._create_error_result(resource_name, str(e), output_dir,
                                             pdf_path.name, file_size, processing_time)

    def _create_error_result(self,
                             resource_name: str,
                             error_message: str,
                             output_dir: Path,
                             filename: str = "unknown",
                             file_size: int = 0,
                             processing_time: float = 0) -> Dict[str, Any]:
        metadata = {
            "resource_name": resource_name,
            "filename": filename,
            "source_type": "pdf",
            "upload_date": datetime.now().isoformat(),
            "extraction_timestamp": datetime.now().isoformat(),
            "file_size_bytes": file_size,
            "processing_time_seconds": round(processing_time, 2),
            "status": "failed",
            "error_message": error_message,
        }
        metadata_file = output_dir / "metadata.json"
        metadata_file.write_text(json.dumps(metadata, indent=2), encoding='utf-8')
        return {
            "success": False,
            "resource_name": resource_name,
            "text_file": None,
            "metadata_file": str(metadata_file),
            "structured_file": None,
            "output_dir": str(output_dir),
            "extracted_text": "",
            "sections": [],
            "outline": [],
            "tables": [],
            "figure_refs": [],
            "content_quality_score": 0.0,
            "metadata": metadata,
            "error": error_message,
        }

    def extract_metadata_only(self, pdf_path: str) -> Dict[str, Any]:
        """Extract only metadata without extracting text — useful for quick file info."""
        try:
            pdf_path = Path(pdf_path)
            doc = fitz.open(pdf_path)
            metadata = {
                "filename": pdf_path.name,
                "resource_name": self._create_resource_name(pdf_path.name),
                "page_count": len(doc),
                "is_encrypted": doc.is_encrypted,
                "file_size_bytes": pdf_path.stat().st_size,
                "file_size_mb": round(pdf_path.stat().st_size / (1024 * 1024), 2),
                "pdf_metadata": doc.metadata,
            }
            doc.close()
            return metadata
        except Exception as e:
            error_handler = ErrorHandler("pdf_metadata")
            error_handler.log_error(e, context=f"Extracting metadata from {pdf_path}")
            return {}


# Example usage and testing
if __name__ == "__main__":
    from utils.file_picker import FilePicker

    print("=== Testing PDF Extractor ===\n")

    extractor = PDFExtractor()

    picker = FilePicker()
    print("Please select a PDF file...")
    test_pdf = picker.pick_pdf()
    picker.close()

    if test_pdf:
        print(f"\n✓ Selected: {Path(test_pdf).name}\n")

        print("1. Extracting metadata only...")
        metadata = extractor.extract_metadata_only(test_pdf)
        print(f"   Resource name: {metadata.get('resource_name', 'N/A')}")
        print(f"   Pages: {metadata.get('page_count', 'N/A')}")
        print(f"   Size: {metadata.get('file_size_mb', 'N/A')} MB")
        print(f"   Encrypted: {metadata.get('is_encrypted', 'N/A')}\n")

        print("2. Full extraction...")
        result = extractor.extract(pdf_path=test_pdf, clean_text=True)

        if result['success']:
            print(f"   ✓ Success!")
            print(f"   Resource name: {result['resource_name']}")
            print(f"   Output directory: {result['output_dir']}")
            print(f"   Text file: {result['text_file']}")
            print(f"   Structured file: {result['structured_file']}")
            print(f"   Pages: {result['metadata']['page_count']}")
            print(f"   Sections detected: {len(result['sections'])}")
            print(f"   Outline entries: {len(result['outline'])}")
            print(f"   Tables detected: {len(result['tables'])}")
            print(f"   Figure refs: {len(result['figure_refs'])}")
            print(f"   Quality score: {result['content_quality_score']}")
            print(f"   Processing time: {result['metadata']['processing_time_seconds']}s")

            if result['outline']:
                print(f"\n   Outline (first 5 entries):")
                for entry in result['outline'][:5]:
                    indent = "  " * (entry['level'] - 1)
                    print(f"   {indent}H{entry['level']}: {entry['title']} (p.{entry['page']})")
        else:
            print(f"   ✗ Failed: {result['error']}")
    else:
        print("❌ No file selected")
        print("   The extractor is ready to use!")
