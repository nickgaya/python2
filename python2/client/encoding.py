import weakref

from python2.encoding import BaseEncoder
from python2.client.exceptions import Py2Error
from python2.client.object import Py2Object


class ClientEncoder(BaseEncoder):
    """ Python 2 client object encoder. """

    def __init__(self, client):
        self.client = weakref.ref(client)

    def _enc_ref(self, obj):
        """ Encode an object as a reference. """
        if isinstance(obj, Py2Object):
            if obj is not self.client().get_object(obj.__oid__):
                raise ValueError("Py2Object {} belongs to a different Python2"
                                 " session".format(obj.__oid__))
            return dict(type='ref', id=obj.__oid__)
        elif isinstance(obj, Py2Error):
            return self._enc_ref(obj.exception)
        else:
            raise TypeError("Cannot encode object of type {}".format(
                type(obj).__name__))

    def _dec_ref(self, data):
        """ Decode an object reference. """
        client = self.client()
        oid = data['id']
        obj = client.get_object(oid)
        if obj is None:
            obj = client.create_object(oid)
        return obj
