"""Synthetic app integration: approved profiles, checked retries and fallback."""
from prompt_integrity import TransportError, load_policy, verify_and_send


class CatalogApplication:
    def __init__(self, policy, transport):
        self.policy = policy
        self.transport = transport

    @classmethod
    def from_release(cls, path, transport, *, config_root, profile, version, sha256):
        # All release arguments come from protected deployment configuration.
        # A load failure stops startup; never derive a replacement pin here.
        policy = load_policy(path, profile, version, config_root=config_root,
                             expected_sha256=sha256)
        return cls(policy, transport)

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
