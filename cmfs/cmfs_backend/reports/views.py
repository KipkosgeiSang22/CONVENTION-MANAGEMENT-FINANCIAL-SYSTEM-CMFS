"""
FILE: cmfs/cmfs_backend/reports/views.py
ACTION: CREATE (Phase 10)

Endpoints:
  GET /api/reports/convention/<convention_id>/   — overall + per-unit reports for a convention
  GET /api/reports/unit/<unit_id>/               — reports for a single unit
  GET /api/reports/<report_id>/                  — one report's metadata
  GET /api/reports/<report_id>/download/         — streams the file (Content-Disposition: attachment)
"""

import os
import re

from django.conf import settings
from django.http import FileResponse, Http404
from rest_framework.views import APIView
from rest_framework.response import Response

from auth_app.permissions import IsAuthenticated, IsSuperAdmin, user_can_access_unit
from conventions.models import Convention, ConventionUnit
from conventions.permissions import user_can_view_convention

from .models import Report, AnnualSummary, AuditLog
from .serializers import ReportSerializer, AnnualSummarySerializer, AuditLogSerializer


def _slug(text: str) -> str:
    text = re.sub(r'[^A-Za-z0-9]+', '-', text or '').strip('-')
    return text or 'report'


def _download_filename(report: Report) -> str:
    """
    Every report file is stored on disk as e.g. reports/{conv}/{unit}/final.xlsx,
    so every single report — overall AND every per-unit one — shares the same
    basename ('final.xlsx' / 'final.pdf' / 'opening_day.xlsx' / ...). Streamed
    with that basename in Content-Disposition, the browser can't tell them
    apart: downloading a second one either overwrites the first or gets
    silently renamed 'final(1).xlsx' by the browser, which looks like
    duplicate files. Build a unique, descriptive name instead.
    """
    convention_slug = _slug(report.convention.name)
    if report.convention_unit_id is None:
        unit_slug = 'overall'
    else:
        unit = report.convention_unit
        unit_slug = _slug(unit.display_name if unit else f'unit-{report.convention_unit_id}')
    return f"{convention_slug}-{unit_slug}-{report.report_type}.{report.format}"


def _can_access_report(user, report: Report) -> bool:
    """
    Overall (convention_unit is NULL) reports: Super Admin / National Head
    always; Regional Head only for a regional-or-narrower convention within
    their own region.
    Per-unit reports: same `user_can_access_unit` check used everywhere else.
    """
    if report.convention_unit_id is None:
        if user.role == 'super_admin':
            return True
        if user.role == 'national_head':
            # National Head is only involved in NATIONAL-scope conventions —
            # mirrors user_can_view_convention, checked here too since this
            # helper is also called directly (report detail/download) without
            # necessarily going through ConventionReportsView first.
            return report.convention.scope == 'national'
        if user.role == 'regional_head':
            return report.convention.units.filter(region_id=user.region_id).exists()
        return False
    return user_can_access_unit(user, report.convention_unit)


class ConventionReportsView(APIView):
    """GET /api/reports/convention/<convention_id>/ — overall + per-unit reports."""
    permission_classes = [IsAuthenticated]

    def get(self, request, convention_id):
        user = request.auth_user
        try:
            convention = Convention.objects.get(pk=convention_id)
        except Convention.DoesNotExist:
            return Response({'error': 'Not found.', 'code': 'not_found'}, status=404)

        if not user_can_view_convention(user, convention):
            return Response({'error': 'Forbidden.', 'code': 'forbidden'}, status=403)

        reports = Report.objects.filter(convention=convention).select_related('convention_unit')
        visible = [r for r in reports if _can_access_report(user, r)]
        return Response({'reports': ReportSerializer(visible, many=True).data})


