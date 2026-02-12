"""
Simple Deterministic Orchestrator
Uses simple wrapper - no validators, clean flow
"""

import os
from pathlib import Path
from typing import Optional, Dict
from datetime import datetime
import json


class SimpleOrchestrator:
    """
    Simple orchestrator - generates all materials
    Clean flow, no validators, just execution
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize orchestrator"""
        from Lecture_Agent.wrapper import SimpleGeneratorWrapper, SimpleExtractorWrapper
        
        self.generators = SimpleGeneratorWrapper()
        self.extractors = SimpleExtractorWrapper()
        
        print("✅ Simple orchestrator initialized")
    
    def process(
        self,
        # Either provide content directly OR file paths
        content: Optional[str] = None,
        pdf_file: Optional[str] = None,
        docx_file: Optional[str] = None,
        url: Optional[str] = None,
        video_url: Optional[str] = None,
        
        # For lecture generator (multi-source)
        lecture_sources: Optional[Dict] = None,
        
        # Metadata
        course_code: str = "COURSE",
        title: str = "Lecture",
        output_dir: str = "output",
        
        # What to generate
        generate_lecture: bool = False,
        generate_script: bool = False,
        generate_worksheet: bool = False,
        generate_quiz: bool = True,
        generate_summary: bool = False,
        generate_flowchart: bool = True
    ) -> Dict:
        """
        Main orchestration - simple flow
        
        Args:
            content: Direct text content (if available)
            pdf_file: Path to PDF (will extract)
            docx_file: Path to DOCX (will extract)
            url: URL to scrape
            video_url: Video URL for transcript
            lecture_sources: Dict of sources for lecture generator
                {
                    "pdf_text": "...",
                    "pdf_query": "...",
                    "website_text": "...",
                    "website_query": "...",
                    etc.
                }
            course_code: Course identifier
            title: Lecture/material title
            output_dir: Output directory
            generate_*: Flags for what to generate
        
        Returns:
            {
                "files": {...},
                "status": "completed"
            }
        """
        
        print("="*80)
        print("🎯 SIMPLE ORCHESTRATOR")
        print("="*80)
        print(f"Course: {course_code}")
        print(f"Title: {title}")
        print(f"Output: {output_dir}")
        print("="*80)
        
        # Setup
        output_path = Path(output_dir) / course_code
        output_path.mkdir(exist_ok=True, parents=True)
        
        results = {
            "course_code": course_code,
            "title": title,
            "timestamp": datetime.now().isoformat(),
            "files": {},
            "status": "in_progress"
        }
        
        # STEP 1: Get content
        if content is None:
            print("\n📥 STEP 1: Extracting content...")
            content = self._extract_content(pdf_file, docx_file, url, video_url)
            print(f"   ✅ Extracted {len(content)} characters")
        else:
            print("\n📥 STEP 1: Using provided content")
            print(f"   ✅ Content: {len(content)} characters")
        
        if not content and not lecture_sources:
            print("\n❌ No content provided!")
            results["status"] = "failed - no content"
            return results
        
        # STEP 2: Generate materials
        print("\n🔧 STEP 2: Generating materials...")
        
        # Lecture (uses multi-source)
        if generate_lecture and lecture_sources:
            print("\n  📚 Generating comprehensive lecture...")
            lecture = self.generators.generate_lecture(
                lecture_topic=title,
                output_dir=output_path,
                course_code=course_code,
                **lecture_sources
            )
            results["files"]["lecture"] = lecture

                # ✅ Use the generated lecture text as content for other generators
            lecture_txt_path = lecture.get("txt")
            if lecture_txt_path and os.path.exists(lecture_txt_path):
                with open(lecture_txt_path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                print(f"   ✅ Using generated lecture text for other generators: {len(content)} chars")
        
        # Script
        if generate_script and content:
            print("\n  📝 Generating script...")
            script = self.generators.generate_script(
                content=content,
                output_dir=output_path,
                course_code=course_code,
                title=title
            )
            results["files"]["script"] = script
        
        # Worksheet
        if generate_worksheet and content:
            print("\n  📋 Generating worksheet...")
            worksheet = self.generators.generate_worksheet(
                content=content,
                output_dir=output_path,
                course_code=course_code,
                title=title
            )
            results["files"]["worksheet"] = worksheet
        
        # Quiz
        if generate_quiz and content:
            print("\n  📝 Generating quiz...")
            quiz = self.generators.generate_quiz(
                content=content,
                output_dir=output_path,
                course_code=course_code,
                title=title
            )
            results["files"]["quiz"] = quiz
        
        # Summary
        if generate_summary and content:
            print("\n  📚 Generating summary...")
            summary = self.generators.generate_summary(
                content=content,
                output_dir=output_path,
                course_code=course_code,
                title=title
            )
            results["files"]["summary"] = summary
        
        # Flowchart
        if generate_flowchart and content:
            print("\n  📊 Generating flowchart...")
            flowchart = self.generators.generate_flowchart(
                content=content,
                output_dir=output_path,
                course_code=course_code,
                title=title
            )
            results["files"]["flowchart"] = flowchart
        
        # STEP 3: Save manifest
        results["status"] = "completed"
        self._save_manifest(results, output_path)
        
        # STEP 4: Print summary
        self._print_summary(results)
        
        return results
    
    def _extract_content(
        self,
        pdf_file: Optional[str] = None,
        docx_file: Optional[str]= None,
        url: Optional[str] = None,
        video_url: Optional[str] =None
    ) -> str:
        """Extract content from files"""
        
        parts = []
        
        if pdf_file:
            print(f"   -> Extracting PDF: {pdf_file}")
            text = self.extractors.extract_pdf(pdf_file)
            if text:
                parts.append(text)
        
        if docx_file:
            print(f"   -> Extracting DOCX: {docx_file}")
            text = self.extractors.extract_docx(docx_file)
            if text:
                parts.append(text)
        
        if url:
            print(f"   -> Extracting URL: {url}")
            text = self.extractors.extract_url(url)
            if text:
                parts.append(text)
        
        if video_url:
            print(f"   -> Extracting video: {video_url}")
            text = self.extractors.extract_video(video_url)
            if text:
                parts.append(text)
        
        return "\n\n".join(parts)
    
    def _save_manifest(self, results: Dict, output_path: Path):
        """Save manifest"""
        manifest_path = output_path / "manifest.json"
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Manifest: {manifest_path}")
    
    def _print_summary(self, results: Dict):
        """Print summary"""
        print("\n" + "="*80)
        print("📊 SUMMARY")
        print("="*80)
        print(f"Status: {results['status']}")
        print(f"Course: {results['course_code']}")
        
        print("\n📦 Generated Files:")
        for name, files in results["files"].items():
            print(f"\n  {name.upper()}:")
            if isinstance(files, dict):
                for key, path in files.items():
                    if path:
                        print(f"    ✓ {key}: {path}")
            else:
                print(f"    ✓ {files}")
        
        print("\n" + "="*80)


# ============================================
# SIMPLE API
# ============================================

def process_simple(
    content: str,
    course_code: str,
    title: str,
    output_dir: str = "output",
    **kwargs
) -> Dict:
    """
    Simplest API - just provide content
    
    Usage:
        result = process_simple(
            content=pdf_text,
            course_code="ML101",
            title="Intro to ML"
        )
    """
    orchestrator = SimpleOrchestrator()
    return orchestrator.process(
        content=content,
        course_code=course_code,
        title=title,
        output_dir=output_dir,
        **kwargs
    )


def process_with_files(
    pdf_file: str = None,
    docx_file: str = None,
    url: str = None,
    course_code: str = "COURSE",
    title: str = "Lecture",
    output_dir: str = "output",
    **kwargs
) -> Dict:
    """
    Process from files - will extract automatically
    
    Usage:
        result = process_with_files(
            pdf_file="lecture.pdf",
            course_code="ML101",
            title="Intro to ML"
        )
    """
    orchestrator = SimpleOrchestrator()
    return orchestrator.process(
        pdf_file=pdf_file,
        docx_file=docx_file,
        url=url,
        course_code=course_code,
        title=title,
        output_dir=output_dir,
        **kwargs
    )


def process_lecture_multisource(
    lecture_topic: str,
    course_code: str,
    lecture_sources: Dict,
    output_dir: str = "output",
    **kwargs
) -> Dict:
    """
    Generate comprehensive lecture from multiple sources
    
    Usage:
        result = process_lecture_multisource(
            lecture_topic="Machine Learning",
            course_code="ML101",
            lecture_sources={
                "pdf_text": pdf_content,
                "pdf_query": "Explain ML basics",
                "website_text": web_content,
                "website_query": "Explain applications"
            }
        )
    """
    orchestrator = SimpleOrchestrator()
    return orchestrator.process(
        lecture_sources=lecture_sources,
        course_code=course_code,
        title=lecture_topic,
        output_dir=output_dir,
        generate_lecture=True,
        **kwargs
    )

def read_text_file(path: str) -> str:
    """Read lecture content from a .txt file safely."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Lecture file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        content = f.read().strip()

    if not content:
        raise ValueError(f"Lecture file is empty: {path}")

    return content


# ============================================
# USAGE EXAMPLES
# ============================================

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()


    
    obj=SimpleOrchestrator()
    content = obj.extractors.extract_pdf("1706.03762v7.pdf")
    content2=obj.extractors.extract_url("https://en.wikipedia.org/wiki/Transformer_(deep_learning)")

    # print("\n\n")
    # print("EXAMPLE 2: Process from PDF file")
    # print("-"*80)
    
    # result2 = process_with_files(
    #     pdf_file="SIST_L2[1].pdf",  # Will extract automatically
    #     course_code="SIS102",
    #     title="sist",
    #     output_dir="output"
    # )
    
    print("\n\n")
    print("EXAMPLE 3: Generate comprehensive lecture (multi-source)")
    print("-"*80)
    
    result3 = process_lecture_multisource(
        lecture_topic="Transformers Fundamentals",
        course_code="AI103",
        lecture_sources={
            "pdf_text": content,
            "pdf_query": "Explain transformers",
            "website_text": content2,
            "website_query": "Explain applications of transormers in deep learning"
        },
        output_dir="output"

    )
    
    # print("\n🎉 All examples complete!")