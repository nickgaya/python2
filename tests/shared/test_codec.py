import sys

import pytest

from python2.shared.codec import (BaseDecodingSession,
                                  BaseEncodingSession,
                                  EncodingDepth)


PYTHON_VERSION = sys.version_info[0]
if PYTHON_VERSION == 2:
    _long = long  # noqa
    _range = xrange  # noqa
    _unicode = unicode  # noqa

    def assert_range_eq(x, y):
        assert x.__reduce__() == y.__reduce__()

else:
    _long = int
    _range = range
    _unicode = str

    def assert_range_eq(x, y):
        assert x == y


class PassthroughEncodingSession(BaseEncodingSession):
    """
    Encoding session that embeds the original object, for testing.
    """
    def _enc_ref(self, obj):
        return dict(type='ref', object=obj)


class PassthroughDecodingSession(BaseDecodingSession):
    """
    Decoding session compatible with passthrough reference encoding.
    """
    def _dec_ref(self, data):
        return data['object']


class DummyObject(object):
    pass


@pytest.fixture
def encoding_session():
    return PassthroughEncodingSession()


@pytest.fixture
def decoding_session():
    return PassthroughDecodingSession()


def basic_cases():
    """ Generate basic test cases. """

    # Singletons
    yield None, {'type': 'None'}
    yield NotImplemented, {'type': 'NotImplemented'}
    yield Ellipsis, {'type': 'Ellipsis'}

    # Numeric types
    yield True, {'type': 'bool', 'value': True}
    yield False, {'type': 'bool', 'value': False}
    yield 0, {'type': 'int', 'value': 0}
    yield 2**100, {'type': 'int', 'value': 2**100}
    yield 0.0, {'type': 'float', 'value': 0.0}
    yield -0.123, {'type': 'float', 'value': -0.123}
    yield 1e100, {'type': 'float', 'value': 1e100}
    yield 1+2j, {'type': 'complex', 'real': 1.0, 'imag': 2.0}

    # String types
    yield b'', {'type': 'bytes', 'data': ''}
    yield b'abc\x00\x80\xff', {'type': 'bytes', 'data': 'YWJjAID/'}
    yield u'', {'type': 'unicode', 'data': ''}
    yield (u'abc\u0000\u0080\u00ff\uffff',
           {'type': 'unicode', 'data': 'YWJjAMKAw7/vv78='})
    yield bytearray(), {'type': 'bytearray', 'data': ''}
    yield (bytearray((1, 97, 0, 255, 128, 98, 99)),
           {'type': 'bytearray', 'data': 'AWEA/4BiYw=='})

    # Ranges
    yield _range(10), {'type': 'range', 'start': 0, 'stop': 10, 'step': 1}
    yield _range(-1, 5), {'type': 'range', 'start': -1, 'stop': 5, 'step': 1}
    yield _range(3, 11, 2), {'type': 'range',
                             'start': 3,
                             'stop': 11,
                             'step': 2}

    # Note: In Python 2, due to the internal representation of xrange objects,
    # there is sometimes no way to determine the original stop value.
    # When encoding the stop value is reconstructed using xrange.__reduce__.
    # Round-trip encoding will produce an equivalent xrange.
    if PYTHON_VERSION == 2:
        yield _range(3, 3, 2), {'type': 'range',
                                'start': 3,
                                'stop': 3,
                                'step': 2}
        yield _range(3, 10, 2), {'type': 'range',
                                 'start': 3,
                                 'stop': 11,  # Not 10
                                 'step': 2}
        yield _range(3, 0, 2), {'type': 'range',
                                'start': 3,
                                'stop': 3,  # Not 0
                                'step': 2}
        yield _range(3, 0, -1), {'type': 'range',
                                 'start': 3,
                                 'stop': 0,
                                 'step': -1}

    # Slices
    yield slice(10), {'type': 'slice',
                      'start': {'type': 'None'},
                      'stop': {'type': 'int', 'value': 10},
                      'step': {'type': 'cached', 'index': 1}}
    yield slice(1, 10), {'type': 'slice',
                         'start': {'type': 'int', 'value': 1},
                         'stop': {'type': 'int', 'value': 10},
                         'step': {'type': 'None'}}
    yield slice(1, 10, 2), {'type': 'slice',
                            'start': {'type': 'int', 'value': 1},
                            'stop': {'type': 'int', 'value': 10},
                            'step': {'type': 'int', 'value': 2}}
    yield slice(None, None, None), {'type': 'slice',
                                    'start': {'type': 'None'},
                                    'stop': {'type': 'cached', 'index': 1},
                                    'step': {'type': 'cached', 'index': 1}}
    yield slice(123, Ellipsis, None), {'type': 'slice',
                                       'start': {'type': 'int', 'value': 123},
                                       'stop': {'type': 'Ellipsis'},
                                       'step': {'type': 'None'}}

    # Lists
    yield [], {'type': 'list', 'items': []}
    yield [1, None], {'type': 'list', 'items': [{'type': 'int', 'value': 1},
                                                {'type': 'None'}]}
    yield [None, None], {'type': 'list', 'items': [
        {'type': 'None'},
        {'type': 'cached', 'index': 1},
    ]}
    yield [[]], {'type': 'list', 'items': [{'type': 'list', 'items': []}]}

    # Tuples
    yield (), {'type': 'tuple', 'items': []}
    yield (1, None), {'type': 'tuple', 'items': [{'type': 'int', 'value': 1},
                                                 {'type': 'None'}]}
    yield (None, None), {'type': 'tuple', 'items': [
        {'type': 'None'},
        {'type': 'cached', 'index': 1},
    ]}
    yield ((),), {'type': 'tuple', 'items': [{'type': 'tuple', 'items': []}]}

    # For hash-based collections, items may be in any order so there is not
    # a unique possible encoding.  Instead, we use round-trip testing to test
    # these cases (see below).

    # Sets
    yield set(), {'type': 'set', 'items': []}
    yield {1}, {'type': 'set', 'items': [{'type': 'int', 'value': 1}]}

    # Frozensets
    yield frozenset(), {'type': 'frozenset', 'items': []}
    yield frozenset({1}), {'type': 'frozenset', 'items': [
        {'type': 'int', 'value': 1}
    ]}

    # Dicts
    yield {}, {'type': 'dict', 'items': []}
    yield {1: 2}, {'type': 'dict', 'items': [
        {'key': {'type': 'int', 'value': 1},
         'value': {'type': 'int', 'value': 2}},
    ]}

    # Circular references
    SR1 = []
    SR1.append(SR1)
    ESR1 = {'type': 'list', 'items': [{'type': 'cached', 'index': 0}]}
    yield SR1, ESR1

    SR2 = {}
    SR2[0] = SR2
    ESR2 = {'type': 'dict', 'items': [
        {'key': {'type': 'int', 'value': 0},
         'value': {'type': 'cached', 'index': 0}},
    ]}
    yield SR2, ESR2

    SR3 = ([],)
    SR3[0].append(SR3)
    ESR3 = {'type': 'tuple', 'items': [
        {'type': 'list', 'items': [{'type': 'cached', 'index': 0}]},
    ]}
    yield SR3, ESR3

    SR4 = ([], [])
    SR4[0].append(SR4[1])
    SR4[1].append(SR4)
    ESR4 = {'type': 'tuple', 'items': [
        {'type': 'list', 'items': [{'type': 'cached', 'index': 2}]},
        {'type': 'list', 'items': [{'type': 'cached', 'index': 0}]},
    ]}
    yield SR4, ESR4

    SR5 = ([],)*2
    SR5[0].append(SR5)
    ESR5 = {'type': 'tuple', 'items': [
        {'type': 'list', 'items': [{'type': 'cached', 'index': 0}]},
        {'type': 'cached', 'index': 1},
    ]}
    yield SR5, ESR5

    SR6 = (SR1,)*2
    ESR6 = {'type': 'tuple', 'items': [
        {'type': 'list', 'items': [{'type': 'cached', 'index': 1}]},
        {'type': 'cached', 'index': 1},
    ]}
    yield SR6, ESR6

    SR7 = ([],)
    SR7[0].append((SR7,))
    ESR7 = {'type': 'tuple', 'items': [
        {'type': 'list', 'items': [
            {'type': 'tuple', 'items': [
                {'type': 'cached', 'index': 0},
            ]},
        ]},
    ]}
    yield SR7, ESR7

    SR8 = ([], [])
    SR8_ = (SR8, SR8[0])
    SR8[0].append(SR8_)
    SR8[1].append(SR8)
    ESR8 = {'type': 'tuple', 'items': [
        {'type': 'list', 'items': [
            {'type': 'tuple', 'items': [
                {'type': 'cached', 'index': 0},
                {'type': 'cached', 'index': 1},
            ]},
        ]},
        {'type': 'list', 'items': [
            {'type': 'cached', 'index': 0},
        ]},
    ]}
    yield SR8, ESR8

    SR9 = ([], [])
    SR9_ = (SR9[1], SR9[0])
    SR9[0].append(SR9_)
    SR9[1].append(SR9)
    ESR9 = {'type': 'tuple', 'items': [
        {'type': 'list', 'items': [
            {'type': 'tuple', 'items': [
                {'type': 'cached', 'index': 2},
                {'type': 'cached', 'index': 1},
            ]},
        ]},
        {'type': 'list', 'items': [
            {'type': 'cached', 'index': 0},
        ]},
    ]}
    yield SR9, ESR9


