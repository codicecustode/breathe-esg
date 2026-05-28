from rest_framework import serializers
from .models import Tenant, DataSource, ImportJob, RawRecord, NormalizedEmissionRecord, AuditEvent


class TenantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tenant
        fields = '__all__'


class DataSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataSource
        fields = '__all__'


class ImportJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImportJob
        fields = '__all__'
        read_only_fields = ('status', 'created_at', 'row_count', 'error_log')


class RawRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = RawRecord
        fields = '__all__'


class NormalizedEmissionRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = NormalizedEmissionRecord
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at', 'approved_by')


class AuditEventSerializer(serializers.ModelSerializer):
    actor_username = serializers.SerializerMethodField()

    class Meta:
        model = AuditEvent
        fields = '__all__'

    def get_actor_username(self, obj):
        return obj.actor.username if obj.actor else None
