"""Explicitly selected packaged example policies; no automatic topic restrictions."""
from importlib.resources import files
from .core import decode, policy_from_dict, require

PROFILES = ('user-input', 'retrieval', 'tool-results', 'security', 'restricted-topics', 'security-and-topics',
            'output-topics', 'output-secrets', 'output-security-and-topics', 'output-personal-data')


def load_profile(name):
    require(name in PROFILES, 'profile_invalid')
    raw = files('prompt_guard').joinpath('policies', name + '.json').read_bytes()
    return policy_from_dict(decode(raw, 65536))
