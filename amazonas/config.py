# -*- coding: utf-8 -*-

import fcntl
import shlex
import inspect
from ConfigParser import SafeConfigParser, NoSectionError, NoOptionError


class Config(SafeConfigParser):
    def read(self, path):
        with open(path) as fp:
            fcntl.flock(fp.fileno(), fcntl.LOCK_SH)
            SafeConfigParser.readfp(self, fp, path)

    def write(self, path):
        with open(path, 'a+') as fp:
            fcntl.flock(fp.fileno(), fcntl.LOCK_EX)
            fp.truncate(0)
            fp.seek(0, 0)
            SafeConfigParser.write(self, fp)

    def set(self, sect, key, val):
        try:
            SafeConfigParser.set(self, sect, key, str(val))
        except NoSectionError:
            SafeConfigParser.add_section(self, sect)
            SafeConfigParser.set(self, sect, key, str(val))

    def get(self, sect, key, type_=''):
        try:
            if not type_:
                return SafeConfigParser.get(self, sect, key)
            return getattr(SafeConfigParser, 'get%s' % type_)(self, sect, key)
        except (NoSectionError, NoOptionError, AttributeError):
            if type_ == 'int':
                return 0
            elif type_ == 'float':
                return 0.0
            elif type_ == 'boolean':
                return False
            return ''

    def getint(self, sect, key):
        return self.get(sect, key, 'int')

    def getfloat(self, sect, key):
        return self.get(sect, key, 'float')

    def getboolean(self, sect, key):
        return self.get(sect, key, 'boolean')

    def getlist(self, sect, key):
        val = self.get(sect, key)
        return shlex.split(val)

    def as_dict(self, sect):
        try:
            keys = SafeConfigParser.options(self, sect)
        except NoSectionError:
            return {}
        return dict([(k, self.get(sect, k)) for k in keys])


_CONF = Config()

for name, method in inspect.getmembers(_CONF, inspect.ismethod):
    globals()[name] = method
