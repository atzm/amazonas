# -*- coding: utf-8 -*-

import os
import sys
import glob
import importlib
import contextlib

from . import util

import six


_PLUGINS_ACTION = {}
_PLUGINS_COMMAND = {}
_PLUGINS_EVENT = {}


def action(name):
    def f(func):
        _PLUGINS_ACTION[name] = func
        return func
    return f


def command(name):
    def f(func):
        _PLUGINS_COMMAND[name] = func
        return func
    return f


def event(name):
    def f(func):
        _PLUGINS_EVENT.setdefault(name, [])
        _PLUGINS_EVENT[name].append(func)
        return func
    return f


def getaction(name):
    try:
        return _PLUGINS_ACTION[name]
    except KeyError:
        pass
    return lambda *_: None


def iteractions():
    return six.iteritems(_PLUGINS_ACTION)


def getcommand(name):
    try:
        return _PLUGINS_COMMAND[name]
    except KeyError:
        pass
    return lambda *_: None


def itercommands():
    return six.iteritems(_PLUGINS_COMMAND)


def getevent(name):
    try:
        return _PLUGINS_EVENT[name]
    except KeyError:
        pass
    return []


def iterevents():
    return six.iteritems(_PLUGINS_EVENT)


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
