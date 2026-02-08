from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from ..models import Student, Biometric, BiometricStation
from ..serializers.student import BiometricSerializer
from django.utils import timezone

class StudentListView(APIView):
    def get(self, request):
        try:
            # check if authenticated via session or API Key
            if not (request.user.is_authenticated or request.auth):
                 return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)
            
            station_name = "API Station"
            if request.user.is_authenticated:
                station_name = f"Admin: {request.user.email}"
            elif request.auth:
                 try:
                     station = BiometricStation.objects.get(api_key=request.auth)
                     station_name = station.name
                 except: pass

            search_query = request.query_params.get('search', '').strip()
            
            # Base queryset
            students = Student.objects.filter(status='enrolled').order_by('id')
            
            if search_query:
                from django.db.models import Q
                students = students.filter(
                    Q(id__icontains=search_query) |
                    Q(biodata__first_name__icontains=search_query) |
                    Q(biodata__surname__icontains=search_query) |
                    Q(admission_number__icontains=search_query)
                )
            
            # Count total before slicing
            total_count = students.count()

            # Pagination parameters
            limit = request.query_params.get('limit')
            offset = request.query_params.get('offset')
            try: limit = int(limit) if limit else 10
            except: limit = 10
            try: offset = int(offset) if offset else 0
            except: offset = 0

            # Apply slicing
            students = students[offset : offset + limit]
            
            data = []
            for s in students:
                biometric = getattr(s, 'biometric', None)
                is_enrolled = False
                fingerprint_url = None
                passport_url = None
                
                biodata = getattr(s, 'biodata', None)
                if biodata and biodata.passport_photo:
                    passport_url = request.build_absolute_uri(biodata.passport_photo.url)
                    
                if biometric:
                    is_enrolled = any([
                        biometric.left_thumb_template,
                        biometric.left_index_template,
                        biometric.right_thumb_template,
                        biometric.right_index_template
                    ])
                    if biometric.right_thumb:
                        fingerprint_url = request.build_absolute_uri(biometric.right_thumb.url)
                    elif biometric.left_thumb:
                        fingerprint_url = request.build_absolute_uri(biometric.left_thumb.url)

                data.append({
                    "id": s.id,
                    "name": s.get_full_name(),
                    "admission_number": s.admission_number or s.application_number,
                    "is_enrolled": is_enrolled,
                    "fingerprint_url": fingerprint_url,
                    "passport_url": passport_url,
                    "biometric": BiometricSerializer(biometric, context={'request': request}).data if biometric else None
                })
            return Response({
                "count": total_count,
                "results": data
            })
        except Exception as e:
            import traceback
            return Response({"error": str(e), "traceback": traceback.format_exc()}, status=500)

class EnrollFingerprintView(APIView):
    def post(self, request):
        try:
            # check if authenticated via session or API Key
            if not (request.user.is_authenticated or request.auth):
                 return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

            station_name = "API Station"
            if request.user.is_authenticated:
                station_name = f"Admin Session ({request.user.email})"
            elif request.auth:
                 try:
                     station = BiometricStation.objects.get(api_key=request.auth)
                     station_name = station.name
                 except: pass

            student_id = request.data.get('student_id')
            finger = request.data.get('finger')
            
            student = get_object_or_404(Student, id=student_id)
            biometric, created = Biometric.objects.get_or_create(student=student)
            
            # Handle Image Upload and Template Mapping
            image_base64 = request.data.get('image')
            template_data = request.data.get('template')
            
            # Map finger name to model fields
            finger_map = {
                'left-thumb': ('left_thumb', 'left_thumb_template'),
                'left-index': ('left_index', 'left_index_template'),
                'right-thumb': ('right_thumb', 'right_thumb_template'),
                'right-index': ('right_index', 'right_index_template'),
                'right-index-finger': ('right_index', 'right_index_template'), # Compatibility
            }
            
            if finger in finger_map:
                img_field, tmpl_field = finger_map[finger]
                
                # Save Image
                if image_base64:
                    import base64
                    from django.core.files.base import ContentFile
                    try:
                        format, imgstr = image_base64.split(';base64,') 
                        ext = format.split('/')[-1] 
                        data = ContentFile(base64.b64decode(imgstr), name=f'{student.admission_number}_{finger}.{ext}')
                        setattr(biometric, img_field, data)
                    except Exception as img_err:
                        print(f"Image save error for {finger}: {img_err}")
                
                # Save Template
                if template_data:
                    setattr(biometric, tmpl_field, template_data)
            
            biometric.notes = f"Biometric for {finger} updated via {station_name} at {timezone.now()}"
            biometric.save()
            
            fingerprint_url = None
            if biometric.right_thumb:
                fingerprint_url = request.build_absolute_uri(biometric.right_thumb.url)
            
            return Response({
                "status": "success", 
                "message": f"Biometric updated for {student.get_full_name()}",
                "fingerprint_url": fingerprint_url
            })
        except Exception as e:
            import traceback
            return Response({"error": str(e), "traceback": traceback.format_exc()}, status=500)

class VerifyFingerprintView(APIView):
    """
    Search/Identify a student by fingerprint.
    Receives 'template' (Base64) and looks for a match in the database.
    """
    def post(self, request):
        try:
            if not (request.user.is_authenticated or request.auth):
                return Response({"error": "Authentication required"}, status=401)

            template = request.data.get('template')
            if not template:
                return Response({"error": "No template data provided"}, status=400)

            # IDENTIFICATION (Search for student with this template)
            # In a real system, you'd use a C library to compare minutiae. 
            # For this MVP "Test" page, we look for an exact template match 
            # or return the student most likely to be scanning (testing purposes).
            
            from django.db.models import Q
            biometric = Biometric.objects.filter(
                Q(left_thumb_template=template) |
                Q(left_index_template=template) |
                Q(right_thumb_template=template) |
                Q(right_index_template=template)
            ).distinct().first()
            
            if biometric:
                student = biometric.student
                return Response({
                    "match": True,
                    "student": {
                        "id": student.id,
                        "name": student.get_full_name(),
                        "admission_number": student.admission_number,
                        "passport_url": request.build_absolute_uri(student.biodata.passport_photo.url) if student.biodata and student.biodata.passport_photo else None
                    }
                })
            else:
                return Response({"match": False, "message": "No matching student found."}, status=200)

        except Exception as e:
            return Response({"error": str(e)}, status=500)

from rest_framework import generics, permissions
from ..serializers import BiometricStationSerializer

class BiometricStationListCreateView(generics.ListCreateAPIView):
    """Admin only: List and Create Stations"""
    queryset = BiometricStation.objects.all().order_by('-created_at')
    serializer_class = BiometricStationSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]

class BiometricStationDetailView(generics.RetrieveDestroyAPIView):
    """Admin only: Delete Stations"""
    queryset = BiometricStation.objects.all()
    serializer_class = BiometricStationSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]
