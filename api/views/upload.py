from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.core.files.storage import default_storage
from django.conf import settings
import os
import uuid

class FileUploadView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response({"error": "No file provided"}, status=400)

        # Generale unique filename
        ext = os.path.splitext(file_obj.name)[1]
        filename = f"uploads/{uuid.uuid4()}{ext}"
        
        # Save to default storage (B2 or Local)
        saved_path = default_storage.save(filename, file_obj)
        
        # Generate Public URL
        if hasattr(settings, 'AWS_S3_ENDPOINT_URL') and settings.AWS_S3_ENDPOINT_URL:
             # B2/S3 specific URL construction if needed, but default_storage.url should work if configured correctly
             file_url = default_storage.url(saved_path)
        else:
             # Local storage URL
             file_url = request.build_absolute_uri(default_storage.url(saved_path))

        return Response({"url": file_url})
