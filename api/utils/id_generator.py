"""
Utility functions for generating readable IDs for different models
"""
import string
import random
from django.db import models


# Model prefixes for different entities
MODEL_PREFIXES = {
    'EXAM': 'EXM',
    'ASSIGNMENT': 'ASM',
    'STUDENT': 'STU',
    'TEACHER': 'TCH',
    'CLASS': 'CLS',
    'SUBJECT': 'SUB',
    'QUESTION': 'QST',
    'RESULT': 'RST',
    'PAYMENT': 'PAY',
    'GUARDIAN': 'GRD',
    'SCHOOL': 'SCH',
    'SESSION': 'SES',
    'TERM': 'TRM',
    'TOPIC': 'TPC',
    'CLUB': 'CLB',
    'FEE': 'FEE',
    'DOCUMENT': 'DOC',
    'BIOMETRIC': 'BIO',
    'CBT': 'CBT',
}


def generate_random_string(length=6):
    """Generate a random alphanumeric string"""
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choice(chars) for _ in range(length))


def generate_readable_id(model_type, instance_id=None):
    """
    Generate a readable ID for a given model type
    
    Args:
        model_type (str): The type of model (e.g., 'EXAM', 'STUDENT')
        instance_id (int, optional): Existing ID to use as base
    
    Returns:
        str: A readable ID like "EXM-IEE83U7"
    """
    prefix = MODEL_PREFIXES.get(model_type, 'UNK')
    random_suffix = generate_random_string(6)
    
    # If an ID is provided, use it as part of the suffix
    if instance_id:
        id_str = str(instance_id).zfill(3)
        return f"{prefix}-{id_str}{random_suffix[3:]}"
    
    return f"{prefix}-{random_suffix}"


def generate_exam_id(exam_id=None):
    """Generate exam ID like EXM-IEE83U7"""
    return generate_readable_id('EXAM', exam_id)

def generate_assignment_id(assignment_id=None):
    """Generate assignment ID like ASM-IEE83U7"""
    return generate_readable_id('ASSIGNMENT', assignment_id)


def generate_student_id(student_id=None):
    """Generate student ID like STU-001ABC"""
    return generate_readable_id('STUDENT', student_id)


def generate_teacher_id(teacher_id=None):
    """Generate teacher ID like TCH-002DEF"""
    return generate_readable_id('TEACHER', teacher_id)


def generate_class_id(class_id=None):
    """Generate class ID like CLS-003GHI"""
    return generate_readable_id('CLASS', class_id)


def generate_subject_id(subject_id=None):
    """Generate subject ID like SUB-004JKL"""
    return generate_readable_id('SUBJECT', subject_id)


def generate_question_id(question_id=None):
    """Generate question ID like QST-005MNO"""
    return generate_readable_id('QUESTION', question_id)


def generate_result_id(result_id=None):
    """Generate result ID like RST-006PQR"""
    return generate_readable_id('RESULT', result_id)


def generate_payment_id(payment_id=None):
    """Generate payment ID like PAY-007STU"""
    return generate_readable_id('PAYMENT', payment_id)


def generate_guardian_id(guardian_id=None):
    """Generate guardian ID like GRD-008VWX"""
    return generate_readable_id('GUARDIAN', guardian_id)


def generate_school_id(school_id=None):
    """Generate school ID like SCH-009YZA"""
    return generate_readable_id('SCHOOL', school_id)


def generate_session_id(session_id=None):
    """Generate session ID like SES-010BCD"""
    return generate_readable_id('SESSION', session_id)


def generate_term_id(term_id=None):
    """Generate term ID like TRM-011EFG"""
    return generate_readable_id('TERM', term_id)


def generate_topic_id(topic_id=None):
    """Generate topic ID like TPC-012HIJ"""
    return generate_readable_id('TOPIC', topic_id)


def generate_club_id(club_id=None):
    """Generate club ID like CLB-013KLM"""
    return generate_readable_id('CLUB', club_id)


def generate_fee_id(fee_id=None):
    """Generate fee ID like FEE-014NOP"""
    return generate_readable_id('FEE', fee_id)


def generate_document_id(document_id=None):
    """Generate document ID like DOC-015QRS"""
    return generate_readable_id('DOCUMENT', document_id)


def generate_biometric_id(biometric_id=None):
    """Generate biometric ID like BIO-016TUV"""
    return generate_readable_id('BIOMETRIC', biometric_id)


def generate_cbt_passcode_id(passcode_id=None):
    """Generate CBT passcode ID like CBT-017WXY"""
    return generate_readable_id('CBT', passcode_id)
