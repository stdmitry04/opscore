import pytest
from unittest.mock import patch

from apps.tasks.models import TaskRecord

pytestmark = pytest.mark.django_db


@pytest.fixture
def task_record(org):
    return TaskRecord.objects.create(
        task_type='agent_chat',
        org=org,
        status='success',
        payload={'message': 'test', 'session_id': 'abc'},
        result={'response': 'Here is the answer.'},
    )


@pytest.fixture
def dead_letter_task(org):
    return TaskRecord.objects.create(
        task_type='embed_document',
        org=org,
        status='dead_letter',
        payload={'document_id': '00000000-0000-0000-0000-000000000001'},
        error='Connection refused',
        retry_count=3,
    )


# ── Task list ─────────────────────────────────────────────────────────────────

class TestTaskList:
    def test_hr_can_list_tasks(self, hr_client, task_record):
        r = hr_client.get('/api/tasks/')
        assert r.status_code == 200
        assert isinstance(r.data, list)

    def test_viewer_cannot_list_tasks(self, viewer_client):
        # viewer has agent.chat.view but not tasks.view
        r = viewer_client.get('/api/tasks/')
        assert r.status_code == 403

    def test_no_perm_denied(self, no_perm_client):
        r = no_perm_client.get('/api/tasks/')
        assert r.status_code == 403

    def test_unauthenticated_denied(self, anon_client):
        r = anon_client.get('/api/tasks/')
        assert r.status_code == 401

    def test_status_filter(self, hr_client, task_record):
        r = hr_client.get('/api/tasks/', {'status': 'success'})
        assert r.status_code == 200
        assert all(t['status'] == 'success' for t in r.data)


# ── Task detail ───────────────────────────────────────────────────────────────

class TestTaskDetail:
    def test_hr_can_get_task(self, hr_client, task_record):
        r = hr_client.get(f'/api/tasks/{task_record.id}/')
        assert r.status_code == 200
        assert r.data['status'] == 'success'
        assert r.data['task_type'] == 'agent_chat'

    def test_nonexistent_task_returns_404(self, hr_client):
        r = hr_client.get('/api/tasks/00000000-0000-0000-0000-000000000000/')
        assert r.status_code == 404

    def test_task_result_included(self, hr_client, task_record):
        r = hr_client.get(f'/api/tasks/{task_record.id}/')
        assert 'result' in r.data


# ── Dead letter queue ─────────────────────────────────────────────────────────

class TestDeadLetterQueue:
    def test_hr_can_view_dlq(self, hr_client, dead_letter_task):
        r = hr_client.get('/api/tasks/dlq/')
        assert r.status_code == 200
        assert any(t['status'] == 'dead_letter' for t in r.data)

    def test_viewer_cannot_view_dlq(self, viewer_client):
        r = viewer_client.get('/api/tasks/dlq/')
        assert r.status_code == 403


# ── Retry task ────────────────────────────────────────────────────────────────

class TestRetryTask:
    def test_admin_can_retry_dead_letter(self, admin_client, dead_letter_task):
        with patch('apps.tasks.tasks.embed_document.apply_async'):
            r = admin_client.post(f'/api/tasks/{dead_letter_task.id}/retry/')
        assert r.status_code == 200
        assert r.data['status'] == 'queued'
        dead_letter_task.refresh_from_db()
        assert dead_letter_task.status == 'pending'
        assert dead_letter_task.retry_count == 0

    def test_retry_non_dead_letter_returns_404(self, admin_client, task_record):
        r = admin_client.post(f'/api/tasks/{task_record.id}/retry/')
        assert r.status_code == 404

    def test_viewer_cannot_retry(self, viewer_client, dead_letter_task):
        r = viewer_client.post(f'/api/tasks/{dead_letter_task.id}/retry/')
        assert r.status_code == 403

    def test_hr_cannot_retry(self, hr_client, dead_letter_task):
        # hr_user has tasks.view but not tasks.edit
        r = hr_client.post(f'/api/tasks/{dead_letter_task.id}/retry/')
        assert r.status_code == 403
