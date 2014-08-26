# -*- coding: utf-8 -*-

import fcntl
import shlex
import inspect
from ConfigParser import SafeConfigParser, NoSectionError, NoOptionError


class Config(SafeConfigParser):
    ENCODE = 'utf-8'

    def reload(self):
        self.read()

    def read(self, path=None):
        if path is None:
            path = getattr(self, 'lastreadpath', None)

        with open(path) as fp:
            fcntl.flock(fp.fileno(), fcntl.LOCK_SH)
            SafeConfigParser.readfp(self, fp, path)

        setattr(self, 'lastreadpath', path)

    def write(self, path):
        with open(path, 'a+') as fp:
            fcntl.flock(fp.fileno(), fcntl.LOCK_EX)
            fp.truncate(0)
            fp.seek(0, 0)
            SafeConfigParser.write(self, fp)

    def set(self, sect, key, val):
        if type(val) is unicode:
            val = val.encode(self.ENCODE)
        else:
            val = str(val)
        try:
            SafeConfigParser.set(self, sect, key, val)
        except NoSectionError:
            SafeConfigParser.add_section(self, sect)
            SafeConfigParser.set(self, sect, key, val)

    def get(self, sect, key, type_=''):
        try:
            val = getattr(SafeConfigParser, 'get%s' % type_)(self, sect, key)
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
        val = self.get(sect, key).encode(self.ENCODE)
        return [unicode(v, self.ENCODE) for v in shlex.split(val)]

    def as_dict(self, sect):
        try:
            keys = SafeConfigParser.options(self, sect)
        except NoSectionError:
            return {}
        return dict([(k, self.get(sect, k)) for k in keys])


_CONF = Config()

for name, method in inspect.getmembers(_CONF, inspect.ismethod):
    globals()[name] = method
