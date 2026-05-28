from django.contrib.auth.models import User
from django.db import models
import uuid


class Tenant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class DataSource(models.Model):
    SOURCE_TYPES = [
        ('SAP',     'SAP'),
        ('UTILITY', 'Utility'),
        ('TRAVEL',  'Travel'),
    ]
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    source_type = models.CharField(max_length=20, choices=SOURCE_TYPES)
    name = models.CharField(max_length=255)

    def __str__(self):
        return f'{self.name} ({self.source_type})'


class ImportJob(models.Model):
    STATUS_CHOICES = [
        ('PENDING',    'Pending'),
        ('PROCESSING', 'Processing'),
        ('COMPLETED',  'Completed'),
        ('FAILED',     'Failed'),
    ]
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    source = models.ForeignKey(DataSource, on_delete=models.CASCADE)
    uploaded_file = models.FileField(upload_to='imports/')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    row_count = models.IntegerField(default=0)
    error_log = models.TextField(blank=True)

    def __str__(self):
        return f'ImportJob {self.id} ({self.source}) [{self.status}]'


class RawRecord(models.Model):
    import_job = models.ForeignKey(ImportJob, on_delete=models.CASCADE)
    raw_data = models.JSONField()
    is_processed = models.BooleanField(default=False)


class NormalizedEmissionRecord(models.Model):
    REVIEW_STATUS = [
        ('PENDING',  'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    raw_record = models.ForeignKey(RawRecord, on_delete=models.SET_NULL, null=True)

    source_type = models.CharField(max_length=20)
    activity_type = models.CharField(max_length=255)

    quantity = models.FloatField()
    normalized_unit = models.CharField(max_length=50)
    scope = models.CharField(max_length=20)

    emission_factor = models.FloatField(default=0)
    calculated_emissions = models.FloatField(default=0)

    suspicious = models.BooleanField(default=False)
    suspicious_reason = models.TextField(blank=True, null=True)

    review_status = models.CharField(max_length=20, choices=REVIEW_STATUS, default='PENDING')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    date = models.DateField(null=True, blank=True)
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_edited = models.BooleanField(default=False)
    edit_reason = models.TextField(blank=True, null=True)

    source_metadata = models.JSONField(default=dict)

    def __str__(self):
        return f'{self.source_type} | {self.activity_type} | {self.calculated_emissions} kg CO2e'


class AuditEvent(models.Model):
    ACTION_CHOICES = [
        ('CREATED',  'Created'),
        ('EDITED',   'Edited'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('FLAGGED',  'Flagged'),
    ]
    record = models.ForeignKey(
        NormalizedEmissionRecord,
        on_delete=models.CASCADE,
        related_name='audit_events',
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    note = models.TextField(blank=True)
    snapshot = models.JSONField()

    def __str__(self):
        return f'{self.action} on record {self.record_id} at {self.timestamp}'
