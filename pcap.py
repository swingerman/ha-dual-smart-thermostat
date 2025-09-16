"""Lightweight ctypes-based wrapper around libpcap for basic operations.

This is a minimal shim to allow compiling and setting BPF filters and opening
live captures without requiring a C-extension build (useful for Python 3.13
dev environments where upstream wheels are not available).

It intentionally implements only a small surface: findalldevs, open_live,
compile, setfilter, close, next_ex. Not a full replacement for pcapy/pypcap.
"""

from ctypes import (
    CDLL,
    POINTER,
    Structure,
    byref,
    c_char,
    c_char_p,
    c_int,
    c_uint,
    c_void_p,
)
from ctypes.util import find_library

libname = find_library("pcap")
if not libname:
    raise ImportError("libpcap not found on system; install libpcap-dev/libpcap")

_pcap = CDLL(libname)


class PcapBpfProgram(Structure):
    _fields_ = [("bf_len", c_uint), ("bf_insns", c_void_p)]


class PcapIf(Structure):
    pass


PcapIf._fields_ = [
    ("next", POINTER(PcapIf)),
    ("name", c_char_p),
    ("description", c_char_p),
    ("addresses", c_void_p),
    ("flags", c_uint),
]


_pcap.pcap_findalldevs.argtypes = [POINTER(POINTER(PcapIf)), c_char_p]
_pcap.pcap_findalldevs.restype = c_int

_pcap.pcap_freealldevs.argtypes = [POINTER(PcapIf)]
_pcap.pcap_freealldevs.restype = None

_pcap.pcap_open_live.argtypes = [c_char_p, c_int, c_int, c_int, c_char_p]
_pcap.pcap_open_live.restype = c_void_p

_pcap.pcap_close.argtypes = [c_void_p]
_pcap.pcap_close.restype = None

_pcap.pcap_compile.argtypes = [
    c_void_p,
    POINTER(PcapBpfProgram),
    c_char_p,
    c_int,
    c_uint,
]
_pcap.pcap_compile.restype = c_int

_pcap.pcap_freecode.argtypes = [POINTER(PcapBpfProgram)]
_pcap.pcap_freecode.restype = None

_pcap.pcap_setfilter.argtypes = [c_void_p, POINTER(PcapBpfProgram)]
_pcap.pcap_setfilter.restype = c_int

_pcap.pcap_next_ex.argtypes = [c_void_p, POINTER(c_void_p), POINTER(c_void_p)]
_pcap.pcap_next_ex.restype = c_int

# pcap_open_dead allows compiling filters without opening a live device
_pcap.pcap_open_dead.argtypes = [c_int, c_int]
_pcap.pcap_open_dead.restype = c_void_p


def findalldevs():
    devpp = POINTER(PcapIf)()
    errbuf = (c_char * 256)()
    res = _pcap.pcap_findalldevs(byref(devpp), errbuf)
    if res != 0:
        raise OSError(
            f"pcap_findalldevs failed: {errbuf.value.decode(errors='ignore')}"
        )
    devs = []
    cur = devpp
    while bool(cur):
        dev = cur.contents
        name = dev.name.decode() if dev.name else None
        desc = dev.description.decode() if dev.description else None
        devs.append((name, desc))
        cur = dev.next
    _pcap.pcap_freealldevs(devpp)
    return devs


class Pcap:
    def __init__(self, device, snaplen=65535, promisc=1, to_ms=1000):
        errbuf = (c_char * 256)()
        self._p = _pcap.pcap_open_live(
            device.encode() if isinstance(device, str) else device,
            snaplen,
            promisc,
            to_ms,
            errbuf,
        )
        if not self._p:
            raise OSError(
                f"pcap_open_live failed: {errbuf.value.decode(errors='ignore')}"
            )

    def compile_filter(self, filter_expr, optimize=True, netmask=0xFFFFFFFF):
        prog = PcapBpfProgram()
        res = _pcap.pcap_compile(
            self._p, byref(prog), filter_expr.encode(), 1 if optimize else 0, netmask
        )
        if res != 0:
            # attempt to get error via pcap_geterr if present
            try:
                _pcap.pcap_geterr.argtypes = [c_void_p]
                _pcap.pcap_geterr.restype = c_char_p
                msg = _pcap.pcap_geterr(self._p)
                raise OSError(
                    f"pcap_compile failed: {msg.decode() if msg else 'unknown'}"
                )
            except Exception:
                raise OSError("pcap_compile failed")
        return prog

    def setfilter(self, prog):
        res = _pcap.pcap_setfilter(self._p, byref(prog))
        if res != 0:
            raise OSError("pcap_setfilter failed")

    def close(self):
        if self._p:
            _pcap.pcap_close(self._p)
            self._p = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()


def compile_filter_on_device(filter_expr):
    """Convenience: find first device and compile filter on it (raises on failure)."""
    # Use pcap_open_dead so we can compile filters without opening a live capture
    DLT_EN10MB = 1
    SNAPLEN = 65535
    dead = _pcap.pcap_open_dead(DLT_EN10MB, SNAPLEN)
    if not dead:
        raise OSError("pcap_open_dead failed")
    prog = PcapBpfProgram()
    res = _pcap.pcap_compile(dead, byref(prog), filter_expr.encode(), 1, 0xFFFFFFFF)
    if res != 0:
        # try to get error
        try:
            _pcap.pcap_geterr.argtypes = [c_void_p]
            _pcap.pcap_geterr.restype = c_char_p
            msg = _pcap.pcap_geterr(dead)
            raise OSError(f"pcap_compile failed: {msg.decode() if msg else 'unknown'}")
        except Exception:
            raise OSError("pcap_compile failed")
    _pcap.pcap_freecode(byref(prog))
    # close dead handle if pcap_close exists
    try:
        _pcap.pcap_close(dead)
    except Exception:
        pass


if __name__ == "__main__":
    print("libpcap shim using:", libname)
    print("devices:", findalldevs())
    try:
        compile_filter_on_device("port 67 or port 68")
        print("compiled DHCP filter OK")
    except Exception as e:
        print("compile failed:", e)
