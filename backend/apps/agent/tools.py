from abc import ABC, abstractmethod
from typing import ClassVar
from django.db.models import Q, Count, Avg
from apps.rbac.services import RBACService
from apps.rbac.permissions_registry import Perm, permission_registry


class ToolResult:
    """
    Structured responses that give the agent enough context to explain failures clearly.
    error_type lets the agent distinguish between actionable errors (permission_denied →
    tell user to contact admin) and non-actionable ones (not_found → the data simply
    doesn't exist). Without this the agent gets a generic string and often hallucinates
    a workaround.
    """

    @staticmethod
    def ok(data: dict) -> dict:
        return {'ok': True, **data}

    @staticmethod
    def error(error_type: str, message: str) -> dict:
        return {'ok': False, 'error_type': error_type, 'error': message}

    @staticmethod
    def permission_denied(perm: str) -> dict:
        return ToolResult.error(
            'permission_denied',
            f'Your role does not include {perm}. Contact an admin to update your permissions.',
        )

    @staticmethod
    def not_found(resource: str, identifier: str = '') -> dict:
        detail = f': {identifier}' if identifier else ''
        return ToolResult.error('not_found', f'{resource} not found{detail}.')

    @staticmethod
    def validation(message: str) -> dict:
        return ToolResult.error('validation_error', message)

    @staticmethod
    def external(service: str, message: str) -> dict:
        return ToolResult.error('external_error', f'{service} is currently unavailable: {message}')


class Tool(ABC):
    name: ClassVar[str]
    description: ClassVar[str]
    required_permission: ClassVar[Perm]
    input_schema: ClassVar[dict]

    def __call__(self, inp: dict, user, org) -> dict:
        if not RBACService.has_permission(user, self.required_permission):
            return ToolResult.permission_denied(str(self.required_permission))
        return self.execute(inp, user, org)

    @classmethod
    def api_definition(cls) -> dict:
        return {'name': cls.name, 'description': cls.description, 'input_schema': cls.input_schema}

    @abstractmethod
    def execute(self, inp: dict, user, org) -> dict: ...


class ToolRegistry:
    def __init__(self, tools: list[Tool]):
        self._by_name: dict[str, Tool] = {}
        for tool in tools:
            permission_registry[tool.required_permission]  # raises at startup if perm not registered
            self._by_name[tool.name] = tool

    def __getitem__(self, name: str) -> Tool:
        if name not in self._by_name:
            raise KeyError(f"Tool {name!r} is not registered.")
        return self._by_name[name]

    def execute(self, name: str, inp: dict, user, org) -> dict:
        try:
            return self[name](inp, user, org)
        except KeyError:
            return ToolResult.error('unknown_tool', f'No tool named {name!r} is registered.')

    def definitions(self) -> list[dict]:
        return [t.api_definition() for t in self._by_name.values()]


class SearchEmployeesTool(Tool):
    name = 'search_employees'
    required_permission = permission_registry[Perm("hr.employee").view]
    description = (
        "Search the employee database by name, department, or job title. "
        "Returns matching employees with basic info. "
        "Use this when the user asks about staff members, headcount, or 'who works in X'."
    )
    input_schema = {
        'type': 'object',
        'properties': {
            'query': {'type': 'string', 'description': 'Search text (name, title, keywords). Empty string returns all.'},
            'department': {'type': 'string', 'description': 'Filter by department name (optional)'},
            'status': {'type': 'string', 'enum': ['active', 'inactive', 'terminated']},
            'limit': {'type': 'integer', 'description': 'Max results (default 10, max 50)', 'default': 10},
        },
    }

    def execute(self, inp, user, org) -> dict:
        from apps.hr.models import Employee
        qs = Employee.objects.filter(org=org)
        query = inp.get('query', '').strip()
        if query:
            qs = qs.filter(
                Q(first_name__icontains=query) | Q(last_name__icontains=query)
                | Q(title__icontains=query) | Q(email__icontains=query)
            )
        if inp.get('department'):
            qs = qs.filter(department__icontains=inp['department'])
        if inp.get('status'):
            qs = qs.filter(status=inp['status'])

        limit = min(int(inp.get('limit', 10)), 50)
        include_salary = RBACService.has_permission(user, permission_registry[Perm("hr.employee.salary").view])
        results = []
        for e in qs.select_related('manager')[:limit]:
            row = {
                'id': str(e.id), 'name': e.full_name, 'title': e.title,
                'department': e.department, 'email': e.email,
                'hire_date': e.hire_date.isoformat(), 'status': e.status,
            }
            if include_salary and e.salary:
                row['salary'] = float(e.salary)
            results.append(row)
        return ToolResult.ok({'employees': results, 'count': len(results), 'salary_visible': include_salary})


