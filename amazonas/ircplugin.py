# -*- coding: utf-8 -*-

import os
import sys
import glob
import importlib
import contextlib

from . import util


_PLUGINS_ACTION = {}
_PLUGINS_COMMAND = {}
_PLUGINS_EVENT = {}


def action(name):
    def f(func):
        _PLUGINS_ACTION.setdefault(name, [])
        _PLUGINS_ACTION[name].append(func)
    return f


def command(name):
    def f(func):
        _PLUGINS_COMMAND.setdefault(name, [])
        _PLUGINS_COMMAND[name].append(func)
    return f


def event(name):
    def f(func):
        _PLUGINS_EVENT.setdefault(name, [])
        _PLUGINS_EVENT[name].append(func)
    return f


def getaction(name):
    try:
        return _PLUGINS_ACTION[name]
    except KeyError:
        pass
    return []


def iteractions():
    return _PLUGINS_ACTION.iteritems()


def getcommand(name):
    try:
        return _PLUGINS_COMMAND[name]
    except KeyError:
        pass
    return []


def itercommands():
    return _PLUGINS_COMMAND.iteritems()


def getevent(name):
    try:
        return _PLUGINS_EVENT[name]
    except KeyError:
        pass
    return []


def iterevents():
    return _PLUGINS_EVENT.iteritems()


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
    _PLUGINS_COMMAND.clear()
    _PLUGINS_EVENT.clear()
