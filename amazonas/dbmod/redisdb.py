# -*- coding: utf-8 -*-

import json
import redis

from .. import db


@db.dbclass(db.DBTYPE_MARKOV, db.DBTYPE_ENTRYPOINT)
class Redis(db.Database):
    def __init__(self, host='localhost', port=6379, db=0, **kw):
        self.redis = redis.StrictRedis(host=host, port=int(port), db=int(db))

    def append(self, key, item):      # XXX: lose probability
        self.redis.sadd(self.serialize(key),
                        json.dumps(item, ensure_ascii=False))

    def get(self, key):
        vals = self.redis.smembers(self.serialize(key))
        if not vals:
            return None
        return [json.loads(v) for v in vals]

    def getrand(self, key):
        val = self.redis.srandmember(self.serialize(key))
        if val is None:
            return None
        return json.loads(val)

    def getrandall(self):             # XXX: not atomic
        key = self.redis.randomkey()
        if key is None:
            return None
        return self.getrand(self.deserialize(key))

    def keys(self):
        return [self.deserialize(k) for k in self.redis.keys()]
