from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from django.db.models import Q, Count, Avg

from apps.rbac.permissions import HasRBACPermission
from apps.rbac.services import RBACService
from apps.rbac.permissions_registry import Perm, permission_registry
from .models import Employee, Job, Document
from .serializers import (
    EmployeeListSerializer,
    EmployeeDetailSerializer,
    EmployeeSalarySerializer,
    JobSerializer,
    DocumentSerializer,
)


class EmployeeViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated, HasRBACPermission]
    required_permission = permission_registry[Perm("hr.employee").view]
    edit_permission = permission_registry[Perm("hr.employee").edit]
    search_fields = ['first_name', 'last_name', 'email', 'title', 'department']
    filterset_fields = ['department', 'status']
    ordering_fields = ['last_name', 'hire_date', 'created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        return Employee.objects.filter(org=self.request.user.org).select_related('manager')

    def get_serializer_class(self):
        can_view_salary = RBACService.has_permission(self.request.user, permission_registry[Perm("hr.employee.salary").view])
        if self.action == 'list':
            return EmployeeListSerializer
        if self.action == 'salary_report' and can_view_salary:
            return EmployeeSalarySerializer
        return EmployeeDetailSerializer

    @action(detail=False, methods=['get'])
    def salary_report(self, request):
        if not RBACService.has_permission(request.user, permission_registry[Perm("hr.employee.salary").view]):
            return Response(
                {'error': f'Missing permission: hr.employee.salary.view'}, status=403
            )
        qs = self.get_queryset().filter(status='active').order_by('-salary')
        serializer = EmployeeSalarySerializer(qs, many=True)
        return Response(serializer.data)


class JobViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated, HasRBACPermission]
    required_permission = permission_registry[Perm("hr.job").view]
    edit_permission = permission_registry[Perm("hr.job").edit]
    search_fields = ['title', 'department', 'description']
    filterset_fields = ['status', 'department']
    ordering = ['-created_at']

    def get_queryset(self):
        return Job.objects.filter(org=self.request.user.org)

    def get_serializer_class(self):
        return JobSerializer


class DocumentViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated, HasRBACPermission]
    required_permission = permission_registry[Perm("hr.document").view]
    edit_permission = permission_registry[Perm("hr.document").edit]
    parser_classes = [MultiPartParser]
    http_method_names = ['get', 'post', 'delete']
    ordering = ['-created_at']

    def get_queryset(self):
        return Document.objects.filter(org=self.request.user.org).order_by('-created_at')

    def get_serializer_class(self):
        return DocumentSerializer

    @action(detail=False, methods=['get'])
    def search(self, request):
        if not RBACService.has_permission(request.user, permission_registry[Perm("hr.document").view]):
            return Response({'error': 'Missing permission: hr.document.view'}, status=403)

        query = request.query_params.get('q', '').strip()
        if not query:
            return Response({'error': 'q parameter required'}, status=400)

        from apps.agent.rag import RAGService
        threshold = float(request.query_params.get('threshold', '0.70'))

        try:
            results = RAGService.search(
                query=query,
                org_id=str(request.user.org.id),
                threshold=threshold,
                top_k=8,
            )
            return Response({'query': query, 'results': results, 'threshold': threshold})
        except Exception as e:
            # qdrant not ready or not indexed yet
            return Response({'query': query, 'results': [], 'error': str(e)})

    def create(self, request, *args, **kwargs):
        file = request.FILES.get('file')
        name = request.data.get('name', file.name if file else 'Untitled')
        doc_type = request.data.get('doc_type', 'other')
        content = request.data.get('content', '')

        if file and not content:
            try:
                content = file.read().decode('utf-8', errors='ignore')
            except Exception:
                content = ''

        doc = Document.objects.create(
            org=request.user.org,
            name=name,
            content=content,
            doc_type=doc_type,
            file_size=len(content.encode()),
        )

        # Trigger async embedding
        from apps.tasks.models import TaskRecord
        from apps.tasks.tasks import embed_document

        task_record = TaskRecord.objects.create(
            task_type='embed_document',
            org=request.user.org,
            payload={'document_id': str(doc.id)},
        )
        embed_document.apply_async(
            kwargs={
                'document_id': str(doc.id),
                'task_record_id': str(task_record.id),
            },
            task_id=str(task_record.id),
            queue='embeddings',
        )

        return Response({
            'document': DocumentSerializer(doc).data,
            'task_id': str(task_record.id),
        }, status=202)


class AnalyticsView(APIView):
    permission_classes = [IsAuthenticated, HasRBACPermission]
    required_permission = permission_registry[Perm("analytics").view]

    def get(self, request):
        org = request.user.org
        qs = Employee.objects.filter(org=org)

        dept_breakdown = list(
            qs.filter(status='active')
            .values('department')
            .annotate(count=Count('id'))
            .order_by('-count')
        )

        salary_agg = qs.filter(status='active').aggregate(avg_salary=Avg('salary'))

        return Response({
            'headcount': {
                'active': qs.filter(status='active').count(),
                'inactive': qs.filter(status='inactive').count(),
                'terminated': qs.filter(status='terminated').count(),
                'total': qs.count(),
            },
            'department_breakdown': dept_breakdown,
            'avg_salary': float(salary_agg['avg_salary'] or 0),
            'open_jobs': Job.objects.filter(org=org, status='open').count(),
        })
