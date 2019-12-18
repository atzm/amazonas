# -*- coding: utf-8 -*-

from .. import util, parser

import six
import MeCab


@parser.parserclass(parser.PARSERTYPE_MORPH)
class Mecab(parser.Parser):
    ENTRY_CLS = {
        u'連体詞':   ('*',),
        u'接頭詞':   (u'形容詞接続', u'数接続', u'動詞接続', u'名詞接続'),
        u'名詞':     (u'引用文字列', u'サ変接続', u'ナイ形容詞語幹',
                      u'形容動詞語幹', u'動詞非自立的', u'副詞可能',  # noqa: E128
                      u'一般', u'数', u'固有名詞', u'代名詞'),        # noqa: E128
        u'動詞':     (u'自立',),
        u'形容詞':   (u'自立',),
        u'副詞':     (u'一般', u'助詞類接続'),
        u'接続詞':   ('*',),
        u'感動詞':   ('*',),
        u'フィラー': ('*',),
        u'未知語':   ('*',),
    }
    END_CLS = {
        u'名詞':   (u'接尾', u'非自立'),
        u'動詞':   (u'自立', u'接尾', u'非自立'),
        u'形容詞': (u'自立', u'接尾', u'非自立'),
        u'助詞':   (u'終助詞', u'特殊', u'副助詞', u'並立助詞'),
        u'助動詞': ('*',),
        u'感動詞': ('*',),
        u'記号':   (u'句点', u'一般'),
    }

    def __init__(self, args='', **kw):
        self.args = str(args)

    def isentry(self, word, info):
        if info[0] not in self.ENTRY_CLS:
            return False
        if info[1] not in self.ENTRY_CLS[info[0]]:
            return False
        if info[-1] == '*':
            return False
        return True

    def isend(self, word, info):
        if info[0] not in self.END_CLS:
            return False
        if info[1] not in self.END_CLS[info[0]]:
            return False
        if info[5].startswith(u'未然'):
            return False
        if info[5].startswith(u'連用'):
            return False
        return True

    def validate_hook(self, parsed):
        for word, info in parsed:
            if info[0] == u'記号' and info[1] in (u'括弧開', u'括弧閉'):
                return False
        return True

    def parse(self, text):
        result = []
        tagger = MeCab.Tagger(self.args)
        encode = tagger.dictionary_info().charset

        for text in text.splitlines():
            # MeCab.Tagger.parse only accepts encoded text in python2,
            # but only accepts unicode text in python3.
            # unicode.strip/split treats wide space as delimiter by default.
            text = text.strip('\t\r\n')
            parsed_text = self._parse(tagger, text, encode)

            for line in parsed_text.splitlines():
                line = line.strip('\t\r\n')

                if not line or line == 'EOS':
                    break
                try:
                    word, info = line.split('\t', 1)
                    result.append([word, info.strip(' \t\r\n').split(',')])
                except Exception:
                    pass

            # pseudo word class for multi-line text generation
            result.append(['\n', [u'記号', u'改行', '*',  '*', '*', '*',
                                  '\n', '\n', '\n']])

        return result

    def _parse(self, tagger, text, encode):
        t = text.encode(encode) if six.PY2 else text
        return util.compat.ucode(tagger.parse(t), encode)
