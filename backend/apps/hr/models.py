import uuid
from django.db import models
from apps.core.models import Organization


class Employee(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('terminated', 'Terminated'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    org = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='employees')
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    title = models.CharField(max_length=150)
    department = models.CharField(max_length=100)
    hire_date = models.DateField()
    salary = models.DecimalField(max_digits=12, decimal_places=2, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    manager = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True, related_name='reports'
    )
    bio = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['org', 'status']),
            models.Index(fields=['org', 'department']),
            models.Index(fields=['org', '-created_at']),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class Job(models.Model):
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('closed', 'Closed'),
        ('draft', 'Draft'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    org = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='jobs')
    title = models.CharField(max_length=200)
    department = models.CharField(max_length=100)
    description = models.TextField()
    requirements = models.TextField()
    salary_min = models.DecimalField(max_digits=12, decimal_places=2, null=True)
    salary_max = models.DecimalField(max_digits=12, decimal_places=2, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=['org', 'status'])]


class Document(models.Model):
    DOC_TYPES = [
        ('policy', 'Policy'),
        ('handbook', 'Handbook'),
        ('job_description', 'Job Description'),
        ('other', 'Other'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    org = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='documents')
    name = models.CharField(max_length=255)
    content = models.TextField()
    doc_type = models.CharField(max_length=50, choices=DOC_TYPES, default='other')
    qdrant_point_ids = models.JSONField(default=list)
    is_indexed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    file_size = models.IntegerField(default=0)
