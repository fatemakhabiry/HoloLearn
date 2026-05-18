"""
URL Extractor for HoloLearn
Extracts text content from web pages.
"""

from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import json
import time
import re
from urllib.parse import urlparse, urljoin

import sys
sys.path.append(str(Path(__file__).parent.parent))
from utils.configs import (
    OUTPUT_DIR,
    LOGS_DIR,
    REQUEST_TIMEOUT,
    USER_AGENT,
    MAX_RETRIES,
    RETRY_DELAY,
    BACKOFF_FACTOR,
)
from utils.error_handler import ErrorHandler
from utils.text_cleaner import TextCleaner

try:
    import requests
    from bs4 import BeautifulSoup
    _WEB_DEPS_AVAILABLE = True
except ImportError as _web_import_err:
    _WEB_DEPS_AVAILABLE = False
    _web_import_err_msg = str(_web_import_err)

_MAX_PAGINATION_PAGES = 5  # safety cap when following "next page" links


class URLExtractor:
    """Extract text from web pages"""

    def __init__(self):
        if not _WEB_DEPS_AVAILABLE:
            raise ImportError(
                f"Web dependencies missing: {_web_import_err_msg}. "
                "Install with: pip install requests beautifulsoup4"
            )

        self.text_cleaner = TextCleaner()
        self.base_output_dir = OUTPUT_DIR
        self.base_logs_dir = LOGS_DIR

        self.base_output_dir.mkdir(parents=True, exist_ok=True)
        self.base_logs_dir.mkdir(parents=True, exist_ok=True)

        self.session = requests.Session()
        self.session.headers.update({'User-Agent': USER_AGENT})

    def _create_resource_name(self, url: str) -> str:
        parsed = urlparse(url)
        domain = parsed.netloc.replace('www.', '')
        path = parsed.path.strip('/')
        name = f"{domain}_{path}" if path else domain
        name = name.lower()
        name = re.sub(r'[^\w\s-]', '_', name)
        name = re.sub(r'[-\s]+', '_', name).strip('_')
        return (name[:50] if len(name) > 50 else name) or "webpage"

    def _setup_resource_directories(self, resource_name: str, output_dir_override: Optional[Path] = None) -> tuple:
        resource_output_dir = Path(output_dir_override) if output_dir_override else self.base_output_dir / resource_name
        resource_logs_dir = self.base_logs_dir / resource_name
        resource_output_dir.mkdir(parents=True, exist_ok=True)
        resource_logs_dir.mkdir(parents=True, exist_ok=True)
        return resource_output_dir, resource_logs_dir

    # ------------------------------------------------------------------ #
    #  Fetch                                                               #
    # ------------------------------------------------------------------ #

    def _fetch_url(self, url: str, error_handler: ErrorHandler) -> Optional[str]:
        """Fetch HTML with retries, exponential backoff, and Retry-After support."""
        for attempt in range(MAX_RETRIES):
            try:
                error_handler.log_info(f"Fetching URL (attempt {attempt + 1}/{MAX_RETRIES})...",
                                       metadata={"url": url})
                response = self.session.get(url, timeout=REQUEST_TIMEOUT, allow_redirects=True)
                response.raise_for_status()

                content_type = response.headers.get('Content-Type', '')
                if 'text/html' not in content_type.lower():
                    error_handler.log_warning(f"URL may not be HTML: {content_type}",
                                              metadata={"url": url})
                return response.text

            except requests.exceptions.HTTPError as e:
                # Respect Retry-After header on 429 / 503
                status = e.response.status_code if e.response is not None else 0
                if status in (429, 503) and e.response is not None:
                    retry_after = int(e.response.headers.get('Retry-After',
                                                              RETRY_DELAY * (BACKOFF_FACTOR ** attempt)))
                    error_handler.log_warning(
                        f"Rate limited (HTTP {status}), waiting {retry_after}s",
                        metadata={"url": url}
                    )
                    time.sleep(retry_after)
                    continue
                error_handler.log_warning(f"HTTP error on attempt {attempt + 1}: {e}",
                                          metadata={"url": url})
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY * (BACKOFF_FACTOR ** attempt))

            except requests.exceptions.Timeout:
                error_handler.log_warning(f"Timeout on attempt {attempt + 1}", metadata={"url": url})
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY * (BACKOFF_FACTOR ** attempt))

            except requests.exceptions.RequestException as e:
                error_handler.log_warning(f"Request failed on attempt {attempt + 1}: {e}",
                                          metadata={"url": url})
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY * (BACKOFF_FACTOR ** attempt))

        return None

    # ------------------------------------------------------------------ #
    #  HTML analysis helpers                                               #
    # ------------------------------------------------------------------ #

    def _extract_text_from_html(self, html: str, url: str) -> str:
        """Extract main readable text from an HTML page."""
        soup = BeautifulSoup(html, 'html.parser')

        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()

        main_content = None
        for selector in ['main', 'article', '[role="main"]', '.content', '#content',
                         '.post-content', '.article-content']:
            main_content = soup.select_one(selector)
            if main_content:
                break
        if not main_content:
            main_content = soup.find('body') or soup

        text = main_content.get_text(separator='\n', strip=True)

        title = ""
        title_tag = soup.find('title')
        if title_tag:
            title = f"Title: {title_tag.get_text().strip()}\n"
            title += f"URL: {url}\n"
            title += "=" * 60 + "\n\n"

        return title + text

    def _extract_internal_links(self, soup, base_url: str) -> List[str]:
        """Return deduplicated list of internal links found on the page."""
        base_domain = urlparse(base_url).netloc
        links = set()
        for a in soup.find_all('a', href=True):
            href = a['href'].strip()
            if not href or href.startswith('#') or href.startswith('javascript:'):
                continue
            full_url = urljoin(base_url, href)
            if urlparse(full_url).netloc == base_domain:
                links.add(full_url)
        return sorted(links)

    def _classify_page_type(self, title: str, url: str, text: str) -> str:
        """Classify the page's role in a course (syllabus, lecture_notes, assignment, article, unknown)."""
        title_l = title.lower()
        url_l = url.lower()
        text_sample = text[:1000].lower()

        if any(k in title_l or k in url_l for k in ['syllabus', 'course outline', 'course description']):
            return 'syllabus'
        if any(k in title_l or k in url_l for k in ['assignment', 'homework', 'problem set',
                                                      'quiz', 'exam', 'exercise']):
            return 'assignment'
        if any(k in title_l or k in url_l for k in ['lecture', 'lesson', 'chapter',
                                                      'module', 'unit', 'notes']):
            return 'lecture_notes'
        if any(phrase in text_sample for phrase in ['by the end of', 'learning objectives',
                                                     'learning outcomes', 'you will learn']):
            return 'lecture_notes'
        if any(k in url_l for k in ['wiki', 'article', 'blog', 'post']):
            return 'article'
        return 'unknown'

    def _find_next_page_url(self, soup, base_url: str) -> Optional[str]:
        """Detect a "next page" link via text, rel attribute, or <link rel='next'>."""
        next_texts = {'next', 'next page', '→', '»', '›', 'next ›', 'forward'}

        # <link rel="next"> in <head>
        link_next = soup.find('link', rel='next')
        if link_next and link_next.get('href'):
            return urljoin(base_url, link_next['href'])

        for a in soup.find_all('a', href=True):
            text = a.get_text().strip().lower()
            rel = a.get('rel', [])
            aria = a.get('aria-label', '').lower()

            if text in next_texts or 'next' in rel or 'next' in aria:
                return urljoin(base_url, a['href'])

        return None

    def _build_sections_from_html(self, soup, url: str) -> List[dict]:
        """Extract heading-delimited sections from the parsed HTML."""
        sections = []
        headings = soup.find_all(['h1', 'h2', 'h3', 'h4'])

        for heading in headings:
            level = int(heading.name[1])
            title = heading.get_text(strip=True)
            if not title:
                continue

            body_parts = []
            sibling = heading.find_next_sibling()
            while sibling and sibling.name not in ['h1', 'h2', 'h3', 'h4']:
                if sibling.name in ['p', 'ul', 'ol', 'div', 'blockquote']:
                    text = sibling.get_text(separator=' ', strip=True)
                    if text:
                        body_parts.append(text)
                sibling = sibling.find_next_sibling()

            sections.append({
                "title": title,
                "body": ' '.join(body_parts),
                "type": f"h{level}",
                "source_location": {"url": url},
            })

        return sections

    def _compute_quality_score(self, text: str, sections: List[dict]) -> float:
        word_score = min(len(text.split()) / 5000, 1.0)
        structure_score = min(len(sections) / 10, 1.0)
        return round(word_score * 0.6 + structure_score * 0.4, 2)

    # ------------------------------------------------------------------ #
    #  Main extraction                                                     #
    # ------------------------------------------------------------------ #

    def extract(self,
                url: str,
                resource_id: Optional[str] = None,
                clean_text: bool = True,
                follow_pagination: bool = True,
                output_dir: Optional[str] = None) -> Dict[str, Any]:
        """
        Extract text from a web page, optionally following pagination.

        Args:
            url: URL to scrape.
            resource_id: Optional unique identifier.
            clean_text: Whether to clean extracted text.
            follow_pagination: Follow "next page" links (up to 5 pages).
            output_dir: Optional shared output directory.

        Returns dict with: success, resource_name, resource_id, text_file,
        metadata_file, structured_file, output_dir, logs_dir, extracted_text,
        sections, internal_links, page_type, content_quality_score, metadata.
        """
        start_time = time.time()

        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url

        resource_name = self._create_resource_name(url)
        override = Path(output_dir) if output_dir else None
        output_dir, logs_dir = self._setup_resource_directories(resource_name, output_dir_override=override)

        error_handler = ErrorHandler(f"url_{resource_name}")
        error_handler.log_file = logs_dir / "extraction.log"
        error_handler.logger = error_handler._setup_logger()

        error_handler.log_info(f"Starting URL extraction: {url}",
                               metadata={"resource_name": resource_name, "output_dir": str(output_dir)})

        try:
            # --- Fetch and accumulate pages ---
            all_text_parts: List[str] = []
            all_sections: List[dict] = []
            internal_links: List[str] = []
            pages_followed = 1
            page_type = "unknown"

            current_url = url
            first_soup = None

            for page_idx in range(_MAX_PAGINATION_PAGES if follow_pagination else 1):
                html = self._fetch_url(current_url, error_handler)
                if not html:
                    if page_idx == 0:
                        raise ValueError("Failed to fetch URL after all retry attempts")
                    break

                soup = BeautifulSoup(html, 'html.parser')

                # On first page: extract links, page type, and soup for section building
                if page_idx == 0:
                    first_soup = soup
                    internal_links = self._extract_internal_links(soup, url)

                    title_tag = soup.find('title')
                    page_title = title_tag.get_text().strip() if title_tag else ""

                page_text = self._extract_text_from_html(html, current_url)
                all_text_parts.append(page_text)

                page_sections = self._build_sections_from_html(soup, current_url)
                all_sections.extend(page_sections)

                if not follow_pagination:
                    break

                next_url = self._find_next_page_url(soup, current_url)
                if not next_url or next_url == current_url:
                    break

                current_url = next_url
                pages_followed += 1

            extracted_text = "\n\n".join(all_text_parts)

            if not extracted_text.strip():
                raise ValueError("No text content extracted from URL")

            if clean_text:
                extracted_text = self.text_cleaner.clean_text(
                    extracted_text, remove_urls=False, remove_emails=False, fix_spacing=True
                )
            extracted_text = self.text_cleaner.remove_duplicate_lines(extracted_text)

            # Classify page type using the accumulated text
            page_type = self._classify_page_type(
                page_title if first_soup else "",
                url,
                extracted_text
            )

            quality_score = self._compute_quality_score(extracted_text, all_sections)
            processing_time = time.time() - start_time

            metadata = {
                "resource_name": resource_name,
                "resource_id": resource_id or resource_name,
                "url": url,
                "source_type": "url",
                "upload_date": datetime.now().isoformat(),
                "extraction_timestamp": datetime.now().isoformat(),
                "processing_time_seconds": round(processing_time, 2),
                "status": "success",
                "error_message": None,
                "character_count": len(extracted_text),
                "word_count": len(extracted_text.split()),
                "domain": urlparse(url).netloc,
                "page_type": page_type,
                "pages_followed": pages_followed,
                "internal_links_count": len(internal_links),
                "section_count": len(all_sections),
                "content_quality_score": quality_score,
            }

            text_file = output_dir / f"{resource_name}_text.txt"
            text_file.write_text(extracted_text, encoding='utf-8')
            metadata["extracted_text_path"] = str(text_file)

            metadata_file = output_dir / f"{resource_name}_metadata.json"
            metadata_file.write_text(json.dumps(metadata, indent=2), encoding='utf-8')

            structured = {
                "sections": all_sections,
                "internal_links": internal_links,
                "page_type": page_type,
            }
            structured_file = output_dir / f"{resource_name}_structured.json"
            structured_file.write_text(json.dumps(structured, indent=2, ensure_ascii=False), encoding='utf-8')

            error_handler.log_success(f"URL extracted successfully: {url}",
                                      metadata={"chars": len(extracted_text),
                                                "pages": pages_followed,
                                                "page_type": page_type,
                                                "time": f"{processing_time:.2f}s"})

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
                "sections": all_sections,
                "internal_links": internal_links,
                "page_type": page_type,
                "content_quality_score": quality_score,
                "metadata": metadata,
            }

        except Exception as e:
            processing_time = time.time() - start_time
            error_handler.log_error(e, context=f"Extracting URL: {url}",
                                    metadata={"resource_name": resource_name})
            return self._create_error_result(resource_name, str(e), output_dir, url, processing_time)

    def _create_error_result(self,
                             resource_name: str,
                             error_message: str,
                             output_dir: Path,
                             url: str = "unknown",
                             processing_time: float = 0) -> Dict[str, Any]:
        metadata = {
            "resource_name": resource_name,
            "url": url,
            "source_type": "url",
            "upload_date": datetime.now().isoformat(),
            "extraction_timestamp": datetime.now().isoformat(),
            "processing_time_seconds": round(processing_time, 2),
            "status": "failed",
            "error_message": error_message,
        }
        metadata_file = output_dir / f"{resource_name}_metadata.json"
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
            "internal_links": [],
            "page_type": "unknown",
            "content_quality_score": 0.0,
            "metadata": metadata,
            "error": error_message,
        }

    def extract_multiple_urls(self, urls: list, follow_pagination: bool = True) -> Dict[str, Any]:
        """Extract text from multiple URLs."""
        results = {"total": len(urls), "successful": 0, "failed": 0, "extractions": []}

        for i, url in enumerate(urls, 1):
            print(f"\n[{i}/{len(urls)}] Processing: {url}")
            result = self.extract(url, follow_pagination=follow_pagination)
            results["extractions"].append(result)
            if result["success"]:
                results["successful"] += 1
                print(f"✓ Success: {result['resource_name']} [{result['page_type']}]")
            else:
                results["failed"] += 1
                print(f"✗ Failed: {result['error']}")

        return results


