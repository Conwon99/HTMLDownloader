import streamlit as st
import requests
from bs4 import BeautifulSoup
from PIL import Image
import urllib.parse
import urllib.request
import os
import zipfile
import io
import tempfile
from pathlib import Path
import base64
from typing import List, Dict, Tuple, Optional, Set
import time
import re
from urllib.robotparser import RobotFileParser

# Set page config
st.set_page_config(
    page_title="Web Scraper & Image Extractor",
    page_icon="🕷️",
    layout="wide"
)

class WebScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.visited_urls = set()
        self.found_urls = set()
        self.base_domain = None
    
    def get_html_content(self, url: str) -> Tuple[str, BeautifulSoup]:
        """Fetch and return HTML content and BeautifulSoup object"""
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            return response.text, soup
        except requests.RequestException as e:
            raise Exception(f"Failed to fetch HTML: {str(e)}")
    
    def find_images(self, soup: BeautifulSoup, base_url: str) -> List[Dict]:
        """Find all images and their locations in the webpage"""
        images = []
        
        # Find all img tags
        img_tags = soup.find_all('img')
        
        for idx, img in enumerate(img_tags):
            src = img.get('src')
            if not src:
                continue
                
            # Convert relative URLs to absolute
            if src.startswith('//'):
                src = 'https:' + src
            elif src.startswith('/'):
                src = urllib.parse.urljoin(base_url, src)
            elif not src.startswith(('http://', 'https://')):
                src = urllib.parse.urljoin(base_url, src)
            
            # Find the section/context where the image is located
            location = self.get_image_location(img)
            
            images.append({
                'url': src,
                'alt': img.get('alt', ''),
                'location': location,
                'index': idx + 1,
                'element': img
            })
        
        return images
    
    def get_image_location(self, img_element) -> str:
        """Determine the location/section of an image in the webpage"""
        # Look for parent elements that might indicate location
        parent = img_element.parent
        location_indicators = []
        
        # Traverse up the DOM to find meaningful parent elements
        current = parent
        depth = 0
        while current and depth < 10:  # Limit depth to avoid infinite loops
            # Check for semantic HTML5 elements
            if current.name in ['header', 'nav', 'main', 'section', 'article', 'aside', 'footer']:
                location_indicators.append(current.name)
            
            # Check for elements with meaningful IDs or classes
            if current.get('id'):
                location_indicators.append(f"#{current['id']}")
            
            if current.get('class'):
                classes = current['class']
                for cls in classes:
                    if any(keyword in cls.lower() for keyword in ['header', 'nav', 'menu', 'sidebar', 'footer', 'content', 'main', 'banner']):
                        location_indicators.append(f".{cls}")
                        break
            
            current = current.parent
            depth += 1
        
        # If no meaningful location found, try to infer from nearby text
        if not location_indicators:
            # Check for nearby headings
            for heading in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                prev_heading = img_element.find_previous(heading)
                if prev_heading and len(prev_heading.get_text().strip()) > 0:
                    location_indicators.append(f"Near heading: {prev_heading.get_text().strip()[:50]}")
                    break
        
        return " > ".join(reversed(location_indicators)) if location_indicators else "Unknown section"
    
    def find_navigation_links(self, soup: BeautifulSoup, base_url: str) -> Set[str]:
        """Find links specifically from navigation areas"""
        links = set()
        
        # Extract base domain for the first time
        if not self.base_domain:
            parsed_url = urllib.parse.urlparse(base_url)
            self.base_domain = f"{parsed_url.scheme}://{parsed_url.netloc}"
        
        # Look for navigation elements in order of priority
        nav_selectors = [
            # HTML5 semantic nav elements
            'nav',
            'header nav',
            # Common navigation class patterns
            '.navbar', '.navigation', '.nav', '.menu', '.main-nav', '.primary-nav',
            '.header-nav', '.site-nav', '.top-nav', '.nav-menu', '.nav-bar',
            # Common navigation ID patterns  
            '#navbar', '#navigation', '#nav', '#menu', '#main-nav', '#primary-nav',
            '#header-nav', '#site-nav', '#top-nav',
            # Header elements that might contain navigation
            'header',
            # Role-based selectors
            '[role="navigation"]',
            # Common navigation parent containers
            '.header', '.site-header', '.main-header'
        ]
        
        nav_links_found = False
        
        # Try each selector until we find navigation links
        for selector in nav_selectors:
            try:
                nav_elements = soup.select(selector)
                if not nav_elements:
                    continue
                
                # Extract links from navigation elements
                for nav_element in nav_elements:
                    nav_links = nav_element.find_all('a', href=True)
                    
                    for link in nav_links:
                        href = link['href']
                        
                        # Skip empty hrefs, anchors, and non-HTTP protocols
                        if not href or href.startswith('#') or href.startswith('mailto:') or href.startswith('tel:'):
                            continue
                        
                        # Convert relative URLs to absolute
                        if href.startswith('//'):
                            absolute_url = 'https:' + href
                        elif href.startswith('/'):
                            absolute_url = self.base_domain + href
                        elif not href.startswith(('http://', 'https://')):
                            absolute_url = urllib.parse.urljoin(base_url, href)
                        else:
                            absolute_url = href
                        
                        # Only include links from the same domain
                        if absolute_url.startswith(self.base_domain):
                            # Clean the URL (remove fragments)
                            parsed = urllib.parse.urlparse(absolute_url)
                            clean_url = urllib.parse.urlunparse(parsed._replace(fragment=''))
                            links.add(clean_url)
                            nav_links_found = True
                
                # If we found navigation links with this selector, stop trying others
                if nav_links_found:
                    break
                    
            except Exception:
                continue
        
        # If no navigation-specific links found, fall back to main content area links
        # but only from likely navigation patterns
        if not links:
            fallback_selectors = [
                'ul li a',  # Common list-based navigation
                '.menu-item a',
                '.nav-item a'
            ]
            
            for selector in fallback_selectors:
                try:
                    fallback_links = soup.select(selector)
                    for link in fallback_links[:10]:  # Limit to first 10 to avoid content links
                        href = link.get('href')
                        if not href or href.startswith('#') or href.startswith('mailto:') or href.startswith('tel:'):
                            continue
                        
                        if href.startswith('//'):
                            absolute_url = 'https:' + href
                        elif href.startswith('/'):
                            absolute_url = self.base_domain + href
                        elif not href.startswith(('http://', 'https://')):
                            absolute_url = urllib.parse.urljoin(base_url, href)
                        else:
                            absolute_url = href
                        
                        if absolute_url.startswith(self.base_domain):
                            parsed = urllib.parse.urlparse(absolute_url)
                            clean_url = urllib.parse.urlunparse(parsed._replace(fragment=''))
                            links.add(clean_url)
                            
                    if links:
                        break
                except Exception:
                    continue
        
        return links
    
    def crawl_website(self, start_url: str, max_pages: int = 50) -> Dict[str, Dict]:
        """Crawl the entire website starting from the given URL"""
        pages_data = {}
        urls_to_visit = [start_url]
        
        while urls_to_visit and len(pages_data) < max_pages:
            current_url = urls_to_visit.pop(0)
            
            # Skip if already visited
            if current_url in self.visited_urls:
                continue
            
            try:
                # Fetch the page
                html_content, soup = self.get_html_content(current_url)
                self.visited_urls.add(current_url)
                
                # Find images on this page
                images = self.find_images(soup, current_url)
                
                # Find navigation links on this page
                page_links = self.find_navigation_links(soup, current_url)
                
                # Add new links to visit queue
                for link in page_links:
                    if link not in self.visited_urls and link not in urls_to_visit:
                        urls_to_visit.append(link)
                
                # Get page title
                title_tag = soup.find('title')
                page_title = title_tag.get_text().strip() if title_tag else "No title"
                
                # Store page data
                pages_data[current_url] = {
                    'title': page_title,
                    'html_content': html_content,
                    'images': images,
                    'links_found': len(page_links),
                    'images_count': len(images)
                }
                
                # Short delay to be respectful
                time.sleep(0.5)
                
            except Exception as e:
                st.warning(f"Failed to crawl {current_url}: {str(e)}")
                continue
        
        return pages_data
    
    def download_and_convert_image(self, img_url: str, output_dir: str, filename: str) -> Optional[str]:
        """Download image and convert to PNG if necessary"""
        try:
            response = self.session.get(img_url, timeout=30)
            response.raise_for_status()
            
            # Get image format from content-type or URL
            content_type = response.headers.get('content-type', '')
            
            # Load image using PIL
            img = Image.open(io.BytesIO(response.content))
            
            # Convert to RGB if necessary (for PNG conversion)
            if img.mode in ('RGBA', 'LA', 'P'):
                # Keep transparency for PNG
                pass
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Determine output format
            if content_type in ['image/jpeg', 'image/jpg'] or img_url.lower().endswith(('.jpg', '.jpeg')):
                # Keep as JPEG
                output_path = os.path.join(output_dir, f"{filename}.jpg")
                img.save(output_path, 'JPEG', quality=95)
            elif content_type == 'image/png' or img_url.lower().endswith('.png'):
                # Keep as PNG
                output_path = os.path.join(output_dir, f"{filename}.png")
                img.save(output_path, 'PNG')
            else:
                # Convert to PNG
                output_path = os.path.join(output_dir, f"{filename}.png")
                img.save(output_path, 'PNG')
            
            return output_path
            
        except Exception as e:
            st.error(f"Failed to download/convert image {img_url}: {str(e)}")
            return None

