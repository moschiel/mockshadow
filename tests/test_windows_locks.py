import ctypes
from ctypes import wintypes
import os
import errno
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from pipeline import retry_io, staging_directory


class LockTests(unittest.TestCase):
    def test_bounded_retry_and_non_lock_errors(self):
        locked = PermissionError("sharing violation")
        locked.winerror = 32
        operation = unittest.mock.Mock(side_effect=[locked, "ok"])
        self.assertEqual(retry_io(operation), "ok")
        operation = unittest.mock.Mock(side_effect=locked)
        with self.assertRaises(PermissionError):
            retry_io(operation, timeout=0)
        self.assertEqual(operation.call_count, 1)
        denied = PermissionError("access denied")
        denied.winerror = 5
        operation = unittest.mock.Mock(side_effect=[denied, "published"])
        self.assertEqual(retry_io(operation), "published")
        operation = unittest.mock.Mock(side_effect=denied)
        with self.assertRaises(PermissionError):
            retry_io(operation, timeout=0)
        self.assertEqual(operation.call_count, 1)
        missing = unittest.mock.Mock(side_effect=FileNotFoundError())
        with self.assertRaises(FileNotFoundError):
            retry_io(missing)
        self.assertEqual(missing.call_count, 1)

    def test_cleanup_cannot_mask_original_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch("pipeline.shutil.rmtree", side_effect=PermissionError("held file")):
                with self.assertRaisesRegex(ValueError, "recipe failed"):
                    with staging_directory(Path(directory)):
                        raise ValueError("recipe failed")

    @unittest.skipUnless(os.name == "nt", "Windows sharing semantics")
    def test_real_exclusive_windows_handle_is_retried(self):
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                      ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
        kernel.CreateFileW.restype = wintypes.HANDLE
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "flash.h"
            path.write_text("original")
            handle = kernel.CreateFileW(str(path), 0x80000000, 0, None, 3, 0, None)
            self.assertNotEqual(handle, ctypes.c_void_p(-1).value)
            timer = threading.Timer(.25, kernel.CloseHandle, args=(handle,))
            timer.start()
            try:
                with self.assertRaises(OSError) as caught:
                    path.write_text("new")
                self.assertEqual(caught.exception.errno, errno.EACCES)
                retry_io(path.write_text, "new")
                self.assertEqual(path.read_text(), "new")
            finally:
                timer.join()
