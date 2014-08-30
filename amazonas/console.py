# -*- coding: utf-8 -*-

import os
import sys
import json
import fcntl
import getopt
import urllib
import inspect
import readline
import traceback

from . import util


class Command(object):
    PATH_PREFIX = '/v0.1'

    def __init__(self, instance, host, port):
        self.instance = instance
        self.client = util.HTTPClient(host, port)

    def cmd(self, cmd):
        return getattr(self, 'cmd_' + cmd, None)

    def path(self, path=''):
        p = '/'.join((self.PATH_PREFIX, self.instance))
        return ''.join((p, path))

    def cmd_quit(self, *args):
        raise StopIteration()
    cmd_q = cmd_quit

    def cmd_print(self, *args):
        code, body = self.client.get(self.path())
        if code == 200:
            print('%s [%f]' % (body['text'], body['score']))
        else:
            print('[failed: %d]' % code)
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
            print('[failed: %d]' % code)
    cmd_l = cmd_learn

    def cmd_maps(self, *args):
        if not args:
            print('syntax: maps <key1> <key2> ...')
            return

        keys = json.dumps(args, ensure_ascii=False).encode('utf-8')
        path = self.path('/'.join(('/keys', urllib.quote(keys, safe=''))))
        code, body = self.client.get(path)
        if code == 200:
            for v in body.get('values', []):
                print(v)
        else:
            print('[failed: %d]' % code)
    cmd_m = cmd_maps

    def cmd_keys(self, *args):
        code, body = self.client.get(self.path('/keys'))
        if code == 200:
            for k in body.get('keys', []):
                json.dump(k, sys.stdout, ensure_ascii=False)
                sys.stdout.write('\n')
        else:
            print('[failed: %d]' % code)
    cmd_k = cmd_keys

    def cmd_entrypoints(self, *args):
        code, body = self.client.get(self.path('/entrypoints'))
        if code == 200:
            for k in body.get('entrypoints', []):
                print(k)
        else:
            print('[failed: %d]' % code)
    cmd_e = cmd_entrypoints

    def cmd_recent(self, *args):
        code, body = self.client.get(self.path('/recents'))
        if code == 200:
            for k in body.get('recents', []):
                print(k)
        else:
            print('[failed: %d]' % code)
    cmd_r = cmd_recent

    def cmd_stat(self, *args):
        code, body = self.client.get(self.path('/stats'))
        if code == 200:
            print('score threshold: %f' % body['threshold'])
            print('markov keys:     %d' % body['keys'])
            print('entrypoints:     %d' % body['entrypoints'])
        else:
            print('[failed: %d]' % code)
    cmd_s = cmd_stat

    def cmd_help(self, *args):
        for n, m in inspect.getmembers(self, inspect.ismethod):
            if n.startswith('cmd_'):
                print(n[4:])
    cmd_h = cmd_help


def main():
    def usage():
        raise SystemExit('syntax: %s [-h host] [-p port] <instance>' %
                         os.path.basename(sys.argv[0]))

    fsenc = sys.getfilesystemencoding()
    host = 'localhost'
    port = 8349

    try:
        opts, args = getopt.gnu_getopt(sys.argv[1:], 'h:p:')
    except getopt.error:
        usage()

    for opt, optarg in opts:
        if opt == '-h':
            host = optarg
        elif opt == '-p':
            port = int(optarg)
            assert(0 <= port <= 65535)

    if not args:
        usage()

    cmd = Command(args[0], host, port)
    readline.parse_and_bind('tab: complete')

    while True:
        try:
            line = raw_input('>>> ').strip()

            if not line:
                continue

            cmdline = util.split(line, fsenc)
            func = cmd.cmd(cmdline[0])

            if not callable(func):
                print('command not found: %s' % cmdline[0])
                continue

            func(*cmdline[1:])

        except EOFError:
            sys.stdout.write('\nbye ;)\n')
            break

        except StopIteration:
            sys.stdout.write('bye ;)\n')
            break

        except:
            traceback.print_exc()


if __name__ == '__main__':
    main()
