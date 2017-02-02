import weakref


class Py2Object:
    """ Proxy for a Python 2 object. """

    __slots__ = ('__client__', '__oid__', '__weakref__')

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

    def __delitem__(self, key):
        return self.__client__.do_command('delitem', object=self)

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
        return self.__client__.do_command('truediv', a=self, b=other)

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
        return self.__client__.do_command('truediv', a=other, b=self)

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
        return self.__client__.do_command('itruediv', a=self, b=other)

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
