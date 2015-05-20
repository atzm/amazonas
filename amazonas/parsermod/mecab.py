# -*- coding: utf-8 -*-

import MeCab

from .. import parser


@parser.parserclass(parser.PARSERTYPE_MORPH)
class Mecab(parser.Parser):
    ENTRY_CLS = {
        u'連体詞':   ('*',),
        u'接頭詞':   (u'形容詞接続', u'数接続', u'動詞接続', u'名詞接続'),
        u'名詞':     (u'引用文字列', u'サ変接続', u'ナイ形容詞語幹',
                      u'形容動詞語幹', u'動詞非自立的', u'副詞可能',
                      u'一般', u'数', u'固有名詞', u'代名詞'),
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
        tagger = MeCab.Tagger(self.args)
        encode = tagger.dictionary_info().charset

        for text in text.encode(encode).splitlines():
            text = text.strip()

            # unicode.strip/split treats wide space as delimiter by default
            for line in tagger.parse(text).splitlines():
                line = unicode(line, encode).strip('\t\r\n')

                if not line or line == 'EOS':
                    break
                try:
                    word, info = line.split('\t', 1)
                    yield word, info.strip(' \t\r\n').split(',')
                except:
                    pass

            # pseudo word class for multi-line text generation
            yield '\n', [u'記号', u'改行', '*',  '*', '*', '*',
                         '\n', '\n', '\n']
