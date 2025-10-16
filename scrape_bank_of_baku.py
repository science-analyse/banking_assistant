#!/usr/bin/env python3
"""
Bank of Baku Website Scraper - Enhanced Version
Extracts all content from bankofbaku.com for RAG application training
Optimized for high-quality, complete data retrieval

Features:
- Sitemap-based discovery for complete coverage
- Smart content chunking optimized for embeddings
- Deduplication and quality filtering
- Retry mechanism and error handling
- Multi-language support with detection
- Hierarchical metadata preservation
"""

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qs
import json
import time
import os
from typing import Set, Dict, List, Optional, Tuple
import re
import hashlib
from collections import defaultdict
from datetime import datetime
import xml.etree.ElementTree as ET
import requests


class BankOfBakuScraper:
    def __init__(self, base_url: str = "http://bankofbaku.com/az", output_dir: str = "scraped_data"):
        self.base_url = base_url
        self.domain = urlparse(base_url).netloc
        self.visited_urls: Set[str] = set()
        self.scraped_data: List[Dict] = []
        self.output_dir = output_dir
        self.failed_urls: Dict[str, str] = {}  # URL -> error message
        self.discovered_urls: Set[str] = set()
        self.content_hashes: Set[str] = set()  # For deduplication
        self.chunk_id_counter = 0

        # RAG optimization settings
        self.target_chunk_size = 512  # tokens (roughly 400 words)
        self.chunk_overlap = 128  # tokens overlap for context preservation
        self.min_chunk_size = 100  # Minimum meaningful content

        # Retry settings
        self.max_retries = 3
        self.retry_delay = 2

        # Setup Selenium with headless Chrome
        chrome_options = Options()
        chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

        # Don't set binary_location for macOS - let it find Chrome automatically
        import platform
        if platform.system() == 'Linux':
            chrome_options.binary_location = '/usr/bin/chromium'

        print("Initializing Chrome driver...", flush=True)
        try:
            # Try system chrome-driver first
            if platform.system() == 'Linux':
                self.driver = webdriver.Chrome(
                    service=Service('/usr/bin/chromiumdriver'),
                    options=chrome_options
                )
            else:
                # For macOS/Windows, use webdriver-manager
                raise Exception("Use webdriver-manager")
        except:
            # Fallback to webdriver-manager (works on all platforms)
            try:
                driver_path = ChromeDriverManager().install()
                # Fix for webdriver-manager bug on macOS ARM64
                if 'THIRD_PARTY_NOTICES.chromedriver' in driver_path:
                    import os
                    driver_dir = os.path.dirname(driver_path)
                    actual_driver = os.path.join(driver_dir, 'chromedriver')
                    if os.path.exists(actual_driver):
                        driver_path = actual_driver
                        # Make sure it's executable
                        os.chmod(driver_path, 0o755)

                self.driver = webdriver.Chrome(
                    service=Service(driver_path),
                    options=chrome_options
                )
            except Exception as e:
                print(f"\nError: Could not initialize Chrome driver: {e}")
                print("\nPlease ensure Chrome or Chromium is installed.")
                print("On macOS: brew install --cask google-chrome")
                print("On Linux: apt-get install chromium-browser")
                raise
        print("Chrome driver ready!", flush=True)

        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        print(f"Output directory created: {output_dir}", flush=True)

        # Load checkpoint if exists
        self.checkpoint_file = os.path.join(output_dir, 'checkpoint.json')
        print("Loading checkpoint...", flush=True)
        self.load_checkpoint()
        print("Scraper initialized successfully!", flush=True)

    def __del__(self):
        """Cleanup - close browser"""
        if hasattr(self, 'driver'):
            try:
                self.driver.quit()
            except:
                pass

    def restart_driver(self):
        """Restart Chrome driver to fix stability issues"""
        print("  Restarting Chrome driver...", flush=True)
        try:
            if hasattr(self, 'driver'):
                self.driver.quit()
        except:
            pass

        time.sleep(2)

        # Reinitialize driver
        driver_path = ChromeDriverManager().install()
        if 'THIRD_PARTY_NOTICES.chromedriver' in driver_path:
            import os
            driver_dir = os.path.dirname(driver_path)
            actual_driver = os.path.join(driver_dir, 'chromedriver')
            if os.path.exists(actual_driver):
                driver_path = actual_driver
                os.chmod(driver_path, 0o755)

        chrome_options = Options()
        chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

        self.driver = webdriver.Chrome(
            service=Service(driver_path),
            options=chrome_options
        )
        print("  ✓ Chrome driver restarted", flush=True)

    def load_checkpoint(self):
        """Load scraping progress from checkpoint"""
        if os.path.exists(self.checkpoint_file):
            try:
                with open(self.checkpoint_file, 'r', encoding='utf-8') as f:
                    checkpoint = json.load(f)
                    self.visited_urls = set(checkpoint.get('visited_urls', []))
                    self.discovered_urls = set(checkpoint.get('discovered_urls', []))
                    self.content_hashes = set(checkpoint.get('content_hashes', []))
                    self.chunk_id_counter = checkpoint.get('chunk_id_counter', 0)
                    print(f"Resumed from checkpoint: {len(self.visited_urls)} URLs already visited")
            except Exception as e:
                print(f"Could not load checkpoint: {e}")

    def save_checkpoint(self):
        """Save scraping progress"""
        checkpoint = {
            'visited_urls': list(self.visited_urls),
            'discovered_urls': list(self.discovered_urls),
            'content_hashes': list(self.content_hashes),
            'chunk_id_counter': self.chunk_id_counter,
            'timestamp': datetime.now().isoformat()
        }
        with open(self.checkpoint_file, 'w', encoding='utf-8') as f:
            json.dump(checkpoint, f, ensure_ascii=False, indent=2)

    def detect_language(self, text: str) -> str:
        """Detect language based on character patterns"""
        if not text:
            return 'unknown'

        # Count character types
        cyrillic = len(re.findall(r'[а-яА-ЯёЁ]', text))
        latin = len(re.findall(r'[a-zA-Z]', text))
        azerbaijani_specific = len(re.findall(r'[əöüğışçƏÖÜĞİŞÇ]', text))

        total = cyrillic + latin + azerbaijani_specific
        if total == 0:
            return 'unknown'

        if cyrillic / total > 0.3:
            return 'ru'
        elif azerbaijani_specific / total > 0.05 or (latin / total > 0.5 and '/az' in self.base_url):
            return 'az'
        elif latin / total > 0.5:
            return 'en'

        return 'unknown'

    def calculate_content_hash(self, content: str) -> str:
        """Calculate hash for content deduplication"""
        # Normalize content for comparison
        normalized = re.sub(r'\s+', ' ', content.lower().strip())
        return hashlib.md5(normalized.encode('utf-8')).hexdigest()

    def is_duplicate_content(self, content: str) -> bool:
        """Check if content is duplicate"""
        content_hash = self.calculate_content_hash(content)
        if content_hash in self.content_hashes:
            return True
        self.content_hashes.add(content_hash)
        return False

    def estimate_tokens(self, text: str) -> int:
        """Rough token estimation (1 token ≈ 0.75 words)"""
        words = len(text.split())
        return int(words / 0.75)

    def fetch_sitemap_urls(self) -> Set[str]:
        """Fetch all URLs from sitemap.xml"""
        sitemap_urls = set()
        sitemap_url = urljoin(self.base_url, '/sitemap.xml')

        try:
            print(f"Fetching sitemap from: {sitemap_url}")
            response = requests.get(sitemap_url, timeout=10)
            response.raise_for_status()

            # Parse XML
            root = ET.fromstring(response.content)

            # Handle namespace
            namespace = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}

            # Extract URLs
            for url_element in root.findall('.//ns:url/ns:loc', namespace):
                url = url_element.text
                if url and self.is_valid_url(url):
                    sitemap_urls.add(url)

            # Also check for sitemap index
            for sitemap_element in root.findall('.//ns:sitemap/ns:loc', namespace):
                try:
                    sub_sitemap_url = sitemap_element.text
                    sub_response = requests.get(sub_sitemap_url, timeout=10)
                    sub_root = ET.fromstring(sub_response.content)
                    for url_element in sub_root.findall('.//ns:url/ns:loc', namespace):
                        url = url_element.text
                        if url and self.is_valid_url(url):
                            sitemap_urls.add(url)
                except Exception as e:
                    print(f"Error fetching sub-sitemap {sub_sitemap_url}: {e}")

            print(f"Found {len(sitemap_urls)} URLs in sitemap")
            return sitemap_urls

        except Exception as e:
            print(f"Could not fetch sitemap: {e}")
            return set()

    def is_valid_url(self, url: str) -> bool:
        """Check if URL belongs to the same domain and is valid"""
        parsed = urlparse(url)

        # Check domain
        if parsed.netloc != self.domain:
            return False

        # Filter out file downloads
        if url.endswith(('.pdf', '.jpg', '.jpeg', '.png', '.gif', '.zip', '.doc', '.docx', '.xls', '.xlsx')):
            return False

        # Remove fragment (but keep the base URL)
        url_without_fragment = url.split('#')[0]

        # Filter out common non-content pages
        excluded_patterns = [
            r'/search\?',
            r'/login',
            r'/logout',
            r'/register',
            r'/api/',
            r'\.xml$',
            r'\.json$'
        ]

        for pattern in excluded_patterns:
            if re.search(pattern, url_without_fragment):
                return False

        return True

    def clean_text(self, text: str) -> str:
        """Clean extracted text"""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove leading/trailing whitespace
        text = text.strip()
        return text

    def extract_structured_content(self, element, depth=0) -> List[Dict]:
        """Extract content with structure preserved - RAG optimized"""
        sections = []

        # Process all direct children to maintain structure
        for child in element.children:
            if child.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                # Found a heading - start new section
                heading_text = self.clean_text(child.get_text())
                if heading_text:
                    sections.append({
                        'type': 'heading',
                        'level': int(child.name[1]),
                        'text': heading_text
                    })

            elif child.name == 'p':
                # Paragraph
                para_text = self.clean_text(child.get_text())
                if para_text and len(para_text) > 20:  # Filter out tiny paragraphs
                    sections.append({
                        'type': 'paragraph',
                        'text': para_text
                    })

            elif child.name in ['ul', 'ol']:
                # List
                list_items = []
                for li in child.find_all('li', recursive=False):
                    item_text = self.clean_text(li.get_text())
                    if item_text:
                        list_items.append(item_text)
                if list_items:
                    sections.append({
                        'type': 'list',
                        'items': list_items
                    })

            elif child.name == 'table':
                # Table
                table_data = []
                for row in child.find_all('tr'):
                    cells = [self.clean_text(cell.get_text()) for cell in row.find_all(['td', 'th'])]
                    if any(cells):  # Only add if not empty
                        table_data.append(cells)
                if table_data:
                    sections.append({
                        'type': 'table',
                        'data': table_data
                    })

            elif child.name in ['div', 'section', 'article'] and child.name:
                # Recursively process containers
                sub_sections = self.extract_structured_content(child, depth + 1)
                sections.extend(sub_sections)

        return sections

    def create_smart_chunks(self, text: str, heading: str = "", content_type: str = "text") -> List[Dict]:
        """Create optimally-sized chunks for RAG with overlap"""
        chunks = []
        sentences = re.split(r'(?<=[.!?])\s+', text)

        current_chunk = []
        current_tokens = 0

        for sentence in sentences:
            sentence_tokens = self.estimate_tokens(sentence)

            # If single sentence exceeds target, split it further
            if sentence_tokens > self.target_chunk_size:
                # Add current chunk if it has content
                if current_chunk:
                    chunks.append({
                        'id': f'chunk_{self.chunk_id_counter}',
                        'heading': heading,
                        'type': content_type,
                        'content': ' '.join(current_chunk),
                        'token_count': current_tokens
                    })
                    self.chunk_id_counter += 1
                    current_chunk = []
                    current_tokens = 0

                # Split long sentence by words
                words = sentence.split()
                word_chunk = []
                word_tokens = 0

                for word in words:
                    word_token_count = self.estimate_tokens(word)
                    if word_tokens + word_token_count > self.target_chunk_size:
                        if word_chunk:
                            chunks.append({
                                'id': f'chunk_{self.chunk_id_counter}',
                                'heading': heading,
                                'type': content_type,
                                'content': ' '.join(word_chunk),
                                'token_count': word_tokens
                            })
                            self.chunk_id_counter += 1
                        word_chunk = [word]
                        word_tokens = word_token_count
                    else:
                        word_chunk.append(word)
                        word_tokens += word_token_count

                if word_chunk:
                    current_chunk = word_chunk
                    current_tokens = word_tokens

            elif current_tokens + sentence_tokens > self.target_chunk_size:
                # Current chunk is full, save it
                if current_chunk:
                    chunks.append({
                        'id': f'chunk_{self.chunk_id_counter}',
                        'heading': heading,
                        'type': content_type,
                        'content': ' '.join(current_chunk),
                        'token_count': current_tokens
                    })
                    self.chunk_id_counter += 1

                # Start new chunk with overlap
                overlap_sentences = current_chunk[-2:] if len(current_chunk) >= 2 else current_chunk
                current_chunk = overlap_sentences + [sentence]
                current_tokens = self.estimate_tokens(' '.join(current_chunk))
            else:
                # Add to current chunk
                current_chunk.append(sentence)
                current_tokens += sentence_tokens

        # Add remaining chunk
        if current_chunk and current_tokens >= self.min_chunk_size:
            chunks.append({
                'id': f'chunk_{self.chunk_id_counter}',
                'heading': heading,
                'type': content_type,
                'content': ' '.join(current_chunk),
                'token_count': current_tokens
            })
            self.chunk_id_counter += 1

        return chunks

    def build_rag_content(self, sections: List[Dict], page_title: str = "") -> Dict:
        """Build RAG-friendly content from structured sections with smart chunking"""
        current_heading = ""
        content_chunks = []
        full_text_parts = []
        current_section_text = []

        def flush_section():
            """Process accumulated section text into chunks"""
            nonlocal current_section_text
            if current_section_text:
                section_text = ' '.join(current_section_text)
                if len(section_text.strip()) >= self.min_chunk_size:
                    smart_chunks = self.create_smart_chunks(
                        section_text,
                        heading=current_heading or page_title,
                        content_type='text'
                    )
                    content_chunks.extend(smart_chunks)
                current_section_text = []

        for section in sections:
            if section['type'] == 'heading':
                # Flush previous section before starting new one
                flush_section()
                current_heading = section['text']
                full_text_parts.append(f"\n## {current_heading}\n")

            elif section['type'] == 'paragraph':
                current_section_text.append(section['text'])
                full_text_parts.append(section['text'])
                full_text_parts.append('\n')

            elif section['type'] == 'list':
                # Flush accumulated text first
                flush_section()

                # Format list items
                list_text = '\n'.join([f"• {item}" for item in section['items']])
                list_chunks = self.create_smart_chunks(
                    list_text,
                    heading=current_heading or page_title,
                    content_type='list'
                )
                content_chunks.extend(list_chunks)
                full_text_parts.append(list_text)
                full_text_parts.append('\n')

            elif section['type'] == 'table':
                # Flush accumulated text first
                flush_section()

                # Format table with better structure preservation
                table_lines = []
                if section['data']:
                    # Create markdown-style table
                    headers = section['data'][0]
                    table_lines.append(' | '.join(headers))
                    table_lines.append('|'.join(['---' for _ in headers]))
                    for row in section['data'][1:]:
                        table_lines.append(' | '.join(row))

                table_text = '\n'.join(table_lines)
                chunk = {
                    'id': f'chunk_{self.chunk_id_counter}',
                    'heading': current_heading or page_title,
                    'type': 'table',
                    'content': table_text,
                    'token_count': self.estimate_tokens(table_text),
                    'table_data': section['data']  # Preserve structured data
                }
                content_chunks.append(chunk)
                self.chunk_id_counter += 1

                full_text_parts.append(table_text)
                full_text_parts.append('\n')

        # Flush any remaining section text
        flush_section()

        return {
            'chunks': content_chunks,
            'full_text': ''.join(full_text_parts).strip()
        }

    def extract_page_content(self, url: str, retry_count: int = 0) -> Optional[Dict]:
        """Extract content from a single page - RAG optimized with JavaScript support and retry logic"""
        try:
            print(f"Scraping: {url}")

            # Load page with Selenium
            self.driver.get(url)

            # Smart wait for content to load
            try:
                # Wait for body
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )

                # Wait for main content area to load (common patterns)
                try:
                    WebDriverWait(self.driver, 5).until(
                        lambda d: d.find_element(By.TAG_NAME, "main") or
                                  d.find_element(By.TAG_NAME, "article") or
                                  len(d.find_elements(By.CSS_SELECTOR, "[class*='content']")) > 0
                    )
                except TimeoutException:
                    pass  # Continue anyway

                # Wait for JavaScript to fully execute and content to stabilize
                time.sleep(2)

                # Check if content loaded by looking for text
                body_text = self.driver.find_element(By.TAG_NAME, "body").text
                if len(body_text.strip()) < 100:
                    # Very little content, might be loading issue
                    print(f"  Warning: Page has very little content, waiting longer...")
                    time.sleep(3)

            except TimeoutException:
                print(f"  Timeout waiting for page to load: {url}")

            # Get rendered HTML
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')

            # Remove noise elements
            for element in soup(['script', 'style', 'nav', 'footer', 'header', 'iframe', 'noscript']):
                element.decompose()

            # Remove common navigation/menu classes
            for cls in ['menu', 'navigation', 'nav', 'sidebar', 'breadcrumb', 'footer', 'header']:
                for element in soup.find_all(class_=re.compile(cls, re.I)):
                    element.decompose()

            # Extract metadata
            title = soup.find('title')
            title_text = self.clean_text(title.get_text()) if title else url.split('/')[-1]

            h1 = soup.find('h1')
            main_heading = self.clean_text(h1.get_text()) if h1 else ""

            meta_desc = soup.find('meta', attrs={'name': 'description'})
            description = meta_desc.get('content', '').strip() if meta_desc else ""

            # Find main content area
            main_content = (
                soup.find('main') or
                soup.find('article') or
                soup.find('div', class_=re.compile('content|main', re.I)) or
                soup.find('body')
            )

            # Extract structured content
            if main_content:
                sections = self.extract_structured_content(main_content)
                rag_content = self.build_rag_content(sections, page_title=title_text)
                content_text = rag_content['full_text']
                content_chunks = rag_content['chunks']
            else:
                content_text = ""
                content_chunks = []

            # Quality checks
            if len(content_text.strip()) < self.min_chunk_size:
                print(f"  Warning: Page has very little content ({len(content_text)} chars)")
                if retry_count < self.max_retries:
                    print(f"  Retrying... (attempt {retry_count + 1}/{self.max_retries})")
                    time.sleep(self.retry_delay)
                    return self.extract_page_content(url, retry_count + 1)

            # Check for duplicate content
            if self.is_duplicate_content(content_text):
                print(f"  Skipping duplicate content")
                return None

            # Detect language
            language = self.detect_language(content_text)

            # Extract URL category
            path_parts = [p for p in urlparse(url).path.split('/') if p]
            category = path_parts[1] if len(path_parts) > 1 else 'home'

            # Extract all links for crawling
            links = set()
            for link in soup.find_all('a', href=True):
                absolute_url = urljoin(url, link['href'])
                # Normalize URL (remove fragments, trailing slashes)
                absolute_url = absolute_url.split('#')[0].rstrip('/')
                if self.is_valid_url(absolute_url) and absolute_url != url:
                    links.add(absolute_url)

            # Build rich metadata for each chunk
            enriched_chunks = []
            for chunk in content_chunks:
                enriched_chunk = {
                    **chunk,
                    'page_url': url,
                    'page_title': title_text,
                    'page_heading': main_heading,
                    'page_description': description,
                    'language': language,
                    'category': category,
                    'scraped_at': datetime.now().isoformat(),
                    'source': 'Bank of Baku'
                }
                enriched_chunks.append(enriched_chunk)

            page_data = {
                'url': url,
                'title': title_text,
                'heading': main_heading,
                'description': description,
                'content': content_text,
                'chunks': enriched_chunks,
                'word_count': len(content_text.split()),
                'chunk_count': len(enriched_chunks),
                'language': language,
                'category': category,
                'scraped_at': datetime.now().isoformat(),
                'links': list(links)
            }

            print(f"  ✓ Extracted {len(enriched_chunks)} chunks, {len(links)} links")
            return page_data

        except Exception as e:
            error_msg = str(e)
            print(f"  Error scraping {url}: {error_msg[:200]}")

            # Check if it's a Chrome crash - restart driver
            if ("no such window" in error_msg or
                "target window already closed" in error_msg or
                "invalid session id" in error_msg or
                "session deleted" in error_msg or
                "disconnected" in error_msg):
                print(f"  Chrome crashed, restarting driver...", flush=True)
                try:
                    self.restart_driver()
                    # Retry immediately after restart
                    if retry_count < self.max_retries:
                        return self.extract_page_content(url, retry_count + 1)
                except Exception as restart_error:
                    print(f"  Failed to restart driver: {restart_error}")

            self.failed_urls[url] = error_msg

            # Normal retry logic for other errors
            if retry_count < self.max_retries:
                print(f"  Retrying... (attempt {retry_count + 1}/{self.max_retries})")
                time.sleep(self.retry_delay)
                return self.extract_page_content(url, retry_count + 1)

            return None

    def crawl(self, start_url: str = None, max_pages: int = 500, use_sitemap: bool = True):
        """Crawl website with comprehensive page discovery"""
        if start_url is None:
            start_url = self.base_url

        # Start with sitemap URLs if available
        if use_sitemap:
            print("\n=== Phase 1: Discovering URLs from sitemap ===")
            sitemap_urls = self.fetch_sitemap_urls()
            if sitemap_urls:
                self.discovered_urls.update(sitemap_urls)
                print(f"Added {len(sitemap_urls)} URLs from sitemap")

        # Initialize crawl queue
        urls_to_visit = set(self.discovered_urls) if self.discovered_urls else {start_url}
        urls_to_visit.add(start_url)

        # Remove already visited URLs
        urls_to_visit -= self.visited_urls

        print(f"\n=== Phase 2: Crawling {len(urls_to_visit)} discovered URLs ===")
        print(f"Already visited: {len(self.visited_urls)}")
        print(f"Max pages: {max_pages}")

        try:
            processed_count = 0
            pages_since_restart = 0

            while urls_to_visit and len(self.visited_urls) < max_pages:
                # Normalize URL before processing
                url = urls_to_visit.pop()
                url = url.rstrip('/')

                if url in self.visited_urls:
                    continue

                # Preventive Chrome restart every 10 pages
                if pages_since_restart >= 10:
                    print(f"\n  Preventive Chrome restart after {pages_since_restart} pages...")
                    try:
                        self.restart_driver()
                        pages_since_restart = 0
                    except Exception as e:
                        print(f"  Warning: Could not restart driver: {e}")

                # Show progress
                processed_count += 1
                print(f"\n[{processed_count}/{min(len(urls_to_visit) + processed_count, max_pages)}] ", end='', flush=True)

                self.visited_urls.add(url)
                page_data = self.extract_page_content(url)

                if page_data:
                    self.scraped_data.append(page_data)
                    pages_since_restart += 1

                    # Add new links to visit
                    for link in page_data['links']:
                        normalized_link = link.rstrip('/')
                        self.discovered_urls.add(normalized_link)
                        if normalized_link not in self.visited_urls and normalized_link not in urls_to_visit:
                            urls_to_visit.add(normalized_link)

                # Be polite - add delay between requests
                time.sleep(1)

                # Save progress periodically
                if len(self.scraped_data) % 10 == 0 and len(self.scraped_data) > 0:
                    self.save_progress()
                    self.save_checkpoint()
                    print(f"\n  Progress saved: {len(self.scraped_data)} pages scraped, {len(urls_to_visit)} remaining", flush=True)

            print(f"\n\n{'='*80}")
            print(f"Crawling complete!")
            print(f"{'='*80}")
            print(f"Pages scraped: {len(self.scraped_data)}")
            print(f"Pages visited: {len(self.visited_urls)}")
            print(f"Pages discovered: {len(self.discovered_urls)}")
            print(f"Failed URLs: {len(self.failed_urls)}")
            print(f"Coverage: {len(self.visited_urls) / len(self.discovered_urls) * 100:.1f}%")

        except KeyboardInterrupt:
            print("\n\nCrawling interrupted by user!")
            print("Saving progress...")
            self.save_progress()
            self.save_checkpoint()

        finally:
            # Always cleanup browser
            if hasattr(self, 'driver'):
                print("Closing browser...")
                self.driver.quit()

    def save_progress(self):
        """Save scraped data to file"""
        output_file = os.path.join(self.output_dir, 'bank_of_baku_data.json')
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.scraped_data, f, ensure_ascii=False, indent=2)
        print(f"Progress saved: {len(self.scraped_data)} pages")

    def save_for_rag(self):
        """Save data in RAG-friendly formats with enhanced metadata"""
        print("\nSaving data in RAG-optimized formats...")

        # Save full data as JSON (including chunks)
        json_file = os.path.join(self.output_dir, 'bank_of_baku_rag.json')
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(self.scraped_data, f, ensure_ascii=False, indent=2)

        # Save chunks separately for easier RAG integration
        chunks_file = os.path.join(self.output_dir, 'bank_of_baku_chunks.json')
        all_chunks = []
        for page in self.scraped_data:
            for chunk in page.get('chunks', []):
                # Chunks already have enriched metadata
                all_chunks.append(chunk)

        with open(chunks_file, 'w', encoding='utf-8') as f:
            json.dump(all_chunks, f, ensure_ascii=False, indent=2)

        # Save chunks in JSONL format (one JSON object per line) for streaming
        jsonl_file = os.path.join(self.output_dir, 'bank_of_baku_chunks.jsonl')
        with open(jsonl_file, 'w', encoding='utf-8') as f:
            for chunk in all_chunks:
                f.write(json.dumps(chunk, ensure_ascii=False) + '\n')

        # Group chunks by category for easier filtering
        chunks_by_category = defaultdict(list)
        for chunk in all_chunks:
            chunks_by_category[chunk.get('category', 'unknown')].append(chunk)

        category_dir = os.path.join(self.output_dir, 'chunks_by_category')
        os.makedirs(category_dir, exist_ok=True)
        for category, chunks in chunks_by_category.items():
            cat_file = os.path.join(category_dir, f'{category}.json')
            with open(cat_file, 'w', encoding='utf-8') as f:
                json.dump(chunks, f, ensure_ascii=False, indent=2)

        # Save as individual text files (one per page)
        text_dir = os.path.join(self.output_dir, 'text_files')
        os.makedirs(text_dir, exist_ok=True)

        for idx, page in enumerate(self.scraped_data):
            # Create filename from URL
            safe_filename = re.sub(r'[^\w\-_\. ]', '_', page['url'].split('/')[-1] or f'page_{idx}')
            text_file = os.path.join(text_dir, f'{idx:04d}_{safe_filename}.txt')

            with open(text_file, 'w', encoding='utf-8') as f:
                f.write(f"Title: {page['title']}\n")
                f.write(f"URL: {page['url']}\n")
                if page['heading']:
                    f.write(f"Heading: {page['heading']}\n")
                if page['description']:
                    f.write(f"Description: {page['description']}\n")
                f.write(f"\n{'='*60}\n\n")
                f.write(page['content'])
                f.write('\n')

        # Save as single combined text file
        combined_file = os.path.join(self.output_dir, 'bank_of_baku_combined.txt')
        with open(combined_file, 'w', encoding='utf-8') as f:
            for page in self.scraped_data:
                f.write(f"\n{'='*80}\n")
                f.write(f"Title: {page['title']}\n")
                f.write(f"URL: {page['url']}\n")
                f.write(f"{'='*80}\n\n")
                f.write(page['content'])
                f.write('\n\n')

        # Calculate statistics by category and language
        stats_by_category = defaultdict(lambda: {'pages': 0, 'chunks': 0, 'words': 0})
        stats_by_language = defaultdict(lambda: {'pages': 0, 'chunks': 0, 'words': 0})

        for page in self.scraped_data:
            category = page.get('category', 'unknown')
            language = page.get('language', 'unknown')

            stats_by_category[category]['pages'] += 1
            stats_by_category[category]['chunks'] += page.get('chunk_count', 0)
            stats_by_category[category]['words'] += page.get('word_count', 0)

            stats_by_language[language]['pages'] += 1
            stats_by_language[language]['chunks'] += page.get('chunk_count', 0)
            stats_by_language[language]['words'] += page.get('word_count', 0)

        # Calculate token statistics
        total_tokens = sum(chunk.get('token_count', 0) for chunk in all_chunks)
        avg_tokens_per_chunk = total_tokens / len(all_chunks) if all_chunks else 0

        # Save comprehensive metadata
        metadata = {
            'scrape_info': {
                'base_url': self.base_url,
                'scraped_at': datetime.now().isoformat(),
                'scraper_version': '2.0_enhanced'
            },
            'statistics': {
                'total_pages': len(self.scraped_data),
                'total_chunks': len(all_chunks),
                'total_words': sum(page['word_count'] for page in self.scraped_data),
                'total_tokens': total_tokens,
                'avg_tokens_per_chunk': round(avg_tokens_per_chunk, 2),
                'pages_discovered': len(self.discovered_urls),
                'pages_visited': len(self.visited_urls),
                'pages_failed': len(self.failed_urls),
                'coverage_percentage': round(len(self.visited_urls) / len(self.discovered_urls) * 100, 2) if self.discovered_urls else 0
            },
            'by_category': dict(stats_by_category),
            'by_language': dict(stats_by_language),
            'urls_scraped': [page['url'] for page in self.scraped_data],
            'failed_urls': self.failed_urls
        }

        metadata_file = os.path.join(self.output_dir, 'metadata.json')
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

        print(f"\n{'='*80}")
        print(f"✓ Data saved to {self.output_dir}/")
        print(f"{'='*80}")
        print(f"  - Full JSON: bank_of_baku_rag.json")
        print(f"  - RAG Chunks: bank_of_baku_chunks.json")
        print(f"  - JSONL Chunks: bank_of_baku_chunks.jsonl")
        print(f"  - By Category: chunks_by_category/")
        print(f"  - Individual files: text_files/")
        print(f"  - Combined text: bank_of_baku_combined.txt")
        print(f"  - Metadata: metadata.json")
        print(f"\n{'='*80}")
        print(f"STATISTICS")
        print(f"{'='*80}")
        print(f"Total pages: {metadata['statistics']['total_pages']}")
        print(f"Total chunks: {metadata['statistics']['total_chunks']}")
        print(f"Total words: {metadata['statistics']['total_words']:,}")
        print(f"Total tokens: {metadata['statistics']['total_tokens']:,}")
        print(f"Avg tokens/chunk: {metadata['statistics']['avg_tokens_per_chunk']}")
        print(f"Coverage: {metadata['statistics']['coverage_percentage']:.1f}%")
        print(f"\nBy Category:")
        for category, stats in sorted(stats_by_category.items(), key=lambda x: x[1]['pages'], reverse=True):
            print(f"  - {category}: {stats['pages']} pages, {stats['chunks']} chunks")
        print(f"\nBy Language:")
        for language, stats in sorted(stats_by_language.items(), key=lambda x: x[1]['pages'], reverse=True):
            print(f"  - {language}: {stats['pages']} pages, {stats['chunks']} chunks")

    def generate_verification_report(self):
        """Generate a detailed verification and quality report"""
        report = []
        report.append("=" * 80)
        report.append("SCRAPING VERIFICATION & QUALITY REPORT")
        report.append("=" * 80)
        report.append(f"\nBase URL: {self.base_url}")
        report.append(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Scraper Version: 2.0 Enhanced")

        # Statistics
        report.append(f"\n{'-' * 80}")
        report.append("COVERAGE STATISTICS")
        report.append(f"{'-' * 80}")
        report.append(f"Total URLs discovered: {len(self.discovered_urls)}")
        report.append(f"Total URLs visited: {len(self.visited_urls)}")
        report.append(f"Successfully scraped: {len(self.scraped_data)}")
        report.append(f"Failed URLs: {len(self.failed_urls)}")
        report.append(f"Unvisited URLs: {len(self.discovered_urls - self.visited_urls)}")

        # Calculate coverage
        coverage = 0
        if self.discovered_urls:
            coverage = (len(self.visited_urls) / len(self.discovered_urls)) * 100
            report.append(f"Coverage: {coverage:.1f}%")

        # Content statistics
        total_words = sum(page.get('word_count', 0) for page in self.scraped_data)
        total_chunks = sum(page.get('chunk_count', 0) for page in self.scraped_data)
        avg_words = total_words / len(self.scraped_data) if self.scraped_data else 0
        avg_chunks = total_chunks / len(self.scraped_data) if self.scraped_data else 0

        report.append(f"\n{'-' * 80}")
        report.append("CONTENT STATISTICS")
        report.append(f"{'-' * 80}")
        report.append(f"Total words extracted: {total_words:,}")
        report.append(f"Total chunks created: {total_chunks:,}")
        report.append(f"Average words per page: {avg_words:.0f}")
        report.append(f"Average chunks per page: {avg_chunks:.1f}")

        # Data quality metrics
        report.append(f"\n{'-' * 80}")
        report.append("DATA QUALITY METRICS")
        report.append(f"{'-' * 80}")

        # Check for pages with low content
        low_content_pages = [p for p in self.scraped_data if p.get('word_count', 0) < 100]
        report.append(f"Pages with low content (<100 words): {len(low_content_pages)}")

        # Language distribution
        lang_dist = defaultdict(int)
        for page in self.scraped_data:
            lang_dist[page.get('language', 'unknown')] += 1
        report.append(f"\nLanguage distribution:")
        for lang, count in sorted(lang_dist.items(), key=lambda x: x[1], reverse=True):
            report.append(f"  - {lang}: {count} pages ({count/len(self.scraped_data)*100:.1f}%)")

        # Unique content check
        report.append(f"\nUnique content hashes: {len(self.content_hashes)}")
        duplicates_detected = len(self.scraped_data) - len(self.content_hashes)
        if duplicates_detected > 0:
            report.append(f"Duplicate pages filtered: {duplicates_detected}")

        # Chunk size distribution
        chunk_sizes = []
        for page in self.scraped_data:
            for chunk in page.get('chunks', []):
                chunk_sizes.append(chunk.get('token_count', 0))

        if chunk_sizes:
            report.append(f"\nChunk token distribution:")
            report.append(f"  - Min: {min(chunk_sizes)}")
            report.append(f"  - Max: {max(chunk_sizes)}")
            report.append(f"  - Avg: {sum(chunk_sizes) / len(chunk_sizes):.0f}")
            report.append(f"  - Target: {self.target_chunk_size}")

            # Check chunk quality
            optimal_chunks = len([s for s in chunk_sizes if 256 <= s <= 768])
            report.append(f"  - Chunks in optimal range (256-768): {optimal_chunks} ({optimal_chunks/len(chunk_sizes)*100:.1f}%)")

        # Page categories
        report.append(f"\n{'-' * 80}")
        report.append("PAGE CATEGORIES")
        report.append(f"{'-' * 80}")
        categories = {}
        for page in self.scraped_data:
            # Extract category from URL path
            path = urlparse(page['url']).path
            parts = [p for p in path.split('/') if p]
            category = parts[1] if len(parts) > 1 else 'root'
            categories[category] = categories.get(category, 0) + 1

        for category, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
            report.append(f"  {category}: {count} pages")

        # Failed URLs
        if self.failed_urls:
            report.append(f"\n{'-' * 80}")
            report.append("FAILED URLS")
            report.append(f"{'-' * 80}")
            for url, error in sorted(self.failed_urls.items())[:20]:  # Show first 20
                report.append(f"  ✗ {url}")
                report.append(f"    Error: {error}")
            if len(self.failed_urls) > 20:
                report.append(f"  ... and {len(self.failed_urls) - 20} more (see metadata.json)")

        # Unvisited URLs
        unvisited = self.discovered_urls - self.visited_urls
        if unvisited:
            report.append(f"\n{'-' * 80}")
            report.append("UNVISITED URLS (Discovered but not scraped)")
            report.append(f"{'-' * 80}")
            for url in sorted(list(unvisited)[:30]):  # Show first 30
                report.append(f"  - {url}")
            if len(unvisited) > 30:
                report.append(f"  ... and {len(unvisited) - 30} more")

        # RAG Readiness Assessment
        report.append(f"\n{'-' * 80}")
        report.append("RAG READINESS ASSESSMENT")
        report.append(f"{'-' * 80}")

        rag_score = 0
        max_score = 100

        # Coverage check (30 points)
        if coverage >= 95:
            report.append("✓ EXCELLENT Coverage: Over 95% of pages scraped (+30)")
            rag_score += 30
        elif coverage >= 80:
            report.append("✓ GOOD Coverage: Over 80% of pages scraped (+25)")
            rag_score += 25
        elif coverage >= 60:
            report.append("⚠ MODERATE Coverage: 60-80% of pages scraped (+15)")
            rag_score += 15
        else:
            report.append("✗ LOW Coverage: Less than 60% scraped (+5)")
            rag_score += 5

        # Chunk quality check (30 points)
        if chunk_sizes and optimal_chunks:
            optimal_ratio = optimal_chunks / len(chunk_sizes)
            if optimal_ratio >= 0.8:
                report.append(f"✓ EXCELLENT Chunk Quality: {optimal_ratio*100:.1f}% optimal size (+30)")
                rag_score += 30
            elif optimal_ratio >= 0.6:
                report.append(f"✓ GOOD Chunk Quality: {optimal_ratio*100:.1f}% optimal size (+25)")
                rag_score += 25
            else:
                report.append(f"⚠ MODERATE Chunk Quality: {optimal_ratio*100:.1f}% optimal size (+15)")
                rag_score += 15

        # Content volume check (20 points)
        if len(self.scraped_data) >= 100:
            report.append(f"✓ EXCELLENT Volume: {len(self.scraped_data)} pages (+20)")
            rag_score += 20
        elif len(self.scraped_data) >= 50:
            report.append(f"✓ GOOD Volume: {len(self.scraped_data)} pages (+15)")
            rag_score += 15
        else:
            report.append(f"⚠ LOW Volume: Only {len(self.scraped_data)} pages (+5)")
            rag_score += 5

        # Data quality check (20 points)
        quality_score = 20
        if low_content_pages:
            quality_penalty = min(10, len(low_content_pages) / len(self.scraped_data) * 20)
            quality_score -= quality_penalty
            report.append(f"⚠ Low content pages detected: {len(low_content_pages)} (-{quality_penalty:.0f})")

        if self.failed_urls:
            fail_penalty = min(10, len(self.failed_urls) / len(self.discovered_urls) * 20)
            quality_score -= fail_penalty
            report.append(f"⚠ Failed URLs: {len(self.failed_urls)} (-{fail_penalty:.0f})")

        if quality_score >= 18:
            report.append(f"✓ EXCELLENT Data Quality (+{quality_score:.0f})")
        elif quality_score >= 15:
            report.append(f"✓ GOOD Data Quality (+{quality_score:.0f})")
        else:
            report.append(f"⚠ MODERATE Data Quality (+{quality_score:.0f})")

        rag_score += quality_score

        # Overall RAG score
        report.append(f"\n{'-' * 80}")
        report.append(f"OVERALL RAG READINESS SCORE: {rag_score}/{max_score}")
        report.append(f"{'-' * 80}")

        if rag_score >= 85:
            report.append("✓✓ EXCELLENT - Data is highly optimized for RAG!")
        elif rag_score >= 70:
            report.append("✓ GOOD - Data is ready for RAG with minor improvements possible")
        elif rag_score >= 50:
            report.append("⚠ FAIR - Data is usable but improvements recommended")
        else:
            report.append("✗ POOR - Significant improvements needed before RAG use")

        # Recommendations
        report.append(f"\n{'-' * 80}")
        report.append("RECOMMENDATIONS")
        report.append(f"{'-' * 80}")

        if coverage >= 90 and rag_score >= 80:
            report.append("✓ Data collection is complete and high-quality!")
            report.append("✓ Ready for RAG application use")
            report.append("\nNext steps:")
            report.append("  1. Load chunks from bank_of_baku_chunks.json")
            report.append("  2. Generate embeddings (e.g., OpenAI, Cohere, or local models)")
            report.append("  3. Store in vector database (e.g., Pinecone, Weaviate, Chroma)")
            report.append("  4. Implement retrieval and generation pipeline")
        else:
            if coverage < 90:
                report.append("⚠ Coverage improvement needed:")
                report.append("  - Review unvisited URLs")
                report.append("  - Increase max_pages limit")
                report.append("  - Check for JavaScript-heavy pages")

            if low_content_pages:
                report.append("\n⚠ Content quality improvement:")
                report.append("  - Review pages with low content")
                report.append("  - Check for blocked/restricted pages")
                report.append("  - Verify page parsing logic")

            if self.failed_urls:
                report.append("\n⚠ Failed URLs need attention:")
                report.append("  - Review error messages in metadata.json")
                report.append("  - Check for rate limiting or blocking")
                report.append("  - Consider manual review")

        report.append(f"\n{'=' * 80}")

        # Save report
        report_text = '\n'.join(report)
        report_file = os.path.join(self.output_dir, 'verification_report.txt')
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report_text)

        print(report_text)
        print(f"\n✓ Verification report saved to: {report_file}")

        return report_text


