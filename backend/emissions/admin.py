from django.contrib import admin
from .models import AuditEvent, DataSource, ImportJob, NormalizedEmissionRecord, RawRecord, Tenant


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')


@admin.register(DataSource)
class DataSourceAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'source_type', 'tenant')


@admin.register(ImportJob)
class ImportJobAdmin(admin.ModelAdmin):
    list_display = ('id', 'source', 'tenant', 'status', 'row_count', 'created_at')
    list_filter = ('status',)


@admin.register(RawRecord)
class RawRecordAdmin(admin.ModelAdmin):
    list_display = ('id', 'import_job', 'is_processed')


@admin.register(NormalizedEmissionRecord)
class NormalizedEmissionRecordAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'source_type', 'activity_type', 'scope',
        'quantity', 'normalized_unit', 'calculated_emissions',
        'review_status', 'suspicious', 'created_at',
    )
    list_filter = ('source_type', 'scope', 'review_status', 'suspicious')
    search_fields = ('activity_type',)


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ('id', 'record_id', 'action', 'actor', 'timestamp')
    list_filter = ('action',)
