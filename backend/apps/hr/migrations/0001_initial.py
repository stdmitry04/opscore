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
            name='Employee',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('first_name', models.CharField(max_length=100)),
                ('last_name', models.CharField(max_length=100)),
                ('email', models.EmailField(max_length=254)),
                ('title', models.CharField(max_length=150)),
                ('department', models.CharField(max_length=100)),
                ('hire_date', models.DateField()),
                ('salary', models.DecimalField(decimal_places=2, max_digits=12, null=True)),
                ('status', models.CharField(choices=[('active', 'Active'), ('inactive', 'Inactive'), ('terminated', 'Terminated')], default='active', max_length=20)),
                ('bio', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('manager', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reports', to='hr.employee')),
                ('org', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='employees', to='core.organization')),
            ],
        ),
        migrations.CreateModel(
            name='Job',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('title', models.CharField(max_length=200)),
                ('department', models.CharField(max_length=100)),
                ('description', models.TextField()),
                ('requirements', models.TextField()),
                ('salary_min', models.DecimalField(decimal_places=2, max_digits=12, null=True)),
                ('salary_max', models.DecimalField(decimal_places=2, max_digits=12, null=True)),
                ('status', models.CharField(choices=[('open', 'Open'), ('closed', 'Closed'), ('draft', 'Draft')], default='draft', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('org', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='jobs', to='core.organization')),
            ],
        ),
        migrations.CreateModel(
            name='Document',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
                ('content', models.TextField()),
                ('doc_type', models.CharField(choices=[('policy', 'Policy'), ('handbook', 'Handbook'), ('job_description', 'Job Description'), ('other', 'Other')], default='other', max_length=50)),
                ('qdrant_point_ids', models.JSONField(default=list)),
                ('is_indexed', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('file_size', models.IntegerField(default=0)),
                ('org', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='documents', to='core.organization')),
            ],
        ),
        migrations.AddIndex(
            model_name='employee',
            index=models.Index(fields=['org', 'status'], name='hr_employee_org_status_idx'),
        ),
        migrations.AddIndex(
            model_name='employee',
            index=models.Index(fields=['org', 'department'], name='hr_employee_org_dept_idx'),
        ),
        migrations.AddIndex(
            model_name='employee',
            index=models.Index(fields=['org', '-created_at'], name='hr_employee_org_created_idx'),
        ),
        migrations.AddIndex(
            model_name='job',
            index=models.Index(fields=['org', 'status'], name='hr_job_org_status_idx'),
        ),
    ]
