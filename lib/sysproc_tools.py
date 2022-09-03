# IDE: PyCharm
# Project: aio_post_tools
# Path: lib
# File: sysproc_tools.py
# Contact: Semyon Mamonov <semyon.mamonov@gmail.com>
# Created by ox23 at 2022-08-18 (y-m-d) 12:09 PM


# Main intention of these functions is to support the question -
# How to create with random port and get used by soffice port
#
# Creation with random port (defined by system)
# $ soffice --headless --accept="socket,host=localhost,tcpNoDelay=1;urp;StarOffice.ComponentContext"
# $ soffice --headless --accept="socket,host=localhost,port=0,tcpNoDelay=1;urp;StarOffice.ComponentContext"
#
# $ netstat -pl --tcp
# (Not all processes could be identified, non-owned process info
#  will not be shown, you would have to be root to see it all.)
# Active Internet connections (only servers)
# Proto Recv-Q Send-Q Local Address           Foreign Address         State       PID/Program name
# .....
# tcp        0      0 localhost:42971         0.0.0.0:*               LISTEN      6552/soffice.bin
# .....
#
# ox23@DESKTOP-Q6MI4SE:~/PycharmProjects/aio_post_tools$ ps -ax | grep soffice
#    6552 pts/4    Sl+    0:00 /usr/lib/libreoffice/program/soffice.bin --headless --accept=socket,host=localhost,tcpNoDelay=1;urp;StarOffice.ComponentContext
#    6563 pts/2    S+     0:00 grep soffice
#
# Netstat - contains pid 6552/soffice.bin - same pid will returned by Popen or some else
# Also, same result can get
# thus,
#
# # https://pypi.org/project/psutil/
# import psutil
# # documentation https://psutil.readthedocs.io/en/latest/
# >>> psutil.net_connections()
# [pconn(fd=115, family=<AddressFamily.AF_INET: 2>, type=<SocketType.SOCK_STREAM: 1>, laddr=addr(ip='10.0.0.1', port=48776), raddr=addr(ip='93.186.135.91', port=80), status='ESTABLISHED', pid=1254),
#  pconn(fd=117, family=<AddressFamily.AF_INET: 2>, type=<SocketType.SOCK_STREAM: 1>, laddr=addr(ip='10.0.0.1', port=43761), raddr=addr(ip='72.14.234.100', port=80), status='CLOSING', pid=2987),
#  pconn(fd=-1, family=<AddressFamily.AF_INET: 2>, type=<SocketType.SOCK_STREAM: 1>, laddr=addr(ip='10.0.0.1', port=60759), raddr=addr(ip='72.14.234.104', port=80), status='ESTABLISHED', pid=None),
#  pconn(fd=-1, family=<AddressFamily.AF_INET: 2>, type=<SocketType.SOCK_STREAM: 1>, laddr=addr(ip='10.0.0.1', port=51314), raddr=addr(ip='72.14.234.83', port=443), status='SYN_SENT', pid=None)
#  ...]
#
# Next way
# All process information are under /proc/<pid>/net or /proc/net. For tcp protocol /proc/<pid>/net/tcp and so on
# about /proc file system and structure each of files - look https://man7.org/linux/man-pages/man5/procfs.5.html
# but it file contains inode instead pid and we need to resolve it
#
# ox23@DESKTOP-Q6MI4SE:~/PycharmProjects/aio_post_tools$ ls -l /proc/7575/fd/*
# ....
# lrwx------ 1 ox23 ox23 64 Aug 17 16:21 /proc/7575/fd/12 -> 'socket:[310036]'
# ....

import re
import socket
import sys

from pathlib import Path

TCP_STATE = {'01': 'ESTABLISHED', '02': 'SYN_SENT', '03': 'SYN_RECV', '04': 'FIN_WAIT1', '05': 'FIN_WAIT2',
             '06': 'TIME_WAIT', '07': 'CLOSE', '08': 'CLOSE_WAIT', '09': 'LAST_ACK', '0A': 'LISTEN',
             '0B': 'CLOSING'}


