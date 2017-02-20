python2
=======

A library for running Python 2 code from a Python 3 application.

    Effortlessly harness the power and convenience of Python 2... in Python 3!

Why?
----

Why not??

This library was created for more whimsical than practical reasons.  In theory,
it could be used to interface with legacy Python 2 code which for one reason or
another cannot be ported to Python 3.

Installation
------------
``python2`` requires a working install of both Python 2 and Python 3.
Currently the library has only been tested with Python 2.7 and Python 3.4, 3.5,
and 3.6.

To install the package::

    pip install -U python2

If using virtualenvs, you will need to create separate Python 2 and 3
virtualenvs, and install the package into both.

Usage
-----
To begin working with Python 2, import the package in Python 3 and create a new
``Python2`` object::

    >>> from python2.client import Python2
    >>> py2 = Python2('/path/to/python2/executable')

This object is our gateway to the Python 2 world.  Python 2 builtins can be
accessed as attributes of the ``Python2`` object. Let's use Python 2's
``__import__()`` function to import the deprecated ``sha`` module, which was
removed in Python 3::

    >>> py2_sha = py2.__import__('sha')
    >>> py2_sha.sha('abc')
    <Py2Object <sha1 HASH object @ 0x107463c30>>

Ahh, just like the good ol' days.  You can deprecate a module but you can't
deprecate the human spirit!

We can use the ``Python2.project()`` method to convert Python 3 objects to
Python 2::

    >>> py2.project(1)
    <Py2Object 1>
    >>> py2.project('foo')
    <Py2Object u'foo'>

You can use ``Python2.lift()`` to lift Python 2 objects back to Python 3.  For
container types, use ``Python2.deeplift()`` to recursively perform the lifting.
``Py2Object`` instances have special properties ``_`` and ``__`` to perform the
equivalent operations::

    >>> o = py2.project([1, 2, 3])
    >>> o
    <Py2Object [1, 2, 3]>
    >>> o._
    [<Py2Object 1>, <Py2Object 2>, <Py2Object 3>]
    >>> o.__
    [1, 2, 3]

Python 2 objects can be used pretty much like regular Python 3 objects.  You
can also freely mix and match with Python 3 builtin types::

    >>> x = py2.project(1)
    >>> x
    <Py2Object 1>
    >>> str(x)
    '1'
    >>> x + 1
    <Py2Object 2>
    >>> d = py2.dict(foo=x, bar=None)
    >>> d['foo'] is x
    True
    >>> del d['foo']
    >>> d
    <Py2Object {u'bar': None}>
    >>> d.__
    {'bar': None}

If you just want to execute some Python 2 code directly, you can use the
``Python2.exec()`` method.  This method accepts a string containing Python 2
code and an optional dict representing the scope to execute the code in, and
returns the resulting scope after executing the code.  This can be used to
define new Python 2 classes and functions::

   >>> scope = py2.exec("""
   ... def foo(x):
   ...     return x + 1
   ... """)
   >>> foo = scope['foo']
   >>> foo(2)
   <Py2Object 3>

If an exception occurs in Python 2, a ``Py2Error`` will be thrown by the
client.  The Python 2 exception is stored as the ``exception`` attribute of the
``Py2Error`` object.  The underlying traceback is attached to the Python 2
exception as the ``__traceback__`` attribute.

::

    >>> py2.int('asdf')
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
      ...
    python2.client.exceptions.Py2Error: ValueError: invalid literal for int() with base 10: 'asdf'

When you're done using Python 2, you can end the session by calling the
``Python2.shutdown()`` method.  You can also use the ``Python2`` object as a
context manager to automatically do the same thing when exiting the context.

::

    >>> py2.shutdown()

Testing
-------
This package uses Tox for testing.  Tests are not included in the Python dist,
so you will need to clone the repo to run them.  To run the unit tests, install
Tox and run the following command from the project's base directory::

    tox

After running tox, you can run the client-server integration tests with the
'integration_tests.sh' script.  This script takes two arguments specifying the
Tox virtualenvs to use for Python 2 and 3, respectively::

    ./integration_tests.sh py27 py36

To modify the behavior of Tox, you can set the ``PYTEST_ADDOPTS`` variable.
For example, you can set the ``-x`` flag to abort after the first test
failure::

    export PYTEST_ADDOPTS=-x

You can use the ``-n NUM`` flag to parallelize the tests using the
`pytest-xdist plugin`_  This adds some overhead to the test setup, so this
option is primarily useful for speeding up the integration tests.

.. _pytest-xdist plugin: http://pytest.org/dev/xdist.html

Caveats
-------

