# -*- coding: utf-8 -*-

import sys
import json
import fcntl
import shlex
import getopt
import inspect
import readline
import traceback

import util
import config
import textgen


class Command(object):
    def __init__(self, textgen):
        self.textgen = textgen

    def getcmd(self, cmd):
        return getattr(self, 'cmd_' + cmd, None)

    def cmd_print(self, *args):
        text, sc = self.textgen.run()
        if text:
            print('%s [%f]' % (text, sc))
        else:
            print('[failed]')
    cmd_p = cmd_print

    def cmd_learn(self, *args):
        self.textgen.learn(' '.join(args))
    cmd_l = cmd_learn

    def cmd_get(self, *args):
        if not args:
            print('[get requires an argument]')
            return
        json.dump(self.textgen.markov.db.get(tuple(json.loads(args[0]))),
                  sys.stdout, ensure_ascii=False)
        sys.stdout.write('\n')
    cmd_g = cmd_get

    def cmd_keys(self, *args):
        for k in self.textgen.markov.db.keys():
            json.dump(k, sys.stdout, ensure_ascii=False)
            sys.stdout.write('\n')
    cmd_k = cmd_keys

    def cmd_entrypoints(self, *args):
        for k in self.textgen.markov.edb.keys():
            print(k)
    cmd_e = cmd_entrypoints

    def cmd_recent(self, *args):
        for r in self.textgen.recent:
            print(r)
    cmd_r = cmd_recent

    def cmd_stat(self, *args):
        print('score threshold: %f' % self.textgen.s_thresh)
        print('markov keys:     %d' % len(self.textgen.markov.db.keys()))
        print('entrypoints:     %d' % len(self.textgen.markov.edb.keys()))
    cmd_s = cmd_stat

    def cmd_help(self, *args):
        for n, m in inspect.getmembers(self, inspect.ismethod):
            if n.startswith('cmd_'):
                print(n[4:])
    cmd_h = cmd_help


def main():
    fsenc = sys.getfilesystemencoding()
    initfile = None
    opts, args = getopt.gnu_getopt(sys.argv[1:], 'f:')

    for opt, optarg in opts:
        if opt == '-f':
            initfile = optarg

    if len(args) < 2:
        raise SystemExit('syntax: %s [-f initfile] <conffile> <instance>' %
                         sys.argv[0])

    conffile = args[0]
    instance = args[1]

    config.read(conffile)
    if instance not in config.getlist('server', 'instances'):
        raise SystemExit('invalid instance name: %s' % instance)

    util.loadmodules()
    generator = textgen.TextGenerator.getinstance(instance)

    if initfile:
        with open(initfile) as file_:
            fcntl.flock(file_.fileno(), fcntl.LOCK_SH)
            for line in file_:
                generator.learn(unicode(line.strip(), fsenc))

    cmd = Command(generator)
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
            func = cmd.getcmd(cmdline[0])

            if not callable(func):
                print('command not found: %s' % cmdline[0])
                continue

            func(*cmdline[1:])
        except:
            traceback.print_exc()


if __name__ == '__main__':
    main()
