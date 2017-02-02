# TODO: Logging

import __builtin__
from functools import wraps
import json
import operator
import sys
import traceback

from python2.encoding import EncodingDepth
from python2.server.encoding import ServerEncoder


def _command(keys, edepth=EncodingDepth.REF):
    def wrapper(func):
        @wraps(func)
        def wrapped(self, data):
            kwargs = {key: self.encoder.decode(data[key]) for key in keys}
            try:
                result = func(self, **kwargs)
            except Exception:
                return self._raise(*sys.exc_info())
            else:
                return self._return(result, edepth=edepth)

        return wrapped

    return wrapper


def _commandfunc(func, keys, edepth=EncodingDepth.REF, name=None):
    def wrapped(self, data):
        args = [self.encoder.decode(data[key]) for key in keys]
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


def _reflect(object):
    """ Identity function. """
    return object


class Python2Server(object):
    """ Python 2 server. """

    def __init__(self, infile, outfile):
        self.infile = infile
        self.outfile = outfile
        self.objects = {}
        self.encoder = ServerEncoder(self)

    def cache_add(self, obj):
        """ Add an object to the server cache. """
        self.objects[id(obj)] = obj

    def cache_get(self, oid):
        """ Get an object by id from the server cache. """
        return self.objects[oid]

    def cache_del(self, oid):
        """ Delete an object by id from the server cache. """
        del self.objects[oid]

    def _send(self, data):
        json.dump(data, self.outfile)
        self.outfile.write('\n')
        self.outfile.flush()

    def _receive(self):
        line = self.infile.readline()
        if line:
            return json.loads(line)

    def _return(self, result, edepth):
        return dict(
            result='return',
            value=self.encoder.encode(result, depth=edepth),
        )

    def _raise(self, exc_type, exc_value, exc_traceback):
        exc_value.__traceback__ = exc_traceback  # XXX: ?
        message = ''.join(traceback.format_exception_only(exc_type, exc_value))
        dct = dict(
            result='raise',
            exception=self.encoder.encode(exc_value, depth=EncodingDepth.REF),
            message=self.encoder.encode(
                unicode(message.rstrip('\n'), errors='replace'),
                depth=EncodingDepth.DEEP),
        )

        # TODO: More elegant way to do this?
        if issubclass(exc_type, StopIteration):
            dct.update(exc_type='StopIteration')

        return dct

    @_command((), edepth=EncodingDepth.DEEP)
    def _do_ping(self):
        """ No-op command used to test client-server communication. """
        pass

    # The following three commands all return the object passed in, but differ
    # in how the return value is encoded.
    _do_project = _commandfunc(_reflect, ('object',), edepth=EncodingDepth.REF,
                               name='project')
    _do_lift = _commandfunc(_reflect, ('object',),
                            edepth=EncodingDepth.SHALLOW, name='lift')
    _do_deeplift = _commandfunc(_reflect, ('object',),
                                edepth=EncodingDepth.DEEP, name='deeplift')

    # Objects returned by reference are stored in the server cache.  This
    # command is used to drop an object from the server cache.
    @_command(('object',), edepth=EncodingDepth.DEEP)
    def _do_del(self, object):
        self.cache_del(id(object))

    @_command(('name',))
    def _do_builtin(self, name):
        """ Lookup a builtin by name. """
        return getattr(__builtin__, name)

    # String conversion
    _do_format = _commandfunc(format, ('object', 'format_spec'),
                              edepth=EncodingDepth.DEEP)
    _do_repr = _commandfunc(repr, ('object',), edepth=EncodingDepth.DEEP)
    _do_str = _commandfunc(str, ('object',), edepth=EncodingDepth.DEEP)
    _do_unicode = _commandfunc(unicode, ('object',), edepth=EncodingDepth.DEEP)

    # Rich comparisons
    # XXX: NotImplemented?
    _do_lt = _commandfunc(operator.lt, ('a', 'b'), edepth=EncodingDepth.DEEP)
    _do_le = _commandfunc(operator.le, ('a', 'b'), edepth=EncodingDepth.DEEP)
    _do_eq = _commandfunc(operator.eq, ('a', 'b'), edepth=EncodingDepth.DEEP)
    _do_ne = _commandfunc(operator.ne, ('a', 'b'), edepth=EncodingDepth.DEEP)
    _do_gt = _commandfunc(operator.gt, ('a', 'b'), edepth=EncodingDepth.DEEP)
    _do_ge = _commandfunc(operator.ge, ('a', 'b'), edepth=EncodingDepth.DEEP)

    # Basic customization
    _do_bool = _commandfunc(bool, ('object',), edepth=EncodingDepth.DEEP)
    _do_hash = _commandfunc(hash, ('object',), edepth=EncodingDepth.DEEP)

    # Attribute access
    _do_getattr = _commandfunc(getattr, ('object', 'name'))
    _do_setattr = _commandfunc(setattr, ('object', 'name', 'value'),
                               edepth=EncodingDepth.DEEP)
    _do_delattr = _commandfunc(delattr, ('object', 'name'),
                               edepth=EncodingDepth.DEEP)

    # Instance/subclass checks
    _do_isinstance = _commandfunc(isinstance, ('object', 'classinfo'),
                                  edepth=EncodingDepth.DEEP)
    _do_issubclass = _commandfunc(issubclass, ('class_', 'classinfo'),
                                  edepth=EncodingDepth.DEEP)

    # Callable objects
    @_command(('object', 'args', 'kwargs'))
    def _do_call(self, object, args, kwargs):
        """ Call a function or callable object. """
        return object(*args, **kwargs)

    # Container types
    _do_len = _commandfunc(len, ('object',), edepth=EncodingDepth.DEEP)
    _do_getitem = _commandfunc(operator.getitem, ('object', 'key'))
    _do_setitem = _commandfunc(operator.setitem, ('object', 'key', 'value'),
                               edepth=EncodingDepth.DEEP)
    _do_setitem = _commandfunc(operator.delitem, ('object', 'key'),
                               edepth=EncodingDepth.DEEP)
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

    _do_complex = _commandfunc(complex, ('object',), edepth=EncodingDepth.DEEP)
    _do_int = _commandfunc(int, ('object',), edepth=EncodingDepth.DEEP)
    _do_float = _commandfunc(float, ('object',), edepth=EncodingDepth.DEEP)
    _do_round = _commandfunc(round, ('object', 'n'), edepth=EncodingDepth.DEEP)
    _do_index = _commandfunc(operator.index, ('object',),
                             edepth=EncodingDepth.DEEP)

    def run(self):
        """
        Read and execute commands until the input stream is closed or an
        exception is raised.
        """
        data = self._receive()
        while data:
            cmethod = getattr(self, '_do_{}'.format(data['command']))
            self._send(cmethod(data))
            data = self._receive()