class GetEmployeeDetailTool(Tool):
    name = 'get_employee_detail'
    required_permission = permission_registry[Perm("hr.employee").view]
    description = "Get complete profile for a specific employee by their UUID. Use when you need full details after a search."
    input_schema = {
        'type': 'object',
        'properties': {'employee_id': {'type': 'string', 'description': 'Employee UUID'}},
        'required': ['employee_id'],
    }

    def execute(self, inp, user, org) -> dict:
        from apps.hr.models import Employee
        try:
            e = Employee.objects.get(id=inp['employee_id'], org=org)
        except Employee.DoesNotExist:
            return ToolResult.not_found('Employee', inp['employee_id'])
        result = {
            'id': str(e.id), 'name': e.full_name, 'email': e.email,
            'title': e.title, 'department': e.department,
            'hire_date': e.hire_date.isoformat(), 'status': e.status, 'bio': e.bio,
        }
        if RBACService.has_permission(user, permission_registry[Perm("hr.employee.salary").view]) and e.salary:
            result['salary'] = float(e.salary)
        return ToolResult.ok(result)


class SearchJobsTool(Tool):
    name = 'search_jobs'
    required_permission = permission_registry[Perm("hr.job").view]
    description = "Search job postings by title, department, or status. Use for questions about open positions or vacancies."
    input_schema = {
        'type': 'object',
        'properties': {
            'query': {'type': 'string'},
            'department': {'type': 'string'},
            'status': {'type': 'string', 'enum': ['open', 'closed', 'draft'], 'default': 'open'},
        },
    }

    def execute(self, inp, user, org) -> dict:
        from apps.hr.models import Job
        qs = Job.objects.filter(org=org)
        if inp.get('query'):
            qs = qs.filter(Q(title__icontains=inp['query']) | Q(department__icontains=inp['query']))
        if inp.get('department'):
            qs = qs.filter(department__icontains=inp['department'])
        qs = qs.filter(status=inp.get('status', 'open'))
        results = [
            {
                'id': str(j.id), 'title': j.title, 'department': j.department, 'status': j.status,
                'description': j.description[:300] + '...' if len(j.description) > 300 else j.description,
                'salary_range': f"${j.salary_min:,.0f} - ${j.salary_max:,.0f}" if j.salary_min else 'Not disclosed',
            }
            for j in qs[:20]
        ]
        return ToolResult.ok({'jobs': results, 'count': len(results)})


class SearchDocumentsTool(Tool):
    name = 'search_documents'
    required_permission = permission_registry[Perm("hr.document").view]
    description = (
        "Search HR documents, policies, and handbooks using semantic search. "
        "Use for policy questions or 'what does the handbook say about X'."
    )
    input_schema = {
        'type': 'object',
        'properties': {
            'query': {'type': 'string', 'description': 'Natural language search query'},
            'doc_type': {'type': 'string', 'enum': ['policy', 'handbook', 'job_description', 'other']},
            'top_k': {'type': 'integer', 'default': 5},
        },
        'required': ['query'],
    }

    def execute(self, inp, user, org) -> dict:
        from apps.agent.rag import RAGService
        query = inp.get('query', '').strip()
        if not query:
            return ToolResult.validation('query is required')
        try:
            results = RAGService.search(
                query=query, org_id=str(org.id),
                doc_type=inp.get('doc_type'), top_k=int(inp.get('top_k', 5)),
            )
            return ToolResult.ok({'results': results, 'count': len(results)})
        except Exception as exc:
            from apps.hr.models import Document
            qs = Document.objects.filter(org=org)
            if inp.get('doc_type'):
                qs = qs.filter(doc_type=inp['doc_type'])
            docs = qs.filter(content__icontains=query)[:5]
            return ToolResult.ok({
                'results': [{'document_name': d.name, 'snippet': d.content[:500], 'doc_type': d.doc_type, 'score': 0.5} for d in docs],
                'count': len(docs),
                'fallback': True,
                'fallback_reason': f'Vector search unavailable ({type(exc).__name__}), using keyword fallback.',
            })


