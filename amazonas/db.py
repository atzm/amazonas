# -*- coding: utf-8 -*-

import json
import importlib
import contextlib
import collections

import six


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
        return next(six.itervalues(_DB_CLASS[type_]))
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
            raise TypeError('%s is not a valid db class' % cls.__name__)
        return cls
    return f


class Database(object):
    def __init__(self, **kw):
        pass

    @contextlib.contextmanager
    def transaction(self):
        yield

    def append(self, key, item):
        pass

    def get(self, key):
        return []

    def getrand(self, key):
        pass

    def getrandall(self):
        pass

    def keys(self):
        return []

    def length(self):
        return 0

    def __len__(self):
        return self.length()

    @staticmethod
    def serialize(data):
        return json.dumps(data, ensure_ascii=False)

    @staticmethod
    def deserialize(data):
        return json.loads(data)
