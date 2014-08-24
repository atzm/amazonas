# -*- coding: utf-8 -*-

import db
import parser
import config


def loadmodules():
    for m in config.getlist('module', 'parsers'):
        parser.loadmodule(m)

    for m in config.getlist('module', 'dbs'):
        db.loadmodule(m)


def getparser(type_, instance):
    d = config.as_dict('parser:%s:%s' % (type_, instance))
    c = parser.getclass(type_, d.pop('type'))
    return c(**d)


def getdb(type_, instance):
    d = config.as_dict('db:%s:%s' % (type_, instance))
    c = db.getclass(type_, d.pop('type'))
    return c(**d)