@pytest.mark.parametrize(('obj', 'encoded'), basic_cases())
def test_encode(encoding_session, obj, encoded):
    assert encoding_session.encode(obj) == encoded


@pytest.mark.parametrize(('obj', 'encoded'), basic_cases())
def test_decode(decoding_session, encoded, obj):
    assert_isomorphic(decoding_session.decode(encoded), obj)


def roundtrip_cases():
    """ Generate test cases for roundtrip testing. """
    # Test basic cases
    for obj, encoded in basic_cases():
        yield obj

    # Test multi-element sets, frozensets, and dicts
    yield {1, 2}
    yield frozenset({1, 2})
    yield {1: 2, 3: 4}

    # Test dict with two values referring to same object
    lst = []
    yield {1: lst, 2: "blah", 3: lst}

    # Test hash objects with shared members.
    # The actual encoding may vary due to the nondeterministic order.
    t0 = ()
    t1 = (t0,)
    yield {t0, t1}
    yield frozenset({t0, t1})
    yield {t0: t1, t1: t0}


@pytest.mark.parametrize('obj', roundtrip_cases())
def test_encode_decode_roundtrip(encoding_session, decoding_session, obj):
    """
    Test that encoding and decoding the given object produces an isomorphic
    object.
    """
    obj_ = decoding_session.decode(encoding_session.encode(obj))
    assert_isomorphic(obj, obj_)


