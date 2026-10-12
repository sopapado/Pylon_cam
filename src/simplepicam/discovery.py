"""Find an installed SDK without distributing vendor binaries."""
import ctypes
import os
import struct
from functools import lru_cache
from pathlib import Path

from .errors import SDKNotFoundError


def dll_bits(path):
    """Read the PE machine field without loading executable code."""
    try:
        with open(str(path), 'rb') as stream:
            if stream.read(2) != b'MZ':
                raise ValueError('missing MZ header')
            stream.seek(60)
            offset = struct.unpack('<I', stream.read(4))[0]
            stream.seek(offset)
            if stream.read(4) != b'PE\0\0':
                raise ValueError('missing PE header')
            machine = struct.unpack('<H', stream.read(2))[0]
        return {0x14c: 32, 0x8664: 64}[machine]
    except (OSError, ValueError, KeyError, struct.error) as exc:
        raise SDKNotFoundError('Invalid or unsupported x86/x64 PICam DLL: {}'.format(path)) from exc


def find_dll(dll_path=None):
    """Explicit path, SIMPLEPICAM_DLL, SDK roots, install folders, then PATH."""
    bits = ctypes.sizeof(ctypes.c_void_p) * 8
    names = ['Picam32.dll'] if bits == 32 else ['Picam.dll', 'Picam64.dll']
    explicit = dll_path or os.environ.get('SIMPLEPICAM_DLL')
    if explicit:
        candidates = [Path(explicit).expanduser()]
    else:
        roots = []
        for key in ('PicamRoot', 'PICAM_ROOT'):
            if os.environ.get(key):
                root = Path(os.environ[key])
                roots.extend([root, root / 'Runtime'])
        for key in ('CommonProgramFiles', 'CommonProgramFiles(x86)',
                    'CommonProgramW6432', 'ProgramFiles', 'ProgramFiles(x86)', 'ProgramW6432'):
            if os.environ.get(key):
                base = Path(os.environ[key])
                roots.extend([base / 'Princeton Instruments/Picam/Runtime',
                              base / 'Common Files/Princeton Instruments/Picam/Runtime'])
        roots.extend(Path(p.strip('"')) for p in os.environ.get('PATH', '').split(os.pathsep) if p)
        candidates = [root / name for root in roots for name in names]
    problems = []
    for candidate in dict.fromkeys(candidates):
        if not candidate.is_file():
            continue
        try:
            actual = dll_bits(candidate)
            if actual == bits:
                return candidate.resolve()
            problems.append('{} is {}-bit'.format(candidate, actual))
        except SDKNotFoundError as exc:
            problems.append(str(exc))
    raise SDKNotFoundError(
        'No compatible PICam DLL found for {}-bit Python. Install the vendor SDK '
        'and drivers, or set SIMPLEPICAM_DLL to its DLL file. {}'.format(bits, '; '.join(problems)))


def load_dll(dll_path=None):
    if os.name != 'nt':
        raise SDKNotFoundError('Camera access currently supports Windows only.')
    path = find_dll(dll_path)
    return _load_windows_path(str(path))


@lru_cache(maxsize=None)
def _load_windows_path(path):
    # Keep one native module reference per resolved DLL for process lifetime;
    # camera close still releases SDK initialization and camera resources.
    try:
        # LOAD_WITH_ALTERED_SEARCH_PATH resolves dependencies beside the SDK DLL.
        # Explicit LoadLibraryExW also works with Python 3.7 (no add_dll_directory).
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        load = kernel.LoadLibraryExW
        load.argtypes = [ctypes.c_wchar_p, ctypes.c_void_p, ctypes.c_uint32]
        load.restype = ctypes.c_void_p
        handle = load(str(path), None, 0x00000008)
        if not handle:
            raise ctypes.WinError(ctypes.get_last_error())
        return ctypes.WinDLL(str(path), handle=handle)
    except OSError as exc:
        raise SDKNotFoundError('Cannot load {}. Check SDK dependencies and Python/DLL bitness: {}'.format(path, exc)) from exc
