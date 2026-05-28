import io

from django.db.models import Sum
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import (
    AuditEvent, DataSource, ImportJob, NormalizedEmissionRecord, RawRecord, Tenant,
)
from .serializers import (
    AuditEventSerializer, DataSourceSerializer, ImportJobSerializer,
    NormalizedEmissionRecordSerializer, RawRecordSerializer, TenantSerializer,
)


def _record_snapshot(record: NormalizedEmissionRecord) -> dict:
    return {
        'source_type': record.source_type,
        'activity_type': record.activity_type,
        'quantity': record.quantity,
        'normalized_unit': record.normalized_unit,
        'scope': record.scope,
        'emission_factor': record.emission_factor,
        'calculated_emissions': record.calculated_emissions,
        'review_status': record.review_status,
        'suspicious': record.suspicious,
        'is_edited': record.is_edited,
    }


class TenantViewSet(viewsets.ModelViewSet):
    queryset = Tenant.objects.all()
    serializer_class = TenantSerializer
    permission_classes = [AllowAny]


class DataSourceViewSet(viewsets.ModelViewSet):
    queryset = DataSource.objects.all()
    serializer_class = DataSourceSerializer
    permission_classes = [AllowAny]


class ImportJobViewSet(viewsets.ModelViewSet):
    queryset = ImportJob.objects.all().order_by('-created_at')
    serializer_class = ImportJobSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        import_job = serializer.save(status='PENDING')

        try:
            source = DataSource.objects.get(pk=import_job.source_id)
            tenant = import_job.tenant
            import_job.status = 'PROCESSING'
            import_job.save(update_fields=['status'])

            file_obj = import_job.uploaded_file
            file_obj.open('rb')

            source_type = source.source_type.upper()
            if source_type == 'SAP':
                from .parsers.sap import parse_sap_csv
                success, err_count, errors = parse_sap_csv(file_obj, import_job, tenant)
            elif source_type == 'UTILITY':
                from .parsers.utility import parse_utility_csv
                success, err_count, errors = parse_utility_csv(file_obj, import_job, tenant)
            elif source_type == 'TRAVEL':
                from .parsers.travel import parse_travel_json
                raw_bytes = file_obj.read()
                success, err_count, errors = parse_travel_json(io.BytesIO(raw_bytes), import_job, tenant)
            else:
                import_job.status = 'FAILED'
                import_job.error_log = f'Unknown source type: {source_type}'
                import_job.save(update_fields=['status', 'error_log'])
                return Response({'error': f'Unknown source type: {source_type}'}, status=400)

            file_obj.close()
            import_job.row_count = success
            import_job.error_log = '\n'.join(errors) if errors else ''
            import_job.status = 'COMPLETED' if success > 0 or err_count == 0 else 'FAILED'
            import_job.save(update_fields=['status', 'row_count', 'error_log'])

        except Exception as exc:
            import_job.status = 'FAILED'
            import_job.error_log = str(exc)
            import_job.save(update_fields=['status', 'error_log'])

        return Response(ImportJobSerializer(import_job).data, status=status.HTTP_201_CREATED)


class RawRecordViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = RawRecord.objects.all()
    serializer_class = RawRecordSerializer
    permission_classes = [AllowAny]


class NormalizedEmissionRecordViewSet(viewsets.ModelViewSet):
    queryset = NormalizedEmissionRecord.objects.all().order_by('-created_at')
    serializer_class = NormalizedEmissionRecordSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = super().get_queryset()
        scope = self.request.query_params.get('scope')
        source_type = self.request.query_params.get('source_type')
        review_status = self.request.query_params.get('review_status')
        suspicious = self.request.query_params.get('suspicious')
        tenant_id = self.request.query_params.get('tenant')

        if scope:
            qs = qs.filter(scope=scope)
        if source_type:
            qs = qs.filter(source_type=source_type)
        if review_status:
            qs = qs.filter(review_status=review_status)
        if suspicious is not None:
            qs = qs.filter(suspicious=(suspicious.lower() in ('true', '1', 'yes')))
        if tenant_id:
            qs = qs.filter(tenant_id=tenant_id)
        return qs

    def perform_update(self, serializer):
        record = serializer.save(is_edited=True)
        edit_reason = self.request.data.get('edit_reason', '')
        if edit_reason:
            record.edit_reason = edit_reason
            record.save(update_fields=['edit_reason'])
        actor = self.request.user if self.request.user.is_authenticated else None
        AuditEvent.objects.create(
            record=record,
            action='EDITED',
            actor=actor,
            note=edit_reason,
            snapshot=_record_snapshot(record),
        )

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        record = self.get_object()
        record.review_status = 'APPROVED'
        record.approved_by = request.user if request.user.is_authenticated else None
        record.save(update_fields=['review_status', 'approved_by'])
        AuditEvent.objects.create(
            record=record,
            action='APPROVED',
            actor=record.approved_by,
            note=request.data.get('note', ''),
            snapshot=_record_snapshot(record),
        )
        return Response({'status': 'approved', 'id': record.id})

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        record = self.get_object()
        record.review_status = 'REJECTED'
        record.save(update_fields=['review_status'])
        actor = request.user if request.user.is_authenticated else None
        AuditEvent.objects.create(
            record=record,
            action='REJECTED',
            actor=actor,
            note=request.data.get('note', ''),
            snapshot=_record_snapshot(record),
        )
        return Response({'status': 'rejected', 'id': record.id})

    @action(detail=False, methods=['get'])
    def summary(self, request):
        qs = self.get_queryset()

        total = qs.aggregate(t=Sum('calculated_emissions'))['t'] or 0.0

        by_scope = {}
        for scope in ('Scope 1', 'Scope 2', 'Scope 3'):
            val = qs.filter(scope=scope).aggregate(t=Sum('calculated_emissions'))['t'] or 0.0
            by_scope[scope] = round(val, 4)

        by_source = {}
        for src in ('SAP', 'UTILITY', 'TRAVEL'):
            val = qs.filter(source_type=src).aggregate(t=Sum('calculated_emissions'))['t'] or 0.0
            by_source[src] = round(val, 4)

        by_status = {}
        for st in ('PENDING', 'APPROVED', 'REJECTED'):
            by_status[st] = qs.filter(review_status=st).count()

        return Response({
            'total_emissions': round(total, 4),
            'by_scope': by_scope,
            'by_source': by_source,
            'by_status': by_status,
            'suspicious_count': qs.filter(suspicious=True).count(),
        })


class AuditEventViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditEvent.objects.all().order_by('-timestamp')
    serializer_class = AuditEventSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = super().get_queryset()
        record_id = self.request.query_params.get('record_id')
        if record_id:
            qs = qs.filter(record_id=record_id)
        return qs
