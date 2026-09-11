"""Read dedicated adapter memory through DXGI's pointer-sized counters."""
import ctypes as c
import re
import uuid


def adapters():
    """Return hardware adapters; unavailable DXGI is an empty result."""
    class Desc(c.Structure):
        _fields_ = [('name', c.c_wchar * 128), ('vendor', c.c_uint32),
                    ('device', c.c_uint32), ('subsys', c.c_uint32),
                    ('revision', c.c_uint32), ('memory', c.c_size_t),
                    ('system', c.c_size_t), ('shared', c.c_size_t),
                    ('luid_low', c.c_uint32), ('luid_high', c.c_int32),
                    ('flags', c.c_uint32)]

    def method(obj, index, result, *args):
        table = c.cast(obj, c.POINTER(c.POINTER(c.c_void_p))).contents
        return c.WINFUNCTYPE(result, c.c_void_p, *args)(table[index])

    factory = c.c_void_p()
    found = []
    try:
        dll = c.WinDLL('dxgi')
        create = dll.CreateDXGIFactory1
        create.argtypes = [c.c_void_p, c.POINTER(c.c_void_p)]
        create.restype = c.c_int32
        iid = (c.c_ubyte * 16).from_buffer_copy(
            uuid.UUID('770aae78-f26f-4dba-a829-253c83d1b387').bytes_le)
        if create(c.byref(iid), c.byref(factory)) < 0:
            return []
        enum = method(factory, 12, c.c_int32, c.c_uint32, c.POINTER(c.c_void_p))
        for index in range(64):
            adapter = c.c_void_p()
            if enum(factory, index, c.byref(adapter)) < 0:
                break
            try:
                desc = Desc()
                if method(adapter, 10, c.c_int32, c.POINTER(Desc))(
                        adapter, c.byref(desc)) >= 0 and not desc.flags & 2:
                    found.append({key: getattr(desc, key) for key in
                                  ('name', 'vendor', 'device', 'subsys', 'revision', 'memory')})
            finally:
                method(adapter, 2, c.c_uint32)(adapter)
    except (OSError, AttributeError):
        return []
    finally:
        if factory.value:
            method(factory, 2, c.c_uint32)(factory)
    return found


def dedicated_memory(row, available):
    """Match PCI identity, never infer capacity from a GPU model name."""
    identity = str(row.get('PNPDeviceID') or '').upper()
    fields = [('VEN', 'vendor'), ('DEV', 'device'),
              ('SUBSYS', 'subsys'), ('REV', 'revision')]
    ids = {key: int(match.group(1), 16) for tag, key in fields
           if (match := re.search(r'(?:\\|&)' + tag + r'_([0-9A-F]+)', identity))}
    if 'vendor' in ids and 'device' in ids:
        matches = [a for a in available if all(a.get(k) == v for k, v in ids.items())]
    else:
        name = str(row.get('Name') or '').strip().casefold()
        matches = [a for a in available if name and a['name'].strip().casefold() == name]
    values = {a['memory'] for a in matches}
    return values.pop() if len(values) == 1 else None


def format_memory(value):
    if value is None:
        return 'N/A'
    if value < 1024 ** 3:
        return f'{value / 1024 ** 2:g} MB'
    return f'{value / 1024 ** 3:.1f}'.removesuffix('.0') + ' GB'
