# -*- coding: utf-8 -*-

import time
import json
import email
import contextlib

from . import compat

import six

from lxml import html
from six.moves import urllib, range


def getmessage(info):
    if hasattr(info, 'get_content_type'):
        return info
    return email.message_from_string(''.join(info.headers))


class HTML(object):
    def __init__(self, url, timeout, headers={}):
        self.url = url
        self.timeout = timeout
        self.headers = headers
        self.content = None

    @staticmethod
    def getparser(f):
        msg = getmessage(f.info())
        encoding = msg.get_content_charset() or None
        return html.HTMLParser(encoding=encoding)

    @property
    def root(self):
        if not self.content:
            req = urllib.request.Request(url=self.url, headers=self.headers)
            arg = {'url': req, 'timeout': self.timeout}
            with contextlib.closing(urllib.request.urlopen(**arg)) as f:
                self.content = html.parse(f, self.getparser(f))
        return self.content.getroot()

    def getcontent(self, xpath):
        try:
            p = self.root.xpath(xpath)[0]
            return dict(text_content=p.text_content().strip(), **p.attrib)
        except Exception:
            return {}


class HTTPClient(object):
    def __init__(self, host, port, https=False, charset='utf-8'):
        self.host = str(host)
        self.port = str(port)
        self.https = bool(https)
        self.charset = str(charset)
        self.content_handler = {}
        self.set_content_handler('application/json', json.loads)

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
            return code, self._parsebody(getmessage(info), body)
        except urllib.error.HTTPError as e:
            return e.getcode(), ''

    def _request(self, method, url, body, headers={}):
        req = urllib.request.Request(url, body, headers)
        req.get_method = lambda: str(method)
        with contextlib.closing(urllib.request.urlopen(req)) as f:
            return f.getcode(), f.info(), f.read()

    def _parsebody(self, msg, body):
        ctype = msg.get_content_type()
        charset = msg.get_content_charset() or self.charset
        body = compat.ucode(body, charset, 'replace')
        return self.get_content_handler(ctype)(body)

    def url(self, path, query={}):
        if self.https:
            scheme = 'https'
            default_port = '443'
        else:
            scheme = 'http'
            default_port = '80'

        if default_port == self.port:
            parts = [scheme, '://', self.host, path]
        else:
            parts = [scheme, '://', self.host, ':', self.port, path]

        if query:
            parts.extend(['?', self.querystring(query)])

        return str(''.join(parts))

    def querystring(self, query):
        q = {}
        for k, v in six.iteritems(query):
            if six.PY2 and compat.isucode(k):
                k = k.encode(self.charset)
            if six.PY2 and compat.isucode(v):
                v = v.encode(self.charset)
            q[k] = v
        return urllib.parse.urlencode(q)


class GoogleClient(HTTPClient):
    def __init__(self, **kw):
        super(GoogleClient, self).__init__('www.google.com', 443, True, **kw)
        self.set_content_handler('text/javascript', json.loads)

    def complete(self, query, locale='en', nr_retry=0, retry_interval=0.2):
        def isvalid(code, body):
            if code != 200:
                return False
            if type(body) is not list:
                return False
            if len(body) < 2:
                return False
            if type(body[1]) is not list:
                return False
            return True

        for x in range(nr_retry + 1):
            code, body = self.get('/complete/search',
                                  client='firefox', hl=locale, q=query)

            if isvalid(code, body):
                return body[1]

            time.sleep(retry_interval)

        return None


