# -*- coding: utf-8 -*-

import fcntl
import codecs
import inspect

from . import util

import six
from six.moves.configparser import (
    RawConfigParser,
    NoSectionError,
    NoOptionError,
)


class Config(object):
    ENCODE = 'utf-8'

    def __init__(self):
        self.cfg = RawConfigParser()
        self.lastreadpath = None

    def reload(self):
        self.cfg = RawConfigParser()
        self.read()

    def read(self, path=None):
        if path is None:
            path = self.lastreadpath

        with codecs.open(path, encoding=self.ENCODE) as fp:
            fcntl.flock(fp.fileno(), fcntl.LOCK_SH)
            self.cfg.readfp(fp, path)

        self.lastreadpath = path

    def write(self, path):
        with codecs.open(path, 'a+', encoding=self.ENCODE) as fp:
            fcntl.flock(fp.fileno(), fcntl.LOCK_EX)
            fp.truncate(0)
            fp.seek(0, 0)
            self.cfg.write(fp)

    def set(self, sect, key, val):
        if six.PY2 and util.compat.isucode(val):
            val = val.encode(self.ENCODE)
        else:
            val = str(val)
        try:
            self.cfg.set(sect, key, val)
        except NoSectionError:
            self.cfg.add_section(sect)
            self.cfg.set(sect, key, val)

    def get(self, sect, key, type_=''):
        try:
            val = getattr(self.cfg, 'get%s' % type_)(sect, key)
            return util.compat.ucode(val, self.ENCODE)
        except (NoSectionError, NoOptionError, AttributeError):
            if type_ == 'int':
                return 0
            elif type_ == 'float':
                return 0.0
            elif type_ == 'boolean':
                return False
            return u''

    def getint(self, sect, key):
        return self.get(sect, key, 'int')

    def getfloat(self, sect, key):
        return self.get(sect, key, 'float')

    def getboolean(self, sect, key):
        return self.get(sect, key, 'boolean')

    def getlist(self, sect, key):
        val = self.get(sect, key)
        return util.split(val)

    def has_section(self, *args, **kwargs):
        return self.cfg.has_section(*args, **kwargs)

    def has_option(self, *args, **kwargs):
        return self.cfg.has_option(*args, **kwargs)

    def as_dict(self, sect):
        try:
            keys = self.cfg.options(sect)
        except NoSectionError:
            return {}
        return dict([(k, self.get(sect, k)) for k in keys])


_CONF = Config()

for name, method in inspect.getmembers(_CONF, inspect.ismethod):
    globals()[name] = method
