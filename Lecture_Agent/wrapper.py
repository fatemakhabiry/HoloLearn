from generators.quiz_generator import QuizGenerator
from generators.script_generator import HologramScriptGenerator
from generators.summary_generator import SummaryGenerator
from generators.worksheet_generator import WorksheetGenerator
from generators.knowledge_graph.kg_generator import generate as kg_generate
from generators.Lecture_Generator.Lecture_api import generate_lecture as lecture_api_generate
import os
from pathlib import Path
from typing import List, Optional, Dict


class SimpleExtractorWrapper:
    """
    Simple wrapper for extractors.
    Returns ONLY extracted text as a string.
    """

    def __init__(self):
        print("Extractor wrapper initialized")

    def extract_pdf(self, file_path: str) -> str:
        """Extract text from PDF"""
        try:
            from extractors.pdf_extractor import PDFExtractor
            extractor = PDFExtractor()
            result = extractor.extract(file_path)
            if result["success"]:
                return result.get("extracted_text", "")
            
            print(f"PDF extraction failed: {result.get('error', 'Unknown error')}")
            return ""
        except Exception as e:
            print(f"PDF extraction failed: {e}")
            return ""

    def extract_docx(self, file_path: str) -> str:
        """Extract text from DOCX"""
        try:
            from extractors.docx_extractor import DOCXExtractor
            extractor = DOCXExtractor()
            result = extractor.extract(file_path)
            if result["success"]:
                return result.get("extracted_text", "")
            print(f"DOCX extraction failed: {result.get('error', 'Unknown error')}")
            return ""
        except Exception as e:
            print(f"DOCX extraction failed: {e}")
            return ""

    def extract_pptx(self, file_path: str) -> str:
        """Extract text from PowerPoint"""
        try:
            from extractors.pptx_extractor import PPTXExtractor
            extractor = PPTXExtractor()
            result = extractor.extract(file_path)
            if result["success"]:
                return result.get("extracted_text", "")
            print(f"PPTX extraction failed: {result.get('error', 'Unknown error')}")
            return ""
        except Exception as e:
            print(f"PPTX extraction failed: {e}")
            return ""

    def extract_audio(self, file_path: str) -> str:
        """Extract transcript from audio"""
        try:
            from extractors.audio_extractor import AudioExtractor
            extractor = AudioExtractor()
            result = extractor.extract(file_path)
            if result["success"]:
                return result.get("extracted_text", "")
            print(f"Audio extraction failed: {result.get('error', 'Unknown error')}")
            return ""
        except Exception as e:
            print(f"Audio extraction failed: {e}")
            return ""

    def extract_video(self, file_path: str) -> str:
        """Extract transcript from video (audio + OCR)"""
        try:
            from extractors.video_extractor import VideoExtractor
            extractor = VideoExtractor()
            result = extractor.extract(file_path)
            if result["success"]:
                return result.get("clean_transcript", "") or result.get("extracted_text", "")
            print(f"Video extraction failed: {result.get('error', 'Unknown error')}")
            return ""
        except Exception as e:
            print(f"Video extraction failed: {e}")
            return ""

    def extract_url(self, url: str) -> str:
        """Extract text from URL"""
        try:
            from extractors.url_extractor import URLExtractor
            extractor = URLExtractor()
            result = extractor.extract(url)
            if result["success"]:
                return result.get("extracted_text", "")
            print(f"URL extraction failed: {result.get('error', 'Unknown error')}")
            return ""
        except Exception as e:
            print(f"URL extraction failed: {e}")
            return ""

    def extract_auto(self, file_path: str) -> str:
        """Auto-detect file type and extract text"""
        ext = Path(file_path).suffix.lower()

        extractors = {
            ".pdf": self.extract_pdf,
            ".docx": self.extract_docx,
            ".doc": self.extract_docx,
            ".pptx": self.extract_pptx,
            ".ppt": self.extract_pptx,
            ".mp3": self.extract_audio,
            ".wav": self.extract_audio,
            ".m4a": self.extract_audio,
            ".flac": self.extract_audio,
            ".ogg": self.extract_audio,
            ".aac": self.extract_audio,
            ".mp4": self.extract_video,
            ".avi": self.extract_video,
            ".mov": self.extract_video,
            ".mkv": self.extract_video,
            ".flv": self.extract_video,
            ".wmv": self.extract_video,
        }

        handler = extractors.get(ext)
        if handler:
            return handler(file_path)

        # Try as URL if no extension match
        if file_path.startswith(("http://", "https://", "www.")):
            return self.extract_url(file_path)

        print(f"Unsupported file type: {ext}")
        return ""


