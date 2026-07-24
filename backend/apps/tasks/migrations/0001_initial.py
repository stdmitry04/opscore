import uuid
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='TaskRecord',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('task_type', models.CharField(max_length=100)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('processing', 'Processing'), ('success', 'Success'), ('failed', 'Failed'), ('dead_letter', 'Dead Letter')], default='pending', max_length=20)),
                ('payload', models.JSONField(default=dict)),
                ('result', models.JSONField(blank=True, null=True)),
                ('error', models.TextField(blank=True)),
                ('retry_count', models.IntegerField(default=0)),
                ('max_retries', models.IntegerField(default=3)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('completed_at', models.DateTimeField(null=True)),
                ('org', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='task_records', to='core.organization')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='taskrecord',
            index=models.Index(fields=['org', 'status'], name='tasks_record_org_status_idx'),
        ),
        migrations.AddIndex(
            model_name='taskrecord',
            index=models.Index(fields=['task_type', 'status'], name='tasks_record_type_status_idx'),
        ),
        migrations.AddIndex(
            model_name='taskrecord',
            index=models.Index(fields=['-created_at'], name='tasks_record_created_idx'),
        ),
    ]
