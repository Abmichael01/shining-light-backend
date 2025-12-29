from django.http import HttpResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import logging
import time
import zipfile
from io import BytesIO
from PIL import Image
import bleach
from bleach.css_sanitizer import CSSSanitizer

logger = logging.getLogger(__name__)

# Sanitization configurations
ALLOWED_TAGS = [
    'a', 'abbr', 'acronym', 'b', 'blockquote', 'br', 'code', 'div', 'em', 
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'hr', 'i', 'img', 'li', 'ol', 'p', 
    'span', 'strong', 'table', 'tbody', 'td', 'th', 'thead', 'tr', 'ul',
    'font', 'style'
]
ALLOWED_ATTRIBUTES = {
    '*': ['class', 'style', 'id'],
    'a': ['href', 'title'],
    'img': ['src', 'alt', 'width', 'height'],
}
ALLOWED_STYLES = [
    'color', 'font-family', 'font-size', 'font-weight', 'text-align', 
    'background-color', 'border', 'padding', 'margin', 'width', 'height', 'display'
]

css_sanitizer = CSSSanitizer(allowed_css_properties=ALLOWED_STYLES)

def sanitize_html(html_content):
    """
    Sanitize HTML to prevent XSS/SSRF/LFI.
    """
    if not html_content:
        return ""
    return bleach.clean(
        html_content,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        css_sanitizer=css_sanitizer,
        strip=True
    )

# Chrome launch args - HARDENED
CHROME_ARGS = [
    '--disable-gpu',
    # '--no-sandbox' # REMOVED: Potentially unsafe. Only re-enable if absolutely necessary in container.
    # '--disable-web-security' # REMOVED: Prevents bypassing CORS/Same-origin policy
]

