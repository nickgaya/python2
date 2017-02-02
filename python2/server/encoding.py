import weakref

from python2.encoding import BaseEncoder


class ServerEncoder(BaseEncoder):
    """ Python 2 server object encoder. """

    def __init__(self, server):
        self.server = weakref.ref(server)

    def _enc_ref(self, obj):
        """ Encode an object as a reference. """
        self.server().cache_add(obj)
        return dict(type='ref', id=id(obj))

    def _dec_ref(self, data):
        """ Decode an object reference. """
        return self.server().cache_get(data['id'])
