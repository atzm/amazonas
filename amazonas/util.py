# -*- coding: utf-8 -*-

import os
import sys
import json
import shlex
import urllib
import urllib2
import datetime


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
    def __init__(self, host, port, https=False, charset='utf-8'):
        self.host = str(host)
        self.port = str(port)
        self.https = bool(https)
        self.charset = str(charset)

    def querystring(self, query):
        q = {}
        for k, v in query.iteritems():
            if type(k) == unicode:
                k = k.encode(self.charset)
            if type(v) == unicode:
                v = v.encode(self.charset)
            q[k] = v
        return urllib.urlencode(q)

    def url(self, path, query={}):
        if self.https:
            scheme = 'https'
        else:
            scheme = 'http'

        parts = [scheme, '://', self.host, ':', self.port, path]

        if query:
            parts.extend(['?', self.querystring(query)])

        return str(''.join(parts))

    def get(self, path, **query):
        return self.request('GET', path, query=query)

    def put(self, path, body, **query):
        return self.request('PUT', path, body=body, query=query)

    def post(self, path, body, **query):
        return self.request('POST', path, body=body, query=query)

    def request(self, method, path, body=None, query={}, headers={}):
        if body is not None:
            body = json.dumps(body, ensure_ascii=False).encode(self.charset)
            ctype = 'application/json; charset=%s' % self.charset.upper()
            headers = headers.copy()
            headers['Content-Type'] = ctype

        try:
            url = self.url(path, query)
            code, info, body = self._request(method, url, body, headers)
            ctype = info.getheader('content-type', '')
            if ctype.startswith('application/json'):
                return code, json.loads(body)
            return code, body
        except urllib2.HTTPError as e:
            return e.getcode(), ''

    def _request(self, method, url, body, headers={}):
        req = urllib2.Request(url, body, headers)
        req.get_method = lambda: str(method)
        obj = urllib2.urlopen(req)
        return obj.getcode(), obj.info(), obj.read()
