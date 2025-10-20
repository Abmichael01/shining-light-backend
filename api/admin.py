from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import (
    User,
    School,
    Session,
    SessionTerm,
    Class,
    Department,
    SubjectGroup,
    Subject,
    Grade,
    Question,
    Student,
    BioData,
    Guardian,
    Document,
    Biometric,
    StudentSubject,
    Staff,
    StaffEducation,
    SalaryGrade,
    StaffSalary,
    SalaryPayment,
    LoanApplication,
    LoanPayment,
    FeeType,
    FeePayment
)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin interface for custom User model"""
    
    list_display = ['email', 'user_type', 'is_active', 'is_staff', 'date_joined']
    list_filter = ['user_type', 'is_active', 'is_staff', 'date_joined']
    search_fields = ['email']
    ordering = ['-date_joined']
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('User Info'), {'fields': ('user_type',)}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'user_type', 'password1', 'password2'),
        }),
    )
    
    readonly_fields = ['date_joined', 'last_login']


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    """Admin interface for School model"""
    
    list_display = ['name', 'school_type', 'code', 'is_active', 'created_at']
    list_filter = ['school_type', 'is_active', 'created_at']
    search_fields = ['name', 'code']
    ordering = ['school_type', 'name']
    readonly_fields = ['code', 'created_at']


class SessionTermInline(admin.TabularInline):
    """Inline for SessionTerm in Session admin"""
    model = SessionTerm
    extra = 0
    fields = ['term_name', 'start_date', 'end_date', 'is_current']


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    """Admin interface for Session model"""
    
    list_display = ['name', 'start_date', 'end_date', 'is_current', 'created_at']
    list_filter = ['is_current', 'start_date']
    search_fields = ['name']
    ordering = ['-start_date']
    inlines = [SessionTermInline]
    
    fieldsets = (
        (None, {
            'fields': ('name', 'start_date', 'end_date', 'is_current')
        }),
    )


@admin.register(SessionTerm)
class SessionTermAdmin(admin.ModelAdmin):
    """Admin interface for SessionTerm model"""
    
    list_display = ['session', 'term_name', 'start_date', 'end_date', 'is_current']
    list_filter = ['session', 'term_name', 'is_current']
    ordering = ['session', 'term_name']
    
    fieldsets = (
        (None, {
            'fields': ('session', 'term_name', 'start_date', 'end_date', 'is_current')
        }),
    )


@admin.register(Class)
class ClassAdmin(admin.ModelAdmin):
    """Admin interface for Class model"""
    
    list_display = ['name', 'class_code', 'school', 'class_staff', 'order']
    list_filter = ['school']
    search_fields = ['name', 'class_code']
    ordering = ['school', 'order', 'name']
    
    fieldsets = (
        (None, {
            'fields': ('name', 'class_code', 'school')
        }),
        (_('Staff Assignment'), {
            'fields': ('class_staff',)
        }),
        (_('Display'), {
            'fields': ('order',)
        }),
    )


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    """Admin interface for Department model"""
    
    list_display = ['name', 'code', 'school', 'created_at']
    list_filter = ['school']
    search_fields = ['name', 'code']
    ordering = ['school', 'name']


@admin.register(SubjectGroup)
class SubjectGroupAdmin(admin.ModelAdmin):
    """Admin interface for SubjectGroup model"""
    
    list_display = ['name', 'code', 'selection_type', 'created_at']
    list_filter = ['selection_type']
    search_fields = ['name', 'code']
    ordering = ['name']
    readonly_fields = ['code']
    
    fieldsets = (
        (None, {
            'fields': ('name', 'code', 'selection_type')
        }),
    )


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    """Admin interface for Subject model"""
    
    list_display = ['name', 'code', 'class_model', 'school', 'department', 'ca_max', 'exam_max']
    list_filter = ['school', 'class_model', 'department', 'subject_group']
    search_fields = ['name', 'code']
    ordering = ['school', 'class_model', 'order', 'name']
    
    fieldsets = (
        (None, {
            'fields': ('name', 'code', 'school', 'class_model')
        }),
        (_('Classification'), {
            'fields': ('department', 'subject_group')
        }),
        (_('Assessment Configuration'), {
            'fields': ('ca_max', 'exam_max')
        }),
        (_('Display'), {
            'fields': ('order',)
        }),
    )


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    """Admin interface for Question model"""
    
    list_display = ['question_text_preview', 'subject', 'topic', 'question_type', 'difficulty', 'is_verified', 'usage_count', 'created_at']
    list_filter = ['subject__school', 'subject', 'question_type', 'difficulty', 'is_verified', 'created_at']
    search_fields = ['question_text', 'topic', 'subject__name']
    ordering = ['-created_at']
    readonly_fields = ['usage_count', 'created_at', 'updated_at', 'created_by']
    
    fieldsets = (
        (None, {
            'fields': ('subject', 'topic', 'question_type', 'difficulty', 'marks')
        }),
        (_('Question Content'), {
            'fields': ('question_text',)
        }),
        (_('Options (For Multiple Choice)'), {
            'fields': ('option_a', 'option_b', 'option_c', 'option_d', 'option_e'),
            'classes': ('collapse',)
        }),
        (_('Answer'), {
            'fields': ('correct_answer', 'explanation')
        }),
        (_('Status'), {
            'fields': ('is_verified', 'usage_count')
        }),
        (_('Metadata'), {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def question_text_preview(self, obj):
        """Show first 100 chars of question"""
        from django.utils.html import strip_tags
        text = strip_tags(obj.question_text)
        return text[:100] + '...' if len(text) > 100 else text
    question_text_preview.short_description = 'Question'
    
    def save_model(self, request, obj, form, change):
        """Set created_by to current user if not set"""
        if not obj.pk:  # New object
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


# ===== Student Management =====

class BioDataInline(admin.StackedInline):
    """Inline for BioData in Student admin"""
    model = BioData
    can_delete = False
    fields = [
        ('surname', 'first_name', 'other_names'),
        ('gender', 'date_of_birth'),
        ('nationality', 'state_of_origin'),
        'permanent_address',
        'lin',
        ('has_medical_condition', 'blood_group'),
        'medical_condition_details'
    ]


class GuardianInline(admin.TabularInline):
    """Inline for Guardian in Student admin"""
    model = Guardian
    extra = 0
    fields = ['guardian_type', 'surname', 'first_name', 'phone_number', 'occupation', 'is_primary_contact']


class DocumentInline(admin.TabularInline):
    """Inline for Document in Student admin"""
    model = Document
    extra = 0
    fields = ['document_type', 'document_file', 'document_number', 'verified', 'verified_by']
    readonly_fields = ['verified_by']


class StudentSubjectInline(admin.TabularInline):
    """Inline for StudentSubject in Student admin"""
    model = StudentSubject
    extra = 0
    fields = ['subject', 'session', 'session_term', 'is_active']


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    """Admin interface for Student model"""
    
    list_display = [
        'get_student_name', 
        'application_number', 
        'admission_number', 
        'status', 
        'school', 
        'class_model',
        'application_date'
    ]
    list_filter = ['status', 'source', 'school', 'class_model', 'department']
    search_fields = ['application_number', 'admission_number', 'biodata__surname', 'biodata__first_name']
    ordering = ['-created_at']
    readonly_fields = ['application_number', 'admission_number', 'created_at', 'updated_at', 'created_by']
    
    inlines = [BioDataInline, GuardianInline, DocumentInline, StudentSubjectInline]
    
    fieldsets = (
        (_('Student Information'), {
            'fields': ('application_number', 'admission_number', 'status', 'source')
        }),
        (_('Academic Information'), {
            'fields': ('school', 'class_model', 'department', 'former_school_attended')
        }),
        (_('Account'), {
            'fields': ('user',)
        }),
        (_('Important Dates'), {
            'fields': (
                'application_date', 
                'review_date', 
                'acceptance_date', 
                'enrollment_date', 
                'graduation_date'
            )
        }),
        (_('Admin Actions'), {
            'fields': ('created_by', 'reviewed_by', 'rejection_reason'),
            'classes': ('collapse',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_student_name(self, obj):
        """Display student name from biodata"""
        return obj.get_full_name()
    get_student_name.short_description = 'Student Name'
    
    def save_model(self, request, obj, form, change):
        """Set created_by when creating student"""
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(BioData)
class BioDataAdmin(admin.ModelAdmin):
    """Admin interface for BioData model"""
    
    list_display = ['get_full_name', 'gender', 'date_of_birth', 'get_age', 'state_of_origin']
    list_filter = ['gender', 'nationality', 'has_medical_condition']
    search_fields = ['surname', 'first_name', 'other_names', 'lin']
    ordering = ['surname', 'first_name']
    
    fieldsets = (
        (_('Personal Information'), {
            'fields': (('surname', 'first_name', 'other_names'), ('gender', 'date_of_birth'), 'passport_photo')
        }),
        (_('Location'), {
            'fields': ('nationality', 'state_of_origin', 'permanent_address')
        }),
        (_('Identification'), {
            'fields': ('lin',)
        }),
        (_('Medical Information'), {
            'fields': (('has_medical_condition', 'blood_group'), 'medical_condition_details')
        }),
    )
    
    def get_full_name(self, obj):
        return str(obj)
    get_full_name.short_description = 'Full Name'
    
    def get_age(self, obj):
        return f"{obj.get_age()} years"
    get_age.short_description = 'Age'


@admin.register(Guardian)
class GuardianAdmin(admin.ModelAdmin):
    """Admin interface for Guardian model"""
    
    list_display = ['get_full_name', 'guardian_type', 'phone_number', 'occupation', 'is_primary_contact', 'student']
    list_filter = ['guardian_type', 'is_primary_contact']
    search_fields = ['surname', 'first_name', 'phone_number', 'email']
    ordering = ['student', 'guardian_type']
    
    fieldsets = (
        (_('Guardian Information'), {
            'fields': ('student', 'guardian_type', 'relationship_to_student')
        }),
        (_('Personal Details'), {
            'fields': (('surname', 'first_name'), 'state_of_origin')
        }),
        (_('Contact Information'), {
            'fields': (('phone_number', 'email'), 'is_primary_contact')
        }),
        (_('Employment'), {
            'fields': ('occupation', 'place_of_employment')
        }),
    )
    
    def get_full_name(self, obj):
        return f"{obj.surname} {obj.first_name}"
    get_full_name.short_description = 'Full Name'


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    """Admin interface for Document model"""
    
    list_display = ['student', 'document_type', 'document_number', 'verified', 'uploaded_at']
    list_filter = ['document_type', 'verified', 'uploaded_at']
    search_fields = ['student__application_number', 'student__admission_number', 'document_number']
    ordering = ['-uploaded_at']
    readonly_fields = ['uploaded_at', 'verified_by', 'verified_at']
    
    fieldsets = (
        (_('Document Information'), {
            'fields': ('student', 'document_type', 'document_file', 'document_number')
        }),
        (_('Verification'), {
            'fields': ('verified', 'verified_by', 'verified_at', 'notes')
        }),
    )
    
    def save_model(self, request, obj, form, change):
        """Set verified_by and verified_at when verifying"""
        if obj.verified and not obj.verified_by:
            obj.verified_by = request.user
            from django.utils import timezone
            obj.verified_at = timezone.now()
        super().save_model(request, obj, form, change)


@admin.register(Biometric)
class BiometricAdmin(admin.ModelAdmin):
    """Admin interface for Biometric model"""
    
    list_display = ['student', 'has_left_thumb', 'has_right_thumb', 'captured_at', 'captured_by']
    list_filter = ['captured_at']
    search_fields = ['student__application_number', 'student__admission_number']
    ordering = ['-captured_at']
    readonly_fields = ['captured_at', 'captured_by']
    
    fieldsets = (
        (_('Student'), {
            'fields': ('student',)
        }),
        (_('Fingerprints'), {
            'fields': ('left_thumb', 'right_thumb')
        }),
        (_('Capture Information'), {
            'fields': ('captured_by', 'captured_at', 'notes')
        }),
    )
    
    def has_left_thumb(self, obj):
        return bool(obj.left_thumb)
    has_left_thumb.boolean = True
    has_left_thumb.short_description = 'Left Thumb'
    
    def has_right_thumb(self, obj):
        return bool(obj.right_thumb)
    has_right_thumb.boolean = True
    has_right_thumb.short_description = 'Right Thumb'
    
    def save_model(self, request, obj, form, change):
        """Set captured_by when creating"""
        if not change:
            obj.captured_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(StudentSubject)
class StudentSubjectAdmin(admin.ModelAdmin):
    """Admin interface for StudentSubject model"""
    
    list_display = ['student', 'subject', 'session', 'session_term', 'is_active', 'registered_at']
    list_filter = ['session', 'session_term', 'is_active', 'registered_at']
    search_fields = [
        'student__application_number', 
        'student__admission_number',
        'subject__name',
        'subject__code'
    ]
    ordering = ['-registered_at']
    readonly_fields = ['registered_at']
    
    fieldsets = (
        (_('Registration'), {
            'fields': ('student', 'subject', 'session', 'session_term', 'is_active')
        }),
    )


# ===========================
# STAFF ADMIN
# ===========================

class StaffEducationInline(admin.TabularInline):
    """Inline for Staff Education records"""
    model = StaffEducation
    extra = 1
    fields = ['level', 'institution_name', 'year_of_graduation', 'degree', 'certificate']


@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    """Admin interface for Staff model"""
    
    list_display = [
        'staff_id', 
        'get_full_name', 
        'staff_type',
        'zone',
        'assigned_class',
        'status', 
        'entry_date'
    ]
    list_filter = ['status', 'staff_type', 'zone', 'marital_status', 'entry_date']
    search_fields = [
        'staff_id', 
        'surname', 
        'first_name', 
        'other_names',
        'phone_number',
        'user__email'
    ]
    ordering = ['-entry_date']
    readonly_fields = ['staff_id', 'created_at', 'updated_at']
    inlines = [StaffEducationInline]
    
    fieldsets = (
        (_('Registration & User'), {
            'fields': ('staff_id', 'user', 'created_by')
        }),
        (_('Personal Information'), {
            'fields': (
                'title', 'surname', 'first_name', 'other_names',
                'nationality', 'state_of_origin', 'date_of_birth',
                'permanent_address', 'phone_number',
                'marital_status', 'religion'
            )
        }),
        (_('Employment Details'), {
            'fields': (
                'entry_date', 'staff_type', 'zone', 'assigned_class',
                'number_of_children_in_school', 'status'
            )
        }),
        (_('Account Details'), {
            'fields': ('account_name', 'account_number', 'bank_name')
        }),
        (_('Documents'), {
            'fields': ('passport_photo',)
        }),
        (_('Tracking'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_full_name(self, obj):
        """Display staff member's full name"""
        return obj.get_full_name()
    get_full_name.short_description = 'Name'