def retry_with_backoff(func, max_retries=3, initial_delay=1):
    """
    Retry a function with exponential backoff.
    """
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            delay = initial_delay * (2 ** attempt)
            logger.warning(f"Attempt {attempt + 1} failed: {str(e)}. Retrying in {delay}s...")
            time.sleep(delay)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def convert_html_to_pdf(request):
    """
    Converts received HTML content to a PDF file using screenshot→image→PDF pipeline.
    This ensures pixel-perfect rendering identical to images.
    Expects 'html_content' and 'filename' in the request body.
    """
    html_content = request.data.get('html_content')
    filename = request.data.get('filename', 'result.pdf')
    
    if not html_content:
        return HttpResponse("HTML content is required", status=400)
    
    def generate_pdf():
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=CHROME_ARGS)
            # 8x device scale for MAXIMUM quality
            page = browser.new_page(
                viewport={'width': 1200, 'height': 1600},
                device_scale_factor=8  # 8x = 9600×12800px effective resolution
            )
            page.set_default_timeout(90000)
            
            logger.info("Setting HTML content for PDF generation (via screenshot)")
            logger.info("Setting HTML content for PDF generation (via screenshot)")
            safe_content = sanitize_html(html_content)
            page.set_content(safe_content)
            
            # Wait for network idle with longer timeout
            try:
                logger.info("Waiting for network idle...")
                page.wait_for_load_state("networkidle", timeout=60000)
            except PlaywrightTimeoutError as e:
                logger.warning(f"Network idle timeout (non-fatal): {str(e)}")
            
            # Wait for fonts to load
            try:
                logger.info("Waiting for fonts to load...")
                page.evaluate("document.fonts.ready")
                logger.info("Fonts loaded")
            except Exception as e:
                logger.warning(f"Font loading check failed: {str(e)}")
            
            # Additional wait for rendering
            page.wait_for_timeout(2000)
            
            # Take screenshot
            logger.info("Taking screenshot for PDF...")
            image_data = page.screenshot(full_page=True, type='png', timeout=60000)
            
            browser.close()
            logger.info("Screenshot captured successfully")
            
            # Convert image to PDF with proper A4 scaling
            logger.info("Converting image to PDF...")
            img = Image.open(BytesIO(image_data))
            
            # A4 dimensions at 300 DPI: 2480 × 3508 pixels
            A4_WIDTH = 2480
            A4_HEIGHT = 3508
            
            # Calculate scaling to fit A4 while maintaining aspect ratio
            img_width, img_height = img.size
            scale = min(A4_WIDTH / img_width, A4_HEIGHT / img_height)
            
            # Resize image to fit A4
            new_width = int(img_width * scale)
            new_height = int(img_height * scale)
            
            logger.info(f"Resizing image from {img_width}×{img_height} to {new_width}×{new_height} for A4")
            img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Convert to RGB if needed
            if img_resized.mode == 'RGBA':
                img_resized = img_resized.convert('RGB')
            
            # Create A4-sized white canvas
            a4_canvas = Image.new('RGB', (A4_WIDTH, A4_HEIGHT), 'white')
            
            # Center the image on canvas
            x_offset = (A4_WIDTH - new_width) // 2
            y_offset = 0  # Top-aligned
            a4_canvas.paste(img_resized, (x_offset, y_offset))
            
            # Save to PDF
            pdf_buffer = BytesIO()
            a4_canvas.save(pdf_buffer, format='PDF', resolution=300.0)
            logger.info("PDF generated successfully with A4 dimensions")
            
            return pdf_buffer.getvalue()
    
    try:
        pdf_data = retry_with_backoff(generate_pdf, max_retries=3)
        response = HttpResponse(pdf_data, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    except Exception as e:
        logger.error(f"PDF Generation error after retries: {str(e)}", exc_info=True)
        return HttpResponse(f'An error occurred during PDF generation: {str(e)}', status=500)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def convert_html_to_image(request):
    """
    Converts received HTML content to a PNG image using Playwright.
    Expects 'html_content' and 'filename' in the request body.
    """
    html_content = request.data.get('html_content')
    filename = request.data.get('filename', 'result.png')
    
    if not html_content:
        return HttpResponse("HTML content is required", status=400)
    
    def generate_image():
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=CHROME_ARGS)
            # 8x device scale for MAXIMUM quality
            page = browser.new_page(
                viewport={'width': 1200, 'height': 1600},
                device_scale_factor=8  # 8x = 9600×12800px effective resolution
            )
            page.set_default_timeout(90000)  # 90 second page timeout
            
            logger.info("Setting HTML content for image generation")
            logger.info("Setting HTML content for image generation")
            safe_content = sanitize_html(html_content)
            page.set_content(safe_content)
            
            # Wait for network idle with longer timeout
            try:
                logger.info("Waiting for network idle...")
                page.wait_for_load_state("networkidle", timeout=60000)
            except PlaywrightTimeoutError as e:
                logger.warning(f"Network idle timeout (non-fatal): {str(e)}")
            
            # Wait for fonts to load
            try:
                logger.info("Waiting for fonts to load...")
                page.evaluate("document.fonts.ready")
                logger.info("Fonts loaded")
            except Exception as e:
                logger.warning(f"Font loading check failed: {str(e)}")
            
            # Additional wait for rendering
            page.wait_for_timeout(2000)
            
            # Take screenshot with timeout
            logger.info("Taking page screenshot...")
            image_data = page.screenshot(full_page=True, type='png', timeout=60000)
            
            browser.close()
            logger.info("Image generated successfully")
            return image_data
    
    try:
        image_data = retry_with_backoff(generate_image, max_retries=3)
        response = HttpResponse(image_data, content_type='image/png')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    except Exception as e:
        logger.error(f"Image Generation error after retries: {str(e)}", exc_info=True)
        return HttpResponse(f'An error occurred during image generation: {str(e)}', status=500)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def convert_multiple_html_to_pdf(request):
    """
    Converts list of HTML content strings to a single PDF.
    Each HTML string is converted to an Image first, then all images are combined into one PDF.
    Expects 'html_pages' (list of strings) and 'filename'.
    """
    html_pages = request.data.get('html_pages', [])
    filename = request.data.get('filename', 'result.pdf')
    
    if not html_pages or not isinstance(html_pages, list):
        return HttpResponse("html_pages list is required", status=400)
    
    def generate_multi_page_pdf():
        images = []
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=CHROME_ARGS)
            # Reduced scale from 3x to 2.5x for stability, increased height for 3-page layout
            context = browser.new_context(
                viewport={'width': 1200, 'height': 1800}, 
                device_scale_factor=2.5
            )
            
            logger.info(f"Processing {len(html_pages)} pages...")
            
            for idx, html_content in enumerate(html_pages):
                logger.info(f"Processing page {idx + 1}/{len(html_pages)}")
                page = context.new_page()
                page.set_default_timeout(90000)  # 90 second page timeout
                
                page.set_content(sanitize_html(html_content))
                
                try:
                    logger.info(f"Page {idx + 1}: Waiting for network idle...")
                    page.wait_for_load_state("networkidle", timeout=60000)
                except PlaywrightTimeoutError as e:
                    logger.warning(f"Page {idx + 1}: Network idle timeout (non-fatal): {str(e)}")
                
                # Wait for fonts
                try:
                    logger.info(f"Page {idx + 1}: Waiting for fonts...")
                    page.evaluate("document.fonts.ready")
                except Exception as e:
                    logger.warning(f"Page {idx + 1}: Font loading failed: {str(e)}")
                
                # Additional rendering wait
                page.wait_for_timeout(1500)
                
                logger.info(f"Page {idx + 1}: Taking screenshot...")
                img_data = page.screenshot(full_page=True, type='png', timeout=60000)
                images.append(Image.open(BytesIO(img_data)))
                
                page.close()
                logger.info(f"Page {idx + 1}: Complete")
            
            browser.close()
            logger.info("All pages processed successfully")
        
        if not images:
            raise Exception("No images generated")
        
        # Save images as PDF
        logger.info("Combining images into PDF...")
        pdf_buffer = BytesIO()
        first_image = images[0]
        other_images = images[1:]
        
        # Convert to RGB for PDF
        if first_image.mode == 'RGBA':
            first_image = first_image.convert('RGB')
        
        converted_others = []
        for img in other_images:
            if img.mode == 'RGBA':
                converted_others.append(img.convert('RGB'))
            else:
                converted_others.append(img)
        
        first_image.save(pdf_buffer, format='PDF', save_all=True, append_images=converted_others)
        logger.info("PDF combined successfully")
        
        return pdf_buffer.getvalue()
    
    try:
        pdf_data = retry_with_backoff(generate_multi_page_pdf, max_retries=2)  # 2 retries for multi-page
        response = HttpResponse(pdf_data, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    except Exception as e:
        logger.error(f"Multi-page PDF Generation error after retries: {str(e)}", exc_info=True)
        return HttpResponse(f'An error occurred: {str(e)}', status=500)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def convert_multiple_html_to_images_zip(request):
    """
    Converts list of HTML content strings to separate PNG images packaged as ZIP.
    Each HTML string becomes one PNG file.
    Expects 'html_pages' (list of strings) and 'filename'.
    Returns ZIP file containing page_1.png, page_2.png, page_3.png, etc.
    """
    html_pages = request.data.get('html_pages', [])
    filename = request.data.get('filename', 'report_images.zip')
    
    if not html_pages or not isinstance(html_pages, list):
        return HttpResponse("html_pages list is required", status=400)
    
    def generate_images_for_zip():
        image_files = []
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=CHROME_ARGS)
            # 8x device scale for MAXIMUM quality
            context = browser.new_context(
                viewport={'width': 1200, 'height': 1800}, 
                device_scale_factor=8  # 8x = 9600×14400px effective resolution
            )
            
            logger.info(f"Generating {len(html_pages)} images for ZIP...")
            
            for idx, html_content in enumerate(html_pages):
                logger.info(f"Processing image {idx + 1}/{len(html_pages)}")
                page = context.new_page()
                page.set_default_timeout(90000)
                
                page.set_content(sanitize_html(html_content))
                
                try:
                    logger.info(f"Image {idx + 1}: Waiting for network idle...")
                    page.wait_for_load_state("networkidle", timeout=60000)
                except PlaywrightTimeoutError as e:
                    logger.warning(f"Image {idx + 1}: Network idle timeout (non-fatal): {str(e)}")
                
                # Wait for fonts
                try:
                    logger.info(f"Image {idx + 1}: Waiting for fonts...")
                    page.evaluate("document.fonts.ready")
                except Exception as e:
                    logger.warning(f"Image {idx + 1}: Font loading failed: {str(e)}")
                
                # Additional rendering wait
                page.wait_for_timeout(1500)
                
                logger.info(f"Image {idx + 1}: Taking screenshot...")
                img_data = page.screenshot(full_page=True, type='png', timeout=60000)
                
                # Store with filename
                image_files.append((f'page_{idx + 1}.png', img_data))
                
                page.close()
                logger.info(f"Image {idx + 1}: Complete")
            
            browser.close()
            logger.info("All images generated successfully")
        
        if not image_files:
            raise Exception("No images generated")
        
        # Create ZIP file
        logger.info("Creating ZIP file...")
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for img_filename, img_data in image_files:
                zip_file.writestr(img_filename, img_data)
                logger.info(f"Added {img_filename} to ZIP")
        
        logger.info("ZIP file created successfully")
        return zip_buffer.getvalue()
    
    try:
        zip_data = retry_with_backoff(generate_images_for_zip, max_retries=2)
        response = HttpResponse(zip_data, content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    except Exception as e:
        logger.error(f"Image ZIP Generation error after retries: {str(e)}", exc_info=True)
        return HttpResponse(f'An error occurred: {str(e)}', status=500)
