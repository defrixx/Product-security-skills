"""POSIX bounded configuration I/O without following links."""
import hashlib
import hmac
import re
import os
from pathlib import Path
import stat
from .core import DEFAULT_LIMITS, IntegrityError, decode, policy_from_dict, require


def _parent(path, root):
    absolute = Path(os.path.abspath(path))
    base = Path(os.path.abspath(root))
    require(absolute.is_relative_to(base) and absolute != base, 'path_boundary')
    fd = os.open(absolute.anchor, os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in absolute.parts[1:-1]:
            new = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd); fd = new
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
                raw = stream.read(limit+1)
                after = os.fstat(stream.fileno())
                require(len(raw) <= limit, 'resource_limit')
                require((before.st_size, before.st_mtime_ns, before.st_ctime_ns) == (after.st_size, after.st_mtime_ns, after.st_ctime_ns), 'source_changed')
                return raw
        finally:
            os.close(folder)
    except IntegrityError:
        raise
    except Exception:
        raise IntegrityError('io_error') from None


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
    except IntegrityError:
        raise
    except Exception:
        raise IntegrityError('output_failed') from None


def load_policy(baseline_path, expected_profile, expected_version, *, config_root, expected_sha256=None):
    """Load an immutable policy; optionally pin exact approved release bytes.

    The expected digest must come from trusted release configuration, never from
    the candidate file or an untrusted request. Existing unpinned callers remain
    responsible for protecting their baseline source.
    """
    if expected_sha256 is not None:
        require(type(expected_sha256) is str and re.fullmatch(r"[0-9a-f]{64}", expected_sha256),
                "baseline_pin_invalid")
    raw = read_bytes(baseline_path, config_root, DEFAULT_LIMITS['baseline_bytes'])
    if expected_sha256 is not None:
        require(hmac.compare_digest(hashlib.sha256(raw).hexdigest(), expected_sha256),
                'baseline_digest_mismatch')
    try:
        obj = decode(raw, DEFAULT_LIMITS, DEFAULT_LIMITS['baseline_bytes'])
        return policy_from_dict(obj, expected_profile, expected_version)
    except IntegrityError as error:
        code = error.code if error.code in ('version_mismatch', 'resource_limit') else 'baseline_invalid'
        raise IntegrityError(code) from None
