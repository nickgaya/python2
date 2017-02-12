import weakref

import pytest

from python2.client import Py2Error, Py2Object


def test_exception(py2, helpers):
    with pytest.raises(Py2Error) as einfo:
        py2.int("asdf")

    py2.ping()  # Make sure session is still working

    assert hasattr(einfo.value, 'exception')
    py2_exc = einfo.value.exception
    assert type(py2_exc) is Py2Object
    assert py2.isinstance(py2_exc, py2.ValueError)
    assert hasattr(py2_exc, '__traceback__')


def test_unique_proxy_objects(py2):
    """
    Test that identical Python 2 objects are represented by the same
    `Py2Object` object.
    """
    f = py2.eval("lambda x: (x, x)")
    o1, o2 = f(py2.object())._
    assert o1 is o2

    p = py2.object()
    assert p is not o1


def test_projected_identity(py2):
    """
    Test that argument projection preserves the identity relationships between
    arguments.
    """
    py2_is = py2.eval("lambda x, y: x is y")
    l = []
    assert py2_is(l, l)
    assert py2_is(l, y=l)  # Mixing args and kwargs
    assert not py2_is([], [])


def test_py2_object_mutation(py2):
    """
    Test that changes to Python 2 objects are reflected in the corresponding
    Py2Object.
    """
    l = py2.list()
    f = py2.eval("lambda l: l.append(1)")
    f(l)
    assert l == [1]


def test_object_lifespan(py2):
    py2_weakref = py2.__import__('weakref')

    # Create custom type to allow weak referencing
    O = py2.type(b'O', (py2.object,), {})
    o = O()

    wr2 = py2_weakref.ref(o)  # Python 2 weakref to object
    wr3 = weakref.ref(o)  # Python 3 weakref to Py2Object object
    assert wr2() is o
    assert wr3() is o

    del o

    # Verify that object is no longer alive in Python 2 or 3
    assert wr2() is py2.None_
    assert wr3() is None
