import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Tenant",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=255)),
            ],
        ),
        migrations.CreateModel(
            name="DataSource",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("source_type", models.CharField(choices=[("SAP", "SAP"), ("UTILITY", "Utility"), ("TRAVEL", "Travel")], max_length=20)),
                ("name", models.CharField(max_length=255)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="emissions.tenant")),
            ],
        ),
        migrations.CreateModel(
            name="ImportJob",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("uploaded_file", models.FileField(upload_to="imports/")),
                ("status", models.CharField(choices=[("PENDING", "Pending"), ("PROCESSING", "Processing"), ("COMPLETED", "Completed"), ("FAILED", "Failed")], default="PENDING", max_length=20)),
                ("source", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="emissions.datasource")),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="emissions.tenant")),
            ],
        ),
        migrations.CreateModel(
            name="RawRecord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("raw_data", models.JSONField()),
                ("is_processed", models.BooleanField(default=False)),
                ("import_job", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="emissions.importjob")),
            ],
        ),
        migrations.CreateModel(
            name="NormalizedEmissionRecord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("source_type", models.CharField(max_length=20)),
                ("activity_type", models.CharField(max_length=255)),
                ("quantity", models.FloatField()),
                ("normalized_unit", models.CharField(max_length=50)),
                ("scope", models.CharField(max_length=20)),
                ("emission_factor", models.FloatField(default=0)),
                ("calculated_emissions", models.FloatField(default=0)),
                ("suspicious", models.BooleanField(default=False)),
                ("suspicious_reason", models.TextField(blank=True, null=True)),
                ("review_status", models.CharField(choices=[("PENDING", "Pending"), ("APPROVED", "Approved"), ("REJECTED", "Rejected")], default="PENDING", max_length=20)),
                ("approved_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ("raw_record", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to="emissions.rawrecord")),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="emissions.tenant")),
            ],
        ),
    ]
