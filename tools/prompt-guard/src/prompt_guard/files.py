"""Bounded POSIX file I/O through directory descriptors without following links."""
import os
import hashlib
import hmac
import re
from pathlib import Path
import stat
from .core import GuardError, require, decode, policy_from_dict


def _parent(path, root):
    absolute = Path(os.path.abspath(path))
    base = Path(os.path.abspath(root))
    require(absolute.is_relative_to(base) and absolute != base, 'path_boundary')
    fd = os.open(absolute.anchor, os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in absolute.parts[1:-1]:
            new = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = new
        return fd, absolute.name
    except Exception:
        os.close(fd)
        raise


def read_bytes(path, root, limit):
    try:
        folder, name = _parent(path, root)
        try:
            fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=folder)
            with os.fdopen(fd, 'rb') as stream:
                before = os.fstat(stream.fileno())
                require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1, 'unsupported_file')
                require(before.st_size <= limit, 'resource_limit')
                raw = stream.read(limit + 1)
                after = os.fstat(stream.fileno())
                require(len(raw) <= limit, 'resource_limit')
                require((before.st_size, before.st_mtime_ns, before.st_ctime_ns) ==
                        (after.st_size, after.st_mtime_ns, after.st_ctime_ns), 'source_changed')
                return raw
        finally:
            os.close(folder)
    except GuardError:
        raise
    except Exception:
        raise GuardError('io_error') from None


def write_new(path, root, raw):
    try:
        folder, name = _parent(path, root)
        try:
            fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=folder)
            with os.fdopen(fd, 'wb') as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
        finally:
            os.close(folder)
    except GuardError:
        raise
    except Exception:
        raise GuardError('output_failed') from None


def load_policy(path, *, config_root, expected_id, expected_version, expected_sha256):
    """Bind policy bytes to an independently selected trusted release."""
    require(type(expected_sha256) is str and re.fullmatch(r'[0-9a-f]{64}', expected_sha256), 'policy_pin_invalid')
    raw = read_bytes(path, config_root, 65536)
    require(hmac.compare_digest(hashlib.sha256(raw).hexdigest(), expected_sha256), 'policy_digest_mismatch')
    value = decode(raw, 65536)
    require(type(value) is dict and value.get('policy_id') == expected_id and value.get('policy_version') == expected_version,
            'policy_identity_mismatch')
    require(type(expected_id) is str and bool(expected_id) and type(expected_version) is str and bool(expected_version),
            'policy_pin_invalid')
    return policy_from_dict(value)
