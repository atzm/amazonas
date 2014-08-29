# -*- coding: utf-8 -*-

import shlex
import subprocess

from .. import parser


@parser.parserclass(parser.PARSERTYPE_MORPH)
class Juman(parser.Parser):
    PIPE_BUF = 512                     # 512B (POSIX.1-2001 minimum)
    JUMAN_RESPAWN_THRESHOLD = 1 << 28  # 256MB
    ENTRY_CLS = {
        u'形容詞':   ('*',),
        u'連体詞':   ('*',),
        u'接続詞':   ('*',),
        u'指示詞':   (u'名詞形態指示詞', u'連体詞形態指示詞',
                      u'副詞形態指示詞'),
        u'感動詞':   ('*',),
        u'名詞':     (u'普通名詞', u'固有名詞', u'組織名', u'地名', u'人名',
                      u'サ変名詞', u'数詞', u'時相名詞'),
        u'接頭辞':   (u'名詞接頭辞', u'動詞接頭辞', u'ナ形容詞接頭辞'),
        u'未定義語': (u'カタカナ', u'アルファベット'),
    }
    END_CLS = {
        u'形容詞': ('*',),
        u'判定詞': ('*',),
        u'助動詞': ('*',),
        u'指示詞': (u'名詞形態指示詞',),
        u'感動詞': ('*',),
        u'名詞':   (u'形式名詞',),
        u'動詞':   ('*',),
        u'助詞':   (u'終助詞',),
        u'接尾辞': (u'形容詞性述語接尾辞', u'形容詞性名詞接尾辞',
                    u'動詞性接尾辞'),
        u'特殊':   (u'句点', u'記号'),
    }

    def __init__(self, path='/usr/bin/juman', args=[], encode='utf-8', **kw):
        self.path = path
        self.args = args
        self.encode = encode
        self.proc = None
        self.size = 0

    def isentry(self, word, info):
        if info[0] not in self.ENTRY_CLS:
            return False
        if info[1] not in self.ENTRY_CLS[info[0]]:
            return False
        return True

    def isend(self, word, info):
        if info[0] not in self.END_CLS:
            return False
        if info[1] not in self.END_CLS[info[0]]:
            return False
        return True

    def validate_hook(self, parsed):
        for word, info in parsed:
            if info[0] == u'特殊' and info[1] in (u'括弧始', u'括弧終'):
                return False
        return True

    def parse(self, text):
        if not text.endswith('\n'):
            text += '\n'

        text = text.encode(self.encode)
        if len(text) > self.PIPE_BUF:
            return

        p = self.getproc(text)
        p.stdin.write(text)
        p.stdin.flush()

        while True:
            line = p.stdout.readline().rstrip()
            if not line or line == 'EOS':
                break

            idx = 0
            words = []
            for x in xrange(3):
                idx = line[1:].index(' ') + 2
                words.append(unicode(line[:idx - 1], self.encode))
                line = line[idx:]

            info = shlex.split(line)  # shlex may fail when unicode

            if len(info) != 9:        # ex. multiple candidates found
                continue

            cls1 = unicode(info[0], self.encode)
            cls2 = unicode(info[2], self.encode)
            cls3 = unicode(info[4], self.encode)
            form = unicode(info[6], self.encode)
            misc = unicode(info[8], self.encode)
            misc = None if misc == 'NIL' else misc
            yield words[0], [cls1, cls2, cls3, form, misc]

    def getproc(self, text):
        self.size += len(text)

        if self.proc:
            if self.size < self.JUMAN_RESPAWN_THRESHOLD:
                return self.proc

            self.proc.kill()

        self.proc = subprocess.Popen([self.path] + self.args,
                                     stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE,
                                     bufsize=-1,
                                     close_fds=True,
                                     universal_newlines=True)
        self.size = 0
        return self.proc

    def __del__(self):
        if self.proc:
            self.proc.kill()
