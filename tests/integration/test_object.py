import operator
import textwrap

import pytest

from python2.client.object import Py2Iterator, Py2Object


# TODO: Test projected/non-projected values for all operations?


class Capture:
    """ Class used to "capture" operations for later use. """
    def __call__(self, *args, **kwargs):
        return lambda f: f(*args, **kwargs)

    def __getitem__(self, key):
        return key


cap = Capture()


def test_object_lift(py2, helpers):
    o = py2.eval("[1, (None, 2), 3]")
    l = o._
    helpers.assert_types_match([Py2Object, Py2Object, Py2Object], l)
    assert l == [1, (None, 2), 3]


def test_object_deeplift(py2, helpers):
    o = py2.eval("[1, (None, 2), 3]")
    l = o.__
    helpers.assert_types_match([int, (type(None), int), int], l)
    assert l == [1, (None, 2), 3]


def test_repr(py2):
    o = py2.eval("[1, 2]")
    assert repr(o) == "<Py2Object [1, 2]>"


def test_str(py2):
    o = py2.eval("[1, 2]")
    assert str(o) == "[1, 2]"


def test_bytes(py2):
    o = py2.eval("[1, 2]")
    assert bytes(o) == b"[1, 2]"


def test_format(py2):
    o = py2.eval("1.2")
    assert "{:7.04f}".format(o) == " 1.2000"


@pytest.mark.parametrize('op', (operator.eq,
                                operator.ge,
                                operator.gt,
                                operator.le,
                                operator.lt,
                                operator.ne))
@pytest.mark.parametrize('d', range(-1, 2))
def test_comparison(py2, op, d):
    x = 123
    y = x + d
    x_ = py2.project(x)
    y_ = py2.project(y)

    assert op(x_, y_) == op(x, y)
    assert op(x_, y) == op(x, y)
    assert op(y, x_) == op(y, x)


def test_hash(py2):
    o = py2.object()
    assert hash(o) == py2.hash(o)


def test_bool(py2):
    assert bool(py2.list()) is False
    assert bool(py2.list((1, 2, 3))) is True


def test_getattr(py2, helpers):
    c = py2.project(1 + 2j)
    helpers.assert_py2_eq(c.real, 1.0)
    helpers.assert_py2_eq(c.imag, 2.0)


def test_getattr_error(py2, helpers):
    o = py2.object()
    with helpers.py2_raises(py2.AttributeError):
        o.y


def test_setattr(py2, helpers):
    O = py2.type(b'O', (py2.object,), {})
    o = O()

    o.x = 1
    helpers.assert_py2_eq(py2.getattr(o, 'x'), 1)


def test_setattr_multiple(py2, helpers):
    O = py2.type(b'O', (py2.object,), {})
    o = O()

    o.x = 1
    o.y = 2
    helpers.assert_py2_eq(py2.getattr(o, 'x'), 1)
    helpers.assert_py2_eq(py2.getattr(o, 'y'), 2)


def test_setattr_update(py2, helpers):
    O = py2.type(b'O', (py2.object,), {})
    o = O()

    o.x = 1
    o.y = 2
    o.x = 3
    helpers.assert_py2_eq(py2.getattr(o, 'x'), 3)
    helpers.assert_py2_eq(py2.getattr(o, 'y'), 2)


def test_setattr_error(py2, helpers):
    o = py2.project(1)
    with helpers.py2_raises(py2.AttributeError):
        o.x = 2


def test_delattr(py2):
    O = py2.type(b'O', (py2.object,), {})
    o = O()

    py2.setattr(o, 'x', 1)
    del o.x
    assert not py2.hasattr(o, 'x')


def test_delattr_error(py2, helpers):
    o = py2.object()
    with helpers.py2_raises(py2.AttributeError):
        del o.x


def test_call_no_args(py2, helpers):
    helpers.assert_py2_eq(py2.list(), [])


@pytest.mark.parametrize(('call', 'expected'), [
    (cap(1), (1, None, (), {})),
    (cap(1, 2), (1, 2, (), {})),
    (cap(1, 2, 3), (1, 2, (3,), {})),
    (cap(1, 2, 3, 4), (1, 2, (3, 4), {})),
    (cap(1, y=2), (1, 2, (), {})),
    (cap(1, z=2), (1, None, (), {'z': 2})),
    (cap(1, 2, z=3), (1, 2, (), {'z': 3})),
    (cap(1, 2, 3, z=4), (1, 2, (3,), {'z': 4})),
    (cap(1, 2, 3, 4, z=4, a=5), (1, 2, (3, 4), {'z': 4, 'a': 5})),
])
def test_call(py2, helpers, call, expected):
    f = py2.eval("lambda x, y=None, *args, **kwargs: (x, y, args, kwargs)")
    helpers.assert_py2_eq(call(f), expected)


