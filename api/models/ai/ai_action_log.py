from django.db import models
from django.utils.translation import gettext_lazy as _


class AIActionLog(models.Model):
    """Approved AI-assisted admin actions with enough data to audit and revert."""

    ACTION_TYPE_CHOICES = [
        ("update_fee_type_amount", "Update Fee Type Amount"),
        ("update_record_fields", "Update Record Fields"),
    ]
    STATUS_CHOICES = [
        ("approved", "Approved"),
        ("reverted", "Reverted"),
        ("failed", "Failed"),
    ]

    action_type = models.CharField(_("action type"), max_length=80, choices=ACTION_TYPE_CHOICES)
    label = models.CharField(_("label"), max_length=120, blank=True)
    summary = models.TextField(_("summary"), blank=True)

    payload = models.JSONField(_("approval payload"), default=dict, blank=True)
    result = models.JSONField(_("approval result"), default=dict, blank=True)
    changes = models.JSONField(_("changes"), default=list, blank=True)

    status = models.CharField(_("status"), max_length=20, choices=STATUS_CHOICES, default="approved")
    error_message = models.TextField(_("error message"), blank=True)

    approved_by = models.ForeignKey(
        "User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="ai_actions_approved",
    )
    reverted_by = models.ForeignKey(
        "User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ai_actions_reverted",
    )
    approved_at = models.DateTimeField(_("approved at"), auto_now_add=True)
    reverted_at = models.DateTimeField(_("reverted at"), null=True, blank=True)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        verbose_name = _("AI Action Log")
        verbose_name_plural = _("AI Action Logs")
        ordering = ["-approved_at"]
        indexes = [
            models.Index(fields=["status", "approved_at"]),
            models.Index(fields=["action_type", "approved_at"]),
        ]

    def __str__(self):
        return self.summary or f"{self.get_action_type_display()} #{self.pk}"
