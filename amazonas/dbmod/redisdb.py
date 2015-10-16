# -*- coding: utf-8 -*-

import redis

from .. import db


@db.dbclass(db.DBTYPE_MARKOV, db.DBTYPE_ENTRYPOINT)
class Redis(db.Database):
    def __init__(self, host='localhost', port=6379, db=0, **kw):
        self.redis = redis.StrictRedis(host=host, port=int(port), db=int(db))

    def append(self, key, item):      # XXX: lose probability
        self.redis.sadd(self.serialize(key), self.serialize(item))

    def get(self, key):
        vals = self.redis.smembers(self.serialize(key))
        return [self.deserialize(v) for v in vals] if vals else None

    def getrand(self, key):
        val = self.redis.srandmember(self.serialize(key))
        return None if val is None else self.deserialize(val)

    def getrandall(self):             # XXX: not atomic
        key = self.redis.randomkey()
        return None if key is None else self.getrand(self.deserialize(key))

    def keys(self):
        return [self.deserialize(k) for k in self.redis.keys()]

    def length(self):
        return self.redis.dbsize()
