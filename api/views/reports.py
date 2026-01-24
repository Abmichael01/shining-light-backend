import requests
import logging
import os
from io import BytesIO
import zipfile
from django.http import HttpResponse
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

logger = logging.getLogger(__name__)

import base64
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch

def call_external_render_api(html_content, format='png', options=None):
    """
    Calls HCTI (htmlcsstoimage.com) API.
    Uses 'device_scale' (2) for Retina quality and strict A4 width.
    """
    hcti_user_id = getattr(settings, 'HCTI_USER_ID', os.getenv('HCTI_USER_ID'))
    hcti_api_key = getattr(settings, 'HCTI_API_KEY', os.getenv('HCTI_API_KEY'))

    if not hcti_user_id or not hcti_api_key:
        logger.error("HCTI_USER_ID/API_KEY not set in settings")
        print("[ERROR] HCTI Credentials missing in settings")
        raise ValueError("Rendering API Credentials missing")

    # Debug logs for credentials
    print(f"[DEBUG] HCTI Auth: UserID={hcti_user_id[:4]}***, Key={hcti_api_key[:4]}***")

    # HCTI Endpoint
    url = "https://hcti.io/v1/image"
    
    # Base Payload for HCTI with SAFER defaults (A4 @ 96 DPI * 2x Scale)
    # Reducing from 3x/1240 to avoid 500 Errors
    defaults = {
        "viewport_width": 794,  # Standard A4 Width
        "viewport_height": 1123, 
        "device_scale": 2,      # Retina Quality (2x) -> 1588px wide (Safe)
        "ms_delay": 1500,       
    }

    # Merge provided options over defaults
    data = {**defaults}
    data["html"] = html_content
    
    if options:
        # Flatten options if they come in as 'viewport' or 'options' dicts (legacy support)
        if 'viewport' in options:
            vp = options['viewport']
            if 'width' in vp: data['viewport_width'] = vp['width']
            if 'height' in vp: data['viewport_height'] = vp['height']
            if 'deviceScaleFactor' in vp: data['device_scale'] = vp['deviceScaleFactor']
        
        # Also blindly merge top-level keys if they match HCTI params
        for key, value in options.items():
            if key in ['viewport_width', 'viewport_height', 'device_scale', 'ms_delay', 'google_fonts', 'use_print_media_queries']:
                data[key] = value

    print(f"[DEBUG] HCTI Payload: Width={data.get('viewport_width')}, Scale={data.get('device_scale')}")

    try:
        response = requests.post(
            url,
            auth=(hcti_user_id, hcti_api_key),
            json=data,
            timeout=60
        )
        
        if not response.ok:
            print(f"[ERROR] HCTI Failed Status: {response.status_code}")
            print(f"[ERROR] HCTI Response Body: {response.text}")
            # Return the upstream error directly to the client for visibility
            return response.content # This returns the JSON error from HCTI
            
        response.raise_for_status()
        
        # HCTI returns a JSON with 'url' which typically ends in .png or .jpg
        result = response.json()
        image_url = result.get('url')
        print(f"[DEBUG] HCTI Success. Image URL: {image_url}")
        
        if not image_url:
            logger.error(f"HCTI response missing url: {result}")
            raise ValueError("Failed to get image URL from HCTI")
            
        # Download the generated content
        file_response = requests.get(image_url + ".png", timeout=60)
        file_response.raise_for_status()
        return file_response.content
        
    except requests.exceptions.RequestException as e:
        logger.error(f"External Render API Error: {str(e)}")
        print(f"[ERROR] Request Exception: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
             # Return the upstream error directly
            return e.response.content
        raise

def generate_report_image(html_content, scale=2):
    """
    Helper to generate a PNG image from HTML with specific settings.
    scale=2 (Retina) is a good balance of quality and file width.
    """
    # Force viewport meta tag for strict browser capturing width
    # 1024px is a very safe standard desktop width that prevents most layout clipping
    if '<meta name="viewport"' not in html_content:
        html_content = '<meta name="viewport" content="width=1024">\n' + html_content

    # Use Flat HCTI Options
    image_options = {
        "viewport_width": 1024,
        "viewport_height": 1123, # Default A4 height, but HCTI expands if content is longer
        "device_scale": scale
    }
    return call_external_render_api(html_content, format='png', options=image_options)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def convert_html_to_pdf(request):
    """
    Converts received HTML -> Image -> PDF.
    Supports 'orientation' ('portrait' or 'landscape') and 'viewport' options.
    """
    html_content = request.data.get('html_content')
    filename = request.data.get('filename', 'result.pdf')
    orientation = request.data.get('orientation', 'portrait')
    user_viewport = request.data.get('viewport', {})
    
    if not html_content:
        return HttpResponse("HTML content is required", status=400)
    
    try:
        # Determine Page Size based on orientation
        from reportlab.lib.pagesizes import landscape, portrait
        
        target_pagesize = A4
        if orientation == 'landscape':
            target_pagesize = landscape(A4)
            # Default viewport for landscape (approx A4 width @ 96dpi)
            default_width = 1123 
        else:
            target_pagesize = portrait(A4)
            # Default viewport for portrait
            default_width = 794

        # Generate Image with Custom Viewport
        # Allow user override, otherwise use intelligent default
        viewport_width = user_viewport.get('width', default_width)
        
        image_options = {
            "viewport_width": viewport_width,
            "viewport_height": user_viewport.get('height', 1123), # Height expands anyway
            "device_scale": user_viewport.get('deviceScaleFactor', 2)
        }
        
        # Inject standard viewport meta if missing, to ensure renderer respects width
        if '<meta name="viewport"' not in html_content:
            html_content = f'<meta name="viewport" content="width={viewport_width}">\n' + html_content

        image_data = call_external_render_api(html_content, format='png', options=image_options)
        
        if not image_data.startswith(b'\x89PNG'):
             print(f"[ERROR] PNG Generation Failed. returned data: {image_data[:100]}")
             return HttpResponse(image_data, status=400, content_type='application/json')

        # Convert to PDF
        img = Image.open(BytesIO(image_data))
        img_width, img_height = img.size
        
        pdf_buffer = BytesIO()
        c = canvas.Canvas(pdf_buffer, pagesize=target_pagesize)
        page_width, page_height = target_pagesize
        
        # Scale image to fit page width
        scale_factor = page_width / img_width
        draw_width = page_width
        draw_height = img_height * scale_factor
        
        # Draw
        if orientation == 'landscape':
             # For landscape, we might want to center vertically if it's short, or multi-page if long
             # For now, simple draw at top
             c.setPageSize((page_width, max(page_height, draw_height))) # Expand height if needed?
             # Actually, if we want standard A4 PDF pages, we shouldn't change page size dynamically 
             # unless we want a long scroll. User asked for "Standard A4".
             # So we keep Standard A4 Page Size.
             c.setPageSize(target_pagesize)
             
             # If content is taller than page, we might ideally split, but Image->PDF is hard to split.
             # We'll just shrink-to-fit if strict single page is needed, OR let it clip/spill.
             # But current logic was expanding height.
             # The previous logic did: c.setPageSize((a4_width, draw_height)) -> Variable Height PDF.
             # Let's preserve that "Variable Height" behavior but with correct Width for landscape.
             c.setPageSize((page_width, draw_height))
        else:
             c.setPageSize((page_width, draw_height))

        c.drawInlineImage(img, 0, 0, width=draw_width, height=draw_height)
        c.showPage()
        c.save()
        
        pdf_data = pdf_buffer.getvalue()

        response = HttpResponse(pdf_data, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    except Exception as e:
        import traceback
        traceback.print_exc()
        return HttpResponse(f'An error occurred: {str(e)}', status=500)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def convert_html_to_image(request):
    """
    Converts received HTML content to a PNG image using External API.
    """
    html_content = request.data.get('html_content')
    filename = request.data.get('filename', 'result.png')
    
    if not html_content:
        return HttpResponse("HTML content is required", status=400)
    
    try:
        # Use Helper
        image_data = generate_report_image(html_content, scale=2)
        
        response = HttpResponse(image_data, content_type='image/png')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    except Exception as e:
        print(f"[ERROR] convert_html_to_image Exception: {str(e)}")
        import traceback
        traceback.print_exc()
        return HttpResponse(f'An error occurred: {str(e)}', status=500)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def convert_multiple_html_to_pdf(request):
    """
    Converts list of HTML content strings to a single PDF.
    """
    html_pages = request.data.get('html_pages', [])
    filename = request.data.get('filename', 'result.pdf')
    
    if not html_pages or not isinstance(html_pages, list):
        return HttpResponse("html_pages list is required", status=400)
    
    try:
        pdf_buffer = BytesIO()
        c = canvas.Canvas(pdf_buffer, pagesize=A4)
        a4_width, a4_height = A4

        for html in html_pages:
            img_data = generate_report_image(html, scale=2)
            
            if not img_data.startswith(b'\x89PNG'):
                print(f"[ERROR] PNG Generation Failed for page. data: {img_data[:100]}")
                return HttpResponse(img_data, status=400, content_type='application/json')
                
            img = Image.open(BytesIO(img_data))
            img_width, img_height = img.size
            
            # Scale to fit width
            scale_factor = a4_width / img_width
            draw_width = a4_width
            draw_height = img_height * scale_factor
            
            c.setPageSize((a4_width, draw_height))
            c.drawInlineImage(img, 0, 0, width=draw_width, height=draw_height)
            c.showPage()
            
        c.save()
        pdf_data = pdf_buffer.getvalue()
        
        response = HttpResponse(pdf_data, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    except Exception as e:
        import traceback
        traceback.print_exc()
        return HttpResponse(f'An error occurred: {str(e)}', status=500)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def convert_multiple_html_to_images_zip(request):
    """
    Converts list of HTML content strings to separate PNG images packaged as ZIP.
    """
    html_pages = request.data.get('html_pages', [])
    filename = request.data.get('filename', 'report_images.zip')
    
    if not html_pages or not isinstance(html_pages, list):
        return HttpResponse("html_pages list is required", status=400)
    
    try:
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for idx, html in enumerate(html_pages):
                img_data = call_external_render_api(html, format='png')
                zip_file.writestr(f'page_{idx + 1}.png', img_data)
        
        response = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    except Exception as e:
        return HttpResponse(f'An error occurred: {str(e)}', status=500)
