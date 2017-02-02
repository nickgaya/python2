import base64
import sys


PYTHON_VERSION = sys.version_info.major
if PYTHON_VERSION == 2:
    _int_types = (int, long)  # noqa
    _bytes = str
    _unicode = unicode  # noqa
    _range = xrange  # noqa
    _items = lambda dct: dct.iteritems()
elif PYTHON_VERSION == 3:
    _int_types = (int,)
    _bytes = bytes
    _unicode = str
    _range = range
    _items = lambda dct: dct.items()
else:
    raise Exception("Unsupported Python version: {}".format(PYTHON_VERSION))


class EncodingDepth(object):
    REF = 0
    SHALLOW = 1
    DEEP = -1


class BaseEncoder(object):
    """ Base encoder for Python 2 client and server. """

    def encode(self, obj, depth=EncodingDepth.DEEP):
        """ Encode an object. """

        if depth:
            if obj is None:
                return dict(type='None')
            elif obj is NotImplemented:
                return dict(type='NotImplemented')
            elif obj is Ellipsis:
                return dict(type='Ellipsis')

            t = type(obj)
            if t is bool:
                return dict(type='bool', value=obj)
            elif any(t is it for it in _int_types):
                return dict(type='int', value=obj)
            elif t is float:
                return dict(type='float', value=obj)
            elif t is complex:
                return dict(type='complex', real=obj.real, imag=obj.imag)
            elif t is _bytes:
                return self._enc_bdata('bytes', obj)
            elif t is _unicode:
                return self._enc_bdata('unicode', obj.encode('utf8'))
            elif t is list:
                return self._enc_iter('list', obj, depth-1)
            elif t is tuple:
                return self._enc_iter('tuple', obj, depth-1)
            elif t is bytearray:
                return self._enc_bdata('bytearray', obj)
            elif t is _range:
                return self._enc_range(obj)
            elif t is set:
                return self._enc_iter('set', obj, depth-1)
            elif t is frozenset:
                return self._enc_iter('frozenset', obj, depth-1)
            elif t is dict:
                return dict(type='dict',
                            items=[self._enc_kv(key, value, depth-1)
                                   for key, value in _items(obj)])
            elif t is slice:
                return dict(type='slice',
                            start=self.encode(obj.start, depth-1),
                            stop=self.encode(obj.stop, depth-1),
                            step=self.encode(obj.step, depth-1))

        return self._enc_ref(obj)

    def _enc_bdata(self, type_, data):
        """ Encode binary data. """
        return dict(type=type_, data=base64.b64encode(data).decode('ascii'))

    def _enc_iter(self, type_, itr, depth):
        """ Encode an iterable collection. """
        return dict(type=type_,
                    items=[self.encode(item, depth) for item in itr])

    if PYTHON_VERSION == 2:
        def _enc_range(self, range_):
            """ Encode a range object. """
            start, stop, step = range_.__reduce__()[1]
            return dict(type='range', start=start, stop=stop, step=step)
    else:
        def _enc_range(self, range_):
            """ Encode a range object. """
            return dict(type='range', start=range_.start, stop=range_.stop,
                        step=range_.step)

    def _enc_kv(self, key, value, depth):
        """ Encode a dict key-value pair. """
        return dict(key=self.encode(key, depth),
                    value=self.encode(value, depth))

    def _enc_ref(self, obj):
        """ Encode an object as a reference. """
        # Implemented by client/server subclasses
        raise NotImplemented()

    def decode(self, data):
        """ Decode an encoded object. """
        dtype = data['type']
        if dtype == 'None':
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
            return [self.decode(item) for item in data['items']]
        elif dtype == 'tuple':
            return tuple(self.decode(item) for item in data['items'])
        elif dtype == 'bytearray':
            return bytearray(self._dec_bdata(data))
        elif dtype == 'range':
            return _range(data['start'], data['stop'], data['step'])
        elif dtype == 'set':
            return {self.decode(item) for item in data['items']}
        elif dtype == 'frozenset':
            return frozenset(self.decode(item) for item in data['items'])
        elif dtype == 'dict':
            return {self.decode(kv['key']): self.decode(kv['value'])
                    for kv in data['items']}
        elif dtype == 'slice':
            return slice(self.decode(data['start']),
                         self.decode(data['stop']),
                         self.decode(data['step']))
        elif dtype == 'ref':
            return self._dec_ref(data)
        else:
            raise ValueError("Invalid data type: {!r}".format(dtype))

    def _dec_bdata(self, data):
        return base64.b64decode(data['data'].encode('ascii'))

    def _dec_ref(self, data):
        """ Decode an object reference. """
        # Implemented by client/server subclasses
        raise NotImplemented()
