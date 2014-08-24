# -*- coding: utf-8 -*-

import sys
import json
import fcntl
import shlex
import getopt
import urllib2
import inspect
import readline
import traceback


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


class Command(object):
    PATH_PREFIX = '/v0.1'

    def __init__(self, instance, host, port):
        self.instance = instance
        self.client = HTTPClient(host, port)

    def cmd(self, cmd):
        return getattr(self, 'cmd_' + cmd, None)

    def path(self, path=''):
        p = '/'.join((self.PATH_PREFIX, self.instance))
        return ''.join((p, path))

    def cmd_print(self, *args):
        code, body = self.client.get(self.path())
        if code == 200 and body['score'] is not None:
            print('%s [%f]' % (body['text'], body['score']))
        else:
            print('[failed]')
    cmd_p = cmd_print

    def cmd_learn(self, *args):
        opts, args = getopt.gnu_getopt(args, 'c:')

        encode = 'utf-8'
        for opt, optarg in opts:
            if opt == '-c':
                encode = optarg

        if not args:
            print('syntax: learn [-c encoding] <file>')
            return

        with open(args[0]) as fp:
            fcntl.flock(fp.fileno(), fcntl.LOCK_SH)
            text = [unicode(line.strip(), encode) for line in fp]

        code, _ = self.client.put(self.path(), {'text': text})
        if code == 204:
            print('[success]')
        else:
            print('[failed]')
    cmd_l = cmd_learn

    def cmd_maps(self, *args):
        if not args:
            print('syntax: maps <key1> <key2> ...')
            return

        code, body = self.client.post(self.path('/maps'), {'key': args})
        if code == 200:
            for v in body.get('values', []):
                print(v)
        else:
            print('[failed]')
    cmd_m = cmd_maps

    def cmd_keys(self, *args):
        code, body = self.client.get(self.path('/keys'))
        if code == 200:
            for k in body.get('keys', []):
                json.dump(k, sys.stdout, ensure_ascii=False)
                sys.stdout.write('\n')
        else:
            print('[failed]')
    cmd_k = cmd_keys

    def cmd_entrypoints(self, *args):
        code, body = self.client.get(self.path('/entrypoints'))
        if code == 200:
            for k in body.get('entrypoints', []):
                print(k)
        else:
            print('[failed]')
    cmd_e = cmd_entrypoints

    def cmd_recent(self, *args):
        code, body = self.client.get(self.path('/recents'))
        if code == 200:
            for k in body.get('recents', []):
                print(k)
        else:
            print('[failed]')
    cmd_r = cmd_recent

    def cmd_stat(self, *args):
        code, body = self.client.get(self.path('/stats'))
        if code == 200:
            print('score threshold: %f' % body['threshold'])
            print('markov keys:     %d' % body['keys'])
            print('entrypoints:     %d' % body['entrypoints'])
        else:
            print('[failed]')
    cmd_s = cmd_stat

    def cmd_help(self, *args):
        for n, m in inspect.getmembers(self, inspect.ismethod):
            if n.startswith('cmd_'):
                print(n[4:])
    cmd_h = cmd_help


def main():
    fsenc = sys.getfilesystemencoding()
    host = 'localhost'
    port = 8349
    opts, args = getopt.gnu_getopt(sys.argv[1:], 'h:p:')

    for opt, optarg in opts:
        if opt == '-h':
            host = optarg
        elif opt == '-p':
            port = int(optarg)
            assert(0 <= port <= 65535)

    if not args:
        raise SystemExit('syntax: %s [-h host] [-p port] <instance>' %
                         sys.argv[0])

    cmd = Command(args[0], host, port)
    readline.parse_and_bind('tab: complete')
    while True:
        try:
            line = raw_input('>>> ').strip()
        except EOFError:
            sys.stdout.write('\nbye ;)\n')
            break

        if not line:
            continue

        try:
            cmdline = [unicode(c, fsenc) for c in shlex.split(line)]
            func = cmd.cmd(cmdline[0])

            if not callable(func):
                print('command not found: %s' % cmdline[0])
                continue

            func(*cmdline[1:])
        except:
            traceback.print_exc()


if __name__ == '__main__':
    main()
