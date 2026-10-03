"""Synthetic boundary example: dispatch only the guard's allow payload."""
from prompt_guard import inspect


def guarded_text(policy, text, send_checked, *, source='user', mode='strict'):
    """send_checked receives checked UTF-8 bytes and applies application controls.

    A prompt-integrity integration assembles its pinned model request from these
    bytes and calls verify_and_send. Authorization of subsequent model-proposed
    actions remains in the application before any effect.
    """
    result = inspect(policy, text, source=source, mode=mode)
    if result.decision != 'allow':
        return result.diagnostics(), None
    return result.diagnostics(), send_checked(result.payload)
