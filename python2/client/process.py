import contextlib
import os
import subprocess

from python2.client.client import Py2Client


class Python2:
    """
    Object representing a running Python 2 instance.

    Initializing a Python2 object spawns a Python 2 subprocess.  To terminate
    the subprocess, use the `Python2.shutdown()` method.  A Python2 object may
    be used as a context manager to automatically shut down when the context is
    exited.
    """

    def __init__(self, executable='python'):
        """
        Initialize a Python2 instance.

        :param executable: Python 2 executable to use (default `'python'`).
        """
        with contextlib.ExitStack() as stack:
            # Create two pipes for communication with the Python 2 server.
            # We need to close the server end of each pipe after spawning the
            # subprocess.  We only need to close the client end if an
            # exception is raised during initialization.

            cread, swrite = os.pipe()
            stack.push(_on_error(os.close, cread))
            stack.callback(os.close, swrite)

            sread, cwrite = os.pipe()
            stack.callback(os.close, sread)
            stack.push(_on_error(os.close, cwrite))

            self._proc = subprocess.Popen(
                [executable, '-m', 'python2.server',
                 '--in', str(sread), '--out', str(swrite)],
                pass_fds=(sread, swrite),
                start_new_session=True,  # Avoid signal issues
                universal_newlines=False)

            stack.push(_on_error(_kill, self._proc))

            self._client = Py2Client(os.fdopen(cread, 'rb'),
                                     os.fdopen(cwrite, 'wb'))

    def ping(self):
        """ Attempt to communicate with the Python 2 process. """
        return self._client.do_command('ping')

    def project(self, object):
        """ Project an object into Python 2. """
        return self._client.do_command('project', object=object)

    def lift(self, object):
        """ Lift an object from Python 2 to 3. """
        return self._client.do_command('lift', object=object)

    def deeplift(self, object):
        """ Recursively lift an object from Python 2 to 3. """
        return self._client.do_command('deeplift', object=object)

    def __getattr__(self, name):
        """ Access Python 2 builtins. """
        # True/False/None are keywords in Python 3
        if name in ('None_', 'True_', 'False_'):
            name = name[:-1]
        return self._client.do_command('builtin', name=name)

    def shutdown(self):
        """ Shut down the Python 2 process. """
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
