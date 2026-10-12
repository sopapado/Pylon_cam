"""Exercise real ctypes bindings against a deterministic fake native SDK."""
import ctypes as c
import unittest
from unittest.mock import patch

import numpy as np

from simplepicam import Camera, PicamError, AcquisitionError
from simplepicam import _types as t
from simplepicam._driver import Driver, unpack_frame


def put(pointer, kind, value):
    c.cast(pointer, c.POINTER(kind))[0] = value


class Function:
    def __init__(self, callback):
        self.callback = callback

    def __call__(self, *args):
        return self.callback(*args)


class FakeSDK:
    def __init__(self):
        self.calls = []
        self.fail = {}
        self.initialized = False
        self.running = False
        self.mask = 0
        self.readouts = 1
        self.frames = 1
        self.pixel_format = 1
        self.rejected = False
        self.fail_array = (t.piint * 1)(t.PicamParameter['Rois'])
        self.roi = t.PicamRoi(0, 1340, 1, 0, 100, 100)
        self.rois = t.PicamRois(c.pointer(self.roi), 1)
        self.buffer = None

    def __getattr__(self, name):
        if not name.startswith('Picam_'):
            raise AttributeError(name)
        fn = Function(lambda *args: self.dispatch(name[6:], *args))
        setattr(self, name, fn)
        return fn

    def dispatch(self, name, *args):
        self.calls.append(name)
        if name in self.fail:
            return self.fail[name]
        if name == 'IsLibraryInitialized':
            put(args[0], t.pibln, self.initialized)
        elif name == 'InitializeLibrary':
            self.initialized = True
        elif name == 'UninitializeLibrary':
            self.initialized = False
        elif name == 'OpenFirstCamera':
            put(args[0], t.pivoid, 0x12345678)
        elif name == 'IsAcquisitionRunning':
            put(args[1], t.pibln, self.running)
        elif name == 'CanReadParameter':
            put(args[2], t.pibln, 1)
        elif name == 'ReadParameterFloatingPointValue':
            put(args[2], t.piflt, -69.5)
        elif name == 'SetParameterRoisValue':
            incoming = c.cast(args[2], c.POINTER(t.PicamRois)).contents.roi_array[0]
            self.roi = t.PicamRoi.from_buffer_copy(incoming)
            self.rois = t.PicamRois(c.pointer(self.roi), 1)
        elif name == 'GetParameterRoisValue':
            put(args[2], c.POINTER(t.PicamRois), c.pointer(self.rois))
        elif name == 'CommitParameters' and self.rejected:
            put(args[1], c.POINTER(t.piint), c.cast(self.fail_array, c.POINTER(t.piint)))
            put(args[2], t.piint, 1)
        elif name == 'GetParameterIntegerValue':
            pixels = self.roi.width * self.roi.height // self.roi.y_binning
            values = dict(SensorActiveWidth=1340, SensorActiveHeight=100,
                          PixelFormat=self.pixel_format, ReadoutStride=(pixels + 4) * 2,
                          FrameStride=(pixels + 4) * 2, FramesPerReadout=self.frames)
            put(args[2], t.piint, values[t.PicamParameterLookup[args[1]]])
        elif name == 'Acquire':
            self.last_timeout = args[2]
            pixels = self.roi.width * self.roi.height // self.roi.y_binning
            self.buffer = (t.pi16u * (pixels + 4))(*([i % 60000 for i in range(pixels)] + [65535] * 4))
            put(args[3], t.PicamAvailableData, t.PicamAvailableData(c.addressof(self.buffer), self.readouts))
            put(args[4], t.piint, self.mask)
        return 0


