import sys


if sys.version_info[0] == 2:
    collect_ignore=['client', 'integration']
elif sys.version_info[0] == 3:
    collect_ignore=['server']
else:
    raise Exception("Unexpected Python major version: {!r}".format(
        sys.version_info[0]))