def create_download_zip(pages_data: Dict, images_dir: str, base_url: str) -> bytes:
    """Create a ZIP file containing HTML pages and images"""
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # Add HTML files for each page
        for i, (page_url, page_data) in enumerate(pages_data.items()):
            # Create safe filename from URL
            filename = f"page_{i+1:03d}_{page_data['title'][:30]}.html"
            filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
            
            # Add page info header
            html_with_info = f"""<!-- Page URL: {page_url} -->
<!-- Page Title: {page_data['title']} -->
<!-- Images Found: {page_data.get('images_count', 0)} -->
<!-- Links Found: {page_data.get('links_found', 0)} -->

{page_data['html_content']}"""
            
            zip_file.writestr(f"pages/{filename}", html_with_info)
        
        # Add images
        if os.path.exists(images_dir):
            for root, dirs, files in os.walk(images_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arc_name = os.path.join('images', file)
                    zip_file.write(file_path, arc_name)
        
        # Add summary file
        summary = f"""Website Scraping Summary
========================
Base URL: {base_url}
Total Pages Scraped: {len(pages_data)}
Scrape Date: {time.strftime('%Y-%m-%d %H:%M:%S')}

Pages:
"""
        for i, (page_url, page_data) in enumerate(pages_data.items()):
            summary += f"{i+1}. {page_data['title']} - {page_url}\n"
            summary += f"   Images: {page_data.get('images_count', 0)}, Links: {page_data.get('links_found', 0)}\n\n"
        
        zip_file.writestr('summary.txt', summary)
    
    zip_buffer.seek(0)
    return zip_buffer.read()

def main():
    st.title("🧭 Navigation-Based Website Scraper")
    st.markdown("Crawl website pages found in navigation menus to extract HTML content and images with format conversion and location labeling.")
    
    # Initialize session state
    if 'scraped_data' not in st.session_state:
        st.session_state.scraped_data = None
    
    # URL input
    url = st.text_input("Enter Website URL:", placeholder="https://example.com")
    
    # Scraping options
    col1, col2, col3 = st.columns(3)
    with col1:
        max_pages = st.number_input("Maximum pages to crawl:", min_value=1, max_value=100, value=20)
    with col2:
        max_images = st.number_input("Maximum images per page:", min_value=1, max_value=50, value=10)
    with col3:
        convert_to_png = st.checkbox("Convert non-JPEG/PNG images to PNG", value=True)
    
    # Scrape button
    if st.button("🔍 Crawl Entire Website", type="primary"):
        if not url:
            st.error("Please enter a valid URL")
            return
        
        # Validate URL
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        try:
            scraper = WebScraper()
            
            # Progress tracking
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Step 1: Crawl all pages
            status_text.text("Crawling website pages...")
            progress_bar.progress(10)
            pages_data = scraper.crawl_website(url, max_pages)
            
            if not pages_data:
                st.error("No pages found to crawl!")
                return
            
            st.info(f"Found {len(pages_data)} pages to process")
            
            # Step 2: Process all images from all pages
            status_text.text("Processing images from all pages...")
            progress_bar.progress(30)
            
            # Create temporary directory for images
            temp_dir = tempfile.mkdtemp()
            images_dir = os.path.join(temp_dir, 'images')
            os.makedirs(images_dir, exist_ok=True)
            
            # Collect all images from all pages
            all_images = []
            image_counter = 0
            
            for page_url, page_data in pages_data.items():
                # Limit images per page
                page_images = page_data['images'][:max_images]
                
                for img_data in page_images:
                    img_data['source_page'] = page_url
                    img_data['source_page_title'] = page_data['title']
                    img_data['global_index'] = image_counter + 1
                    all_images.append(img_data)
                    image_counter += 1
            
            # Download and process images
            processed_images = []
            for i, img_data in enumerate(all_images):
                try:
                    status_text.text(f"Processing image {i+1}/{len(all_images)}...")
                    
                    filename = f"image_{i+1:03d}_from_page_{img_data['global_index']}"
                    output_path = scraper.download_and_convert_image(
                        img_data['url'], images_dir, filename
                    )
                    if output_path:
                        img_data['local_path'] = output_path
                        processed_images.append(img_data)
                    
                    # Update progress
                    progress = 30 + (60 * (i + 1) / len(all_images))
                    progress_bar.progress(int(progress))
                    
                except Exception as e:
                    st.warning(f"Failed to process image {i+1}: {str(e)}")
                    continue
            
            # Step 3: Complete
            status_text.text("Website crawling completed!")
            progress_bar.progress(100)
            
            # Store results in session state
            st.session_state.scraped_data = {
                'url': url,
                'pages_data': pages_data,
                'all_images': processed_images,
                'images_dir': images_dir,
                'total_pages': len(pages_data),
                'total_images': len(processed_images)
            }
            
            time.sleep(1)  # Brief pause to show completion
            status_text.empty()
            progress_bar.empty()
            
        except Exception as e:
            st.error(f"Error during website crawling: {str(e)}")
            return
    
    # Display results
    if st.session_state.scraped_data:
        data = st.session_state.scraped_data
        
        st.success(f"Successfully crawled {data['url']}")
        st.info(f"Found {data['total_pages']} pages and {data['total_images']} images")
        
        # Tabs for different views
        tab1, tab2, tab3, tab4 = st.tabs(["📄 All Pages", "🖼️ All Images", "📊 Summary", "📥 Download"])
        
        with tab1:
            st.subheader("Crawled Pages")
            
            for i, (page_url, page_data) in enumerate(data['pages_data'].items()):
                with st.expander(f"Page {i+1}: {page_data['title']}"):
                    st.write("**URL:**", page_url)
                    st.write("**Title:**", page_data['title'])
                    st.write("**Images found:**", page_data['images_count'])
                    st.write("**Links found:**", page_data['links_found'])
                    
                    # Show HTML content (truncated)
                    st.write("**HTML Content (first 1000 characters):**")
                    st.code(page_data['html_content'][:1000] + "...", language='html')
        
        with tab2:
            st.subheader("All Extracted Images")
            
            # Initialize session state for image categorization
            if 'image_categories' not in st.session_state:
                st.session_state.image_categories = {}
            
            # Category counters
            hero_count = sum(1 for cat in st.session_state.image_categories.values() if cat == "Hero")
            about_count = sum(1 for cat in st.session_state.image_categories.values() if cat == "AboutMe")
            gallery_count = sum(1 for cat in st.session_state.image_categories.values() if cat == "Gallery")
            
            st.write(f"**Categories:** Hero ({hero_count}) | About Me ({about_count}) | Gallery ({gallery_count})")
            
            # Display images in 3-column grid
            images_per_row = 3
            total_images = len(data['all_images'])
            
            for row_start in range(0, total_images, images_per_row):
                cols = st.columns(images_per_row)
                
                for col_idx in range(images_per_row):
                    img_idx = row_start + col_idx
                    
                    if img_idx < total_images:
                        img_data = data['all_images'][img_idx]
                        
                        with cols[col_idx]:
                            # Display image
                            if 'local_path' in img_data and os.path.exists(img_data['local_path']):
                                st.image(img_data['local_path'], use_container_width=True)
                            else:
                                st.error("Image not available")
                            
                            # Category selection
                            current_category = st.session_state.image_categories.get(img_idx, "None")
                            category = st.selectbox(
                                "Category:",
                                options=["None", "Hero", "AboutMe", "Gallery"],
                                index=["None", "Hero", "AboutMe", "Gallery"].index(current_category),
                                key=f"img_category_{img_idx}"
                            )
                            
                            # Update category in session state
                            if category != "None":
                                st.session_state.image_categories[img_idx] = category
                            elif img_idx in st.session_state.image_categories:
                                del st.session_state.image_categories[img_idx]
                            
                            # Image name and basic info
                            filename = os.path.basename(img_data['local_path']) if 'local_path' in img_data else f"image_{img_data['global_index']}"
                            st.write(f"**{filename}**")
                            st.write(f"From: {img_data['source_page_title']}")
                            st.write(f"Location: {img_data['location']}")
                            
                            # Show details in expander
                            with st.expander("Details"):
                                st.write("**Original URL:**", img_data['url'])
                                st.write("**Alt text:**", img_data['alt'] or "None")
                                st.write("**Source page:**", img_data['source_page'])
            
            # Download categorized images button
            if st.session_state.image_categories:
                st.write("---")
                if st.button("📦 Download Categorized Images (ZIP)", type="primary"):
                    # Create ZIP with categorized images with custom names
                    zip_buffer = io.BytesIO()
                    
                    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                        # Track how many images of each category we've processed
                        category_counts = {"Hero": 0, "AboutMe": 0, "Gallery": 0}
                        
                        for img_idx, category in st.session_state.image_categories.items():
                            img_data = data['all_images'][img_idx]
                            if 'local_path' in img_data and os.path.exists(img_data['local_path']):
                                # Get the original file extension
                                original_filename = os.path.basename(img_data['local_path'])
                                _, ext = os.path.splitext(original_filename)
                                
                                # Default to .jpg if no extension found
                                if not ext:
                                    ext = '.jpg'
                                
                                # Create custom filename based on category
                                if category == "Hero":
                                    category_counts["Hero"] += 1
                                    if category_counts["Hero"] == 1:
                                        custom_filename = f"Hero{ext}"
                                    else:
                                        custom_filename = f"Hero{category_counts['Hero']}{ext}"
                                elif category == "AboutMe":
                                    category_counts["AboutMe"] += 1
                                    if category_counts["AboutMe"] == 1:
                                        custom_filename = f"AboutMe{ext}"
                                    else:
                                        custom_filename = f"AboutMe{category_counts['AboutMe']}{ext}"
                                elif category == "Gallery":
                                    category_counts["Gallery"] += 1
                                    if category_counts["Gallery"] == 1:
                                        custom_filename = f"Gallery{ext}"
                                    else:
                                        custom_filename = f"Gallery{category_counts['Gallery']}{ext}"
                                
                                zip_file.write(img_data['local_path'], custom_filename)
                    
                    zip_buffer.seek(0)
                    st.download_button(
                        label=f"📥 Download {len(st.session_state.image_categories)} Categorized Images",
                        data=zip_buffer.read(),
                        file_name=f"categorized_images_{int(time.time())}.zip",
                        mime="application/zip"
                    )
        
        with tab3:
            st.subheader("Crawling Summary")
            
            # Overview metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Pages", data['total_pages'])
            with col2:
                st.metric("Total Images", data['total_images'])
            with col3:
                st.metric("Avg Images/Page", round(data['total_images'] / data['total_pages'], 1))
            
            # Page breakdown
            st.write("**Page Details:**")
            for i, (page_url, page_data) in enumerate(data['pages_data'].items()):
                st.write(f"{i+1}. **{page_data['title']}**")
                st.write(f"   - URL: {page_url}")
                st.write(f"   - Images: {page_data['images_count']}, Links: {page_data['links_found']}")
                st.write("")
        
        with tab4:
            st.subheader("Download All Content")
            
            # Create download package
            zip_data = create_download_zip(
                data['pages_data'],
                data['images_dir'],
                data['url']
            )
            
            # Download button
            st.download_button(
                label="📦 Download Complete Website (ZIP)",
                data=zip_data,
                file_name=f"website_complete_{int(time.time())}.zip",
                mime="application/zip"
            )
            
            st.write("**The ZIP file contains:**")
            st.write("- All HTML pages from the website")
            st.write("- All images found on the website")
            st.write("- Summary file with crawling details")
            st.write("- Organized folder structure")
            
            # Individual page downloads
            st.write("**Individual Page Downloads:**")
            for i, (page_url, page_data) in enumerate(data['pages_data'].items()):
                st.download_button(
                    label=f"📄 {page_data['title']}",
                    data=page_data['html_content'],
                    file_name=f"page_{i+1:03d}_{page_data['title'][:30]}.html",
                    mime="text/html"
                )

if __name__ == "__main__":
    main()
