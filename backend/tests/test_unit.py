"""
Unit tests — no database, no HTTP. Tests the core invariants of the
permission registry, ToolResult, and short-term memory.
"""
import pytest
from unittest.mock import patch, MagicMock

from apps.rbac.permissions_registry import Perm, PermRegistry, permission_registry
from apps.agent.tools import Tool, ToolRegistry, ToolResult


# ── Perm class ────────────────────────────────────────────────────────────────

class TestPermClass:
    def test_str_is_the_code(self):
        assert str(Perm("hr.employee")) == 'hr.employee'

    def test_view_appends_leaf(self):
        assert str(Perm("hr.employee").view) == 'hr.employee.view'

    def test_edit_appends_leaf(self):
        assert str(Perm("hr.employee").edit) == 'hr.employee.edit'

    def test_nested_dotted_code(self):
        assert str(Perm("hr.employee.salary").view) == 'hr.employee.salary.view'

    def test_view_is_perm_instance(self):
        assert isinstance(Perm("hr.employee").view, Perm)


# ── PermRegistry ──────────────────────────────────────────────────────────────

class TestPermRegistry:
    def test_valid_perm_lookup(self):
        p = permission_registry[Perm("hr.employee").view]
        assert str(p) == 'hr.employee.view'

    def test_unknown_perm_raises_key_error(self):
        with pytest.raises(KeyError, match="not registered"):
            permission_registry[Perm("totally.fake").view]

    def test_registry_contains_all_20_leaf_perms(self):
        # 10 base perms × 2 leaves (view + edit) = 20
        assert len(permission_registry._registry) == 20

    def test_all_known_perms_accessible(self):
        known = [
            "hr.employee", "hr.employee.salary", "hr.job", "hr.document",
            "analytics", "analytics.salary_report",
            "agent.chat", "agent.tool_calls",
            "tasks", "rbac",
        ]
        for base in known:
            permission_registry[Perm(base).view]
            permission_registry[Perm(base).edit]

    def test_custom_registry_with_bad_perm_raises_at_init(self):
        from abc import abstractmethod
        from typing import ClassVar

        class BrokenTool(Tool):
            name = 'broken'
            description = 'broken'
            required_permission = Perm("nonexistent.thing").view
            input_schema = {'type': 'object', 'properties': {}}

            def execute(self, inp, user, org):
                return {}

        with pytest.raises(KeyError):
            ToolRegistry([BrokenTool()])


# ── ToolResult ────────────────────────────────────────────────────────────────

class TestToolResult:
    def test_ok_sets_ok_true(self):
        r = ToolResult.ok({'count': 3})
        assert r['ok'] is True
        assert r['count'] == 3

    def test_ok_merges_data_at_top_level(self):
        r = ToolResult.ok({'employees': [], 'total': 0})
        assert 'employees' in r
        assert 'total' in r

    def test_error_sets_ok_false(self):
        r = ToolResult.error('not_found', 'Employee not found')
        assert r['ok'] is False
        assert r['error_type'] == 'not_found'
        assert 'not found' in r['error'].lower()

    def test_permission_denied_includes_perm_name(self):
        r = ToolResult.permission_denied('hr.employee.salary.view')
        assert r['ok'] is False
        assert r['error_type'] == 'permission_denied'
        assert 'hr.employee.salary.view' in r['error']

    def test_not_found_with_identifier(self):
        r = ToolResult.not_found('Employee', 'abc-123')
        assert r['ok'] is False
        assert 'abc-123' in r['error']

    def test_not_found_without_identifier(self):
        r = ToolResult.not_found('Employee')
        assert r['ok'] is False
        assert 'Employee' in r['error']

    def test_validation_error_type(self):
        r = ToolResult.validation('key is required')
        assert r['error_type'] == 'validation_error'

    def test_external_error_includes_service_name(self):
        r = ToolResult.external('Qdrant', 'connection refused')
        assert r['error_type'] == 'external_error'
        assert 'Qdrant' in r['error']


# ── ShortTermMemory ───────────────────────────────────────────────────────────

class TestShortTermMemory:
    def test_get_unknown_session_returns_empty_list(self):
        from apps.agent.memory import ShortTermMemory
        result = ShortTermMemory.get('nonexistent-session-xyz')
        assert result == []

    def test_append_and_get(self):
        from apps.agent.memory import ShortTermMemory
        sid = 'test-session-unit'
        msgs = [{'role': 'user', 'content': 'hello'}]
        ShortTermMemory.append(sid, msgs)
        result = ShortTermMemory.get(sid)
        assert len(result) == 1
        assert result[0]['role'] == 'user'

    def test_sliding_window_trims_oldest_messages(self):
        from apps.agent.memory import ShortTermMemory, MAX_TURNS
        sid = 'test-session-trim'
        # Fill beyond the window: MAX_TURNS turns × 2 messages each + extra
        for i in range(MAX_TURNS + 5):
            ShortTermMemory.append(sid, [
                {'role': 'user', 'content': f'msg {i}'},
                {'role': 'assistant', 'content': f'reply {i}'},
            ])
        result = ShortTermMemory.get(sid)
        assert len(result) == MAX_TURNS * 2

    def test_clear_removes_session(self):
        from apps.agent.memory import ShortTermMemory
        sid = 'test-session-clear'
        ShortTermMemory.append(sid, [{'role': 'user', 'content': 'hi'}])
        ShortTermMemory.clear(sid)
        assert ShortTermMemory.get(sid) == []
