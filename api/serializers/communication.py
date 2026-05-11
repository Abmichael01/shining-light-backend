from rest_framework import serializers
from api.models import AIActionLog, AIMessageDraft, Class, CommunicationTemplate

class CommunicationTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommunicationTemplate
        fields = '__all__'
        read_only_fields = ['created_by', 'created_at', 'updated_at']


class AIMessageDraftSerializer(serializers.ModelSerializer):
    class_id = serializers.PrimaryKeyRelatedField(
        source='class_model',
        queryset=Class.objects.all(),
        required=False,
        allow_null=True,
    )
    class_name = serializers.CharField(source='class_model.name', read_only=True, allow_null=True)
    created_by_email = serializers.EmailField(source='created_by.email', read_only=True, allow_null=True)
    approved_by_email = serializers.EmailField(source='approved_by.email', read_only=True, allow_null=True)
    sent_by_email = serializers.EmailField(source='sent_by.email', read_only=True, allow_null=True)
    target_summary = serializers.SerializerMethodField()

    class Meta:
        model = AIMessageDraft
        fields = [
            'id',
            'channel',
            'target_group',
            'class_id',
            'class_name',
            'student_ids',
            'custom_recipients',
            'prompt',
            'subject',
            'content',
            'status',
            'ai_model',
            'send_summary',
            'error_message',
            'rejection_reason',
            'target_summary',
            'created_by_email',
            'approved_by_email',
            'sent_by_email',
            'approved_at',
            'rejected_at',
            'sent_at',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'status',
            'ai_model',
            'send_summary',
            'error_message',
            'rejection_reason',
            'created_by_email',
            'approved_by_email',
            'sent_by_email',
            'approved_at',
            'rejected_at',
            'sent_at',
            'created_at',
            'updated_at',
        ]
        extra_kwargs = {
            'subject': {'required': False, 'allow_blank': True},
            'content': {'required': False, 'allow_blank': True},
            'student_ids': {'required': False},
            'custom_recipients': {'required': False},
        }

    def validate_student_ids(self, value):
        if value is None:
            return []
        if not isinstance(value, list):
            raise serializers.ValidationError('student_ids must be a list.')
        return [str(item).strip() for item in value if str(item).strip()]

    def validate_custom_recipients(self, value):
        if value is None:
            return []
        if not isinstance(value, list):
            raise serializers.ValidationError('custom_recipients must be a list.')
        return [str(item).strip() for item in value if str(item).strip()]

    def get_target_summary(self, obj):
        if obj.target_group == 'specific_class' and obj.class_model:
            return f"{obj.class_model.name}"
        if obj.target_group == 'custom':
            count = len(obj.student_ids or []) + len(obj.custom_recipients or [])
            return f"Custom recipients ({count})"
        return obj.get_target_group_display()


class AIActionLogSerializer(serializers.ModelSerializer):
    approved_by_email = serializers.EmailField(source='approved_by.email', read_only=True, allow_null=True)
    reverted_by_email = serializers.EmailField(source='reverted_by.email', read_only=True, allow_null=True)
    can_revert = serializers.SerializerMethodField()

    class Meta:
        model = AIActionLog
        fields = [
            'id',
            'action_type',
            'label',
            'summary',
            'payload',
            'result',
            'changes',
            'status',
            'error_message',
            'approved_by_email',
            'reverted_by_email',
            'approved_at',
            'reverted_at',
            'created_at',
            'updated_at',
            'can_revert',
        ]
        read_only_fields = fields

    def get_can_revert(self, obj):
        return obj.status == 'approved'
