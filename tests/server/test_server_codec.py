import pytest

from python2.server.codec import ServerCodec
from python2.shared.codec import EncodingDepth


class MockServer(object):
    def __init__(self):
        self.codec = ServerCodec(self)
        self.objects = {}

    def cache_add(self, obj):
        self.objects[id(obj)] = obj

    def cache_get(self, oid):
        return self.objects[oid]


@pytest.fixture
def server():
    return MockServer()


def cases():
    """ Generator for encoding/decoding test cases """
    yield (None, EncodingDepth.REF, {'type': 'ref', 'id': id(None)},
           {id(None): None})
    yield None, EncodingDepth.SHALLOW, {'type': 'None'}, {}
    yield None, EncodingDepth.DEEP, {'type': 'None'}, {}

    obj = object()
    for depth in (EncodingDepth.REF,
                  EncodingDepth.SHALLOW,
                  EncodingDepth.DEEP):
        yield obj, depth, {'type': 'ref', 'id': id(obj)}, {id(obj): obj}

    o1, o2 = object(), object()
    t = o1, o2, None
    yield t, EncodingDepth.REF, {'type': 'ref', 'id': id(t)}, {id(t): t}
    yield t, EncodingDepth.SHALLOW, {'type': 'tuple', 'items': [
        {'type': 'ref', 'id': id(o1)},
        {'type': 'ref', 'id': id(o2)},
        {'type': 'ref', 'id': id(None)},
    ]}, {id(o1): o1, id(o2): o2, id(None): None}
    yield t, EncodingDepth.DEEP, {'type': 'tuple', 'items': [
        {'type': 'ref', 'id': id(o1)},
        {'type': 'ref', 'id': id(o2)},
        {'type': 'None'},
    ]}, {id(o1): o1, id(o2): o2}

    l = [1, 2]
    yield l, EncodingDepth.REF, {'type': 'ref', 'id': id(l)}, {id(l): l}
    yield l, EncodingDepth.SHALLOW, {'type': 'list', 'items': [
        {'type': 'ref', 'id': id(l[0])},
        {'type': 'ref', 'id': id(l[1])},
    ]}, {id(l[0]): l[0], id(l[1]): l[1]}
    yield l, EncodingDepth.DEEP, {'type': 'list', 'items': [
        {'type': 'int', 'value': 1},
        {'type': 'int', 'value': 2},
    ]}, {}


@pytest.mark.parametrize(('obj', 'depth', 'expected', 'refs'), cases())
def test_encode(server, obj, depth, expected, refs):
    encoded = server.codec.encode(obj, depth)
    assert encoded == expected
    assert server.objects == refs


@pytest.mark.parametrize(('expected', 'depth', 'encoded', 'refs'), cases())
def test_decode(server, refs, encoded, expected, depth):
    server.objects = refs
    obj = server.codec.decode(encoded)
    assert obj == expected


def test_ref_roundtrip(server):
    # Ensure decoding a ref returns the referenced object
    l = []
    encoded = server.codec.encode(l, EncodingDepth.REF)
    decoded = server.codec.decode(encoded)
    assert decoded is l


def test_value_roundtrip(server):
    l = []
    encoded = server.codec.encode(l, EncodingDepth.DEEP)
    decoded = server.codec.decode(encoded)
    assert decoded is not l
    assert decoded == l


def test_encoding_session(server):
    session = server.codec.encoding_session()
    l = []
    e1 = session.encode(l, EncodingDepth.DEEP)
    e2 = session.encode(l, EncodingDepth.DEEP)

    assert e1 == {'type': 'list', 'items': []}
    assert e2 == {'type': 'cached', 'index': 0}
    assert server.objects == {}


def test_encoding_separate(server):
    l = []
    e1 = server.codec.encode(l, EncodingDepth.DEEP)
    e2 = server.codec.encode(l, EncodingDepth.DEEP)

    assert e1 == {'type': 'list', 'items': []}
    # Should not be cached
    assert e2 == {'type': 'list', 'items': []}


def test_encoding_separate_sessions(server):
    session1 = server.codec.encoding_session()
    session2 = server.codec.encoding_session()
    l = []
    e1 = session1.encode(l, EncodingDepth.DEEP)
    e2 = session1.encode(l, EncodingDepth.DEEP)
    e3 = session2.encode(l, EncodingDepth.DEEP)

    assert e1 == {'type': 'list', 'items': []}
    # Same session
    assert e2 == {'type': 'cached', 'index': 0}
    # Different session
    assert e3 == {'type': 'list', 'items': []}


def session_cases():
    """
    Test cases for encoding multiple objects with different encoding depths.
    """
    l = []
    ll = [l]

    yield (
        (l, EncodingDepth.DEEP, {'type': 'list', 'items': []}),
        (l, EncodingDepth.REF, {'type': 'ref', 'id': id(l)}),
    ), {id(l): l}

    yield (
        (l, EncodingDepth.REF, {'type': 'ref', 'id': id(l)}),
        (l, EncodingDepth.DEEP, {'type': 'list', 'items': []}),
    ), {id(l): l}

    yield (
        (l, EncodingDepth.DEEP, {'type': 'list', 'items': []}),
        (l, EncodingDepth.REF, {'type': 'ref', 'id': id(l)}),
        # Objects encoded as values should be cached
        (l, EncodingDepth.DEEP, {'type': 'cached', 'index': 0}),
        # Refs should not be cached
        (l, EncodingDepth.REF, {'type': 'ref', 'id': id(l)}),
    ), {id(l): l}

    yield (
        (ll, EncodingDepth.DEEP, {'type': 'list', 'items': [
            {'type': 'list', 'items': []},
        ]}),
        (ll, EncodingDepth.SHALLOW, {'type': 'list', 'items': [
            {'type': 'ref', 'id': id(l)},
        ]}),
        (ll, EncodingDepth.REF, {'type': 'ref', 'id': id(ll)}),
    ), {id(ll): ll, id(l): l}


@pytest.mark.parametrize(('calls', 'refs'), session_cases())
def test_encoding_session_multiple_depths(server, calls, refs):
    session = server.codec.encoding_session()
    for obj, depth, expected in calls:
        encoded = session.encode(obj, depth)
        assert encoded == expected

    assert server.objects == refs


def test_decoding_session(server):
    session = server.codec.decoding_session()
    o1 = session.decode({'type': 'list', 'items': []})
    o2 = session.decode({'type': 'cached', 'index': 0})
    assert o1 is o2


def test_decoding_separate(server):
    l1 = server.codec.decode({'type': 'list', 'items': []})
    l2 = server.codec.decode({'type': 'list', 'items': [
        {'type': 'cached', 'index': 0},
    ]})

    assert l2 is not l1
    assert l2[0] is l2


def test_decoding_separate_sessions(server):
    session1 = server.codec.decoding_session()
    session2 = server.codec.decoding_session()
    l1 = session1.decode({'type': 'list', 'items': []})
    l2 = session2.decode({'type': 'list', 'items': [
        {'type': 'cached', 'index': 0},
    ]})

    assert l2 is not l1
    assert l2[0] is l2