class CameraTests(unittest.TestCase):
    def setUp(self):
        Driver._active = False
        self.sdk = FakeSDK()
        self.loader = patch('simplepicam._driver.load_dll', return_value=self.sdk)
        self.loader.start()

    def tearDown(self):
        self.loader.stop()
        Driver._active = False

    def test_constructor_is_inert(self):
        Camera()
        self.assertEqual(self.sdk.calls, [])

    def test_padding_1344_to_1340_and_detached_copy(self):
        with Camera() as cam:
            data = cam.get_spectrum(exposure_ms=100)
            self.assertEqual(data.shape, (1340,))
            self.assertEqual(data.dtype, np.uint16)
            np.testing.assert_array_equal(data, np.arange(1340))
            self.sdk.buffer[0] = 500
            self.assertEqual(data[0], 0)
            self.assertEqual(cam.temperature_c, -69.5)
            self.assertEqual(self.sdk.last_timeout, 10100)
        self.assertIn('CloseCamera', self.sdk.calls)
        self.assertFalse(self.sdk.initialized)

    def test_roi_unbinned_orientation(self):
        with Camera() as cam:
            data = cam.get_spectrum(y_start=5, y_height=2, y_binning=1)
            self.assertEqual(data.shape, (2, 1340))
            self.assertEqual(data[1, 0], 1340)
            self.assertEqual(self.sdk.roi.y, 5)

    def test_configure_once_and_exposure_override(self):
        with Camera() as cam:
            cam.configure(200, 5, 90, 90)
            cam.get_spectrum()
            cam.get_spectrum()
            self.assertEqual(self.sdk.calls.count('CommitParameters'), 1)
            cam.get_spectrum(300, timeout_ms=5000)
            self.assertEqual(self.sdk.roi.y, 5)
            self.assertEqual(self.sdk.roi.height, 90)
            self.assertEqual(self.sdk.last_timeout, 5000)

    def test_invalid_settings_do_not_reach_setter(self):
        cases = [dict(exposure_ms=-1), dict(exposure_ms=float('nan')),
                 dict(y_start=-1), dict(y_height=101), dict(y_binning=3),
                 dict(y_height=2.5), dict(y_binning=True), dict(y_height=0)]
        with Camera() as cam:
            for kwargs in cases:
                with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                    cam.configure(**kwargs)
            self.assertNotIn('SetParameterFloatingPointValue', self.sdk.calls)

    def test_failed_commit_frees_parameters_and_blocks_acquisition(self):
        self.sdk.rejected = True
        with Camera() as cam:
            with self.assertRaisesRegex(PicamError, 'Rois'):
                cam.get_spectrum()
            self.assertIn('DestroyParameters', self.sdk.calls)
            self.assertNotIn('Acquire', self.sdk.calls)
            self.assertFalse(cam._configured)

    def test_acquisition_error_closes_camera(self):
        for failure in ('mask', 'timeout', 'empty'):
            with self.subTest(failure=failure):
                self.sdk.mask = 2 if failure == 'mask' else 0
                self.sdk.readouts = 0 if failure == 'empty' else 1
                self.sdk.fail = {'Acquire': 32} if failure == 'timeout' else {}
                cam = Camera().open()
                with self.assertRaises(AcquisitionError):
                    cam.get_spectrum()
                self.assertFalse(cam._opened)
                self.assertFalse(self.sdk.initialized)

    def test_no_camera_cleans_up_without_demo(self):
        self.sdk.fail['OpenFirstCamera'] = 34
        with self.assertRaisesRegex(PicamError, 'NoCamerasAvailable'):
            Camera().open()
        self.assertFalse(self.sdk.initialized)
        self.assertFalse(Driver._active)
        self.assertFalse(any('Demo' in name for name in self.sdk.calls))

    def test_external_initialization_not_uninitialized(self):
        self.sdk.initialized = True
        with self.assertRaises(PicamError):
            Camera().open()
        self.assertNotIn('UninitializeLibrary', self.sdk.calls)

    def test_single_session_and_idempotent_close(self):
        with Camera() as cam:
            with self.assertRaises(PicamError):
                Camera().open()
            cam.close()
            cam.close()
        self.assertEqual(self.sdk.calls.count('CloseCamera'), 1)

    def test_body_exception_preserved_despite_cleanup_error(self):
        self.sdk.fail['CloseCamera'] = 4
        with self.assertWarns(RuntimeWarning):
            with self.assertRaisesRegex(ValueError, 'original'):
                with Camera():
                    raise ValueError('original')
        self.assertIn('UninitializeLibrary', self.sdk.calls)
        self.assertTrue(Driver._active)

    def test_cleanup_failure_reported(self):
        cam = Camera().open()
        self.sdk.fail['CloseCamera'] = 4
        with self.assertRaises(PicamError):
            cam.close()
        self.assertFalse(cam._opened)

    def test_native_signatures_and_boolean_size(self):
        with Camera():
            self.assertEqual(c.sizeof(t.pibln), 4)
            self.assertEqual(self.sdk.Picam_OpenFirstCamera.argtypes, [c.POINTER(t.pivoid)])
            self.assertEqual(self.sdk.Picam_Acquire.argtypes[1], t.pi64s)

    def test_closed_operations_fail(self):
        cam = Camera()
        with self.assertRaises(PicamError):
            cam.get_spectrum()
        with self.assertRaises(PicamError):
            _ = cam.temperature_c

    def test_unsupported_format_and_frames_rejected_before_acquire(self):
        for attribute in ('pixel_format', 'frames'):
            with self.subTest(attribute=attribute):
                setattr(self.sdk, attribute, 2)
                with Camera() as cam:
                    with self.assertRaises(AcquisitionError):
                        cam.get_spectrum()
                setattr(self.sdk, attribute, 1)
        self.assertNotIn('Acquire', self.sdk.calls)

    def test_invalid_layout_rejected_before_pointer_access(self):
        for args in [(None, 1, 2688, 2688, 1, 1340, 1),
                     (1, 0, 2688, 2688, 1, 1340, 1),
                     (1, 1, 100, 100, 1, 1340, 1),
                     (1, 1, 2688, 2689, 1, 1340, 1)]:
            with self.assertRaises(AcquisitionError):
                unpack_frame(*args)


if __name__ == '__main__':
    unittest.main()