class APIClientV01(HTTPClient):
    PATH_PREFIX = '/v0.1'

    def learn(self, instance, lines, nr_retry=0, retry_interval=0.2):
        def isvalid(code, body):
            if code != 204:
                return False
            return True

        path = '/'.join((self.PATH_PREFIX, instance))
        for x in range(nr_retry + 1):
            code, body = self.put(path, {'text': lines})

            if isvalid(code, body):
                return True

            time.sleep(retry_interval)

        return False

    def generate(self, instance, entrypoint=None,
                 nr_retry=0, retry_interval=0.2):
        def isvalid(code, body):
            if code != 200:
                return False
            if type(body) is not dict:
                return False
            if 'text' not in body:
                return False
            if 'score' not in body:
                return False
            if not compat.isucode(body['text']):
                return False
            if not compat.isnum(body['score']):
                return False
            return True

        path = '/'.join((self.PATH_PREFIX, instance))
        query = {'entrypoint': entrypoint} if entrypoint else {}
        for x in range(nr_retry + 1):
            code, body = self.get(path, **query)

            if isvalid(code, body):
                return body['score'], body['text']

            time.sleep(retry_interval)

        return None, None

    def entries(self, instance, nr_retry=0, retry_interval=0.2):
        def isvalid(code, body):
            if code != 200:
                return False
            if type(body) is not dict:
                return False
            if 'keys' not in body:
                return False
            if type(body['keys']) is not list:
                return False
            return True

        path = '/'.join((self.PATH_PREFIX, instance, 'entrypoints'))
        for x in range(nr_retry + 1):
            code, body = self.get(path)

            if isvalid(code, body):
                return body['keys']

            time.sleep(retry_interval)

        return None

    def recent_entries(self, instance, nr_retry=0, retry_interval=0.2):
        def isvalid(code, body):
            if code != 200:
                return False
            if type(body) is not dict:
                return False
            if 'keys' not in body:
                return False
            if type(body['keys']) is not list:
                return False
            return True

        path = '/'.join((self.PATH_PREFIX, instance, 'recent-entrypoints'))
        for x in range(nr_retry + 1):
            code, body = self.get(path)

            if isvalid(code, body):
                return body['keys']

            time.sleep(retry_interval)

        return None

    def keys(self, instance, nr_retry=0, retry_interval=0.2):
        def isvalid(code, body):
            if code != 200:
                return False
            if type(body) is not dict:
                return False
            if 'keys' not in body:
                return False
            if type(body['keys']) is not list:
                return False
            return True

        path = '/'.join((self.PATH_PREFIX, instance, 'keys'))
        for x in range(nr_retry + 1):
            code, body = self.get(path)

            if isvalid(code, body):
                return body['keys']

            time.sleep(retry_interval)

        return None

    def values(self, instance, keys, nr_retry=0, retry_interval=0.2):
        def isvalid(code, body):
            if code != 200:
                return False
            if type(body) is not dict:
                return False
            if 'values' not in body:
                return False
            if type(body['values']) is not list:
                return False
            return True

        keys = json.dumps(keys, ensure_ascii=False).encode('utf-8')
        keys = urllib.parse.quote(keys, safe='')
        path = '/'.join((self.PATH_PREFIX, instance, 'keys', keys))
        for x in range(nr_retry + 1):
            code, body = self.get(path)

            if isvalid(code, body):
                return body['values']

            time.sleep(retry_interval)

        return None

    def histories(self, instance, nr_retry=0, retry_interval=0.2):
        def isvalid(code, body):
            if code != 200:
                return False
            if type(body) is not dict:
                return False
            if 'histories' not in body:
                return False
            if type(body['histories']) is not list:
                return False
            return True

        path = '/'.join((self.PATH_PREFIX, instance, 'histories'))
        for x in range(nr_retry + 1):
            code, body = self.get(path)

            if isvalid(code, body):
                return body['histories']

            time.sleep(retry_interval)

        return None

    def stats(self, instance, nr_retry=0, retry_interval=0.2):
        def isvalid(code, body):
            if code != 200:
                return False
            if type(body) is not dict:
                return False
            for x in ('threshold', 'maxchain', 'keys', 'entrypoints'):
                if x not in body:
                    return False
                if not compat.isnum(body[x]):
                    return False
            return True

        path = '/'.join((self.PATH_PREFIX, instance, 'stats'))
        for x in range(nr_retry + 1):
            code, body = self.get(path)

            if isvalid(code, body):
                return body

            time.sleep(retry_interval)

        return None
