"""Stage independent skill folders for review and manual Bifrost import."""
from pathlib import Path
import hashlib
import json
import shutil
import stat

SKILLS = ('secure-development', 'sensitive-data-cleanup', 'security-review',
          'security-report-triage', 'security-fix-verification')


def stage(destination, root=None):
    root = Path(root) if root else Path(__file__).resolve().parents[2]
    destination = Path(destination)
    # Preflight every input before writing; do not follow links or special files.
    entries = []
    for name in SKILLS:
        source = root / 'skills' / name
        if not (source / 'SKILL.md').is_file():
            raise ValueError('skill_entry_missing')
        for parent in (root, root / 'skills', source):
            if parent.is_symlink():
                raise ValueError('skill_link_rejected')
        for path in sorted(source.rglob('*')):
            mode = path.lstat().st_mode
            if not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
                raise ValueError('skill_file_rejected')
            if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc':
                entries.append((path, path.relative_to(root / 'skills')))
    # Never overwrite an existing directory, including symlink destinations.
    destination.mkdir(parents=False, exist_ok=False)
    manifest = {}
    try:
        for source, relative in entries:
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target, follow_symlinks=False)
            manifest[relative.as_posix()] = hashlib.sha256(target.read_bytes()).hexdigest()
        (destination / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    except Exception:
        shutil.rmtree(destination)
        raise
    return manifest


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    stage(args.destination)
