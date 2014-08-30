# -*- coding: utf-8 -*-

from __future__ import print_function

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
    FILE = sys.stdout

    def complete(self, text, state):
        candidates = [n for n, m in self.itercmd() if n.startswith(text)]
        try:
            return candidates[state]
        except:
            return None

    def print(self, *args, **kwargs):
        print(file=self.FILE, *args, **kwargs)

    def run(self, cmdline):
        cmd = self.getcmd(cmdline[0])
        if callable(cmd):
            cmd(*cmdline[1:])
        else:
            self.print('command not found: %s' % cmdline[0])

    def getcmd(self, name):
        return getattr(self, 'cmd_' + name, None)

    def itercmd(self):
        for n, m in inspect.getmembers(self, inspect.ismethod):
            if n.startswith('cmd_'):
                yield n[4:], m

    def printhelp(self, cmd_list=None):
        if cmd_list is None:
            cmd = inspect.currentframe().f_back.f_code.co_name[4:]
            cmd_list = [(cmd, self.getcmd(cmd))]

        maxlen = max(len(n) for n in zip(*cmd_list)[0])
        head_fmt = ' '.join(('%%-%ds' % maxlen, '%s'))
        body_fmt = ' '.join((' ' * maxlen, '%s'))

        for n, m in cmd_list:
            if not m.__doc__:
                self.print(n, end='\n\n')
                continue

            lines = [s.strip() for s in m.__doc__.strip().splitlines()]

            self.print(head_fmt % (n, lines[0]))
            for line in lines[1:]:
                self.print(body_fmt % line)
            self.print()

    def cmd_help(self, *args):
        '''[<command>]
        Print help message.
        '''
        if not args:
            return self.printhelp(list(self.itercmd()))

        cmd = self.getcmd(args[0])
        if callable(cmd):
            self.printhelp([(args[0], cmd)])
        else:
            self.print('command not found: %s' % args[0])

    def cmd_quit(self, *args):
        '''(no arguments required)
        Quit the console.
        '''
        raise StopIteration()


class ConsoleCommand(Command):
    PATH_PREFIX = '/v0.1'

    def __init__(self, instance, host, port):
        self.instance = instance
        self.client = util.HTTPClient(host, port)

    def path(self, path=''):
        p = '/'.join((self.PATH_PREFIX, self.instance))
        return ''.join((p, path))

    def cmd_print(self, *args):
        '''(no arguments required)
        Generate a text and print it / its score.
        '''
        code, body = self.client.get(self.path())
        if code == 200:
            self.print('%s [%f]' % (body['text'], body['score']))
        else:
            self.print('[failed: %d]' % code)

    def cmd_learn(self, *args):
        '''[-c <encoding>] <file>
        Learn from a file.  The <encoding> is used to decode
        the text in the <file> (defaults to "utf-8").
        '''
        try:
            opts, args = getopt.gnu_getopt(args, 'c:')
        except getopt.error:
            return self.printhelp()
        if not args:
            return self.printhelp()

        encode = 'utf-8'
        for opt, optarg in opts:
            if opt == '-c':
                encode = optarg

        with open(args[0]) as fp:
            fcntl.flock(fp.fileno(), fcntl.LOCK_SH)
            text = [unicode(line.strip(), encode) for line in fp]

        code, _ = self.client.put(self.path(), {'text': text})
        if code == 204:
            self.print('[success]')
        else:
            self.print('[failed: %d]' % code)

    def cmd_map(self, *args):
        '''<key1> [<key2> [...]]
        Get values of the Markov Table on specified key(s).
        Keys can be shown by the "key" command.
        '''
        if not args:
            return self.printhelp()

        keys = json.dumps(args, ensure_ascii=False).encode('utf-8')
        path = self.path('/'.join(('/keys', urllib.quote(keys, safe=''))))
        code, body = self.client.get(path)
        if code == 200:
            for v in body.get('values', []):
                json.dump(v, self.FILE, ensure_ascii=False)
                self.print()
        else:
            self.print('[failed: %d]' % code)

    def cmd_key(self, *args):
        '''(no arguments required)
        Print keys of the Markov Table.
        '''
        code, body = self.client.get(self.path('/keys'))
        if code == 200:
            for k in body.get('keys', []):
                for i in k:
                    json.dump(i, self.FILE, ensure_ascii=False)
                    self.print(' ', end='')
                self.print()
        else:
            self.print('[failed: %d]' % code)

    def cmd_entry(self, *args):
        '''(no arguments required)
        Print candidate entrypoints to generate a text.
        '''
        code, body = self.client.get(self.path('/entrypoints'))
        if code == 200:
            for k in body.get('entrypoints', []):
                json.dump(k, self.FILE, ensure_ascii=False)
                self.print()
        else:
            self.print('[failed: %d]' % code)

    def cmd_recent(self, *args):
        '''(no arguments required)
        Print recent learned text.
        '''
        code, body = self.client.get(self.path('/recents'))
        if code == 200:
            for k in body.get('recents', []):
                json.dump(k, self.FILE, ensure_ascii=False)
                self.print()
        else:
            self.print('[failed: %d]' % code)

    def cmd_stat(self, *args):
        '''(no arguments required)
        Print statistics.
        '''
        code, body = self.client.get(self.path('/stats'))
        if code == 200:
            self.print('score threshold: %f' % body['threshold'])
            self.print('markov keys:     %d' % body['keys'])
            self.print('entrypoints:     %d' % body['entrypoints'])
        else:
            self.print('[failed: %d]' % code)


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

    name = os.path.splitext(os.path.basename(sys.argv[0]))[0]
    cmd = ConsoleCommand(args[0], host, port)
    readline.set_completer(cmd.complete)
    readline.parse_and_bind('tab: complete')

    while True:
        try:
            line = raw_input('%s> ' % name).strip()
            if line:
                cmd.run(util.split(line, fsenc))

        except EOFError:
            print()
            print('bye ;)')
            break

        except StopIteration:
            print('bye ;)')
            break

        except KeyboardInterrupt:
            print()

        except:
            traceback.print_exc()


if __name__ == '__main__':
    main()