def test_call_mixed(py2, helpers):
    f = py2.eval("lambda x, y: (x, y)")
    helpers.assert_py2_eq(f(1, py2.project(2)), (1, 2))
    helpers.assert_py2_eq(f(py2.None_, y=py2.list()), (None, []))
    helpers.assert_py2_eq(f(y=py2.project('a'), x=py2.project('b')),
                          ('b', 'a'))


@pytest.mark.parametrize(('obj', 'expected'), (([], 0), ([12, 7], 2)))
def test_len(py2, obj, expected):
    obj = py2.project(obj)
    assert len(obj) == expected


@pytest.mark.parametrize(('obj', 'key', 'expected'), [
    ("abc", cap[1], "b"),
    ([1, 2, 3, 4, 5], cap[:2], [1, 2]),
    ('rats', cap[::-1], 'star'),
    ({(3, 4): 5}, cap[3, 4], 5)
])
@pytest.mark.parametrize('project_key', (True, False))
def test_getitem(py2, helpers, obj, key, expected, project_key):
    obj = py2.project(obj)
    if project_key:
        key = py2.project(key)
    helpers.assert_py2_eq(obj[key], expected)


def test_getitem_indexerror(py2, helpers):
    l = py2.range(10)
    with helpers.py2_raises(py2.IndexError):
        l[10]


def test_getitem_keyerror(py2, helpers):
    d = py2.project({'foo': 'bar', 1: 2, (3, 4): 5})
    with helpers.py2_raises(py2.KeyError):
        d[2]


@pytest.mark.parametrize(('obj', 'key', 'value', 'expected'), [
    ([0, 1, 2, 3, 4], cap[1], 'foo', [0, 'foo', 2, 3, 4]),
    ([1, 2, 3], cap[:], (10, 20), [10, 20]),
    ({}, cap[1], 2, {1: 2}),
    ({'foo': 'bar'}, cap['foo'], 'baz', {'foo': 'baz'}),
])
@pytest.mark.parametrize('project_key', (True, False))
def test_setitem_list(py2, obj, key, value, expected, project_key):
    obj = py2.project(obj)
    if project_key:
        key = py2.project(key)
    obj[key] = value
    assert obj == expected


@pytest.mark.parametrize(('obj', 'key', 'expected'), [
    (['x', 'y', 'z'], cap[1], ['x', 'z']),
    ([1, 2, 3, 4, 5], cap[:2], [3, 4, 5]),
    ([0, 1, 2, 3, 4, 5, 6], cap[1::2], [0, 2, 4, 6]),
    ({'foo': 'bar', 123: 456}, cap['foo'], {123: 456}),
])
@pytest.mark.parametrize('project_key', (True, False))
def test_delitem(py2, obj, key, expected, project_key):
    obj = py2.project(obj)
    if project_key:
        key = py2.project(key)
    del obj[key]
    assert obj == expected


def test_iter_next(py2, helpers):
    i = iter(py2.project('woo'))
    assert isinstance(i, Py2Iterator)
    helpers.assert_py2_eq(next(i), 'w')
    helpers.assert_py2_eq(next(i), 'o')
    helpers.assert_py2_eq(next(i), 'o')

    with helpers.py2_raises(py2.StopIteration) as einfo:
        next(i)

    assert isinstance(einfo.value, StopIteration)


def test_iter_implicit(py2, helpers):
    o = py2.project(['a', None, ()])
    l = list(o)
    helpers.assert_types_match([Py2Object, Py2Object, Py2Object], l)
    assert l == ['a', None, ()]


def test_reversed(py2):
    t = py2.project((3, 4, 5))
    r = reversed(t)
    assert py2.isinstance(r, py2.reversed)
    assert list(iter(r)) == [5, 4, 3]


def test_contains(py2):
    d = {'asdf': 125}
    assert 'asdf' in d
    assert 125 not in d


