""" Python 2 client """

# TODO: Proper logging

import base64
import contextlib
import json
import os
import subprocess
import weakref


def _on_error(fn, *args, **kwargs):
    def __exit__(exc_type, exc_value, traceback):
        if exc_type is not None:
            fn(*args, **kwargs)

    return __exit__


def _kill(proc):
    try:
        proc.kill()
    finally:
        proc.wait()


class Python2:
    def __init__(self):
        with contextlib.ExitStack() as stack
            # We need to close the server ends of each pipe after spawning the
            # subprocess.  We only need to close the client ends if an
            # exception is raised during initialization.

            cread, swrite = os.pipe()
            stack.push(_on_error(os.close, cread))
            stack.callback(os.close, swrite)

            sread, cwrite = os.pipe()
            stack.callback(os.close, sread)
            stack.push(_on_error(os.close, cwrite))

            self._proc = subprocess.Popen(
                ['python', '-m', 'p2server',
                 '--in', str(sread), '--out', str(swrite)],
                pass_fds=(sread, swrite),
                start_new_session=True,  # Avoid signal issues
                universal_newlines=False)

            stack.push(_on_error(_kill, self._proc))

            self._client = Py2Client(os.fdopen(cread, 'rb'),
                                     os.fdopen(cwrite, 'wb'))

    def ping(self):
        return self._client.do_command('ping')

    def project(self, value):
        """ Project the given value into Python 2. """
        return self._client.do_command('project', value=value)

    def lift(self, object, deep=False):
        """ Lift the given value from Python 2 to 3. """
        return self._client.do_command('deeplift' if deep else 'lift',
                                       object=object)

    def shutdown(self):
        try:
            self._client.close()
        except Exception:
            pass

        try:
            self._proc.wait(timeout=1)
        except Exception:
            _kill(self._proc)

    def __enter__(self):
        return self

    def __exit__(self):
        self.shutdown()

    def __getattr__(self, name):
        # True/False/None are keywords in Python 3
        if name in ('None_', 'True_', 'False_'):
            name = name[:-1]
        return self._client.do_command('builtin', name=name)


class Py2Client:
    def __init__(self, infile, outfile):
        self.infile = infile
        self.outfile = outfile
        self.objects = weakref.WeakValueDictionary()

    def _send(self, data):
        print("Sending: {!r}".format(data))
        self.outfile.writelines((json.dumps(data, self.outfile).encode(),
                                 b'\n'))
        self.outfile.flush()

    def _receive(self):
        data = json.loads(self.infile.readline().decode())
        print("Received: {!r}".format(data))
        return data

    def _enc(self, obj):
        """ Encode an object. """

        if obj is None:
            return dict(type='none')
        elif obj is NotImplemented:
            return dict(type='NotImplemented')
        elif obj is Ellipsis:
            return dict(type='Ellipsis')

        t = type(obj)
        if t == bool:
            return dict(type='bool', value=obj)
        elif t == int:
            return dict(type='int', value=obj)
        elif t == float:
            return dict(type='float', value=obj)
        elif t == complex:
            return dict(type='complex', real=obj.real, imag=obj.imag)
        elif t == bytes:
            return self._enc_bdata('bytes', obj)
        elif t == str:
            return self._enc_bdata('unicode', obj.encode('utf8'))
        elif t == list:
            return self._enc_iter('list', obj)
        elif t == tuple:
            return self._enc_iter('tuple', obj)
        elif t == bytearray:
            return self._enc_bdata('bytearray', obj)
        elif t == range:
            return dict(type='range', start=r.start, stop=r.stop, step=r.step)
        elif t == set:
            return self._enc_iter('set', obj)
        elif t == frozenset:
            return self._enc_iter('frozenset', obj)
        elif t == set:
            return self._enc_iter('set', obj)
        elif t == frozenset:
            return self._enc_iter('frozenset', obj)
        elif t == dict:
            return dict(type='dict',
                        items=[self._enc_kv(key, value)
                               for key, value in obj.items()])
        elif t == slice:
            return dict(type='slice',
                        start=self._enc(obj.start),
                        stop=self._enc(obj.stop),
                        step=self._enc(obj.step))
        elif t == Py2Object:
            if obj is not self.objects[obj.__oid__]:
                raise ValueError("Py2Object {} belongs to a different Python2"
                                 " session".format(obj.__oid__))

            return dict(type='object', id=obj.__oid__)
        elif issubclass(t, Py2Error):
            return self._enc(obj.exception)
        else:
            raise TypeError("Cannot encode object of type {}".format(
                t.__name__))

    def _enc_bdata(self, type_, data):
        """ Encode binary data. """
        return dict(type=type_, data=base64.b64encode(data).decode('ascii'))

    def _enc_iter(self, type_, itr):
        """ Encode an iterable collection. """
        return dict(type=type_, items=[self._enc(item) for item in itr])

    def _enc_kv(self, key, value):
        """ Encode a dict key-value pair. """
        return dict(key=self._enc(key), value=self._enc(value))

    def _dec(self, data):
        """ Decode an encoded object. """
        dtype = data['type']
        if dtype == 'none':
            return None
        elif dtype == 'NotImplemented':
            return NotImplemented
        elif dtype == 'Ellipsis':
            return Ellipsis
        elif dtype in ('bool', 'int', 'float'):
            return data['value']
        elif dtype == 'complex':
            return complex(real=data['real'], imag=data['imag'])
        elif dtype == 'bytes':
            return self._dec_bdata(data)
        elif dtype == 'unicode':
            return self._dec_bdata(data).decode('utf8')
        elif dtype == 'list':
            return [self._dec(item) for item in data['items']]
        elif dtype == 'tuple':
            return tuple(self._dec(item) for item in data['items'])
        elif dtype == 'bytearray':
            return bytearray(self._dec_bdata(data))
        elif dtype == 'range':
            return range(data['start'], data['stop'], data['step'])
        elif dtype == 'set':
            return {self._dec(item) for item in data['items']}
        elif dtype == 'frozenset':
            return frozenset(self._dec(item) for item in data['items'])
        elif dtype == 'dict':
            return {self._dec(kv['key']): self._dec(kv['value'])
                    for kv in data['items']}
        elif dtype == 'slice':
            return slice(self._dec(data['start']),
                         self._dec(data['stop']),
                         self._dec(data['step']))
        elif dtype == 'object':
            oid = data['id']
            if oid in self.objects:
                return self.objects[oid]
            else:
                obj = Py2Object(self, oid)
                self.objects[oid] = obj
                return obj
        else:
            raise ValueError("Invalid data type: {!r}".format(dtype))

    def _dec_bdata(self, data):
        return base64.b64decode(data['data'].encode('ascii'))

    def do_command(self, command, **kwargs):
        data = {key: self._enc(value) for key, value in kwargs.items()}
        data.update(command=command)
        self._send(data)
        result = self._receive()
        if result['result'] == 'return':
            return self._dec(result['value'])
        elif result['result'] == 'raise':
            exception_type = Py2Error
            if result.get('exc_type') == 'StopIteration':
                exception_type = Py2StopIteration
            raise exception_type(self._dec(result['message']),
                                 self._dec(result['exception']))

    def close(self):
        with contextlib.ExitStack() as stack:
            stack.callback(self.infile.close)
            stack.callback(self.outfile.close)


