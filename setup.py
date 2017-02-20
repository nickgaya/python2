from setuptools import find_packages, setup


__version__ = '1.2'


setup(
    name='python2',
    version=__version__,
    author="Nicholas Gaya",
    author_email="nickgaya@users.noreply.github.com",
    description="A library for running Python 2 code from a Python 3 "
                "application.",
    url="https://github.com/nickgaya/python2",
    download_url="https://github.com/nickgaya/python2/tarball/{}".format(
        __version__),
    license="MIT",
    packages=find_packages(),
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
    keywords=['python2', 'legacy', 'compatibility'],
)
