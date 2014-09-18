# -*- coding: utf-8 -*-

import time
import json
import email
import urllib
import urllib2


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

        for x in xrange(nr_retry + 1):
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
        for x in xrange(nr_retry + 1):
            code, body = self.put(path, {'text': lines})

            if isvalid(code, body):
                return True

            time.sleep(retry_interval)

        return False

    def generate(self, instance, nr_retry=0, retry_interval=0.2):
        def isvalid(code, body):
            if code != 200:
                return False
            if type(body) is not dict:
                return False
            if 'text' not in body:
                return False
            if 'score' not in body:
                return False
            if type(body['text']) is not unicode:
                return False
            if not isinstance(body['score'], (int, long, float)):
                return False
            return True

        path = '/'.join((self.PATH_PREFIX, instance))
        for x in xrange(nr_retry + 1):
            code, body = self.get(path)

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
        for x in xrange(nr_retry + 1):
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
        for x in xrange(nr_retry + 1):
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
        for x in xrange(nr_retry + 1):
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
        keys = urllib.quote(keys, safe='')
        path = '/'.join((self.PATH_PREFIX, instance, 'keys', keys))
        for x in xrange(nr_retry + 1):
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
        for x in xrange(nr_retry + 1):
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
                if not isinstance(body[x], (int, long, float)):
                    return False
            return True

        path = '/'.join((self.PATH_PREFIX, instance, 'stats'))
        for x in xrange(nr_retry + 1):
            code, body = self.get(path)

            if isvalid(code, body):
                return body

            time.sleep(retry_interval)

        return None
