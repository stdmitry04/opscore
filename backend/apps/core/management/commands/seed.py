"""
python manage.py seed
Seeds demo organization, 4 demo users (with different roles), 50 employees, 5 jobs, and 3 sample documents.
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from datetime import date, timedelta
from pathlib import Path
import random

DEPARTMENTS = ['Engineering', 'Sales', 'HR', 'Finance', 'Operations', 'Marketing', 'Legal']
TITLES = {
    'Engineering': ['Software Engineer', 'Senior Engineer', 'Staff Engineer', 'Engineering Manager', 'DevOps Engineer'],
    'Sales': ['Account Executive', 'Sales Manager', 'SDR', 'VP of Sales'],
    'HR': ['HR Coordinator', 'HR Manager', 'Recruiter', 'VP People'],
    'Finance': ['Financial Analyst', 'Controller', 'CFO', 'Accountant'],
    'Operations': ['Operations Manager', 'Chief of Staff', 'Program Manager'],
    'Marketing': ['Marketing Manager', 'Content Writer', 'Growth Lead'],
    'Legal': ['General Counsel', 'Legal Analyst'],
}

FIRST_NAMES = [
    'James', 'Mary', 'Robert', 'Patricia', 'John', 'Jennifer', 'Michael', 'Linda',
    'William', 'Barbara', 'David', 'Susan', 'Richard', 'Jessica', 'Joseph', 'Sarah',
    'Thomas', 'Karen', 'Charles', 'Lisa', 'Christopher', 'Nancy', 'Daniel', 'Margaret',
    'Matthew', 'Betty', 'Anthony', 'Sandra', 'Mark', 'Ashley', 'Elena', 'Dmitry',
    'Sofia', 'Alex', 'Jordan', 'Taylor', 'Morgan', 'Casey', 'Riley', 'Avery',
]
LAST_NAMES = [
    'Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis',
    'Rodriguez', 'Martinez', 'Hernandez', 'Lopez', 'Gonzalez', 'Wilson', 'Anderson',
    'Thomas', 'Taylor', 'Moore', 'Jackson', 'Martin',
]

SAMPLE_POLICY = """
REMOTE WORK POLICY

1. Eligibility
All full-time employees who have completed 90 days of employment are eligible for remote work arrangements, subject to manager approval and role requirements.

2. Work Hours
Remote employees must be available during core hours: 10 AM to 3 PM local time, Monday through Friday. Outside of core hours, employees have flexibility to manage their schedule.

3. Equipment
The company provides a laptop and $500 home office stipend per year for qualifying remote employees. Internet costs are not reimbursed.

4. Performance
Remote employees are evaluated on outcomes and deliverables, not hours worked. Managers should set clear OKRs quarterly.

5. Security
All remote work must be done on company-issued devices or approved BYOD devices with MDM installed. Use of public WiFi requires VPN.
"""

SAMPLE_HANDBOOK = """
EMPLOYEE HANDBOOK — BENEFITS SECTION

Health Insurance
We offer medical, dental, and vision insurance. Premiums are covered at 90% for the employee and 70% for dependents. Open enrollment is in November each year.

401(k)
Employees are eligible to contribute to our 401(k) plan after 30 days. We match 4% of salary up to the IRS annual limit. Vesting is immediate.

PTO
Full-time employees accrue 15 days PTO per year for the first 3 years, 20 days thereafter. Up to 10 days may roll over to the next year.

Parental Leave
12 weeks fully paid parental leave for primary caregivers. 4 weeks for secondary caregivers.

