from ..generators.quiz_generator import QuizGenerator
from ..generators.script_generator import HologramScriptGenerator
from ..generators.summary_generator import SummaryGenerator
from ..generators.worksheet_generator import WorksheetGenerator
from ..generators.knowledge_graph_generator import FlowchartGenerator
from ..generators.generate_lecture import LectureGenerator
import os
from pathlib import Path
from typing import Optional, Dict


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
            from ..extractors.pdf_extractor import PDFExtractor
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
            from ..extractors.docx_extractor import DOCXExtractor
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
            from ..extractors.pptx_extractor import PPTXExtractor
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
            from ..extractors.audio_extractor import AudioExtractor
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
            from ..extractors.video_extractor import VideoExtractor
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
            from ..extractors.url_extractor import URLExtractor
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

    def __init__(self, api_key: Optional[str] = None):
        pass
    
    # ============================================
    # LECTURE GENERATOR (Your Teammate's)
    # ============================================
    
    def generate_lecture(
        self,
        lecture_topic: str,
        output_dir: Path,
        course_code: str = "",
        # Source materials
        website_text: Optional[str] = None,
        website_query: Optional[str] = None,
        video_text: Optional[str] = None,
        video_query: Optional[str] = None,
        pptx_text: Optional[str] = None,
        pptx_query: Optional[str] = None,
        audio_text: Optional[str] = None,
        audio_query: Optional[str] = None,
        pdf_text: Optional[str] = None,
        pdf_query: Optional[str] = None,
        docx_text: Optional[str] = None,
        docx_query: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Generate comprehensive lecture PDF
        
        Returns:
            {"pdf": "path", "txt": "path"}
        """
        print("\n📚 Generating lecture...")
        
        try:
            api_key=os.getenv("GROQ_API_KEY_LECTURE")
            generator=LectureGenerator(groq_api_key=api_key)            
            output_dir.mkdir(exist_ok=True, parents=True)
            filename = f"{course_code}_lecture" if course_code else "lecture"
            pdf_path = output_dir / f"{filename}.pdf"
            
            generator.generate_lecture_sync(
                lecture_topic=lecture_topic,
                output_pdf_path=str(pdf_path),
                groq_api_key=self.api_key,
                website_text=website_text,
                website_query=website_query,
                video_text=video_text,
                video_query=video_query,
                pptx_text=pptx_text,
                pptx_query=pptx_query,
                audio_text=audio_text,
                audio_query=audio_query,
                pdf_text=pdf_text,
                pdf_query=pdf_query,
                docx_text=docx_text,
                docx_query=docx_query
            )
            
            txt_path = str(pdf_path).replace('.pdf', '.txt')
            
            print(f"   ✅ PDF: {pdf_path}")
            print(f"   ✅ Text: {txt_path}")
            
            return {
                "pdf": str(pdf_path),
                "txt": txt_path
            }
        
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            return {"pdf": None, "txt": None}
    
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
        title: str = ""
    ) -> Dict[str, str]:
        """
        Generate worksheet (MCQ, T/F, Written)
        
        Returns:
            {"questions_pdf": "path", "answers_pdf": "path", "json": "path"}
        """
        print("\n📋 Generating worksheet...")
        
        try:       
            api_key=os.getenv("GROQ_API_KEY_WORKSHEET")     
            output_dir.mkdir(exist_ok=True, parents=True)
            questions_path = output_dir / f"{course_code}_worksheet.pdf"
            answers_path = output_dir / f"{course_code}_worksheet_answers.pdf"
            
            gen = WorksheetGenerator(api_key=api_key)
            gen.generate_pdfs(
                content=content,
                questions_path=str(questions_path),
                answers_path=str(answers_path),
                course_code=course_code,
                title=title
            )
            
            json_path = str(questions_path).replace('.pdf', '.json')
            
            print(f"   ✅ Questions: {questions_path}")
            print(f"   ✅ Answers: {answers_path}")
            
            return {
                "questions_pdf": str(questions_path),
                "answers_pdf": str(answers_path),
                "json": json_path
            }
        
        except Exception as e:
            print(f"   ❌ Failed: {e}")
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
    # FLOWCHART GENERATOR
    # ============================================
    
    def generate_flowchart(
        self,
        content: str,
        output_dir: Path,
        course_code: str = "",
        title: str = ""
    ) -> Dict[str, str]:
        """
        Generate flowchart
        
        Returns:
            {"html": "path", "mmd": "path"}
        """
        print("\n📊 Generating flowchart...")
        
        try:    
            api_key=os.getenv("GROQ_API_KEY_FLOWCHART")        
            output_dir.mkdir(exist_ok=True, parents=True)
            flowchart_path = output_dir / f"{course_code}_flowchart.html"
            
            gen = FlowchartGenerator(api_key=api_key)
            gen.generate_html(
                content=content,
                output_path=str(flowchart_path),
                course_code=course_code,
                title=title
            )
            
            mmd_path = str(flowchart_path).replace('.html', '.mmd')
            
            print(f"   ✅ HTML: {flowchart_path}")
            print(f"   ✅ Mermaid: {mmd_path}")
            
            return {
                "html": str(flowchart_path),
                "mmd": mmd_path
            }
        
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            return {"html": None, "mmd": None}
  
    
