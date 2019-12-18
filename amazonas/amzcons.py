# -*- coding: utf-8 -*-

from __future__ import print_function

import os
import sys
import json
import glob
import fcntl
import codecs
import string
import getopt
import inspect
import argparse
import readline
import traceback

from . import util

import six


class Command(object):
    FILE = sys.stdout

    def complete(self, text, state):
        if readline.get_begidx() == 0:
            return self.complete_cmd(text, state)

        return self.complete_file(text, state)

    def complete_cmd(self, text, state):
        candidates = [n for n, m in self.itercmd() if n.startswith(text)]

        if len(candidates) == 1:
            candidates[0] += ' '

        try:
            return candidates[state]
        except IndexError:
            return None

    def complete_file(self, text, state):
        candidates = glob.glob(os.path.expanduser(text) + '*')

        if len(candidates) == 1:
            if os.path.isdir(candidates[0]):
                if not candidates[0].endswith('/'):
                    candidates[0] += '/'
            else:
                candidates[0] += ' '

        try:
            return candidates[state]
        except IndexError:
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

    def printhelp(self, cmdlist=None):
        if cmdlist is None:
            cmd = inspect.currentframe().f_back.f_code.co_name[4:]
            cmdlist = [(cmd, self.getcmd(cmd))]
        self.print(util.formathelp(cmdlist))

    def cmd_help(self, *args):
        '''[<command>]
        Display help message.
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
    def __init__(self, instance, host, port):
        self.instance = instance
        self.client = util.http.APIClientV01(host, port)

    def cmd_print(self, *args):
        '''[-e <entrypoint>]
        Generate a text and display it / its score.
        '''
        try:
            opts, args = getopt.gnu_getopt(args, 'e:')
        except getopt.error:
            return self.printhelp()

        entrypoint = None
        for opt, optarg in opts:
            if opt == '-e':
                entrypoint = optarg

        score, text = self.client.generate(self.instance, entrypoint)
        if None not in (score, text):
            self.print('%s [%f]' % (text, score))
        else:
            self.print('[failed]')

    def cmd_learn(self, *args):
        '''[-r] [-c <encoding>] <file>
        Learn each line in <file>.  The <encoding> is used to
        decode the text in the <file> (defaults to "utf-8").
        If -r is specified, <file> is treated as one text.
        '''
        try:
            opts, args = getopt.gnu_getopt(args, 'rc:')
        except getopt.error:
            return self.printhelp()
        if not args:
            return self.printhelp()

        raw = False
        encode = 'utf-8'
        for opt, optarg in opts:
            if opt == '-r':
                raw = True
            elif opt == '-c':
                encode = optarg

        with codecs.open(util.abspath(args[0]), 'rU', encode) as fp:
            fcntl.flock(fp.fileno(), fcntl.LOCK_SH)
            text = util.compat.ucode(fp.read().strip(), encode)

        if raw:
            text = [text]
        else:
            text = [line.strip() for line in text.splitlines() if line.strip()]

        if self.client.learn(self.instance, text):
            self.print('[success]')
        else:
            self.print('[failed]')

    def cmd_key(self, *args):
        '''(no arguments required)
        Display keys of the Markov Table.
        '''
        keys = self.client.keys(self.instance)
        if keys is None:
            return self.print('[failed]')
        for k in keys:
            for i in k:
                json.dump(i, self.FILE, ensure_ascii=False)
                self.print(' ', end='')
            self.print()

    def cmd_value(self, *args):
        '''<key1> [<key2> [...]]
        Get values of the Markov Table on specified key(s).
        Keys can be shown by the "key" command.
        '''
        if not args:
            return self.printhelp()

        values = self.client.values(self.instance, args)
        if values is None:
            return self.print('[failed]')
        for v in values:
            json.dump(v, self.FILE, ensure_ascii=False)
            self.print()

    def cmd_entry(self, *args):
        '''(no arguments required)
        Display candidate entrypoints to generate a text.
        '''
        entries = self.client.entries(self.instance)
        if entries is None:
            return self.print('[failed]')
        for e in entries:
            json.dump(e, self.FILE, ensure_ascii=False)
            self.print()

    def cmd_rentry(self, *args):
        '''(no arguments required)
        Display recent learned candidate entrypoints.
        '''
        entries = self.client.recent_entries(self.instance)
        if entries is None:
            return self.print('[failed]')
        for e in entries:
            json.dump(e, self.FILE, ensure_ascii=False)
            self.print()

    def cmd_history(self, *args):
        '''(no arguments required)
        Display recent learned/generated text.
        '''
        histories = self.client.histories(self.instance)
        if histories is None:
            return self.print('[failed]')
        for h in histories:
            json.dump(h, self.FILE, ensure_ascii=False)
            self.print()

    def cmd_stat(self, *args):
        '''(no arguments required)
        Display statistics.
        '''
        stats = self.client.stats(self.instance)
        if stats is None:
            return self.print('[failed]')

        self.print('score threshold: %f' % stats['threshold'])
        self.print('markov maxchain: %d' % stats['maxchain'])
        self.print('markov keys:     %d' % stats['keys'])
        self.print('entrypoints:     %d' % stats['entrypoints'])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('-a', '--address', type=str, default='localhost',
                    help='address or hostname of the API server')
    ap.add_argument('-p', '--port', type=int, default=8349,
                    help='port number of the API server')
    ap.add_argument('instance', type=str,
                    help='instance name to control')
    args = ap.parse_args()

    cmd = ConsoleCommand(args.instance, args.address, args.port)
    name = os.path.splitext(ap.prog)[0]
    fsenc = sys.getfilesystemencoding()

    readline.set_completer_delims(string.whitespace)
    readline.set_completer(cmd.complete)
    readline.parse_and_bind('tab: complete')

    while True:
        try:
            line = util.compat.ucode(
                six.moves.input('%s> ' % name).strip(), fsenc)
            if line:
                cmd.run(util.split(line))

        except EOFError:
            print()
            print('bye ;)')
            break

        except StopIteration:
            print('bye ;)')
            break

        except KeyboardInterrupt:
            print()

        except Exception:
            traceback.print_exc()


if __name__ == '__main__':
    main()