class UnitReportsView(APIView):
    """GET /api/reports/unit/<unit_id>/ — reports for a single ConventionUnit."""
    permission_classes = [IsAuthenticated]

    def get(self, request, unit_id):
        user = request.auth_user
        try:
            unit = ConventionUnit.objects.get(pk=unit_id)
        except ConventionUnit.DoesNotExist:
            return Response({'error': 'Not found.', 'code': 'not_found'}, status=404)

        if not user_can_access_unit(user, unit):
            return Response({'error': 'Forbidden.', 'code': 'forbidden'}, status=403)

        reports = Report.objects.filter(convention_unit=unit)
        return Response({'reports': ReportSerializer(reports, many=True).data})


class ReportDetailView(APIView):
    """GET /api/reports/<report_id>/ — one report's metadata."""
    permission_classes = [IsAuthenticated]

    def get(self, request, report_id):
        user = request.auth_user
        try:
            report = Report.objects.select_related('convention_unit', 'convention').get(pk=report_id)
        except Report.DoesNotExist:
            return Response({'error': 'Not found.', 'code': 'not_found'}, status=404)

        if not _can_access_report(user, report):
            return Response({'error': 'Forbidden.', 'code': 'forbidden'}, status=403)

        return Response({'report': ReportSerializer(report).data})


class ReportDownloadView(APIView):
    """GET /api/reports/<report_id>/download/ — streams the file directly."""
    permission_classes = [IsAuthenticated]

    def get(self, request, report_id):
        user = request.auth_user
        try:
            report = Report.objects.select_related('convention_unit', 'convention').get(pk=report_id)
        except Report.DoesNotExist:
            return Response({'error': 'Not found.', 'code': 'not_found'}, status=404)

        if not _can_access_report(user, report):
            return Response({'error': 'Forbidden.', 'code': 'forbidden'}, status=403)

        if report.status != 'generated' or not report.file_path:
            return Response({'error': 'Report is not ready for download.', 'code': 'not_ready'}, status=400)

        abs_path = os.path.join(settings.MEDIA_ROOT, report.file_path)
        if not os.path.exists(abs_path):
            raise Http404('Report file missing on disk.')

        filename = _download_filename(report)
        content_type = (
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            if report.format == 'xlsx' else 'application/pdf'
        )
        response = FileResponse(open(abs_path, 'rb'), content_type=content_type)
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response


