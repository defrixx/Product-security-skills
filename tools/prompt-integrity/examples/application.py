"""Synthetic app integration: approved profiles, checked retries and fallback."""
from prompt_integrity import TransportError, verify_and_send


class CatalogApplication:
    def __init__(self, policy, transport):
        self.policy = policy
        self.transport = transport

    def answer(self, user_text, *, mutate_attempt=None):
        # These are trusted release choices, never request-selected profiles.
        attempts = [('primary', 'synthetic-model'), ('primary', 'synthetic-model'),
                    ('fallback', 'synthetic-backup')]
        for number, (alias, model) in enumerate(attempts):
            request = {'model': model, 'stream': False, 'messages': [
                {'role': 'system', 'content': 'Answer questions about the synthetic demo catalog.'},
                {'role': 'user', 'content': user_text}]}
            # Test hook models application middleware BEFORE the checked boundary.
            if mutate_attempt is not None:
                mutate_attempt(number, request)
            try:
                return verify_and_send(self.policy, request, alias, self.transport)
            except TransportError:
                if number == len(attempts)-1:
                    raise
        raise AssertionError('unreachable')
