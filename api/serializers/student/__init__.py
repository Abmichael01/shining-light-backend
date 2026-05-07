from .base import BioDataSerializer, GuardianSerializer, DocumentSerializer, BiometricSerializer, TermReportSerializer
from .main import StudentSerializer, StudentListSerializer, CBTStudentProfileSerializer
from .registration import StudentRegistrationSerializer
from .subjects import StudentSubjectSerializer, ResultScoreSubmissionSerializer
from .admission_results import AdmissionExamResultSerializer, AdmissionExamSubjectResultSerializer

# For backward compatibility or internal use if needed
StudentDetailSerializer = StudentSerializer
