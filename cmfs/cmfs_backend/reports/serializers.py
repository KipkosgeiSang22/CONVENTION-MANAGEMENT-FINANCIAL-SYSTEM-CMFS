"""
FILE: cmfs/cmfs_backend/reports/serializers.py
ACTION: CREATE (Phase 10)
"""

from rest_framework import serializers
from .models import Report, AnnualSummary, AuditLog


class ReportSerializer(serializers.ModelSerializer):
    unit_display_name = serializers.SerializerMethodField()
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = [
            'id', 'convention_id', 'convention_unit_id', 'unit_display_name',
            'report_type', 'format', 'status', 'error_message',
            'generated_by_id', 'generated_at', 'created_at', 'download_url',
        ]

    def get_unit_display_name(self, obj):
        return obj.convention_unit.display_name if obj.convention_unit_id else 'Overall Summary'

    def get_download_url(self, obj):
        if obj.status != 'generated':
            return None
        return f'/api/reports/{obj.id}/download/'


class AnnualSummarySerializer(serializers.ModelSerializer):
    xlsx_download_url = serializers.SerializerMethodField()
    pdf_download_url = serializers.SerializerMethodField()

    class Meta:
        model = AnnualSummary
        fields = [
            'id', 'year', 'status', 'summary_totals', 'error_message',
            'triggered_by_id', 'generated_at', 'created_at',
            'xlsx_download_url', 'pdf_download_url',
        ]

    def get_xlsx_download_url(self, obj):
        if obj.status != 'generated' or not obj.xlsx_path:
            return None
        return f'/api/reports/annual-summary/{obj.year}/download/?format=xlsx'

    def get_pdf_download_url(self, obj):
        if obj.status != 'generated' or not obj.pdf_path:
            return None
        return f'/api/reports/annual-summary/{obj.year}/download/?format=pdf'


class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = [
            'id', 'timestamp', 'user_id', 'user_name', 'action',
            'table_name', 'record_id', 'previous_value', 'new_value', 'ip_address',
        ]
