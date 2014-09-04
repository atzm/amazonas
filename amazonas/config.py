# -*- coding: utf-8 -*-

import fcntl
import inspect
from ConfigParser import RawConfigParser, NoSectionError, NoOptionError

from . import util


class Config(RawConfigParser):
    ENCODE = 'utf-8'

    def reload(self):
        self.read()

    def read(self, path=None):
        if path is None:
            path = getattr(self, 'lastreadpath', None)

        with open(path) as fp:
            fcntl.flock(fp.fileno(), fcntl.LOCK_SH)
            RawConfigParser.readfp(self, fp, path)

        setattr(self, 'lastreadpath', path)

    def write(self, path):
        with open(path, 'a+') as fp:
            fcntl.flock(fp.fileno(), fcntl.LOCK_EX)
            fp.truncate(0)
            fp.seek(0, 0)
            RawConfigParser.write(self, fp)

    def set(self, sect, key, val):
        if type(val) is unicode:
            val = val.encode(self.ENCODE)
        else:
            val = str(val)
        try:
            RawConfigParser.set(self, sect, key, val)
        except NoSectionError:
            RawConfigParser.add_section(self, sect)
            RawConfigParser.set(self, sect, key, val)

    def get(self, sect, key, type_=''):
        try:
            val = getattr(RawConfigParser, 'get%s' % type_)(self, sect, key)
            if type(val) is str:
                return unicode(val, self.ENCODE)
            return val
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

    def as_dict(self, sect):
        try:
            keys = RawConfigParser.options(self, sect)
        except NoSectionError:
            return {}
        return dict([(k, self.get(sect, k)) for k in keys])


def enabled(sect):
    global _CONF

    if not _CONF.has_section(sect):
        return False

    if not _CONF.getboolean(sect, 'enable'):
        return False

    try:
        time_ = _CONF.get(sect, 'time')
        if time_ and not util.time_in(time_):
            return False
    except:
        return False

    return True


_CONF = Config()

for name, method in inspect.getmembers(_CONF, inspect.ismethod):
    globals()[name] = method
