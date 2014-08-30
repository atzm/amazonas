# -*- coding: utf-8 -*-

import importlib
import collections


PARSERTYPE_MORPH = 'morph'
_PARSER_CLASS = {}


def loadmodule(name):
    importlib.import_module('amazonas.parsermod.%s' % name)


def getclass(type_, name=None):
    global _PARSER_CLASS
    if name is not None:
        return _PARSER_CLASS[type_][name]
    try:
        return _PARSER_CLASS[type_].itervalues().next()
    except (KeyError, StopIteration):
        pass
    return None


def parserclass(*type_):
    def f(cls):
        global _PARSER_CLASS
        if issubclass(cls, Parser) and cls is not Parser:
            for t in type_:
                _PARSER_CLASS.setdefault(t, collections.OrderedDict())
                _PARSER_CLASS[t][cls.__name__] = cls
        else:
            raise UserWarning('%s is not a valid parser class' % cls.__name__)
        return cls
    return f


class Parser(object):
    def __init__(self, **kw):
        pass

    def entrypoints(self, parsed):
        return [w for w, i in parsed if self.isentry(w, i)]

    def validate(self, parsed):
        entry_word, entry_info = parsed[0]
        end_word, end_info = parsed[-1]

        if not self.isentry(entry_word, entry_info):
            return False

        if not self.isend(end_word, end_info):
            return False

        if not self.validate_hook(parsed):
            return False

        return True

    def isentry(self, word, info):
        return True

    def isend(self, word, info):
        return True

    def validate_hook(self, parsed):
        return True

    def parse(self, text):
        return []