def get_socket_inodes(pid: int) -> list[int]:
    result = []
    rc = re.compile(r'socket:\[(?P<inode>\d+)\]')
    pfd = Path(f'/proc/{pid}/fd')
    if not pfd.is_dir():
        raise FileExistsError(f'Process {pid} is not ran yet. Directory {pfd} does not exists')
    for f in pfd.iterdir():
        if f.is_symlink():
            m = rc.match(str(f.readlink()))  # f.readlink() -> 'socket:[369865]'
            if m:
                sinode = m.group('inode')
                result.append(int(sinode))
    return result


def get_net_info(file, test_calback=None) -> list[tuple[tuple[str, int], tuple[str, int], str, int]]:
    """
    It returns info about local addresses.
    test_calback takes 3 parameters:
        1 - 2-tuple (bytes that compatible with socket.inet_aton and socket.inet_ntoa, port as integer)
        2 - 2-tuple (bytes that compatible with socket.inet_aton and socket.inet_ntoa, port as integer)
        3 - string (2 char) that compatible witn TCP_STATE
        4 - inode as integer

    :param file:
    :param test_calback: if None or returns True result in human readable view will be added to result
    :return:
    """
    res = []
    with open(file, 'r') as fd:
        header = fd.readline()

        # we need indexes 1-local_address + 3-state + 9-inode
        def str_to_bytes(address_ip) -> tuple[bytes, int]:
            sa, sp = address_ip.split(':')
            return int(sa, 16).to_bytes(4, sys.byteorder), int(sp, 16)

        while line := fd.readline():
            parts = line.split()
            la, ra, st, i = str_to_bytes(parts[1]), str_to_bytes(parts[2]), parts[3], int(parts[9])
            if test_calback is None or test_calback(la, ra, st, i):
                res.append(((socket.inet_ntoa(la[0]), la[1]), (socket.inet_ntoa(ra[0]), ra[1]), TCP_STATE[st], i))
    return res


def pid_to_address(pid, info='tcp'):
    """
    Returns list of 3-tuples
        0 - 2-tuple (address_ip:str, port:int)
        1 - Current status: str (value from TCP_STATE)
        3 - inode: int

    :param pid: int
    :param info: str default 'tcp'
    :return: list tcp/ip information related with pid
    """
    pfd = Path(f'/proc/{pid}/net/{info}')
    if not pfd.is_file():
        raise FileExistsError(f'Process {pid} is not ran yet. File {pfd} does not exists')

    osocks = get_socket_inodes(pid)
    if osocks:
        osocks = get_net_info(pfd, lambda la, ra, st, i: i in osocks)

    return osocks


def address_info(address: tuple[str, int] = None, info: str = 'tcp'):
    pfd = Path(f'/proc/net/{info}')
    if not pfd.is_file():
        raise FileExistsError(f'File {pfd} does not exists')

    baddr = None
    if address is not None:
        baddr = (socket.inet_aton(socket.gethostbyname(address[0])), address[1])

    def test_callback(bla: tuple[bytes, int], bra: tuple[bytes, int], st: str, inode: int):
        return baddr is None or baddr == bla

    return get_net_info(pfd, test_callback)


def get_local_ips(info: str = 'tcp', keep_unknown=True):
    """
        Will returns active local ip addresses
        Result can have 0.0.0.0 ip address because it was used in system,
        but it is not desirable. By default it will return.
        I try to resolve it via socket.gethostbyaddr(addr) with catching socket.herror.
        Thus, if keep_unknown=False (not default) it will use socket.gethostbyaddr(addr)
        Probably, it has side effect when hosts is not right configured in the system.
        For example, socket.gethostbyaddr('127.0.0.5') - will raise socket.herror

    :param info:
    :param keep_unknown:
    :return:
    """

    res = set()
    for net_info in address_info(info=info):
        addr = net_info[0][0]
        try:
            if not keep_unknown:
                socket.gethostbyaddr(addr)
        except socket.herror as exc:
            pass
        else:
            res.add(addr)

    return res


if __name__ == '__main__':
    print(pid_to_address(7416))
    print(address_info(('localhost', 2002)))
    print(address_info())
    print(get_local_ips())




