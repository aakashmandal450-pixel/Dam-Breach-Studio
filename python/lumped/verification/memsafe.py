"""Worker sizing by available memory (Windows and Linux), shared by the table build and the acceptance test."""
import os

GB_PER_WORKER = 1.5     # measured peak of the deepest table point (C/b = 32, a/b = 2): 0.84 GB, plus margin


def available_gb():
    try:
        if os.name == "nt":
            import ctypes

            class MS(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                            ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                            ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                            ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                            ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
            m = MS(); m.dwLength = ctypes.sizeof(MS)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
            return m.ullAvailPhys / 2**30, m.ullTotalPhys / 2**30
        avail = os.sysconf("SC_AVPHYS_PAGES") * os.sysconf("SC_PAGE_SIZE") / 2**30
        total = os.sysconf("SC_PHYS_PAGES") * os.sysconf("SC_PAGE_SIZE") / 2**30
        return avail, total
    except Exception:
        return None, None


def choose_workers(requested=0):
    cpus = os.cpu_count() or 2
    avail, total = available_gb()
    by_mem = max(1, int((avail - 1.0) // GB_PER_WORKER)) if avail else 1
    auto = max(1, min(cpus - 1, by_mem, 6))
    n = requested if requested > 0 else auto
    note = (f"{cpus} cores, {avail:.1f} of {total:.1f} GB memory free -> {auto} worker(s) by default"
            if avail else f"{cpus} cores, free memory unknown -> {auto} worker(s)")
    if requested > 0 and avail and requested * GB_PER_WORKER > avail - 1.0:
        note += f"; WARNING: {requested} requested may exceed free memory"
    return n, note
