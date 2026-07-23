"""Windows shim for missing POSIX resource module in Home Assistant development environment."""

RLIMIT_NOFILE = 7


def getrlimit(resource):
    return (1024, 2048)


def setrlimit(resource, limits):
    pass
