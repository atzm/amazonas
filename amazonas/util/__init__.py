# -*- coding: utf-8 -*-

from __future__ import print_function

import os
import sys
import time
import json
import email
import shlex
import urllib
import urllib2
import datetime
import cStringIO

from . import jlyrics


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


def split(data):
    data = data.encode('utf-8', 'replace')
    return [unicode(c, 'utf-8', 'replace') for c in shlex.split(data)]


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
    io = cStringIO.StringIO()

    maxlen = max(len(n) for n in zip(*cmdlist)[0])
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


def gcomplete(query, locale='en', nr_retry=0, retry_interval=0.2):
    client = HTTPClient('www.google.com', 443, True)

    for x in xrange(nr_retry + 1):
        code, body = client.get('/complete/search', hl=locale,
                                client='firefox', q=query)
        if code == 200:
            break

        time.sleep(retry_interval)
    else:
        return []

    if type(body) is not list:
        return []

    if len(body) < 2:
        return []

    if type(body[1]) is not list:
        return []

    return body[1]


class HTTPClient(object):
    def __init__(self, host, port, https=False, charset='utf-8'):
        self.host = str(host)
        self.port = str(port)
        self.https = bool(https)
        self.charset = str(charset)
        self.content_handler = {}

        self.set_content_handler('application/json', json.loads)
        self.set_content_handler('text/javascript',  json.loads)

    def set_content_handler(self, ctype, func):
        self.content_handler[ctype] = func

    def get_content_handler(self, ctype, default=lambda x: x):
        return self.content_handler.get(ctype, default)

    def del_content_handler(self, ctype):
        self.content_handler.pop(ctype, None)

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
            return code, self._parsebody(''.join(info.headers), body)
        except urllib2.HTTPError as e:
            return e.getcode(), ''

    def _request(self, method, url, body, headers={}):
        req = urllib2.Request(url, body, headers)
        req.get_method = lambda: str(method)
        obj = urllib2.urlopen(req)
        return obj.getcode(), obj.info(), obj.read()

    def _parsebody(self, strhdr, body):
        message = email.message_from_string(strhdr)
        ctype = message.get_content_type()
        charset = message.get_content_charset() or self.charset
        body = unicode(body, charset, 'replace')
        return self.get_content_handler(ctype)(body)

    def url(self, path, query={}):
        if self.https:
            scheme = 'https'
        else:
            scheme = 'http'

        parts = [scheme, '://', self.host, ':', self.port, path]

        if query:
            parts.extend(['?', self.querystring(query)])

        return str(''.join(parts))

    def querystring(self, query):
        q = {}
        for k, v in query.iteritems():
            if type(k) == unicode:
                k = k.encode(self.charset)
            if type(v) == unicode:
                v = v.encode(self.charset)
            q[k] = v
        return urllib.urlencode(q)