def multi_cases():
    """
    Generate test cases for encoding multiple objects with the same session.
    """
    yield (1, 2), ({'type': 'int', 'value': 1},
                   {'type': 'int', 'value': 2})
    yield (None, None), ({'type': 'None'}, {'type': 'cached', 'index': 0})

    # Should be encoded as distinct objects
    yield ([], []), ({'type': 'list', 'items': []},
                     {'type': 'list', 'items': []})

    # Same object encoded multiple times
    l = []
    yield (l, l), ({'type': 'list', 'items': []},
                   {'type': 'cached', 'index': 0})

    # More complicated nesting
    t = ()
    yield ([1, t], {t: [t]}), (
        {'type': 'list', 'items': [
            {'type': 'int', 'value': 1},
            {'type': 'tuple', 'items': []},
        ]},
        {'type': 'dict', 'items': [
            {'key': {'type': 'cached', 'index': 2},
             'value': {'type': 'list', 'items': [
                {'type': 'cached', 'index': 2}]}}
        ]},
    )


@pytest.mark.parametrize(('objs', 'encodeds'), multi_cases())
def test_encode_multiple(encoding_session, objs, encodeds):
    """ Test encoding multiple objects in a single session. """
    for obj, encoded in zip(objs, encodeds):
        assert encoding_session.encode(obj) == encoded


@pytest.mark.parametrize(('objs', 'encodeds'), multi_cases())
def test_decode_multiple(decoding_session, encodeds, objs):
    """ Test decoding multiple objects in a single session. """
    iso = {}  # Extend isomorphism across all decoded objects
    for obj, encoded in zip(objs, encodeds):
        assert_isomorphic(decoding_session.decode(encoded), obj, iso)


def roundtrip_multi_cases():
    """ Roundtrip multiple object test cases. """
    for obj, encoded in multi_cases():
        yield obj


@pytest.mark.parametrize('objs', roundtrip_multi_cases())
def test_roundtrip_multiple(encoding_session, decoding_session, objs):
    """ Test roundtrip encoding/decoding with multiple objects. """
    encs = [encoding_session.encode(obj) for obj in objs]
    objs_ = [decoding_session.decode(enc) for enc in encs]

    iso = {}
    for obj, obj_ in zip(objs, objs_):
        assert_isomorphic(obj, obj_, iso)


