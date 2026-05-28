import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('emissions', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='importjob',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='importjob',
            name='row_count',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='importjob',
            name='error_log',
            field=models.TextField(blank=True, default=''),
            preserve_default=False,
        ),

        migrations.AddField(
            model_name='normalizedemissionrecord',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='normalizedemissionrecord',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddField(
            model_name='normalizedemissionrecord',
            name='date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='normalizedemissionrecord',
            name='period_start',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='normalizedemissionrecord',
            name='period_end',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='normalizedemissionrecord',
            name='is_edited',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='normalizedemissionrecord',
            name='edit_reason',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='normalizedemissionrecord',
            name='source_metadata',
            field=models.JSONField(default=dict),
        ),

        migrations.CreateModel(
            name='AuditEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('action', models.CharField(
                    choices=[
                        ('CREATED', 'Created'), ('EDITED', 'Edited'),
                        ('APPROVED', 'Approved'), ('REJECTED', 'Rejected'), ('FLAGGED', 'Flagged'),
                    ],
                    max_length=20,
                )),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('note', models.TextField(blank=True)),
                ('snapshot', models.JSONField()),
                ('actor', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    to=settings.AUTH_USER_MODEL,
                )),
                ('record', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='audit_events',
                    to='emissions.normalizedemissionrecord',
                )),
            ],
        ),
    ]
