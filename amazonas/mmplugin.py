# -*- coding: utf-8 -*-

import os
import sys
import glob
import importlib
import contextlib

from . import util


_PLUGINS_ACTION = {}


def action(name):
    def f(func):
        _PLUGINS_ACTION[name] = func
        return func
    return f


def getaction(name):
    try:
        return _PLUGINS_ACTION[name]
    except KeyError:
        pass
    return lambda *_: None


def iteractions():
    return _PLUGINS_ACTION.iteritems()


def load(path):
    @contextlib.contextmanager
    def syspath(path):
        try:
            sys.path.insert(0, path)
            yield sys.path
        finally:
            sys.path.pop(0)

    path = util.abspath(path)
    with syspath(path):
        for f in sorted(glob.iglob(os.path.sep.join((path, '*.py')))):
            name = os.path.splitext(os.path.basename(f))[0]
            importlib.import_module(name)


def unload():
    _PLUGINS_ACTION.clear()