def ref_cases():
    l = [1, 2]
    yield l, EncodingDepth.REF, {'type': 'ref', 'object': l}
    yield l, EncodingDepth.SHALLOW, {'type': 'list', 'items': [
        {'type': 'ref', 'object': 1},
        {'type': 'ref', 'object': 2},
    ]}
    yield l, EncodingDepth.DEEP, {'type': 'list', 'items': [
        {'type': 'int', 'value': 1},
        {'type': 'int', 'value': 2},
    ]}

    o = DummyObject()
    yield o, EncodingDepth.REF, {'type': 'ref', 'object': o}
    yield o, EncodingDepth.SHALLOW, {'type': 'ref', 'object': o}
    yield o, EncodingDepth.DEEP, {'type': 'ref', 'object': o}

    # Nested data structure
    c = {1: [o]}
    yield c, EncodingDepth.REF, {'type': 'ref', 'object': c}
    yield c, EncodingDepth.SHALLOW, {'type': 'dict', 'items': [
        {'key': {'type': 'ref', 'object': 1},
         'value': {'type': 'ref', 'object': [o]}},
    ]}
    yield c, EncodingDepth.DEEP, {'type': 'dict', 'items': [
        {'key': {'type': 'int', 'value': 1},
         'value': {'type': 'list', 'items': [{'type': 'ref', 'object': o}]}},
    ]}

    # Test data struture containing duplicate object
    # Refs should not be cached
    t = (o, o)
    yield t, EncodingDepth.REF, {'type': 'ref', 'object': t}
    yield t, EncodingDepth.SHALLOW, {'type': 'tuple', 'items': [
        {'type': 'ref', 'object': o},
        {'type': 'ref', 'object': o},
    ]}
    yield t, EncodingDepth.DEEP, {'type': 'tuple', 'items': [
        {'type': 'ref', 'object': o},
        {'type': 'ref', 'object': o},
    ]}

    # Circular reference
    l = []
    l.append(l)
    yield l, EncodingDepth.REF, {'type': 'ref', 'object': l}
    yield l, EncodingDepth.SHALLOW, {'type': 'list', 'items': [
        {'type': 'ref', 'object': l},
    ]}
    yield l, EncodingDepth.DEEP, {'type': 'list', 'items': [
        {'type': 'cached', 'index': 0},
    ]}


@pytest.mark.parametrize(('obj', 'depth', 'encoded'), ref_cases())
def test_encode_refs(encoding_session, obj, depth, encoded):
    assert encoding_session.encode(obj, depth=depth) == encoded


@pytest.mark.parametrize(('obj', 'depth', 'encoded'), ref_cases())
def test_decode_refs(decoding_session, encoded, obj, depth):
    if depth == EncodingDepth.REF:
        assert decoding_session.decode(encoded) is obj
    elif depth == EncodingDepth.SHALLOW:
        assert decoding_session.decode(encoded) == obj
    else:
        assert_isomorphic(decoding_session.decode(encoded), obj)


def assert_isomorphic(x, y, iso=None):
    """
    Assert that two objects are isomorphic.

    Objects are considered isomorphic if there exists a bijection between the
    objects and their children that respects object type and structure.
    """
    if iso is None:
        iso = {}

    if id(x) in iso or id(y) in iso:
        assert id(y) == iso.get(id(x))
        assert id(x) == iso.get(id(y))
        return

    iso[id(x)] = id(y)
    iso[id(y)] = id(x)

    assert type(x) == type(y)

    t = type(x)
    if t in (type(None), type(NotImplemented), type(Ellipsis), bool, int,
             _long, float, complex, bytes, _unicode, bytearray, set,
             frozenset, DummyObject):
        assert x == y
    elif t is _range:
        assert_range_eq(x, y)
    elif t is slice:
        assert_isomorphic(x.start, y.start, iso)
        assert_isomorphic(x.stop, y.stop, iso)
        assert_isomorphic(x.step, y.step, iso)
    elif t in (list, tuple):
        assert len(x) == len(y)
        for i in _range(len(x)):
            assert_isomorphic(x[i], y[i], iso)
    elif t is dict:
        assert len(x) == len(y)
        for k in x:
            assert k in y
            assert_isomorphic(x[k], y[k], iso)
    else:
        raise TypeError("Unsupported type: {}".format(t.__name__))