class SimpleGeneratorWrapper:

    def __init__(self):
        pass
   
    # ============================================
    # LECTURE API
    # ============================================
 
    def generate_lecture_api(
        self,
        lecture_topic: str,
        output_dir: Path,
        course_code: str = "",
        openrouter_api_key: Optional[str] = None,
        # text-based source pairs
        pdf_path: Optional[str] = None,
        pdf_query: Optional[str] = None,
        docx_path: Optional[str] = None,
        docx_query: Optional[str] = None,
        pptx_path: Optional[str] = None,
        pptx_query: Optional[str] = None,
        txt_path: Optional[str] = None,
        txt_query: Optional[str] = None,
        url_path: Optional[str] = None,
        url_query: Optional[str] = None,
        # images: flat list [path1, caption1, path2, caption2, ...]
        images: Optional[List[str]] = None,
    ) -> Dict[str, Optional[str]]:
        """
        Generate a lecture PDF, TXT, and JSON using the OpenRouter-based Lecture_api.
 
        Returns:
            {"pdf": "path", "txt": "path", "json": "path"}
        """
        print(f"\nGenerating lecture (Lecture API): {lecture_topic}")
 
        try:
            api_key = openrouter_api_key or os.getenv("OPENROUTER_API_KEY")
            if not api_key:
                raise EnvironmentError(
                    "No OpenRouter API key provided. Pass openrouter_api_key= or "
                    "set the OPENROUTER_API_KEY environment variable."
                )
 
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
 
            filename = f"{course_code}_lecture" if course_code else "lecture"
            pdf_output = str(output_dir / f"{filename}.pdf")
 
            # Build the sources dict expected by Lecture_api
            sources: Dict[str, List[str]] = {}
 
            _text_sources = [
                ("pdf",  pdf_path,  pdf_query),
                ("docx", docx_path, docx_query),
                ("pptx", pptx_path, pptx_query),
                ("txt",  txt_path,  txt_query),
                ("url",  url_path,  url_query),
            ]
            for key, path, query in _text_sources:
                if path and query:
                    sources[key] = [path, query]
                elif path and not query:
                    print(f"{key}_path provided but {key}_query is missing — skipping.")
                elif query and not path:
                    print(f"{key}_query provided but {key}_path is missing — skipping.")
 
            if images:
                sources["image"] = images
 
            if not sources:
                raise ValueError(
                    "No valid sources provided. Supply at least one (path, query) pair."
                )
 
            pdf_path_out = lecture_api_generate(
                lecture_topic=lecture_topic,
                output_pdf_path=pdf_output,
                openrouter_api_key=api_key,
                sources=sources,
            )
 
            txt_path_out  = pdf_path_out.rsplit(".", 1)[0] + ".txt"
            json_path_out = pdf_path_out.rsplit(".", 1)[0] + ".json"
 
            print(f"PDF:  {pdf_path_out}")
            print(f"Text: {txt_path_out}")
            print(f"JSON: {json_path_out}")
 
            return {
                "pdf":  pdf_path_out,
                "txt":  txt_path_out,
                "json": json_path_out,
            }
 
        except Exception as e:
            print(f"Failed: {e}")
            return {"pdf": None, "txt": None, "json": None}
    
    # ============================================
    # SCRIPT GENERATOR (Hologram)
    # ============================================
    
    def generate_script(
        self,
        content: str,
        output_dir: Path,
        course_code: str = "",
        title: str = "",
        duration: int = 15
    ) -> Dict[str, str]:
        """
        Generate hologram script
        
        Returns:
            {"txt": "path"}
        """
        print("\n📝 Generating script...")
        
        try:
            api_key=os.getenv("GROQ_API_KEY_SCRIPT")
            output_dir.mkdir(exist_ok=True, parents=True)
            script_path = output_dir / f"{course_code}_script.txt"
            
            gen = HologramScriptGenerator(api_key=api_key)
            gen.generate_and_save(
                content=content,
                output_path=str(script_path),
                course_code=course_code,
                title=title,
                duration=duration,
                language="English"
            )
            
            print(f"   ✅ Script: {script_path}")
            
            return {"txt": str(script_path)}
        
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            return {"txt": None}
        
    # ============================================
    # WORKSHEET GENERATOR
    # ============================================
    
    def generate_worksheet(
        self,
        content: str,
        output_dir: Path,
        course_code: str = "",
        title: str = "",
        num_mcq: int = 20,
        num_tf: int = 10,
        num_written: int = 10,
    ) -> Dict[str, str]:
        """
        Generate worksheet (MCQ, T/F, Written)
        
        Returns:
            {"questions_pdf": "path", "answers_pdf": "path", "json": "path"}
        """
        print("\nGenerating worksheet...")
        
        try:       
            api_key=os.getenv("GROQ_API_KEY_WORKSHEET")     
            output_dir.mkdir(exist_ok=True, parents=True)
            questions_path = output_dir / f"{course_code}_worksheet.pdf"
            answers_path = output_dir / f"{course_code}_worksheet_answers.pdf"
            json_path = output_dir / f"{course_code}_worksheet.json"
            
            gen = WorksheetGenerator(api_key=api_key)
            worksheet = gen.generate(
                content=content,
                course_code=course_code,
                title=title,
                num_mcq=num_mcq,
                num_tf=num_tf,
                num_written=num_written,
            )
 
            gen._create_questions_pdf(worksheet, str(questions_path), course_code, title)
            gen._create_answers_pdf(worksheet, str(answers_path), course_code, title)
 
            import json as _json
            with open(json_path, "w", encoding="utf-8") as jf:
                _json.dump(worksheet, jf, indent=2, ensure_ascii=False)
 
            print(f"Questions: {questions_path}")
            print(f"Answers: {answers_path}")
            print(f"JSON: {json_path}")
            
            return {
                "questions_pdf": str(questions_path),
                "answers_pdf": str(answers_path),
                "json": str(json_path),
            }
        
        except Exception as e:
            print(f"Failed: {e}")
            return {"questions_pdf": None, "answers_pdf": None, "json": None}

    # ============================================
    # QUIZ GENERATOR
    # ============================================
    
    def generate_quiz(
        self,
        content: str,
        output_dir: Path,
        course_code: str = "",
        title: str = "",
        num_questions: int = 20
    ) -> Dict[str, str]:
        """
        Generate quiz
        
        Returns:
            {"quiz_pdf": "path", "answers_pdf": "path"}
        """
        print("\n📝 Generating quiz...")
        
        try:   
            api_key=os.getenv("GROQ_API_KEY_QUIZ")         
            output_dir.mkdir(exist_ok=True, parents=True)
            quiz_path = output_dir / f"{course_code}_quiz.pdf"
            answers_path = output_dir / f"{course_code}_quiz_answers.pdf"
            
            gen = QuizGenerator(api_key=api_key)
            gen.generate_pdfs(
                content=content,
                quiz_path=str(quiz_path),
                answers_path=str(answers_path),
                course_code=course_code,
                title=title,
                num_questions=num_questions,
                time_limit=30
            )
            
            print(f"   ✅ Quiz: {quiz_path}")
            print(f"   ✅ Answers: {answers_path}")
            
            return {
                "quiz_pdf": str(quiz_path),
                "answers_pdf": str(answers_path)
            }
        
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            return {"quiz_pdf": None, "answers_pdf": None}
    
    # ============================================
    # SUMMARY GENERATOR
    # ============================================
    
    def generate_summary(
        self,
        content: str,
        output_dir: Path,
        course_code: str = "",
        title: str = ""
    ) -> Dict[str, str]:
        """
        Generate student summary
        
        Returns:
            {"pdf": "path", "txt": "path"}
        """
        print("\n📚 Generating summary...")
        
        try:  
            api_key=os.getenv("GROQ_API_KEY_SUMMARY")          
            output_dir.mkdir(exist_ok=True, parents=True)
            summary_path = output_dir / f"{course_code}_summary.pdf"
            
            gen = SummaryGenerator(api_key=api_key)
            gen.generate_pdf(
                content=content,
                output_path=str(summary_path),
                course_code=course_code,
                title=title
            )
            
            txt_path = str(summary_path).replace('.pdf', '.txt')
            
            print(f"   ✅ PDF: {summary_path}")
            print(f"   ✅ Text: {txt_path}")
            
            return {
                "pdf": str(summary_path),
                "txt": txt_path
            }
        
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            return {"pdf": None, "txt": None}

    # ============================================
    # KNOWLEDGE GRAPH GENERATOR
    # ============================================
 
    def generate_knowledge_graph(
        self,
        txt_path: str,
        output_dir: Path,
        course_code: str = "",
    ) -> Dict[str, Optional[str]]:
        """
        Generate an interactive knowledge-graph HTML from a plain-text file.
 
        Returns:
            {"html": "path"}
        """
        print(f"\nGenerating knowledge graph...")
 
        try:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
 
            filename = f"{course_code}_knowledge_graph" if course_code else "knowledge_graph"
            html_output = str(output_dir / f"{filename}.html")
 
            html_path_out = kg_generate(
                txt_path=txt_path,
                course_code=course_code,
                output_path=html_output,
            )
 
            print(f"HTML: {html_path_out}")
 
            return {"html": html_path_out}
 
        except Exception as e:
            print(f"Failed: {e}")
            return {"html": None}  
    
