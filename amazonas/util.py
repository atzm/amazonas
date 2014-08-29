# -*- coding: utf-8 -*-

import json
import shlex
import urllib2
import datetime

import db
import parser
import config


def loadmodules():
    for m in config.getlist('module', 'parsers'):
        parser.loadmodule(m)

    for m in config.getlist('module', 'dbs'):
        db.loadmodule(m)


def getparser(type_, instance):
    d = config.as_dict('parser:%s:%s' % (type_, instance))
    c = parser.getclass(type_, d.pop('type'))
    return c(**d)


def getdb(type_, instance):
    d = config.as_dict('db:%s:%s' % (type_, instance))
    c = db.getclass(type_, d.pop('type'))
    return c(**d)


def time_in(time_str):
    now = datetime.datetime.today()
    date = '%s/%s/%s' % (now.year, now.month, now.day)

    for t in shlex.split(time_str.encode('utf-8')):
        start, end = t.split('-', 1)

        start = datetime.datetime.strptime(
            '%s %s' % (date, start), '%Y/%m/%d %H:%M')
        end = datetime.datetime.strptime(
            '%s %s' % (date, end), '%Y/%m/%d %H:%M')

        if start <= now <= end:
            return True

    return False


def config_enabled(sect):
    if not config.has_section(sect):
        return False

    if not config.getboolean(sect, 'enable'):
        return False

    try:
        time_ = config.get(sect, 'time')
        if time_ and not time_in(time_):
            return False
    except:
        return False

    return True


class HTTPClient(object):
    def __init__(self, host, port):
        self.host = host
        self.port = port

    def url(self, path):
        return ''.join(('http://', self.host, ':', str(self.port), path))

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
