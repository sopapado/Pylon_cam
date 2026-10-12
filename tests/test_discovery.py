import ctypes
import os
import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from simplepicam.discovery import dll_bits, find_dll
from simplepicam import SDKNotFoundError


def make_pe(path, bits):
    data = bytearray(134)
    data[:2] = b'MZ'
    struct.pack_into('<I', data, 60, 128)
    data[128:132] = b'PE\0\0'
    struct.pack_into('<H', data, 132, 0x14c if bits == 32 else 0x8664)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


class DiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.bits = ctypes.sizeof(ctypes.c_void_p) * 8
        self.name = 'Picam32.dll' if self.bits == 32 else 'Picam.dll'

    def tearDown(self):
        self.temp.cleanup()

    def test_explicit_path_and_bitness(self):
        dll = make_pe(self.root / self.name, self.bits)
        self.assertEqual(find_dll(dll), dll.resolve())
        make_pe(dll, 64 if self.bits == 32 else 32)
        with self.assertRaisesRegex(SDKNotFoundError, 'bit Python'):
            find_dll(dll)

    def test_environment_root_and_path_discovery(self):
        dll = make_pe(self.root / 'Runtime' / self.name, self.bits)
        for env in [{'PicamRoot': str(self.root)}, {'PATH': str(dll.parent)},
                    {'SIMPLEPICAM_DLL': str(dll)}]:
            with self.subTest(env=env), patch.dict(os.environ, env, clear=True):
                self.assertEqual(find_dll(), dll.resolve())

    def test_common_install_location(self):
        dll = make_pe(self.root / 'Princeton Instruments/Picam/Runtime' / self.name, self.bits)
        with patch.dict(os.environ, {'CommonProgramFiles': str(self.root)}, clear=True):
            self.assertEqual(find_dll(), dll.resolve())

    def test_bad_explicit_path_does_not_fall_back(self):
        dll = make_pe(self.root / self.name, self.bits)
        with patch.dict(os.environ, {'SIMPLEPICAM_DLL': str(dll)}, clear=True):
            with self.assertRaises(SDKNotFoundError):
                find_dll(self.root / 'missing.dll')

    def test_invalid_and_missing_dll(self):
        bad = self.root / self.name
        bad.write_bytes(b'not a DLL')
        with self.assertRaises(SDKNotFoundError):
            dll_bits(bad)
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(SDKNotFoundError):
                find_dll()
