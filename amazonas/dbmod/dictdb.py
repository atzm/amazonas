# -*- coding: utf-8 -*-

import json
import fcntl
import errno
import codecs
import random

from .. import db


@db.dbclass(db.DBTYPE_MARKOV, db.DBTYPE_ENTRYPOINT)
class Dict(db.Database):
    def __init__(self, path=None, **kw):
        self.path = path
        self.load()

    def append(self, key, item):
        key = self.serialize(key)
        self.table.setdefault(key, [])
        self.table[key].append(item)

    def get(self, key):
        vals = self.table.get(self.serialize(key), None)
        if not vals:
            return None
        return vals

    def getrand(self, key):
        try:
            return random.choice(self.table[self.serialize(key)])
        except:
            return None

    def getrandall(self):
        try:
            return random.choice(random.choice(self.table.values()))
        except:
            return None

    def keys(self):
        return [self.deserialize(k) for k in self.table.keys()]

    def length(self):
        return len(self.table)

    def load(self):
        self.table = {}

        if not self.path:
            return

        try:
            with open(self.path) as fp:
                fcntl.flock(fp.fileno(), fcntl.LOCK_SH)
                self.table = json.load(fp)
        except IOError as e:
            if e.errno != errno.ENOENT:
                raise

    def save(self):
        if not self.path:
            return

        with codecs.open(self.path, mode='a+', encoding='utf-8') as fp:
            fcntl.flock(fp.fileno(), fcntl.LOCK_EX)
            fp.truncate(0)
            fp.seek(0, 0)
            json.dump(self.table, fp, ensure_ascii=False, indent=4)

    def __del__(self):
        self.save()