Learning & Development
$1,500 annual L&D budget for courses, conferences, and books. Requires manager pre-approval.
"""


class Command(BaseCommand):
    help = 'Seed demo data for OpsCore portfolio project'

    def handle(self, *args, **options):
        from apps.core.models import Organization, User
        from apps.rbac.models import Permission, Role, RolePermission, UserRole
        from apps.rbac.permissions_registry import sync_permissions
        from apps.hr.models import Employee, Job, Document

        self.stdout.write('Syncing permissions...')
        sync_permissions()

        self.stdout.write('Creating organization...')
        org, _ = Organization.objects.get_or_create(
            slug='acme-corp',
            defaults={'name': 'Acme Corporation'},
        )

        self.stdout.write('Creating roles...')
        all_perms = list(Permission.objects.all())
        perm_map = {p.code: p for p in all_perms}

        def make_role(name, description, perm_codes):
            role, _ = Role.objects.get_or_create(
                org=org, name=name, defaults={'description': description}
            )
            role.permissions.clear()
            for code in perm_codes:
                if code in perm_map:
                    RolePermission.objects.get_or_create(role=role, permission=perm_map[code])
            return role

        admin_role = make_role('Admin', 'Full access to all systems', [p.code for p in all_perms])
        hr_role = make_role('HR Manager', 'Full HR access, no finance', [
            'hr.employee.view', 'hr.employee.edit',
            'hr.employee.salary.view',
            'hr.job.view', 'hr.job.edit',
            'hr.document.view', 'hr.document.edit',
            'analytics.view', 'agent.chat.view', 'agent.tool_calls.view',
            'tasks.view', 'rbac.view',
        ])
        finance_role = make_role('Finance', 'Finance and analytics access', [
            'hr.employee.view', 'hr.employee.salary.view',
            'analytics.view', 'analytics.salary_report.view',
            'agent.chat.view', 'tasks.view',
        ])
        readonly_role = make_role('Viewer', 'Read-only access', [
            'hr.employee.view', 'hr.job.view', 'hr.document.view',
            'analytics.view', 'agent.chat.view',
        ])

        self.stdout.write('Creating demo users...')

        def make_user(email, first, last, role, password='demo1234'):
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'first_name': first,
                    'last_name': last,
                    'org': org,
                    'is_staff': role == admin_role,
                },
            )
            if created:
                user.set_password(password)
                user.save()
            UserRole.objects.get_or_create(user=user, role=role)
            return user

        make_user('admin@acme-demo.com', 'Alex', 'Admin', admin_role)
        make_user('hr@acme-demo.com', 'Hannah', 'Rivera', hr_role)
        make_user('finance@acme-demo.com', 'Frank', 'Chen', finance_role)
        make_user('viewer@acme-demo.com', 'Vera', 'Patel', readonly_role)

        self.stdout.write('Creating 50 employees...')
        if Employee.objects.filter(org=org).count() < 50:
            employees_to_create = []
            for i in range(50):
                dept = random.choice(DEPARTMENTS)
                title = random.choice(TITLES[dept])
                fname = random.choice(FIRST_NAMES)
                lname = random.choice(LAST_NAMES)
                hire_date = date.today() - timedelta(days=random.randint(30, 1800))
                employees_to_create.append(Employee(
                    org=org,
                    first_name=fname,
                    last_name=lname,
                    email=f"{fname.lower()}.{lname.lower()}{i}@acme-corp.com",
                    title=title,
                    department=dept,
                    hire_date=hire_date,
                    salary=random.randint(60, 200) * 1000,
                    status=random.choices(
                        ['active', 'inactive', 'terminated'],
                        weights=[85, 10, 5],
                    )[0],
                    bio=f"{fname} is a {title} in the {dept} department with {random.randint(1, 15)} years of experience.",
                ))
            Employee.objects.bulk_create(employees_to_create)

        self.stdout.write('Creating jobs...')
        job_data = [
            ('Senior Software Engineer', 'Engineering', 'We are looking for a senior engineer to lead backend systems.', 140000, 180000),
            ('HR Business Partner', 'HR', 'Partner with business units to support people strategy.', 90000, 120000),
            ('Financial Analyst', 'Finance', 'Analyze financial data and support planning cycles.', 80000, 110000),
            ('Marketing Manager', 'Marketing', 'Own our content and demand generation programs.', 95000, 130000),
            ('Operations Manager', 'Operations', 'Streamline processes across the organization.', 100000, 135000),
        ]
        for title, dept, desc, sal_min, sal_max in job_data:
            Job.objects.get_or_create(
                org=org,
                title=title,
                defaults={
                    'department': dept,
                    'description': desc,
                    'requirements': f'5+ years experience in {dept}. Strong communication skills. Bachelor degree or equivalent.',
                    'salary_min': sal_min,
                    'salary_max': sal_max,
                    'status': 'open',
                },
            )

        self.stdout.write('Creating sample documents...')
        Document.objects.get_or_create(
            org=org,
            name='Remote Work Policy',
            defaults={'content': SAMPLE_POLICY, 'doc_type': 'policy'},
        )
        Document.objects.get_or_create(
            org=org,
            name='Employee Handbook - Benefits',
            defaults={'content': SAMPLE_HANDBOOK, 'doc_type': 'handbook'},
        )

        self.stdout.write('Loading fixture documents...')
        fixtures_dir = Path(__file__).resolve().parents[4] / 'fixtures' / 'documents'
        if fixtures_dir.exists():
            for txt_file in sorted(fixtures_dir.glob('*.txt')):
                doc_name = txt_file.stem.replace('_', ' ').title()
                content = txt_file.read_text(encoding='utf-8')
                # infer doc_type from filename
                if 'policy' in txt_file.stem or 'philosophy' in txt_file.stem or 'incident' in txt_file.stem:
                    doc_type = 'policy'
                elif 'handbook' in txt_file.stem or 'practices' in txt_file.stem or 'process' in txt_file.stem or 'guide' in txt_file.stem:
                    doc_type = 'handbook'
                else:
                    doc_type = 'other'

                doc, created = Document.objects.get_or_create(
                    org=org,
                    name=doc_name,
                    defaults={'content': content, 'doc_type': doc_type}
                )
                if created:
                    from apps.tasks.models import TaskRecord
                    task_record = TaskRecord.objects.create(
                        task_type='embed_document',
                        org=org,
                        payload={'document_id': str(doc.id)},
                    )
                    from apps.tasks.tasks import embed_document
                    embed_document.apply_async(
                        kwargs={'document_id': str(doc.id), 'task_record_id': str(task_record.id)},
                        queue='embeddings',
                    )
                    self.stdout.write(f'  Queued embedding for: {doc_name}')
                else:
                    self.stdout.write(f'  Already exists: {doc_name}')

        self.stdout.write(self.style.SUCCESS('Seed complete'))
        self.stdout.write('')
        self.stdout.write('Demo credentials:')
        self.stdout.write('  admin@acme-demo.com / demo1234  (Admin - all permissions)')
        self.stdout.write('  hr@acme-demo.com / demo1234     (HR Manager)')
        self.stdout.write('  finance@acme-demo.com / demo1234 (Finance)')
        self.stdout.write('  viewer@acme-demo.com / demo1234  (Viewer - read only)')
