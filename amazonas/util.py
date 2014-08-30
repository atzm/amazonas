# -*- coding: utf-8 -*-

import os
import sys
import json
import shlex
import urllib2
import datetime


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
    if type(data) is unicode:
        data = data.encode(encoding)
    return [unicode(c, encoding) for c in shlex.split(data)]


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


class HTTPClient(object):
    def __init__(self, host, port):
        self.host = str(host)
        self.port = int(port)

    def url(self, path):
        return str(''.join(('http://', self.host, ':', str(self.port), path)))

    def get(self, path):
        return self.request('GET', path)

    def put(self, path, body):
        return self.request('PUT', path, body)

    def post(self, path, body):
        return self.request('POST', path, body)

    def request(self, method, path, body=None, headers={}):
        if body is not None:
            body = json.dumps(body, ensure_ascii=False).encode('utf-8')
            headers = headers.copy()
            headers.update({'Content-Type': 'application/json; charset=UTF-8'})

        try:
            code, info, body = self._request(method, path, body, headers)
            ctype = info.getheader('content-type', '')
            if ctype.startswith('application/json'):
                return code, json.loads(body)
            return code, body
        except urllib2.HTTPError as e:
            return e.getcode(), ''

    def _request(self, method, path, body, headers={}):
        url = self.url(path)
        req = urllib2.Request(url, body, headers)
        req.get_method = lambda: str(method)
        obj = urllib2.urlopen(req)
        return obj.getcode(), obj.info(), obj.read()