class DevGenerateReportsView(APIView):
    """
    POST /api/reports/dev-generate/<convention_id>/

    DEVELOPMENT/TESTING CONVENIENCE ONLY — not part of the Phase 10 spec.
    Lets Super Admin generate (or regenerate) the full report set on demand,
    at ANY convention status, without going through the irreversible
    financial-close flow. Intended so reports can be inspected/tested while
    a convention is still DRAFT/OPEN/ACTIVE, before real financial close is
    appropriate.

    Body (optional): {"report_type": "final" | "opening_day"}  (default "final")

    Consider removing or gating this behind settings.DEBUG before production,
    since it bypasses the pre-close checklist and TOTP confirmation.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, convention_id):
        user = request.auth_user
        if user.role != 'super_admin':
            return Response(
                {'error': 'This test/dev tool is restricted to Super Admin.', 'code': 'forbidden'},
                status=403,
            )

        try:
            convention = Convention.objects.get(pk=convention_id)
        except Convention.DoesNotExist:
            return Response({'error': 'Not found.', 'code': 'not_found'}, status=404)

        report_type = request.data.get('report_type', 'final')
        if report_type not in ('final', 'opening_day'):
            return Response({'error': 'report_type must be "final" or "opening_day".'}, status=400)

        from .generators import generate_reports_for_convention
        reports = generate_reports_for_convention(convention, report_type=report_type, generated_by_id=user.id)
        failed = [r for r in reports if r.status == 'failed']

        return Response({
            'message': f'Generated {len(reports)} report file(s) for "{convention.name}"'
                       + (f' — {len(failed)} FAILED, check error_message.' if failed else '.'),
            'reports': ReportSerializer(reports, many=True).data,
        })


# ── Annual Summary (Phase 11) ────────────────────────────────────────────────

class AnnualSummaryListView(APIView):
    """
    GET /api/reports/annual-summary/ — list every AnnualSummary generated so
    far (Super Admin only — this is a Super-Admin-only artefact per the
    Annual Summary Report spec, emailed only to Super Admin).
    """
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def get(self, request):
        summaries = AnnualSummary.objects.all()
        return Response({'annual_summaries': AnnualSummarySerializer(summaries, many=True).data})


class AnnualSummaryDownloadView(APIView):
    """
    GET /api/reports/annual-summary/<year>/download/?format=xlsx|pdf
    Streams the annual summary file directly. Super Admin only.
    """
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def get(self, request, year):
        try:
            summary = AnnualSummary.objects.get(year=year)
        except AnnualSummary.DoesNotExist:
            return Response({'error': 'Not found.', 'code': 'not_found'}, status=404)

        if summary.status != 'generated':
            return Response({'error': 'Annual summary is not ready for download.', 'code': 'not_ready'}, status=400)

        fmt = request.query_params.get('format', 'xlsx')
        if fmt not in ('xlsx', 'pdf'):
            return Response({'error': 'format must be "xlsx" or "pdf".'}, status=400)

        rel_path = summary.xlsx_path if fmt == 'xlsx' else summary.pdf_path
        abs_path = os.path.join(settings.MEDIA_ROOT, rel_path)
        if not rel_path or not os.path.exists(abs_path):
            raise Http404('Annual summary file missing on disk.')

        content_type = (
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            if fmt == 'xlsx' else 'application/pdf'
        )
        response = FileResponse(open(abs_path, 'rb'), content_type=content_type)
        response['Content-Disposition'] = f'attachment; filename="annual-summary-{year}.{fmt}"'
        return response


class DevGenerateAnnualSummaryView(APIView):
    """
    POST /api/reports/annual-summary/dev-generate/<year>/

    DEVELOPMENT/TESTING CONVENIENCE ONLY — lets Super Admin generate (or
    regenerate) the Annual Summary for a given year on demand, without
    waiting for the 7-days-after-December-close automatic trigger. Mirrors
    DevGenerateReportsView above.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, year):
        user = request.auth_user
        if user.role != 'super_admin':
            return Response(
                {'error': 'This test/dev tool is restricted to Super Admin.', 'code': 'forbidden'},
                status=403,
            )

        from conventions.tasks import generate_annual_summary
        summary = generate_annual_summary(year, triggered_by=user.id)

        return Response({
            'message': f'Annual summary for {year}: {summary.status}'
                       + (f' — {summary.error_message}' if summary.status == 'failed' else '.'),
            'annual_summary': AnnualSummarySerializer(summary).data,
        })


# ── Audit Log Viewer (Phase 11) ───────────────────────────────────────────────

class AuditLogListView(APIView):
    """
    GET /api/audit-logs/ — Super Admin only, paginated, searchable/filterable
    by user, action, and date range.

    Query params:
      page       (default 1)
      page_size  (default 50, max 200)
      user_id    exact match
      action     case-insensitive substring match
      date_from  ISO date (inclusive)
      date_to    ISO date (inclusive)
    """
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def get(self, request):
        qs = AuditLog.objects.all()

        user_id = request.query_params.get('user_id')
        if user_id:
            qs = qs.filter(user_id=user_id)

        action = request.query_params.get('action')
        if action:
            qs = qs.filter(action__icontains=action)

        date_from = request.query_params.get('date_from')
        if date_from:
            qs = qs.filter(timestamp__date__gte=date_from)

        date_to = request.query_params.get('date_to')
        if date_to:
            qs = qs.filter(timestamp__date__lte=date_to)

        try:
            page = max(1, int(request.query_params.get('page', 1)))
        except (TypeError, ValueError):
            page = 1
        try:
            page_size = min(200, max(1, int(request.query_params.get('page_size', 50))))
        except (TypeError, ValueError):
            page_size = 50

        total = qs.count()
        start = (page - 1) * page_size
        results = qs[start:start + page_size]

        return Response({
            'results': AuditLogSerializer(results, many=True).data,
            'total': total,
            'page': page,
            'page_size': page_size,
            'total_pages': (total + page_size - 1) // page_size if page_size else 1,
        })
