""" Python 2 server """

# TODO: Logging

import __builtin__
import argparse
import base64
from functools import wraps
import json
import operator
import os
import sys
import traceback

# Encoding depth
REF = 0  # Encode as reference
SHALLOW = 1  # Encode as value
DEEP = -1  # Recursively encode as value


def _command(keys, edepth=REF):
    def wrapper(func):
        @wraps(func)
        def wrapped(self, data):
            kwargs = {key: self._dec(data[key]) for key in keys}
            try:
                result = func(self, **kwargs)
            except Exception:
                return self._raise(*sys.exc_info())
            else:
                return self._return(result, edepth=edepth)

        return wrapped

    return wrapper


def _commandfunc(func, keys, edepth=REF, name=None):
    def wrapped(self, data):
        args = [self._dec(data[key]) for key in keys]
        try:
            result = func(*args)
        except Exception:
            return self._raise(*sys.exc_info())
        else:
            return self._return(result, edepth=edepth)

    if name is None:
        name = func.__name__
    wrapped.__name__ = '_do_{}'.format(name)

    return wrapped


# TODO: Factor encoding into separate module shared by client and server?
class Python2Server(object):
    def __init__(self, infile, outfile):
        self.infile = infile
        self.outfile = outfile
        self.objects = {}

    def _send(self, data):
        json.dump(data, self.outfile)
        self.outfile.write('\n')
        self.outfile.flush()

    def _receive(self):
        line = self.infile.readline()
        if line:
            return json.loads(line)

    def _enc(self, obj, edepth):
        """ Encode an object. """

        if edepth:
            if obj is None:
                return dict(type='none')
            elif obj is NotImplemented:
                return dict(type='NotImplemented')
            elif obj is Ellipsis:
                return dict(type='Ellipsis')

            t = type(obj)
            if t == bool:
                return dict(type='bool', value=obj)
            elif t in (int, long):
                return dict(type='int', value=obj)
            elif t == float:
                return dict(type='float', value=obj)
            elif t == complex:
                return dict(type='complex', real=obj.real, imag=obj.imag)
            elif t == bytes:
                return self._enc_bdata('bytes', obj)
            elif t == unicode:
                return self._enc_bdata('unicode', obj.encode('utf8'))
            elif t == list:
                return self._enc_iter('list', obj, edepth-1)
            elif t == tuple:
                return self._enc_iter('tuple', obj, edepth-1)
            elif t == bytearray:
                return self._enc_bdata('bytearray', obj)
            elif t == xrange:
                start, stop, step = xrange.__reduce__()[1]
                return dict(type='range', start=start, stop=stop, step=step)
            elif t == set:
                return self._enc_iter('set', obj, edepth-1)
            elif t == frozenset:
                return self._enc_iter('frozenset', obj, edepth-1)
            elif t == dict:
                return dict(type='dict',
                            items=[self._enc_kv(key, value, edepth-1)
                                   for key, value in obj.iteritems()])
            elif t == slice:
                return dict(type='slice',
                            start=self._enc(obj.start, edepth-1),
                            stop=self._enc(obj.stop, edepth-1),
                            step=self._enc(obj.step, edepth-1))

        return self._enc_ref(obj)

    def _enc_bdata(self, type_, data):
        """ Encode binary data. """
        return dict(type=type_, data=base64.b64encode(data).decode('ascii'))

    def _enc_iter(self, type_, itr, edepth):
        """ Encode an iterable collection. """
        return dict(type=type_, items=[self._enc(item, edepth) for item in itr])

    def _enc_kv(self, key, value, edepth):
        """ Encode a dict key-value pair. """
        return dict(key=self._enc(key, edepth), value=self._enc(value, edepth))

    def _enc_ref(self, obj):
        """ Encode an object as a reference. """
        oid = id(obj)
        self.objects[oid] = obj
        return dict(type='object', id=oid)

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
            return xrange(data['start'], data['stop'], data['step'])
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
            return self.objects[data['id']]
        else:
            raise ValueError("Invalid data type: {!r}".format(dtype))

    def _dec_bdata(self, data):
        return base64.b64decode(data['data'].encode('ascii'))

    def _return(self, result, edepth=REF):
        return dict(
            result='return',
            value=self._enc(result, edepth=edepth),
        )

    def _raise(self, exc_type, exc_value, exc_traceback):
        exc_value.__traceback__ = exc_traceback  # XXX: ?
        message = ''.join(traceback.format_exception_only(exc_type, exc_value))
        dct = dict(
            result='raise',
            exception=self._enc_ref(exc_value),
            message=self._enc(unicode(message.rstrip('\n'), errors='replace'),
                              edepth=DEEP),
        )

        # TODO: More elegant way to do this?
        if issubclass(exc_type, StopIteration):
            dct.update(exc_type='StopIteration')

        return dct

    @_command((), edepth=DEEP)
    def _do_ping(self):
        pass

    @_command(('object',))
    def _do_project(self, object):
        """ Convert a value to an object. """
        return value

    @_command(('object',), edepth=SHALLOW)
    def _do_lift(self, object):
        """ Convert an object to a value if possible. """
        return object

    @_command(('object',), edepth=DEEP)
    def _do_deeplift(self, object):
        """ Recursively convert an object to a value if possible. """
        return object

    @_command(('object',), edepth=DEEP)
    def _do_del(self, object):
        """ Delete an object from the server cache. """
        del self.objects[id(object)]

    @_command(('name',))
    def _do_builtin(self, name):
        """ Lookup a builtin by name. """
        return getattr(__builtin__, name)

    # String conversion
    _do_format = _commandfunc(format, ('object', 'format_spec'), edepth=DEEP)
    _do_repr = _commandfunc(repr, ('object',), edepth=DEEP)
    _do_str = _commandfunc(str, ('object',), edepth=DEEP)
    _do_unicode = _commandfunc(unicode, ('object',), edepth=DEEP)

    # Rich comparisons
    # XXX: NotImplemented?
    _do_lt = _commandfunc(operator.lt, ('a', 'b'), edepth=DEEP)
    _do_le = _commandfunc(operator.le, ('a', 'b'), edepth=DEEP)
    _do_eq = _commandfunc(operator.eq, ('a', 'b'), edepth=DEEP)
    _do_ne = _commandfunc(operator.ne, ('a', 'b'), edepth=DEEP)
    _do_gt = _commandfunc(operator.gt, ('a', 'b'), edepth=DEEP)
    _do_ge = _commandfunc(operator.ge, ('a', 'b'), edepth=DEEP)

    # Basic customization
    _do_bool = _commandfunc(bool, ('object',), edepth=DEEP)
    _do_hash = _commandfunc(hash, ('object',), edepth=DEEP)  # XXX?

    # Attribute access
    _do_getattr = _commandfunc(getattr, ('object', 'name'))
    _do_setattr = _commandfunc(
        setattr, ('object', 'name', 'value'), edepth=DEEP)
    _do_delattr = _commandfunc(delattr, ('object', 'name'), edepth=DEEP)

    # Instance/subclass checks
    _do_isinstance = _commandfunc(
        isinstance, ('object', 'classinfo'), edepth=DEEP)
    _do_issubclass = _commandfunc(
        issubclass, ('class_', 'classinfo'), edepth=DEEP)

    # Callable objects
    @_command(('object', 'args', 'kwargs'))
    def _do_call(self, object, args, kwargs):
        """ Call a function or callable object. """
        return object(*args, **kwargs)

    # Container types
    _do_len = _commandfunc(len, ('object',), edepth=DEEP)
    _do_getitem = _commandfunc(operator.getitem, ('object', 'key'))
    _do_setitem = _commandfunc(
        operator.setitem, ('object', 'key', 'value'), edepth=DEEP)
    _do_setitem = _commandfunc(
        operator.delitem, ('object', 'key'), edepth=DEEP)
    _do_iter = _commandfunc(iter, ('object',))
    _do_reversed = _commandfunc(reversed, ('object',))
    _do_contains = _commandfunc(operator.contains, ('object', 'item'))

    # Iterators
    _do_next = _commandfunc(next, ('object',))

    # Numeric types
    _do_add = _commandfunc(operator.add, ('a', 'b'))
    _do_sub = _commandfunc(operator.sub, ('a', 'b'))
    _do_mul = _commandfunc(operator.mul, ('a', 'b'))
    _do_div = _commandfunc(operator.div, ('a', 'b'))
    _do_truediv = _commandfunc(operator.truediv, ('a', 'b'))
    _do_floordiv = _commandfunc(operator.floordiv, ('a', 'b'))
    _do_mod = _commandfunc(operator.mod, ('a', 'b'))
    _do_divmod = _commandfunc(divmod, ('a', 'b'))
    _do_pow = _commandfunc(pow, ('a', 'b'))
    _do_pow3 = _commandfunc(pow, ('a', 'b', 'm'))
    _do_lshift = _commandfunc(operator.lshift, ('a', 'b'))
    _do_rshift = _commandfunc(operator.rshift, ('a', 'b'))
    _do_and = _commandfunc(operator.and_, ('a', 'b'))
    _do_xor = _commandfunc(operator.xor, ('a', 'b'))
    _do_or = _commandfunc(operator.or_, ('a', 'b'))

    _do_iadd = _commandfunc(operator.iadd, ('a', 'b'))
    _do_isub = _commandfunc(operator.isub, ('a', 'b'))
    _do_imul = _commandfunc(operator.imul, ('a', 'b'))
    _do_idiv = _commandfunc(operator.idiv, ('a', 'b'))
    _do_itruediv = _commandfunc(operator.itruediv, ('a', 'b'))
    _do_ifloordiv = _commandfunc(operator.ifloordiv, ('a', 'b'))
    _do_imod = _commandfunc(operator.imod, ('a', 'b'))
    _do_ipow = _commandfunc(pow, ('a', 'b'))
    _do_ilshift = _commandfunc(operator.ilshift, ('a', 'b'))
    _do_irshift = _commandfunc(operator.irshift, ('a', 'b'))
    _do_iand = _commandfunc(operator.iand, ('a', 'b'))
    _do_ixor = _commandfunc(operator.ixor, ('a', 'b'))
    _do_ior = _commandfunc(operator.ior, ('a', 'b'))

    _do_neg = _commandfunc(operator.neg, ('object'))
    _do_pos = _commandfunc(operator.pos, ('object'))
    _do_abs = _commandfunc(operator.abs, ('object'))
    _do_invert = _commandfunc(operator.invert, ('object'))

    _do_complex = _commandfunc(complex, ('object',), edepth=DEEP)
    _do_int = _commandfunc(int, ('object',), edepth=DEEP)
    _do_float = _commandfunc(float, ('object',), edepth=DEEP)
    _do_round = _commandfunc(round, ('object', 'n'), edepth=DEEP)
    _do_index = _commandfunc(operator.index, ('object',), edepth=DEEP)

    # TODO: More magic methods

    def run(self):
        """ Read and execute commands until the input stream is closed or an
            exception is raised. """

        data = self._receive()
        while data:
            cmethod = getattr(self, '_do_{}'.format(data['command']))
            self._send(cmethod(data))
            data = self._receive()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--in', '-i', dest='in_', type=int, default=0,
                        help="File descriptor for server input")
    parser.add_argument('--out', '-o', type=int, default=1,
                        help="File descriptor for server output")
    args = parser.parse_args()

    server = Python2Server(os.fdopen(args.in_, 'rb'),
                           os.fdopen(args.out, 'wb'))
    sys.stderr.write('Python 2 server started\n')
    server.run()
    sys.stderr.write('Python 2 server exited cleanly\n')


if __name__ == '__main__':
    main()
