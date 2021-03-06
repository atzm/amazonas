# -*- coding: utf-8 -*-

import string
import importlib
import collections

import six


PARSERTYPE_MORPH = 'morph'
_PARSER_CLASS = {}


def loadmodule(name):
    importlib.import_module('amazonas.parsermod.%s' % name)


def getclass(type_, name=None):
    global _PARSER_CLASS
    if name is not None:
        return _PARSER_CLASS[type_][name]
    try:
        return next(six.itervalues(_PARSER_CLASS[type_]))
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
            raise TypeError('%s is not a valid parser class' % cls.__name__)
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

    @staticmethod
    def split(parsed, chars='\n'):
        data = []
        for word, info in parsed:
            if word in chars:
                yield data
                data = []
                continue
            data.append((word, info))
        yield data

    @staticmethod
    def strip(parsed, chars=string.whitespace):
        parsed = list(parsed)

        while True:
            if not parsed:
                return parsed
            if parsed[0][0] in chars:
                parsed.pop(0)
            else:
                break

        while True:
            if not parsed:
                return parsed
            if parsed[-1][0] in chars:
                parsed.pop(-1)
            else:
                break

        return parsed
