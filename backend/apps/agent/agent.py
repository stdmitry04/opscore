import json
from django.conf import settings
from .tools import tool_registry
from .memory import ShortTermMemory, LongTermMemory

MODEL = 'claude-sonnet-4-6'
MAX_TOKENS = 4096


def _serialize_content(content) -> list:
    # the SDK returns typed objects (TextBlock, ToolUseBlock) that json.dumps can't handle,
    # so we convert to plain dicts before writing to Redis
    if isinstance(content, str):
        return [{'type': 'text', 'text': content}]
    result = []
    for block in content:
        if hasattr(block, 'model_dump'):
            result.append(block.model_dump())
        elif hasattr(block, '__dict__'):
            result.append({k: v for k, v in block.__dict__.items() if not k.startswith('_')})
        else:
            result.append(block)
    return result


def _build_system_prompt(user, org) -> str:
    long_term = LongTermMemory.format_for_system_prompt(user)

    from apps.rbac.services import RBACService
    permissions = list(RBACService.get_user_permissions(user))

    parts = [
        f"You are an AI assistant for {org.name}'s HR and operations platform.",
        f"You are speaking with {user.display_name} ({user.email}).",
        # telling the model which permissions the user has lets it self-enforce access rules
        # without us having to intercept every tool call to check
        f"User's active permissions: {', '.join(permissions) if permissions else 'none'}.",
        "",
        "You have access to tools for searching employees, jobs, documents, and getting analytics.",
        "Always use tools to look up real data rather than making things up.",
        "When you can't find data or the user lacks permission, say so clearly.",
        "Be concise and professional.",
    ]

    if long_term:
        parts.append("")
        parts.append(long_term)

    return "\n".join(parts)


def run_agent(message: str, session_id: str, user, org) -> dict:
    import anthropic

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    history = ShortTermMemory.get(session_id)
    new_user_message = {'role': 'user', 'content': message}
    messages = history + [new_user_message]

    system_prompt = _build_system_prompt(user, org)
    tool_calls_trace = []

    # loop because claude can chain multiple tool calls before giving a final answer —
    # e.g. search_employees → get_employee_detail → get_analytics in one user turn
    while True:
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=system_prompt,
            tools=tool_registry.definitions(),
            messages=messages,
        )

        if response.stop_reason == 'end_turn':
            final_text = ''
            for block in response.content:
                if hasattr(block, 'text'):
                    final_text = block.text
                    break

            # serialize before Redis storage — SDK objects aren't json-serializable
            serialized_content = _serialize_content(response.content)
            assistant_message = {'role': 'assistant', 'content': serialized_content}
            ShortTermMemory.append(session_id, [new_user_message, assistant_message])

            return {
                'session_id': session_id,
                'response': final_text,
                'tool_calls': tool_calls_trace,
                'usage': {
                    'input_tokens': response.usage.input_tokens,
                    'output_tokens': response.usage.output_tokens,
                },
            }

        elif response.stop_reason == 'tool_use':
            tool_results = []

            for block in response.content:
                if block.type == 'tool_use':
                    tool_name = block.name
                    tool_input = block.input

                    try:
                        result = tool_registry.execute(tool_name, tool_input, user, org)
                    except Exception as e:
                        # unexpected — tool.execute() should return ToolResult.error, not raise
                        result = {'ok': False, 'error_type': 'unexpected', 'error': str(e)}

                    tool_calls_trace.append({
                        'tool': tool_name,
                        'input': tool_input,
                        'output': result,
                        'ok': result.get('ok', True),
                    })

                    tool_results.append({
                        'type': 'tool_result',
                        'tool_use_id': block.id,
                        'content': json.dumps(result),
                    })

            # keep SDK objects for the in-process continuation — the API accepts them directly,
            # only Redis storage needs plain dicts
            messages.append({'role': 'assistant', 'content': response.content})
            messages.append({'role': 'user', 'content': tool_results})

        else:
            break

    return {
        'session_id': session_id,
        'response': 'Agent loop ended unexpectedly.',
        'tool_calls': tool_calls_trace,
    }