@pytest.mark.parametrize('op', (operator.add,
                                operator.sub,
                                operator.mul,
                                operator.truediv,
                                operator.floordiv,
                                operator.mod,
                                divmod,
                                operator.pow,
                                operator.lshift,
                                operator.rshift,
                                operator.and_,
                                operator.xor,
                                operator.or_))
def test_operators(py2, helpers, op):
    x, y = 4, 3
    x_ = py2.project(x)
    y_ = py2.project(y)

    helpers.assert_py2_eq(op(x_, y_), op(x, y))
    helpers.assert_py2_eq(op(x_, y), op(x, y))
    helpers.assert_py2_eq(op(y, x_), op(y, x))


def test_pow3(py2, helpers):
    x, y, z = 5, 10000, 10
    x_ = py2.project(x)
    y_ = py2.project(y)
    z_ = py2.project(z)

    helpers.assert_py2_eq(pow(x_, y, z), pow(x, y, z))
    helpers.assert_py2_eq(pow(x_, y_, z), pow(x, y, z))
    helpers.assert_py2_eq(pow(x_, y, z_), pow(x, y, z))
    helpers.assert_py2_eq(pow(x_, y_, z_), pow(x, y, z))


@pytest.mark.parametrize(('op', 'obj', 'other', 'expected'), (
    (operator.iadd, [1, 2], [3, 4], [1, 2, 3, 4]),
    (operator.isub, {1, 2}, {2, 3}, {1}),
    (operator.imul, [1], 2, [1, 1]),
    (operator.iand, {1, 2}, {2, 3}, {2}),
    (operator.ixor, {1, 2}, {2, 3}, {1, 3}),
    (operator.ior, {1, 2}, {2, 3}, {1, 2, 3}),
))
@pytest.mark.parametrize('project_other', (True, False))
def test_inplace_operators(py2, helpers, op, obj, other, expected,
                           project_other):
    obj = py2.project(obj)
    if project_other:
        other = py2.project(other)
    obj2 = op(obj, other)
    assert obj2 is obj  # In-place operation
    helpers.assert_py2_eq(obj2, expected)


@pytest.mark.parametrize(('op'), (operator.itruediv,
                                  operator.ifloordiv,
                                  operator.imod,
                                  operator.ipow,
                                  operator.ilshift,
                                  operator.irshift))
@pytest.mark.parametrize('project_other', (True, False))
def test_obscure_inplace_operators(py2, op, project_other):
    """ Test inplace operators not covered by native types, above. """

    scope = py2.exec(textwrap.dedent("""
        class O(object):
            def __idiv__(self, other):
                self.div = other
                return self

            def __itruediv__(self, other):
                self.itruediv = other
                return self

            def __ifloordiv__(self, other):
                self.ifloordiv = other
                return self

            def __imod__(self, other):
                self.imod = other
                return self

            def __ipow__(self, other):
                self.ipow = other
                return self

            def __ilshift__(self, other):
                self.ilshift = other
                return self

            def __irshift__(self, other):
                self.irshift = other
                return self
    """))
    O = scope['O']
    obj = O()
    other = "foo"
    if project_other:
        other = py2.project(other)

    obj2 = op(obj, other)

    assert obj2 is obj  # In-place
    # Make sure correct method was called
    assert getattr(obj, op.__name__) == other


@pytest.mark.parametrize('value', (0, 10, 1.23, 5.1+0.6j))
def test_complex(py2, value):
    value_ = py2.project(value)
    assert complex(value_) == complex(value)


@pytest.mark.parametrize('value', (0, 10, 1.23))
def test_int(py2, value):
    value_ = py2.project(value)
    assert int(value_) == int(value)


@pytest.mark.parametrize('value', (0, 5, 1.1))
def test_float(py2, value):
    value_ = py2.project(value)
    assert float(value_) == float(value)


@pytest.mark.parametrize('value', (0, 67334, 1241.23456))
@pytest.mark.parametrize('n', (0, 2, -3))
@pytest.mark.parametrize('project_n', (True, False))
def test_round(py2, value, n, project_n):
    value_ = py2.project(value)
    n_ = py2.project(n) if project_n else n
    assert round(value_, n_) == round(value, n)


def test_index(py2):
    O = py2.type(b'O', (py2.object,),
                 {'__index__': py2.eval("lambda self: 123")})
    o = O()
    assert bin(o) == bin(123)
