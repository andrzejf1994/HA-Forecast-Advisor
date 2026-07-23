"""Windows shim for missing POSIX fcntl module in Home Assistant development environment."""

FASYNC = 8192
FD_CLOEXEC = 1
DN_ACCESS = 1
DN_ACTION = 1
DN_ATTRIB = 1
DN_CREATE = 1
DN_DELETE = 1
DN_MODIFY = 1
DN_MULTISHOT = 2147483648
DN_RENAME = 1
F_DUPFD = 0
F_DUPFD_CLOEXEC = 1030
F_GETFD = 1
F_GETFL = 3
F_GETLEASE = 1026
F_GETLK = 5
F_GETOWN = 9
F_GETSIG = 10
F_NOTIFY = 1026
F_RDLCK = 0
F_SETFD = 2
F_SETFL = 4
F_SETLEASE = 1024
F_SETLK = 6
F_SETLKW = 7
F_SETOWN = 8
F_SETSIG = 11
F_UNLCK = 2
F_WRLCK = 1
LOCK_EX = 2
LOCK_NB = 4
LOCK_SH = 1
LOCK_UN = 8


def fcntl(fd, cmd, arg=0):
    return 0


def ioctl(fd, request, arg=0, mutate_flag=True):
    return 0


def flock(fd, operation):
    return 0


def lockf(fd, cmd, len=0, start=0, whence=0):
    return 0