@admin.register(StaffEducation)
class StaffEducationAdmin(admin.ModelAdmin):
    """Admin interface for StaffEducation model"""
    
    list_display = ['staff', 'level', 'institution_name', 'year_of_graduation', 'degree']
    list_filter = ['level', 'degree', 'year_of_graduation']
    search_fields = [
        'staff__staff_id',
        'staff__surname',
        'staff__first_name',
        'institution_name'
    ]
    ordering = ['-year_of_graduation']
    
    fieldsets = (
        (None, {
            'fields': ('staff', 'level', 'institution_name', 'year_of_graduation', 'degree', 'certificate')
        }),
    )


@admin.register(SalaryGrade)
class SalaryGradeAdmin(admin.ModelAdmin):
    """Admin interface for SalaryGrade model"""
    
    list_display = ['grade_number', 'monthly_amount', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['description']
    ordering = ['grade_number']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        (None, {
            'fields': ('grade_number', 'monthly_amount', 'description', 'is_active')
        }),
        (_('Tracking'), {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(StaffSalary)
class StaffSalaryAdmin(admin.ModelAdmin):
    """Admin interface for StaffSalary model"""
    
    list_display = ['staff', 'salary_grade', 'effective_date', 'assigned_by']
    list_filter = ['salary_grade', 'effective_date']
    search_fields = [
        'staff__staff_id',
        'staff__surname',
        'staff__first_name'
    ]
    ordering = ['-effective_date']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        (None, {
            'fields': ('staff', 'salary_grade', 'effective_date', 'notes')
        }),
        (_('Tracking'), {
            'fields': ('assigned_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(SalaryPayment)
class SalaryPaymentAdmin(admin.ModelAdmin):
    """Admin interface for SalaryPayment model"""
    
    list_display = [
        'staff', 
        'month', 
        'year', 
        'amount', 
        'deductions', 
        'net_amount', 
        'status',
        'payment_date'
    ]
    list_filter = ['status', 'year', 'month', 'payment_date']
    search_fields = [
        'staff__staff_id',
        'staff__surname',
        'staff__first_name',
        'reference_number'
    ]
    ordering = ['-year', '-month', 'staff']
    readonly_fields = ['net_amount', 'created_at', 'updated_at']
    
    fieldsets = (
        (_('Staff & Period'), {
            'fields': ('staff', 'salary_grade', 'month', 'year')
        }),
        (_('Payment Details'), {
            'fields': ('amount', 'deductions', 'net_amount', 'status', 'payment_date', 'reference_number')
        }),
        (_('Notes'), {
            'fields': ('notes',)
        }),
        (_('Tracking'), {
            'fields': ('processed_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


class LoanPaymentInline(admin.TabularInline):
    """Inline for Loan Payments"""
    model = LoanPayment
    extra = 0
    fields = ['amount', 'payment_date', 'month', 'year', 'reference_number', 'processed_by']
    readonly_fields = ['processed_by']


@admin.register(LoanApplication)
class LoanApplicationAdmin(admin.ModelAdmin):
    """Admin interface for LoanApplication model"""
    
    list_display = [
        'application_number',
        'staff',
        'loan_amount',
        'total_amount',
        'monthly_deduction',
        'status',
        'application_date'
    ]
    list_filter = ['status', 'application_date', 'approval_date']
    search_fields = [
        'application_number',
        'staff__staff_id',
        'staff__surname',
        'staff__first_name'
    ]
    ordering = ['-application_date']
    readonly_fields = [
        'application_number', 
        'total_amount', 
        'monthly_deduction',
        'created_at', 
        'updated_at'
    ]
    inlines = [LoanPaymentInline]
    
    fieldsets = (
        (_('Application Info'), {
            'fields': ('application_number', 'staff', 'application_date', 'status')
        }),
        (_('Loan Details'), {
            'fields': (
                'loan_amount', 
                'interest_rate', 
                'total_amount',
                'repayment_period_months',
                'monthly_deduction',
                'purpose'
            )
        }),
        (_('Review'), {
            'fields': (
                'reviewed_by',
                'review_notes',
                'approval_date',
                'disbursement_date',
                'rejection_reason'
            )
        }),
        (_('Tracking'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(LoanPayment)
class LoanPaymentAdmin(admin.ModelAdmin):
    """Admin interface for LoanPayment model"""
    
    list_display = [
        'loan_application',
        'amount',
        'payment_date',
        'month',
        'year',
        'reference_number',
        'processed_by'
    ]
    list_filter = ['payment_date', 'year', 'month']
    search_fields = [
        'loan_application__application_number',
        'loan_application__staff__staff_id',
        'reference_number'
    ]
    ordering = ['-payment_date']
    readonly_fields = ['created_at']
    
    fieldsets = (
        (None, {
            'fields': (
                'loan_application',
                'amount',
                'payment_date',
                'month',
                'year',
                'reference_number',
                'notes'
            )
        }),
        (_('Tracking'), {
            'fields': ('processed_by', 'created_at'),
            'classes': ('collapse',)
        }),
    )


# ===========================
# FEE ADMIN
# ===========================

@admin.register(FeeType)
class FeeTypeAdmin(admin.ModelAdmin):
    """Admin interface for FeeType model"""
    
    list_display = [
        'name',
        'amount',
        'school',
        'max_installments',
        'is_mandatory',
        'is_recurring_per_term',
        'is_active',
        'created_at'
    ]
    list_filter = ['school', 'is_mandatory', 'is_recurring_per_term', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    filter_horizontal = ['applicable_classes']
    ordering = ['school', 'name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('name', 'description', 'amount', 'school')
        }),
        (_('Applicability'), {
            'fields': ('applicable_classes',)
        }),
        (_('Payment Options'), {
            'fields': ('max_installments', 'is_mandatory', 'is_recurring_per_term', 'is_active')
        }),
        (_('Tracking'), {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(FeePayment)
class FeePaymentAdmin(admin.ModelAdmin):
    """Admin interface for FeePayment model"""
    
    list_display = [
        'receipt_number',
        'student',
        'fee_type',
        'amount',
        'installment_number',
        'payment_date',
        'payment_method',
        'processed_by'
    ]
    list_filter = ['payment_method', 'payment_date', 'fee_type', 'session', 'session_term']
    search_fields = [
        'receipt_number',
        'reference_number',
        'student__admission_number',
        'student__biodata__surname',
        'student__biodata__first_name',
        'fee_type__name'
    ]
    ordering = ['-payment_date', '-created_at']
    readonly_fields = ['receipt_number', 'created_at']
    
    fieldsets = (
        (_('Payment Information'), {
            'fields': ('student', 'fee_type', 'amount', 'installment_number')
        }),
        (_('Session/Term'), {
            'fields': ('session', 'session_term')
        }),
        (_('Payment Details'), {
            'fields': ('payment_date', 'payment_method', 'reference_number', 'receipt_number')
        }),
        (_('Notes'), {
            'fields': ('notes',)
        }),
        (_('Tracking'), {
            'fields': ('processed_by', 'created_at'),
            'classes': ('collapse',)
        }),
    )

