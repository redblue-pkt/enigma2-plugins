# -*- coding: utf-8 -*-
#
# http://voorloopnul.com/blog/a-python-netstat-in-less-than-100-lines-of-code/
#
# Changed by betonme
# Added netstat parameter
#  getstate, getuid, getpid   to improve performance
#  readable                   to get IP and port separated

from pwd import getpwuid
from os import readlink
from re import search
from glob import glob
from six import iteritems


PROC_TCP = "/proc/net/tcp"
STATE = {
    '01': 'ESTABLISHED',
    '02': 'SYN_SENT',
    '03': 'SYN_RECV',
    '04': 'FIN_WAIT1',
    '05': 'FIN_WAIT2',
    '06': 'TIME_WAIT',
    '07': 'CLOSE',
    '08': 'CLOSE_WAIT',
    '09': 'LAST_ACK',
    '0A': 'LISTEN',
    '0B': 'CLOSING'
}


def _load():
    ''' Read the table of tcp connections & remove header  '''
    with open(PROC_TCP, 'r') as f:
        content = f.readlines()
        content.pop(0)
    return content


def _hex2dec(s):
    return str(int(s, 16))


def _ip(s):
    ip = [(_hex2dec(s[6:8])), (_hex2dec(s[4:6])), (_hex2dec(s[2:4])), (_hex2dec(s[0:2]))]
    return '.'.join(ip)


def _remove_empty(array):
    return [x for x in array if x != '']


def _convert_ip_port(array):
    host, port = array.split(':')
    return _ip(host), _hex2dec(port)


def netstat(getstate=None, getuid=True, getpid=True, readable=True):
    '''
    Function to return a list with status of tcp connections at linux systems
    To get pid of all network process running on system, you must run this script
    as superuser
    '''
    getstate = [key for key, value in iteritems(STATE) if value == getstate]
    if getstate:
        getstate = getstate[0]

    content = _load()
    result = []
    for line in content:
        line_array = _remove_empty(line.split(' '))	 # Split lines and remove empty spaces.

        state = line_array[3]
        if getstate:
            # Filter states not equal getstate
            if state != getstate:
                continue
        state = STATE[state]

        l_host, l_port = _convert_ip_port(line_array[1])  # Convert ipaddress and port from hex to decimal.
        r_host, r_port = _convert_ip_port(line_array[2])
        tcp_id = line_array[0]
        if getuid:
            uid = getpwuid(int(line_array[7]))[0]	   # Get user from UID.
        else:
            uid = None
        inode = line_array[9]						   # Need the inode to get process pid.
        if getpid:
            pid = _get_pid_of_inode(inode)				  # Get pid prom inode.
            try:											# try read the process name.
                exe = readlink('/proc/' + pid + '/exe')
            except:
                exe = None
        else:
            pid = None
            exe = None

        if readable:
            nline = [tcp_id, uid, l_host + ':' + l_port, r_host + ':' + r_port, state, pid, exe]
        else:
            nline = [tcp_id, uid, l_host, l_port, r_host, r_port, state, pid, exe]
        result.append(nline)
    return result


def _get_pid_of_inode(inode):
    '''
    To retrieve the process pid, check every running process and look for one using
    the given inode.
    '''
    for item in glob('/proc/[0-9]*/fd/[0-9]*'):
        try:
            if search(inode, os.readlink(item)):
                return item.split('/')[2]
        except:
            pass
    return None
