# -*- coding: utf-8 -*-

import json
import importlib
import collections


DBTYPE_MARKOV = 'markov'
DBTYPE_ENTRYPOINT = 'entrypoint'
_DB_CLASS = {}


def loadmodule(name):
    importlib.import_module('amazonas.dbmod.%s' % name)


def getclass(type_, name=None):
    global _DB_CLASS
    if name is not None:
        return _DB_CLASS[type_][name]
    try:
        return _DB_CLASS[type_].itervalues().next()
    except (KeyError, StopIteration):
        pass
    return None


def dbclass(*type_):
    def f(cls):
        global _DB_CLASS
        if issubclass(cls, Database) and cls is not Database:
            for t in type_:
                _DB_CLASS.setdefault(t, collections.OrderedDict())
                _DB_CLASS[t][cls.__name__] = cls
        else:
            raise UserWarning('%s is not a valid db class' % cls.__name__)
        return cls
    return f


class Database(object):
    def __init__(self, **kw):
        pass

    def append(self, key, item):
        pass

    def get(self, key):
        pass

    def getrand(self, key):
        pass

    def getrandall(self):
        pass

    def keys(self):
        pass

    @staticmethod
    def serialize(data):
        return json.dumps(data, ensure_ascii=False)

    @staticmethod
    def deserialize(data):
        return json.loads(data)
