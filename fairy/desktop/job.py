"""Tie model processes to the bridge lifetime on Windows."""

import ctypes
from ctypes import wintypes
import sys


def attach_process_job():
    if sys.platform != "win32":
        return None

    class BasicLimit(ctypes.Structure):
        _fields_ = [("process_time", ctypes.c_int64), ("job_time", ctypes.c_int64),
                    ("flags", wintypes.DWORD), ("min_working", ctypes.c_size_t),
                    ("max_working", ctypes.c_size_t), ("active_limit", wintypes.DWORD),
                    ("affinity", ctypes.c_size_t), ("priority", wintypes.DWORD),
                    ("scheduling", wintypes.DWORD)]

    class IoCounters(ctypes.Structure):
        _fields_ = [(name, ctypes.c_uint64) for name in
                    ("read_ops", "write_ops", "other_ops", "read_bytes", "write_bytes", "other_bytes")]

    class ExtendedLimit(ctypes.Structure):
        _fields_ = [("basic", BasicLimit), ("io", IoCounters), ("process_memory", ctypes.c_size_t),
                    ("job_memory", ctypes.c_size_t), ("peak_process_memory", ctypes.c_size_t),
                    ("peak_job_memory", ctypes.c_size_t)]

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    kernel.CreateJobObjectW.restype = wintypes.HANDLE
    kernel.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
    kernel.SetInformationJobObject.restype = wintypes.BOOL
    kernel.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    kernel.AssignProcessToJobObject.restype = wintypes.BOOL
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.CreateJobObjectW(None, None)
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    limits = ExtendedLimit()
    limits.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    if not kernel.SetInformationJobObject(handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
        error = ctypes.get_last_error()
        kernel.CloseHandle(handle)
        raise ctypes.WinError(error)
    if not kernel.AssignProcessToJobObject(handle, kernel.GetCurrentProcess()):
        error = ctypes.get_last_error()
        kernel.CloseHandle(handle)
        raise ctypes.WinError(error)
    return handle
