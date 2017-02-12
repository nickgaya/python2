# TODO: Logging

import contextlib
import json
import logging
import weakref

from python2.client.codec import ClientCodec
from python2.client.exceptions import Py2Error, Py2StopIteration
from python2.client.object import Py2Object


logger = logging.getLogger(__name__)


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
        self.codec = ClientCodec(self)

    def get_object(self, oid):
        """ Get the Py2Object with the given object id, or None. """
        return self.objects.get(oid)

    def create_object(self, oid):
        """ Create a Py2Object with the given object id. """
        obj = Py2Object(self, oid)
        self.objects[oid] = obj
        return obj

    def _send(self, data):
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Sending: {!r}".format(data))
        self.outfile.write(json.dumps(data).encode())
        self.outfile.write(b'\n')
        self.outfile.flush()

    def _receive(self):
        data = json.loads(self.infile.readline().decode())
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Received: {!r}".format(data))
        return data

    def encode_command(self, command, *args):
        session = self.codec.encoding_session()
        return dict(command=command,
                    args=[session.encode(arg) for arg in args])

    def decode_result(self, data):
        if data['result'] == 'return':
            return self.codec.decode(data['value'])
        elif data['result'] == 'raise':
            exception_type = Py2Error
            if data.get('exc_type') == 'StopIteration':
                exception_type = Py2StopIteration
            raise exception_type(
                self.codec.decode(data['message']),
                exception=self.codec.decode(data['exception'])
            )
        else:
            raise Exception("Invalid server response: result={!r}".format(
                data['result']))

    def do_command(self, command, *args):
        self._send(self.encode_command(command, *args))
        return self.decode_result(self._receive())

    def close(self):
        with contextlib.ExitStack() as stack:
            stack.callback(self.infile.close)
            stack.callback(self.outfile.close)
