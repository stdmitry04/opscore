from rest_framework import serializers
from .models import Employee, Job, Document


class EmployeeListSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = Employee
        fields = [
            'id', 'full_name', 'first_name', 'last_name', 'email',
            'title', 'department', 'hire_date', 'status', 'created_at',
        ]


class EmployeeDetailSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = Employee
        fields = '__all__'


class EmployeeSalarySerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = Employee
        fields = ['id', 'full_name', 'title', 'department', 'salary']


class JobSerializer(serializers.ModelSerializer):
    class Meta:
        model = Job
        fields = '__all__'


class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ['id', 'name', 'doc_type', 'is_indexed', 'created_at', 'file_size']
