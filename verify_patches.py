import os
import django
from django.conf import settings
import logging

# Configure minimal settings to allow import
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "serverConfig.settings")

try:
    django.setup()
    print("[PASS] Django setup successful")
except Exception as e:
    print(f"[FAIL] Django setup failed: {e}")

# Test 1: Verify DEBUG is False by default
if settings.DEBUG is False:
    print("[PASS] DEBUG is False by default")
else:
    print(f"[FAIL] DEBUG is {settings.DEBUG}, expected False")

# Test 2: Verify HTML Sanitization
try:
    from api.views.reports import sanitize_html
    
    malicious_inputs = [
        ('<script>alert(1)</script>', ''),
        ('<img src=x onerror=alert(1)>', '<img src="x">'),
        ('<a href="javascript:alert(1)">Click</a>', '<a>Click</a>'),
        ('<iframe></iframe>', ''),
        ('<div style="color:red; background-image:url(javascript:alert(1))">Test</div>', '<div style="color: red;">Test</div>') # Bleach style sanitization might vary, checking basic
    ]
    
    print("\nStarting Sanitization Tests...")
    for input_html, expected_contain in malicious_inputs:
        output = sanitize_html(input_html)
        # We check if dangerous part is removed
        if "<script>" in output or "onerror" in output or "javascript:" in output or "iframe" in output:
             print(f"[FAIL] Failed to sanitize: {input_html} -> {output}")
        else:
             print(f"[PASS] Sanitized: {input_html} -> {output}")

except ImportError as e:
    print(f"[FAIL] Could not import reports.py: {e}")
except Exception as e:
    print(f"[FAIL] Error during sanitization test: {e}")
