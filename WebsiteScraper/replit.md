# Complete Website Scraper & Image Extractor

## Overview

This is a Streamlit-based web application that crawls entire websites to extract HTML content and images from all pages. The application provides a user-friendly interface for users to input URLs, automatically discover and crawl all pages within a website, and download comprehensive packages containing all HTML content and images with detailed organization and labeling.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Framework**: Streamlit
- **Layout**: Wide layout configuration for better user experience
- **Interface**: Single-page application with form inputs and interactive elements
- **Styling**: Uses Streamlit's built-in components and styling

### Backend Architecture
- **Core Logic**: Python-based web scraping using requests and BeautifulSoup
- **Session Management**: Persistent HTTP session with custom headers for better scraping compatibility
- **Image Processing**: PIL (Python Imaging Library) for image handling
- **File Management**: Temporary file handling for downloads and processing

## Key Components

### WebScraper Class
- **Purpose**: Main scraping engine that handles HTTP requests, HTML parsing, and website crawling
- **Features**:
  - Session-based requests with realistic User-Agent headers
  - HTML content fetching with error handling
  - Image discovery and extraction from web pages
  - URL resolution for relative links
  - **Website Crawling**: Automatic discovery and crawling of all pages within a website
  - **Link Discovery**: Intelligent extraction of internal links from each page
  - **Domain Filtering**: Ensures crawling stays within the target website domain

### Core Libraries
- **Streamlit**: Web application framework
- **requests**: HTTP client for web scraping
- **BeautifulSoup**: HTML parsing and manipulation
- **PIL**: Image processing and validation
- **urllib**: URL parsing and handling

### File Processing
- **Temporary Files**: Uses Python's tempfile module for safe file handling
- **ZIP Archives**: Capability to package multiple images for download
- **Base64 Encoding**: For embedding images and downloads in the web interface

## Data Flow

1. **User Input**: User provides a URL and crawling parameters through the Streamlit interface
2. **URL Validation**: Application validates the provided URL
3. **Website Crawling**: WebScraper discovers and crawls all pages within the website domain
4. **Link Discovery**: Each page is analyzed to find internal links for further crawling
5. **HTML Parsing**: BeautifulSoup parses HTML from each page to find image elements
6. **Image Discovery**: All img tags are identified and their sources extracted from every page
7. **URL Resolution**: Relative URLs are converted to absolute URLs
8. **Image Download**: Images are downloaded and processed with format conversion
9. **Organization**: Images are labeled with their source page and location context
10. **Result Display**: All pages and images are displayed in organized tabs
11. **Comprehensive Download**: ZIP package containing all HTML pages, images, and summary

## External Dependencies

### Core Dependencies
- **streamlit**: Web application framework
- **requests**: HTTP client library
- **beautifulsoup4**: HTML parsing library
- **Pillow**: Image processing library
- **urllib**: Built-in Python URL handling

### System Dependencies
- **Python 3.7+**: Required for modern Python features
- **Web Browser**: Required for Streamlit interface

## Deployment Strategy

### Local Development
- **Runtime**: Python-based application
- **Server**: Streamlit's built-in development server
- **Port**: Default Streamlit port (8501)
- **Command**: `streamlit run app.py`

### Production Considerations
- **Scalability**: Single-threaded Streamlit application
- **Security**: User-Agent spoofing for better scraping success
- **Error Handling**: Comprehensive exception handling for web requests
- **Resource Management**: Temporary file cleanup and memory management

### Deployment Options
- **Streamlit Cloud**: Native deployment platform
- **Docker**: Containerized deployment
- **Heroku/Railway**: Cloud platform deployment
- **Self-hosted**: Server deployment with reverse proxy

## Technical Decisions

### Web Scraping Approach
- **Chosen**: requests + BeautifulSoup
- **Rationale**: Lightweight, reliable, and handles most static content
- **Limitations**: Cannot handle JavaScript-rendered content
- **Alternative**: Selenium for dynamic content (not implemented)

### Image Processing
- **Chosen**: PIL/Pillow
- **Rationale**: Comprehensive image handling and validation
- **Features**: Format conversion, size validation, error handling

### User Interface
- **Chosen**: Streamlit
- **Rationale**: Rapid development, Python-native, built-in components
- **Trade-offs**: Limited customization vs. fast development

### Session Management
- **Chosen**: requests.Session with persistent headers
- **Rationale**: Better success rate with realistic browser headers
- **Security**: Minimal risk as it's read-only scraping