# Example usage and testing
if __name__ == "__main__":
    print("=== Testing URL Extractor ===\n")

    extractor = URLExtractor()

    print("Enter a URL to extract (or press Enter to skip):")
    user_url = input("> ").strip()

    test_urls = [
        "https://en.wikipedia.org/wiki/Machine_learning",
        "https://www.python.org/about/",
    ]

    if user_url:
        print(f"\nExtracting: {user_url}\n")
        result = extractor.extract(user_url, clean_text=True, follow_pagination=True)

        if result['success']:
            print(f"   ✓ Success!")
            print(f"   Resource name: {result['resource_name']}")
            print(f"   Page type: {result['page_type']}")
            print(f"   Pages followed: {result['metadata']['pages_followed']}")
            print(f"   Sections: {len(result['sections'])}")
            print(f"   Internal links: {len(result['internal_links'])}")
            print(f"   Quality score: {result['content_quality_score']}")
            print(f"   Structured file: {result['structured_file']}")
        else:
            print(f"   ✗ Failed: {result['error']}")
    else:
        print(f"No URL provided. Testing with {len(test_urls)} example URLs...\n")
        results = extractor.extract_multiple_urls(test_urls)
        print(f"\n{'='*60}")
        print(f"Total: {results['total']} | Success: {results['successful']} | Failed: {results['failed']}")
        print(f"{'='*60}")
