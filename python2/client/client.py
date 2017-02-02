# TODO: Logging

import contextlib
import json
import weakref

from python2.client.encoding import ClientEncoder
from python2.client.exceptions import Py2Error, Py2StopIteration
from python2.client.object import Py2Object


class Py2Client:
    """
    Python 2 internal client.

    This class is used to send commands to a Python 2 process and unpack the
    responses.
    """

    def __init__(self, infile, outfile):
        self.infile = infile
        self.outfile = outfile
        self.objects = weakref.WeakValueDictionary()
        self.encoder = ClientEncoder(self)

    def get_object(self, oid):
        """ Get the Py2Object with the given object id, or None. """
        return self.objects.get(oid)

    def create_object(self, oid):
        """ Create a Py2Object with the given object id. """
        obj = Py2Object(self, oid)
        self.objects[oid] = obj
        return obj

    def _send(self, data):
        print("Sending: {!r}".format(data))
        self.outfile.writelines((json.dumps(data, self.outfile).encode(),
                                 b'\n'))
        self.outfile.flush()

    def _receive(self):
        data = json.loads(self.infile.readline().decode())
        print("Received: {!r}".format(data))
        return data

    def do_command(self, command, **kwargs):
        data = {key: self.encoder.encode(value)
                for key, value in kwargs.items()}
        data.update(command=command)
        self._send(data)
        result = self._receive()
        if result['result'] == 'return':
            return self.encoder.decode(result['value'])
        elif result['result'] == 'raise':
            exception_type = Py2Error
            if result.get('exc_type') == 'StopIteration':
                exception_type = Py2StopIteration
            raise exception_type(self.encoder.decode(result['message']),
                                 self.encoder.decode(result['exception']))

    def close(self):
        with contextlib.ExitStack() as stack:
            stack.callback(self.infile.close)
            stack.callback(self.outfile.close)