Supported types
```````````````
Projection is only supported for basic builtin types.  Other objects cannot be
projected to Python 2.  The supported types are: ``bool``, ``int``, ``float``,
``complex``, ``bytes``, ``unicode``, ``bytearray``, ``range``, ``slice``,
``list``, ``tuple``, ``set``, ``frozenset``, and ``dict``.  The ``None``,
``NotImplemented``, and ``Ellipsis`` singletons are also supported.

In particular, Python 3 functions, types, and instances of user-defined classes
cannot currently be projected into Python 2.

Type introspection
``````````````````
The ``Py2Object`` class implements many "magic methods" from the Python 3 data
model.  As a result, a ``Py2Object`` appears to be callable, iterable, etc.,
even if the underlying object is not.  Attempting to perform such operations may
result in a ``Py2Error``.

If you need to introspect a Python 2 object, use Python 2 builtin functions.
For example::

    >>> i = py2.project(1)
    >>> py2.callable(i)
    <Py2Object False>
    >>> py2.isinstance(i, py2.int)
    <Py2Object True>

String types
````````````
In Python 2, ``str`` objects are raw byte strings, while in Python 3 they are
Unicode strings.  This can lead to some confusion, as projecting a Python 3
``str`` will result in a Python 2 ``unicode`` object, while lifting a Python 2
``str`` will return a Python 3 ``bytes`` object.

    >>> py2.project('foo')
    <Py2Object u'foo'>
    >>> py2.lift(py2.str(123))
    b'123'

Division
````````
The behavior of the division operator changed with `PEP 238`_.  This created
two alternate division operations, "true division" and "classic division".
Classic division was removed in Python 3.

To respect this change, when two ``Py2Object`` s are divided, classic division
is used.  When a ``Py2Object`` divides or is divided by a Python 3 value, true division is used.

::

    >>> i = py2.project(1)
    >>> j = py2.project(2)
    >>> i / j  # classic division
    <Py2Object 0>
    >>> i / 2  # true division
    <Py2Object 0.5>
    >>> 1 / j  # true division
    <Py2Object 0.5>

.. _PEP 238: https://www.python.org/dev/peps/pep-0238/

Further discussion
------------------

How it works
````````````
When you launch a Python 2 session, the library spawns a child process running
Python 2.  This child process acts as a server that listens for commands from
the Python 3 client.  For each command, the server performs an operation in
Python 2 and returns the result either as an encoded value or a reference to a
Python 2 object stored on the server.

On the client side, the library wraps Python 2 references with the
``Py2Object`` class.  This class implements many of the "magic methods" of the
`Python 3 data model`_ by sending commands to the Python 2 server to perform
the appropriate operation on the underlying Python 2 object.

.. _Python 3 data model: https://docs.python.org/3/reference/datamodel.html

Call-by-value semantics
```````````````````````
When projecting a value or calling a Python 2 function with Python 3 arguments,
the arguments will be passed to Python 2 "by value", that is, by encoding the
value of the argument to be decoded by the server.  When using a Python 2
object, the object is stored in the Python 2 session and is passed "by
reference".

This has some implications for the semantics of Python 2 functions.  Suppose we
have a Python 2 function that mutates a list.  If we pass this function a
Python 3 list, the list will be copied into Python 2 and the copy will be
mutated, but the original will not be modified::

    >>> f = py2.eval("lambda l: l.append(1)")
    >>> l = []
    >>> f(l)
    <Py2Object None>
    >>> l
    []

However, if we project the list into Python 2 before passing it to the
function, then we can observe the modifications on the projected list::

    >>> py2_l = py2.project(l)
    >>> f(py2_l)
    <Py2Object None>
    >>> py2_l
    <Py2Object [1]>

Return semantics
````````````````
Returning generally occurs by reference except for operations that require a
specific return type (``str()``, ``int()``, etc.).  The main reason for this is
that returning by value may lose information about object identity that needs
to be preserved.  Return values can be easily lifted to Python 2 if desired.

Object identity and lifespan
````````````````````````````
Each Python 2 object returned by the server is represented by a unique
``Py2Object``.  This means that the ``is`` operator can be used to determine if
two ``Py2Object`` s refer to the same underlying object.

The Python 2 server stores all objects it returns, to prevent them from being
deallocated.  When the corresponding ``Py2Object`` is deallocated in the Python
3 process, the underlying Python 2 object will be removed from the server cache
to allow it to be deallocated as appropriate.

Encoding algorithm
``````````````````
This library uses a simple JSON encoding for supported types.  For a given
function call, each unique object will only be encoded once.  This means that
data structures with circular references are supported.  For a detailed
description of the algorithm, see the ``python2.shared.codec`` module.

Possible improvements
---------------------

Python 2 types
``````````````
Currently there is a single type for Python 2 objects in Python 3,
``Py2Object``. An alternate strategy would be to dynamically create Python 3
classes for each Python 2 type encountered, and create proxy objects as
instances of these classes.

The main benefit of this change would be better type introspection for Python 2
objects (see the discussion at `Type introspection`_).  However, it would be
more cumbersome and incur a performance cost, since the client would need to
know the type of each object and the methods supported by that type.
Additionally, this approach would not fully support the dynamic nature of the
Python type system, since the proxied type would not reflect changes to the
underlying type such as adding or removing methods.

This would require the server to return the object type for references, and
some mechanism for the client to introspect Python 2 types.  The client would
cache types for the lifetime of the Python 2 session, with a mechanism to
explicitly refresh a type to pick up any changes that had occurred in Python 2.

Bootstrapping the type system might be a little tricky.  We would want to
create a base type that all proxy types are instances of, *including the base
type itself.*  We would also probably want a base type for all proxy objects
including non-types.

Python 3 proxy objects in Python 2
``````````````````````````````````
Currently the relationship between client and server is asymmetrical.  The
client has a representation of Python 2 objects, but the server does not have
a way to represent Python 3 objects.  We might like to add such a mechanism.
This would mean that instead of the simple request-response pattern from client
to server we have now, there would be the possibility of callbacks.  In effect,
the two processes would act more like coroutines with the flow of control
passing back and forth between them.

Better Python version support
`````````````````````````````
We could extend support to more Python 2 and 3 versions.

Similar projects
----------------
After writing this library, I discovered that I'm not the only one to have had
this idea.  `Sux`_ is a library that provides similar functionality, with some
notable differences:

- The library is much smaller and more lightweight, and only needs to be
  installed in the Python 3 environment to work.

- The main emphasis is on imports and function calls, which makes sense since
  these are the most important operations for the using legacy packages.  Most
  other operators (e.g. arithmetic operators) are not supported.

- The library uses Pickle to communicate between the Python 2 and 3 processes.
  This is a good idea and I should probably have done the same, although I had
  fun implementing the current encoding algorithm.

.. _Sux: https://github.com/nicois/sux/
