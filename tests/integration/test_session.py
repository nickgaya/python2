import os
import signal
import textwrap

import pytest

from python2.client import Py2Error, Py2Object


def test_ping(py2):
    py2.ping()


def test_project(py2, helpers):
    o = py2.project(123)
    helpers.assert_py2_eq(o, 123)


def test_project_failure(py2):
    with pytest.raises(TypeError):
        py2.project(object())

    py2.ping()  # Make sure session is still ok


def test_lift(py2, helpers):
    o = py2.eval("[1, (None, 2), 3]")
    l = py2.lift(o)
    helpers.assert_types_match([Py2Object, Py2Object, Py2Object], l)
    assert l == [1, (None, 2), 3]


def test_deeplift(py2, helpers):
    o = py2.eval("[1, (None, 2), 3]")
    l = py2.deeplift(o)
    helpers.assert_types_match([int, (type(None), int), int], l)
    assert l == [1, (None, 2), 3]


def test_exec(py2):
    d = py2.exec(textwrap.dedent("""
        class C(object):
            pass
    """))
    C = d['C']
    c = C()
    assert py2.type(c) == C
    assert C.__name__ == 'C'
    assert py2.type(C) == py2.type


def test_exec_with_scope(py2):
    scope = py2.project({'foo': 'bar'})
    scope_ = py2.exec(textwrap.dedent("""
        def f():
            return foo
    """), scope)
    assert scope_ is scope
    f = scope['f']
    scope['foo'] = 'baz'
    assert f() == 'baz'


def test_builtins(py2, helpers):
    helpers.assert_py2_eq(py2.None_, None)
    helpers.assert_py2_eq(py2.True_, True)
    helpers.assert_py2_eq(py2.False_, False)
    helpers.assert_py2_eq(py2.int('1'), 1)
    helpers.assert_py2_eq(py2.range(3), [0, 1, 2])


def test_import(py2):
    m = py2.__import__('string')
    assert type(m) is Py2Object
    assert m.__name__ == 'string'
    assert m.digits == '0123456789'


def test_non_builtin(py2):
    with pytest.raises(Py2Error):
        py2.asdf

    # Make sure session still works after exception
    py2.ping()


def test_signal_handling(py2):
    with pytest.raises(KeyboardInterrupt):
        os.kill(os.getpid(), signal.SIGINT)

    py2.ping()  # Client should not receive signal
