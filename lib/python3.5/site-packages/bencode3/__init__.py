#!/usr/bin/env python3
import logging

log = logging.getLogger(__name__)

class BencodeError(Exception):
    pass


def decode_string(x, f):
    colon = f + x[f:].find(b':')
    log.debug('%s,%s,%s', f, colon, x[f:colon])
    n = int(x[f:colon].decode('ascii'))
    if chr(x[f]) == '0' and colon != f+1:
        raise ValueError()
    s_start = colon + 1
    s_end = s_start + n
    s = x[s_start:s_end]
    try:
        s = s.decode('utf-8')
    except:
        pass
    log.debug('decode string, get "%s"', s)
    return (s, s_end)


def decode_dict(x, f):
    log.debug('decode dict')
    r = {}
    f += 1
    while chr(x[f]) != 'e':
        k, f = decode_string(x, f)
        log.debug('get key "%s" for dict', k)
        key = chr(x[f])
        r[k], f = decode_func[key](x, f)
    f += 1
    return (r, f)


def decode_list(x, f):
    r = []
    f += 1
    while True:
        if chr(x[f]) == 'e':
            log.debug('exit at %d', f)
            f += 1
            break
        key = chr(x[f])
        v, f = decode_func[key](x, f)
        r.append(v)
    log.debug('decode list, get "%s"', r)
    return (r, f)


def decode_int(x, f):
    f += 1
    next_f = f + x[f:].find(b'e')
    n = int(x[f:next_f].decode('ascii'))
    return (n, next_f+1)


decode_func = {}
decode_func['l'] = decode_list
decode_func['d'] = decode_dict
decode_func['i'] = decode_int
decode_func['0'] = decode_string
decode_func['1'] = decode_string
decode_func['2'] = decode_string
decode_func['3'] = decode_string
decode_func['4'] = decode_string
decode_func['5'] = decode_string
decode_func['6'] = decode_string
decode_func['7'] = decode_string
decode_func['8'] = decode_string
decode_func['9'] = decode_string


def bdecode(x):
    assert isinstance(x, bytes) or isinstance(x, bytearray)
    try:
        key = chr(x[0])
        r, l = decode_func[key](x, 0)
    except Exception:
        raise BencodeError("invalid input")
    log.debug('%s/%s', l, len(x))
    if l != len(x):
        raise BencodeError("inner error, should process all bytes")
    return r


def encode_str(payload, encoding=None):
    if encoding is None:
        encoding = 'utf-8'
    if isinstance(payload, str):
        payload = payload.encode(encoding)
    assert isinstance(payload, bytes)
    l = len(payload)
    return (str(l) + ':').encode('ascii') +  payload


def encode_int(payload, _=None):
    assert isinstance(payload, int)
    base = 'i%se' % str(payload)
    return base.encode('ascii')


def encode_list(payload, encoding=None):
    assert isinstance(payload, list)
    base = b'l'
    for item in payload:
        key = type(item)
        base += encode_func[key](item, encoding)
    base += b'e'
    return base


def encode_dict(payload, encoding=None):
    assert isinstance(payload, dict)
    base = b'd'
    keys = list(payload.keys())
    keys.sort()
    for key in keys:
        base += encode_str(key)
        v = payload[key]
        key = type(v)
        base += encode_func[key](v, encoding)
    base += b'e'
    return base


encode_func = {}
encode_func[str] = encode_str
encode_func[bytes] = encode_str
encode_func[int] = encode_int
encode_func[list] = encode_list
encode_func[dict] = encode_dict


def bencode(x):
    retval = b''
    encoding = 'utf-8'
    key = type(x)
    retval = encode_func[key](x, encoding)
    return retval