class GetAnalyticsTool(Tool):
    name = 'get_analytics'
    required_permission = permission_registry[Perm("analytics").view]
    description = "Get workforce statistics. Use for headcount, department breakdowns, or salary distribution."
    input_schema = {
        'type': 'object',
        'properties': {
            'metric': {
                'type': 'string',
                'enum': ['headcount', 'department_breakdown', 'salary_distribution', 'open_jobs_by_dept', 'recent_hires'],
            },
        },
        'required': ['metric'],
    }

    def execute(self, inp, user, org) -> dict:
        from apps.hr.models import Employee, Job
        from django.utils import timezone
        from datetime import timedelta

        metric = inp['metric']
        qs = Employee.objects.filter(org=org)

        if metric == 'headcount':
            return ToolResult.ok({
                'active': qs.filter(status='active').count(),
                'inactive': qs.filter(status='inactive').count(),
                'terminated': qs.filter(status='terminated').count(),
                'total': qs.count(),
            })
        elif metric == 'department_breakdown':
            return ToolResult.ok({'departments': list(qs.filter(status='active').values('department').annotate(count=Count('id')).order_by('-count'))})
        elif metric == 'salary_distribution':
            if not RBACService.has_permission(user, permission_registry[Perm("analytics.salary_report").view]):
                return ToolResult.permission_denied('analytics.salary_report.view')
            return ToolResult.ok(qs.filter(status='active').aggregate(avg=Avg('salary'), count=Count('id')))
        elif metric == 'open_jobs_by_dept':
            return ToolResult.ok({'departments': list(Job.objects.filter(org=org, status='open').values('department').annotate(count=Count('id')).order_by('-count'))})
        elif metric == 'recent_hires':
            cutoff = timezone.now().date() - timedelta(days=90)
            recent = qs.filter(hire_date__gte=cutoff).order_by('-hire_date')[:10]
            return ToolResult.ok({'recent_hires': [{'name': e.full_name, 'title': e.title, 'department': e.department, 'hire_date': e.hire_date.isoformat()} for e in recent]})
        return ToolResult.error('unknown_metric', f'Unknown metric: {metric}')


class SavePreferenceTool(Tool):
    name = 'save_preference'
    required_permission = permission_registry[Perm("agent.chat").view]
    description = (
        "Persist a user preference for future conversations. "
        "Use ONLY when the user explicitly states a preference — e.g., "
        "'always show me salary data', 'I prefer bullet point summaries', "
        "'default to the Engineering department'. "
        "Do not use for temporary context. Each key overwrites the previous value."
    )
    input_schema = {
        'type': 'object',
        'properties': {
            'key': {
                'type': 'string',
                'description': 'Short snake_case preference key (e.g., "response_format", "default_department")',
            },
            'value': {
                'type': 'string',
                'description': 'The preference value as a plain string',
            },
        },
        'required': ['key', 'value'],
    }

    def execute(self, inp, user, org) -> dict:
        from apps.agent.memory import LongTermMemory
        key = inp.get('key', '').strip()
        value = inp.get('value', '').strip()
        if not key:
            return ToolResult.validation('key is required')
        if not value:
            return ToolResult.validation('value is required')
        LongTermMemory.update(user, {key: value})
        return ToolResult.ok({'saved': True, 'key': key, 'value': value})


tool_registry = ToolRegistry([
    SearchEmployeesTool(),
    GetEmployeeDetailTool(),
    SearchJobsTool(),
    SearchDocumentsTool(),
    GetAnalyticsTool(),
    SavePreferenceTool(),
])
