# -*- coding: utf-8 -*-

from __future__ import print_function

import os
import sys
import shlex
import datetime

from . import http
from . import jlyrics

import six

__all__ = [
    'compat',
    'http',
    'jlyrics',
    'abspath',
    'daemonize',
    'split',
    'time_in',
    'formathelp',
]


def abspath(path):
    return os.path.abspath(os.path.expanduser(path))


def daemonize(chdir='/', close=True):
    if os.fork() > 0:
        sys.exit(0)

    os.setsid()

    if os.fork() > 0:
        sys.exit(0)

    if chdir:
        os.chdir(chdir)

    if close:
        os.umask(0)
        os.close(0)
        os.close(1)
        os.close(2)
        sys.__stdin__ = sys.stdin = open(os.devnull)
        sys.__stdout__ = sys.stdout = open(os.devnull, 'w')
        sys.__stderr__ = sys.stderr = open(os.devnull, 'w')


def split(data, encoding='utf-8'):
    if six.PY2:  # shlex cannot split unicode w/o correct encoding in python2
        data = data.encode(encoding, 'replace')
        return [c.decode(encoding, 'replace') for c in shlex.split(data)]
    return shlex.split(data)


def time_in(time_str):
    now = datetime.datetime.today()
    date = '%s/%s/%s' % (now.year, now.month, now.day)

    for t in split(time_str):
        start, end = t.split('-', 1)

        start = datetime.datetime.strptime(
            '%s %s' % (date, start), '%Y/%m/%d %H:%M')
        end = datetime.datetime.strptime(
            '%s %s' % (date, end), '%Y/%m/%d %H:%M')

        if start <= now <= end:
            return True

    return False


def formathelp(cmdlist):
    io = six.StringIO()

    maxlen = max(len(n) for n in list(zip(*cmdlist))[0])
    head_fmt = ' '.join(('%%-%ds' % maxlen, '%s'))
    body_fmt = ' '.join((' ' * maxlen, '%s'))

    for n, m in cmdlist:
        if not m.__doc__:
            print(n, end='\n\n', file=io)
            continue

        doc = m.__doc__.strip()

        if not doc:
            print(n, end='\n\n', file=io)
            continue

        lines = [s.strip() for s in doc.splitlines()]

        print(head_fmt % (n, lines[0]), file=io)

        for line in lines[1:]:
            print(body_fmt % line, file=io)

        print(file=io)

    return io.getvalue().strip()
