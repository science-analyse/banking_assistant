"""
Improved Web scraper for Bank of Baku card pages
Extracts high-quality data for RAG (Retrieval-Augmented Generation)
"""

import requests
from bs4 import BeautifulSoup
import json
import time
from typing import List, Dict, Any
from pathlib import Path
import re
from collections import OrderedDict


class ImprovedBankOfBakuScraper:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def read_urls_from_file(self, file_path: str) -> List[str]:
        """Read URLs from a text file"""
        with open(file_path, 'r', encoding='utf-8') as f:
            urls = [line.strip() for line in f if line.strip()]
        return urls

    def clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        if not text:
            return ""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove leading/trailing whitespace
        text = text.strip()
        return text

    def remove_duplicates(self, texts: List[str]) -> List[str]:
        """Remove duplicate consecutive texts while preserving order"""
        if not texts:
            return []

        seen = OrderedDict()
        for text in texts:
            # Use a normalized version for comparison
            normalized = text.lower().strip()
            if normalized and normalized not in seen:
                seen[normalized] = text

        return list(seen.values())

    def extract_page_content(self, url: str) -> Dict[str, Any]:
        """Extract high-quality content from a single page"""
        try:
            print(f"Scraping: {url}")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            response.encoding = 'utf-8'

            soup = BeautifulSoup(response.content, 'html.parser')

            # Extract title - try multiple approaches
            title = ""

            # Try h1 first
            h1_tag = soup.find('h1')
            if h1_tag:
                title = self.clean_text(h1_tag.get_text())

            # If no h1 or empty, try meta title
            if not title:
                meta_title = soup.find('meta', property='og:title')
                if meta_title:
                    title = self.clean_text(meta_title.get('content', ''))

            # If still no title, try page title tag
            if not title:
                title_tag = soup.find('title')
                if title_tag:
                    title = self.clean_text(title_tag.get_text())
                    # Remove common suffixes
                    title = re.sub(r'\s*[\|\-]\s*Bank of Baku.*$', '', title, flags=re.IGNORECASE)

            # Remove unwanted elements
            for element in soup(['script', 'style', 'nav', 'footer', 'header',
                                'iframe', 'noscript', 'form', 'button']):
                element.decompose()

            # Also remove common navigation/menu classes
            for nav_class in ['menu', 'nav', 'navigation', 'sidebar', 'footer-',
                             'header-', 'breadcrumb', 'social', 'share']:
                for element in soup.find_all(class_=lambda x: x and nav_class in x.lower()):
                    element.decompose()

            # Extract main content - try to find the main content area
            main_content = None

            # Try various content selectors
            content_selectors = [
                ('main', {}),
                ('article', {}),
                ('div', {'class': re.compile(r'content|main|page|product|card|detail', re.I)}),
                ('div', {'id': re.compile(r'content|main|page', re.I)}),
            ]

            for tag, attrs in content_selectors:
                main_content = soup.find(tag, attrs)
                if main_content:
                    break

            # If still nothing, use body
            if not main_content:
                main_content = soup.find('body')

            # Extract meaningful paragraphs and sections
            paragraphs = []
            seen_texts = set()

            if main_content:
                # Process headings and paragraphs separately for better structure
                for element in main_content.find_all(['h1', 'h2', 'h3', 'h4', 'p', 'li', 'td', 'div']):
                    # Skip if element contains other block elements (likely a container)
                    if element.find(['h1', 'h2', 'h3', 'h4', 'p', 'div']):
                        continue

                    text = self.clean_text(element.get_text())

                    # Filter criteria
                    if not text:
                        continue
                    if len(text) < 15:  # Too short
                        continue
                    if text in seen_texts:  # Duplicate
                        continue
                    if text.count(' ') < 2:  # Not enough words
                        continue

                    # Skip navigation-like text
                    nav_keywords = ['kartlar', 'kreditlər', 'əmanətlər', 'onlayn xidmətlər',
                                   'bank haqqında', 'müraciət et', 'prevnext']
                    if any(text.lower().startswith(kw) for kw in nav_keywords) and len(text) < 100:
                        continue

                    seen_texts.add(text)

                    # Add heading marker for better chunking later
                    if element.name in ['h1', 'h2', 'h3', 'h4']:
                        paragraphs.append(f"## {text}")
                    else:
                        paragraphs.append(text)

            # Join paragraphs with double newline
            content_text = '\n\n'.join(paragraphs)

            # Extract features/list items separately
            features = []
            seen_features = set()

            if main_content:
                for ul in main_content.find_all(['ul', 'ol']):
                    for li in ul.find_all('li', recursive=False):
                        feature_text = self.clean_text(li.get_text())
                        if feature_text and len(feature_text) > 10 and feature_text not in seen_features:
                            seen_features.add(feature_text)
                            features.append(feature_text)

            # Determine card type from URL
            card_type = "credit" if "/kredit-kartlari/" in url else "debet"

            # Extract card name/product name from URL or title
            card_name = title
            if not card_name and url:
                # Try to extract from URL
                parts = url.rstrip('/').split('/')
                if parts:
                    card_name = parts[-1].replace('-', ' ').title()

            return {
                'url': url,
                'title': title,
                'card_name': card_name,
                'card_type': card_type,
                'content': content_text,
                'features': features[:20],  # Limit to 20 most relevant features
                'word_count': len(content_text.split()),
                'paragraph_count': len(paragraphs),
                'scraped_at': time.strftime('%Y-%m-%d %H:%M:%S')
            }

        except Exception as e:
            print(f"Error scraping {url}: {str(e)}")
            return {
                'url': url,
                'error': str(e),
                'scraped_at': time.strftime('%Y-%m-%d %H:%M:%S')
            }

    def create_smart_chunks(self, data: Dict[str, Any], chunk_size: int = 400, overlap: int = 50) -> List[Dict[str, Any]]:
        """
        Create intelligent chunks with overlap for better RAG retrieval
        """
        chunks = []
        content = data.get('content', '')

        if not content:
            return chunks

        # Split by double newline (paragraphs)
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]

        if not paragraphs:
            return chunks

        current_chunk = ""
        current_words = []
        chunk_id = 0

        for para in paragraphs:
            para_words = para.split()

            # If adding this paragraph would exceed chunk size
            if len(current_words) + len(para_words) > chunk_size:
                # Save current chunk if it's not empty
                if current_chunk:
                    chunks.append({
                        'chunk_id': chunk_id,
                        'text': current_chunk.strip(),
                        'word_count': len(current_words),
                        'metadata': {
                            'source_url': data['url'],
                            'title': data['title'],
                            'card_name': data.get('card_name', ''),
                            'card_type': data['card_type'],
                            'chunk_index': chunk_id,
                            'total_chunks': 0  # Will update at the end
                        }
                    })
                    chunk_id += 1

                    # Create overlap: keep last 'overlap' words
                    if len(current_words) > overlap:
                        overlap_words = current_words[-overlap:]
                        current_chunk = ' '.join(overlap_words) + '\n\n' + para
                        current_words = overlap_words + para_words
                    else:
                        current_chunk = para
                        current_words = para_words
                else:
                    # Paragraph is very long, split it
                    if len(para_words) > chunk_size:
                        for i in range(0, len(para_words), chunk_size - overlap):
                            chunk_words = para_words[i:i + chunk_size]
                            chunks.append({
                                'chunk_id': chunk_id,
                                'text': ' '.join(chunk_words),
                                'word_count': len(chunk_words),
                                'metadata': {
                                    'source_url': data['url'],
                                    'title': data['title'],
                                    'card_name': data.get('card_name', ''),
                                    'card_type': data['card_type'],
                                    'chunk_index': chunk_id,
                                    'total_chunks': 0
                                }
                            })
                            chunk_id += 1
                        current_chunk = ""
                        current_words = []
                    else:
                        current_chunk = para
                        current_words = para_words
            else:
                # Add paragraph to current chunk
                if current_chunk:
                    current_chunk += '\n\n' + para
                else:
                    current_chunk = para
                current_words.extend(para_words)

        # Add the last chunk
        if current_chunk.strip():
            chunks.append({
                'chunk_id': chunk_id,
                'text': current_chunk.strip(),
                'word_count': len(current_words),
                'metadata': {
                    'source_url': data['url'],
                    'title': data['title'],
                    'card_name': data.get('card_name', ''),
                    'card_type': data['card_type'],
                    'chunk_index': chunk_id,
                    'total_chunks': 0
                }
            })

        # Update total_chunks in all chunks
        total = len(chunks)
        for chunk in chunks:
            chunk['metadata']['total_chunks'] = total

        return chunks

    def scrape_all_urls(self, url_files: List[str], delay: float = 1.0) -> List[Dict[str, Any]]:
        """Scrape all URLs from multiple files"""
        all_data = []

        for url_file in url_files:
            print(f"\nReading URLs from: {url_file}")
            urls = self.read_urls_from_file(url_file)
            print(f"Found {len(urls)} URLs")

            for url in urls:
                data = self.extract_page_content(url)
                all_data.append(data)
                time.sleep(delay)

        return all_data

    def save_data(self, data: List[Dict[str, Any]], output_dir: str = 'data'):
        """Save scraped data in multiple formats suitable for RAG"""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        # 1. Save raw scraped data
        with open(output_path / 'raw_data.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Saved raw data to {output_path / 'raw_data.json'}")

        # 2. Create and save RAG-formatted chunks
        all_chunks = []
        for item in data:
            if 'error' not in item:
                chunks = self.create_smart_chunks(item, chunk_size=400, overlap=50)
                all_chunks.extend(chunks)

        # Save as JSON
        with open(output_path / 'rag_chunks.json', 'w', encoding='utf-8') as f:
            json.dump(all_chunks, f, ensure_ascii=False, indent=2)
        print(f"Saved {len(all_chunks)} RAG chunks to {output_path / 'rag_chunks.json'}")

        # Save as JSONL
        with open(output_path / 'rag_chunks.jsonl', 'w', encoding='utf-8') as f:
            for chunk in all_chunks:
                f.write(json.dumps(chunk, ensure_ascii=False) + '\n')
        print(f"Saved RAG chunks to {output_path / 'rag_chunks.jsonl'}")

        # 3. Create detailed statistics
        total_words = sum(d.get('word_count', 0) for d in data if 'error' not in d)
        avg_chunks_per_page = len(all_chunks) / len([d for d in data if 'error' not in d]) if data else 0

        stats = {
            'total_pages': len(data),
            'successful_scrapes': len([d for d in data if 'error' not in d]),
            'failed_scrapes': len([d for d in data if 'error' in d]),
            'total_chunks': len(all_chunks),
            'avg_chunks_per_page': round(avg_chunks_per_page, 2),
            'card_types': {
                'credit': len([d for d in data if d.get('card_type') == 'credit']),
                'debet': len([d for d in data if d.get('card_type') == 'debet'])
            },
            'total_words': total_words,
            'avg_words_per_chunk': round(sum(c.get('word_count', 0) for c in all_chunks) / len(all_chunks), 2) if all_chunks else 0,
            'quality_metrics': {
                'pages_with_titles': len([d for d in data if d.get('title') and 'error' not in d]),
                'pages_with_content': len([d for d in data if d.get('word_count', 0) > 100 and 'error' not in d]),
                'avg_paragraphs_per_page': round(sum(d.get('paragraph_count', 0) for d in data if 'error' not in d) / len([d for d in data if 'error' not in d]), 2) if data else 0
            }
        }

        with open(output_path / 'stats.json', 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)

        print(f"\n{'='*60}")
        print(f"Scraping Statistics:")
        print(f"  Total pages: {stats['total_pages']}")
        print(f"  Successful: {stats['successful_scrapes']}")
        print(f"  Failed: {stats['failed_scrapes']}")
        print(f"  Total chunks: {stats['total_chunks']}")
        print(f"  Avg chunks per page: {stats['avg_chunks_per_page']}")
        print(f"  Credit cards: {stats['card_types']['credit']}")
        print(f"  Debet cards: {stats['card_types']['debet']}")
        print(f"  Total words: {stats['total_words']}")
        print(f"  Avg words per chunk: {stats['avg_words_per_chunk']}")
        print(f"\nQuality Metrics:")
        print(f"  Pages with titles: {stats['quality_metrics']['pages_with_titles']}")
        print(f"  Pages with content (>100 words): {stats['quality_metrics']['pages_with_content']}")
        print(f"  Avg paragraphs per page: {stats['quality_metrics']['avg_paragraphs_per_page']}")

        return stats


def main():
    """Main execution function"""
    scraper = ImprovedBankOfBakuScraper()

    # Define URL files
    url_files = [
        'data/credit cards urls.txt',
        'data/debet cards urls.txt'
    ]

    # Scrape all URLs
    print("Starting improved web scraping...")
    print("=" * 60)
    data = scraper.scrape_all_urls(url_files, delay=1.0)

    # Save data
    print("\n" + "=" * 60)
    print("Saving data...")
    stats = scraper.save_data(data)

    print("\n" + "=" * 60)
    print("Scraping completed successfully!")
    print(f"Check the 'data' folder for high-quality RAG-ready data")


if __name__ == "__main__":
    main()
