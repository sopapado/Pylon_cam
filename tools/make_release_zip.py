"""Create a review ZIP from an explicit allowlist; never collect the workspace."""
import hashlib
from pathlib import Path
import tarfile
import zipfile


ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / 'dist'
VERSION = '0.1.0'
PREFIX = 'simplepicam-' + VERSION


def safe_name(name):
    parts = Path(name).parts
    return (not any(p in ('reference', 'artifacts', '.venv', '.git', '__pycache__') for p in parts)
            and Path(name).suffix.lower() not in ('.dll', '.exe', '.pyc', '.pyo', '.pyx', '.dat'))


def main():
    wheel = DIST / (PREFIX + '-py3-none-any.whl')
    source = DIST / (PREFIX + '.tar.gz')
    with zipfile.ZipFile(str(wheel)) as archive:
        assert all(safe_name(name) for name in archive.namelist())
        assert archive.testzip() is None
    with tarfile.open(str(source)) as archive:
        assert all(safe_name(name) for name in archive.getnames())
    files = [ROOT / name for name in (
        '.gitignore', '.gitattributes', 'LICENSE', 'NOTICE.md', 'README.md',
        'MANIFEST.in', 'pyproject.toml', 'requirements.txt', 'requirements-dev.txt')]
    for folder, pattern in [('src/simplepicam', '*.py'), ('tests', '*.py'),
                            ('examples', '*.py'), ('docs', '*.md'),
                            ('tools', '*.py'), ('.github/workflows', '*.yml')]:
        files.extend(sorted((ROOT / folder).glob(pattern)))
    files.extend([wheel, source])
    target = DIST / (PREFIX + '-project.zip')
    with zipfile.ZipFile(str(target), 'w', zipfile.ZIP_DEFLATED) as archive:
        for file in files:
            relative = file.relative_to(ROOT)
            assert safe_name(str(relative)), relative
            archive.write(str(file), PREFIX + '/' + relative.as_posix())
    with zipfile.ZipFile(str(target)) as archive:
        assert archive.testzip() is None
        assert len(archive.namelist()) == len(files)
    sums = []
    for file in (wheel, source, target):
        sums.append('{}  {}'.format(hashlib.sha256(file.read_bytes()).hexdigest(), file.name))
    (DIST / 'SHA256SUMS.txt').write_text('\n'.join(sums) + '\n', encoding='ascii')
    print('Verified {} files in {}'.format(len(files), target))


if __name__ == '__main__':
    main()
