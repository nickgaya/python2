python2
-------

A library for running Python 2 code from a Python 3 application.

    Effortlessly harness the power and convenience of Python 2... in Python 3!

Why?
====

Why not??

In theory, you could use this library to interface with Python 2 code which for
one reason or another cannot be ported to Python 3. However, the main reason
for creating this library was sheer whimsy.

Usage
=====

`python2` requires a working install of both Python 2 and Python 3. To begin
working with Python 2, import the package and create a new Python2 object::

    >>> from python2.client import Python2
    >>> p2 = Python2()

Python 2 builtins can be accessed as attributes of the `Python2` object. Let's
use Python 2's `__import__()` function to import the deprecated `sha` module, which was removed in Python 3.

    >>> p2_sha = p2.__import__('sha')
    >>> p2_sha.sha('abc')
    <Py2Object <sha1 HASH object @ 0x107463c30>>

And we're in business!

We can use the `Python2.project()` method to convert Python 3 objects to Python
2::

    >>> p2.project(1)
    <Py2Object 1>
    >>> p2.project('foo')
    <Py2Object u'foo'>

`Py2Object` instances have a special property, `_`, which can be used to lift
Python 2 objects back into Python 3.  For container types, the `__` attribute
can be used to perform this operation recursively.

    >>> o = p2.project([1, 2, 3])
    >>> o
    <Py2Object [1, 2, 3]>
    >>> o._
    [<Py2Object 1>, <Py2Object 2>, <Py2Object 3>]
    >>> o.__
    [1, 2, 3]

Python 2 objects can be used pretty much like regular Python 3 objects.  You
can also freely mix and match with Python 3 builtin types.

    >>> x = p2.project(1)
    >>> x
    <Py2Object 1>
    >>> str(x)
    '1'
    >>> x + 1
    <Py2Object 2>
    >>> isinstance(x, p2.int)
    True
    >>> d = p2.dict(foo=x, bar=None)
    >>> d['foo'] is x
    True
    >>> del d['foo']
    >>> d
    <Py2Object {u'bar': None}>
    >>> d.__
    {'bar': None}
