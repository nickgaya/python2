import contextlib

import pytest

from python2.client import Py2Error, Py2Object, Python2


def pytest_addoption(parser):
    parser.addoption("--python2", default="python2",
                     help="Python 2 executable for client to use")


@pytest.fixture
def py2command():
    return pytest.config.getoption("--python2")


@pytest.fixture
def py2(py2command):
    with Python2(py2command, logging_basic={'level': 'DEBUG'}) as session:
        yield session


class Helpers:
    def __init__(self, py2):
        self.py2 = py2

    @staticmethod
    def assert_py2_eq(obj, expected):
        assert type(obj) is Py2Object
        assert obj == expected

    @staticmethod
    def assert_types_match(spec, actual):
        if type(spec) is type:
            assert type(actual) is spec
        else:
            assert type(actual) is type(spec)

            if type(spec) in (list, tuple):
                assert len(spec) == len(actual)
                for sx, ax in zip(spec, actual):
                    Helpers.assert_types_match(sx, ax)
            else:
                # For now, this function just support lists/tuples
                raise TypeError("Unsupported spec type: {}".format(
                    type(spec).__name__))

    @contextlib.contextmanager
    def py2_raises(self, p2e):
        with pytest.raises(Py2Error) as einfo:
            yield einfo

        assert self.py2.isinstance(einfo.value.exception, p2e)


@pytest.fixture
def helpers(py2):
    return Helpers(py2)
