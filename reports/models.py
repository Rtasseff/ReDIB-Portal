"""
Reports and statistics models for ReDIB COA portal.
Based on design document section 9 - Reporting and Statistics.
"""

from django.db import models
from django.conf import settings
from calls.models import Call
from core.models import Node


class ReportGeneration(models.Model):
    """
    Track generated reports for audit and download.
    """

    REPORT_TYPES = [
        ('call_summary', 'Call Summary Report'),
        ('node_statistics', 'Node Usage Statistics'),
        ('ministry_annual', 'Ministry Annual Report'),
        ('equipment_utilization', 'Equipment Utilization Report'),
        ('publication_outcomes', 'Publication Outcomes Report'),
        ('user_activity', 'User Activity Report'),
    ]

    report_type = models.CharField(max_length=50, choices=REPORT_TYPES)
    title = models.CharField(max_length=200)

    # Report parameters
    call = models.ForeignKey(Call, on_delete=models.CASCADE, null=True, blank=True)
    node = models.ForeignKey(Node, on_delete=models.CASCADE, null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    # Generated output
    file_path = models.FileField(upload_to='reports/%Y/%m/', blank=True)
    file_format = models.CharField(
        max_length=10,
        choices=[('pdf', 'PDF'), ('xlsx', 'Excel'), ('csv', 'CSV')],
        default='pdf'
    )

    # Metadata
    generated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    generated_at = models.DateTimeField(auto_now_add=True)
    parameters_json = models.JSONField(default=dict, help_text='Report generation parameters')

    class Meta:
        ordering = ['-generated_at']
        verbose_name = 'Report Generation'

    def __str__(self):
        return f"{self.title} ({self.get_file_format_display()}) - {self.generated_at.date()}"
