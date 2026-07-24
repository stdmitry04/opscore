import pytest
from unittest.mock import patch

pytestmark = pytest.mark.django_db


class TestChatEndpoint:
    def test_viewer_can_post_message(self, viewer_client):
        with patch('apps.tasks.tasks.run_agent_task.apply_async'):
            r = viewer_client.post('/api/agent/chat/', {'message': 'How many employees do we have?'})
        assert r.status_code == 202
        assert 'task_id' in r.data
        assert 'session_id' in r.data

    def test_session_id_echoed_if_provided(self, viewer_client):
        with patch('apps.tasks.tasks.run_agent_task.apply_async'):
            r = viewer_client.post('/api/agent/chat/', {
                'message': 'Hello', 'session_id': 'my-session-abc'
            })
        assert r.status_code == 202
        assert r.data['session_id'] == 'my-session-abc'

    def test_session_id_generated_if_absent(self, viewer_client):
        with patch('apps.tasks.tasks.run_agent_task.apply_async'):
            r = viewer_client.post('/api/agent/chat/', {'message': 'Hello'})
        assert r.status_code == 202
        assert r.data['session_id']  # not empty

    def test_empty_message_rejected(self, viewer_client):
        r = viewer_client.post('/api/agent/chat/', {'message': ''})
        assert r.status_code == 400

    def test_missing_message_rejected(self, viewer_client):
        r = viewer_client.post('/api/agent/chat/', {})
        assert r.status_code == 400

    def test_no_perm_user_denied(self, no_perm_client):
        r = no_perm_client.post('/api/agent/chat/', {'message': 'Hello'})
        assert r.status_code == 403

    def test_unauthenticated_denied(self, anon_client):
        r = anon_client.post('/api/agent/chat/', {'message': 'Hello'})
        assert r.status_code == 401

    def test_task_record_created(self, viewer_client, org):
        from apps.tasks.models import TaskRecord
        initial_count = TaskRecord.objects.count()
        with patch('apps.tasks.tasks.run_agent_task.apply_async'):
            r = viewer_client.post('/api/agent/chat/', {'message': 'How many jobs are open?'})
        assert r.status_code == 202
        assert TaskRecord.objects.count() == initial_count + 1
        task = TaskRecord.objects.get(id=r.data['task_id'])
        assert task.task_type == 'agent_chat'


class TestClearSessionEndpoint:
    def test_clear_session(self, viewer_client):
        session_id = 'test-session-to-clear'
        r = viewer_client.delete(f'/api/agent/sessions/{session_id}/')
        assert r.status_code == 200
        assert r.data['cleared'] is True

    def test_clear_removes_memory(self, viewer_client):
        from apps.agent.memory import ShortTermMemory
        session_id = 'populated-session'
        ShortTermMemory.append(session_id, [{'role': 'user', 'content': 'hi'}])
        viewer_client.delete(f'/api/agent/sessions/{session_id}/')
        assert ShortTermMemory.get(session_id) == []

    def test_unauthenticated_denied(self, anon_client):
        r = anon_client.delete('/api/agent/sessions/some-session/')
        assert r.status_code == 401