def main():
    """Main execution function"""
    print("=" * 80)
    print("Bank of Baku Website Scraper - Enhanced v2.0")
    print("Optimized for RAG with smart chunking and complete coverage")
    print("=" * 80)

    scraper = BankOfBakuScraper(
        base_url="http://bankofbaku.com/az",
        output_dir="scraped_data"
    )

    print("\nStarting comprehensive crawl...")
    print("Features enabled:")
    print("  ✓ Sitemap-based discovery")
    print("  ✓ Smart content chunking (target: 512 tokens)")
    print("  ✓ Duplicate detection")
    print("  ✓ Language detection")
    print("  ✓ Retry logic for failed pages")
    print("  ✓ Checkpoint system for resumption")

    scraper.crawl(max_pages=500, use_sitemap=True)

    print("\nSaving data for RAG application...")
    scraper.save_for_rag()

    print("\nGenerating verification report...")
    scraper.generate_verification_report()

    print("\n" + "=" * 80)
    print("✓ Scraping complete!")
    print("=" * 80)
    print("\nData is ready for RAG! Check these files:")
    print("  - bank_of_baku_chunks.json (recommended for RAG)")
    print("  - bank_of_baku_chunks.jsonl (for streaming)")
    print("  - chunks_by_category/ (filtered by topic)")
    print("  - verification_report.txt (quality assessment)")


if __name__ == "__main__":
    main()