class Py2Error(Exception):
    def __init__(self, message, exception):
        super(Py2Error, self).__init__(message)
        self.exception = exception

    def __repr__(self):
        return "<{} {!r}>".format(self.__class__.__name__, self.exception)


# Special exception type so iterators work properly
class Py2StopIteration(Py2Error, StopIteration):
    pass


class Py2Object:
    __slots__ = '__client__', '__oid__', '__weakref__'

    def __init__(self, client, oid):
        object.__setattr__(self, '__client__', weakref.proxy(client))
        object.__setattr__(self, '__oid__', oid)

    @property
    def _(self):
        """ Convert this object to its Python 3 equivalent. """
        return self.__client__.do_command('lift', object=self)

    @property
    def __(self):
        """ Recursively convert this object to its Python 3 equivalent. """
        return self.__client__.do_command('deeplift', object=self)

    def __repr__(self):
        obj_repr = self.__client__.do_command('repr', object=self)
        return '<{} {}>'.format(self.__class__.__name__,
                                obj_repr.decode(errors='replace'))

    def __str__(self):
        return self.__client__.do_command('unicode', object=self)

    def __bytes__(self):
        return self.__client__.do_command('str', object=self)

    def __format__(self, format_spec):
        return self.__client__.do_command(
            'format', object=self, format_spec=format_spec)

    def __lt__(self, other):
        return self.__client__.do_command('lt', a=self, b=other)

    def __le__(self, other):
        return self.__client__.do_command('le', a=self, b=other)

    def __eq__(self, other):
        return self.__client__.do_command('eq', a=self, b=other)

    def __ne__(self, other):
        return self.__client__.do_command('ne', a=self, b=other)

    def __gt__(self, other):
        return self.__client__.do_command('gt', a=self, b=other)

    def __ge__(self, other):
        return self.__client__.do_command('ge', a=self, b=other)

    def __bool__(self):
        return self.__client__.do_command('bool', object=self)

    # XXX?
    def __hash__(self):
        return self.__client__.do_command('hash', object=self)

    def __getattr__(self, name):
        return self.__client__.do_command('getattr', object=self, name=name)

    def __setattr__(self, name, value):
        return self.__client__.do_command(
            'setattr', object=self, name=name, value=value)

    def __delattr__(self, name):
        return self.__client__.do_command('delattr', object=self, name=name)

    # XXX?
    def __dir__(self):
        return self.__client__.do_command('dir', object=self)

    def __call__(self, *args, **kwargs):
        return self.__client__.do_command(
            'call', object=self, args=args, kwargs=kwargs)

    def __instancecheck__(self, instance):
        return isinstance(instance, Py2Object) and self.__client__.do_command(
            'isinstance', object=instance, classinfo=self)

    def __subclasscheck__(self, subclass):
        return issubclass(subclass, Py2Object) and self.__client__.do_command(
            'issubclass', class_=subclass, classinfo=self)

    def __len__(self):
        return self.__client__.do_command('len', object=self)

    def __getitem__(self, key):
        return self.__client__.do_command('getitem', object=self, key=key)

    def __setitem__(self, key, value):
        return self.__client__.do_command(
            'setitem', object=self, key=key, value=value)

    def __iter__(self):
        return self.__client__.do_command('iter', object=self)

    def __reversed__(self):
        return self.__client__.do_command('reversed', object=self)

    def __contains__(self, item):
        return self.__client__.do_command('contains', object=self, item=item)

    def __next__(self):
        return self.__client__.do_command('next', object=self)

    def __add__(self, other):
        return self.__client__.do_command('add', a=self, b=other)

    def __sub__(self, other):
        return self.__client__.do_command('sub', a=self, b=other)

    def __mul__(self, other):
        return self.__client__.do_command('mul', a=self, b=other)

    def __truediv__(self, other):
        return self.__client__.do_command('div', a=self, b=other)

    def __floordiv__(self, other):
        return self.__client__.do_command('floordiv', a=self, b=other)

    def __mod__(self, other):
        return self.__client__.do_command('mod', a=self, b=other)

    def __divmod__(self, other):
        return self.__client__.do_command('divmod', a=self, b=other)

    def __pow__(self, other, modulo=None):
        if modulo is None:
            return self.__client__.do_command('pow', a=self, b=other)
        else:
            return self.__client__.do_command(
                'pow3', a=self, b=other, m=modulo)

    def __lshift__(self, other):
        return self.__client__.do_command('lshift', a=self, b=other)

    def __rshift__(self, other):
        return self.__client__.do_command('rshift', a=self, b=other)

    def __and__(self, other):
        return self.__client__.do_command('and', a=self, b=other)

    def __xor__(self, other):
        return self.__client__.do_command('xor', a=self, b=other)

    def __or__(self, other):
        return self.__client__.do_command('or', a=self, b=other)

    def __radd__(self, other):
        return self.__client__.do_command('add', a=other, b=self)

    def __rsub__(self, other):
        return self.__client__.do_command('sub', a=other, b=self)

    def __rmul__(self, other):
        return self.__client__.do_command('mul', a=other, b=self)

    def __rtruediv__(self, other):
        # TODO: div?
        return self.__client__.do_command('div', a=other, b=self)

    def __rfloordiv__(self, other):
        return self.__client__.do_command('floordiv', a=other, b=self)

    def __rmod__(self, other):
        return self.__client__.do_command('mod', a=other, b=self)

    def __rdivmod__(self, other):
        return self.__client__.do_command('divmod', a=other, b=self)

    def __rpow__(self, other):
        return self.__client__.do_command('pow', a=other, b=self)

    def __rlshift__(self, other):
        return self.__client__.do_command('lshift', a=other, b=self)

    def __rrshift__(self, other):
        return self.__client__.do_command('rshift', a=other, b=self)

    def __rand__(self, other):
        return self.__client__.do_command('and', a=other, b=self)

    def __rxor__(self, other):
        return self.__client__.do_command('xor', a=other, b=self)

    def __ror__(self, other):
        return self.__client__.do_command('or', a=other, b=self)

    def __iadd__(self, other):
        return self.__client__.do_command('iadd', a=self, b=other)

    def __isub__(self, other):
        return self.__client__.do_command('isub', a=self, b=other)

    def __imul__(self, other):
        return self.__client__.do_command('imul', a=self, b=other)

    def __itruediv__(self, other):
        # TODO: div?
        return self.__client__.do_command('idiv', a=self, b=other)

    def __ifloordiv__(self, other):
        return self.__client__.do_command('ifloordiv', a=self, b=other)

    def __imod__(self, other):
        return self.__client__.do_command('imod', a=self, b=other)

    def __ipow__(self, other):
        return self.__client__.do_command('ipow', a=self, b=other)

    def __ilshift__(self, other):
        return self.__client__.do_command('ilshift', a=self, b=other)

    def __irshift__(self, other):
        return self.__client__.do_command('irshift', a=self, b=other)

    def __iand__(self, other):
        return self.__client__.do_command('iand', a=self, b=other)

    def __ixor__(self, other):
        return self.__client__.do_command('ixor', a=self, b=other)

    def __ior__(self, other):
        return self.__client__.do_command('or', a=self, b=other)

    def __complex__(self):
        return self.__client__.do_command('complex', object=self)

    def __int__(self):
        return self.__client__.do_command('int', object=self)

    def __float__(self):
        return self.__client__.do_command('float', object=self)

    def __round__(self, n=0):
        return self.__client__.do_command('round', object=self, n=n)

    def __index__(self):
        return self.__client__.do_command('index', object=self)

    def __del__(self):
        # TODO: Clean this up
        print("Deleting object {}".format(self.__oid__))
        try:
            self.__client__.do_command('del', object=self)
        except Exception as e:
            print("Delete failed: {}: {}".format(type(e).__name__, e))


# Caveats
# - Exceptions
# - Types
# - Iterators
# - callable, etc.
# - bytes/unicode
# - div vs truediv
# - context managers
# - pass by value
