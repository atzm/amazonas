# -*- coding: utf-8 -*-

import random
import operator
import collections

from . import db
from . import util
from . import parser
from . import config


class MarkovTable(object):
    def __init__(self, db, edb, level=2, maxchain=50):
        self.db = db
        self.edb = edb
        self.level = int(level)
        self.maxchain = int(maxchain)

    @classmethod
    def getinstance(cls, instance):
        return cls(util.getdb(db.DBTYPE_MARKOV, instance),
                   util.getdb(db.DBTYPE_ENTRYPOINT, instance),
                   **config.as_dict('markov:%s' % instance))

    def learn(self, itemlist):
        def check(key):
            return len([k for k in key if k]) == len(key)

        entry = None
        items = [''] * self.level

        for item in itemlist:
            if check(items):
                key = tuple(items)
                self.db.append(key, item)

                if not entry:
                    entry = key

            items.pop(0)
            items.append(item)

        if entry:
            self.edb.append(entry[0], entry)

    def run(self, entry=None):
        if entry:
            items = self.edb.getrand(entry)
        else:
            items = self.edb.getrandall()
        if items is None:
            return []

        items = list(items)
        data = items[:]

        for x in xrange(self.maxchain):
            item = self.db.getrand(tuple(items))
            if item is None:
                break

            data.append(item)
            items.pop(0)
            items.append(item)

        return data


class TextGenerator(object):
    def __init__(self, parser, markov, retry=50, s_thresh=0.0, n_recent=100):
        self.parser = parser
        self.markov = markov
        self.retry = int(retry)
        self.s_thresh = float(s_thresh)
        self.n_recent = int(n_recent)
        self.cls_order = collections.deque(maxlen=self.n_recent)
        self.recent = collections.deque(maxlen=self.n_recent)

    @classmethod
    def getinstance(cls, instance, markov_cls=MarkovTable):
        markov = markov_cls.getinstance(instance)
        return cls(util.getparser(parser.PARSERTYPE_MORPH, instance), markov,
                   **config.as_dict('textgen:%s' % instance))

    def learn(self, line):
        info = tuple(self.parser.parse(line))
        if len(info) <= self.markov.level:
            return

        zipped = zip(*info)
        self.markov.learn(zipped[0])
        self.cls_order.append(zip(*zipped[1])[0])
        self.recent.append(line)

    def run(self):
        for x in xrange(self.retry):
            try:
                entry = random.choice(self.entrypoints)
            except IndexError:
                entry = None

            try:
                text = ''.join(self.markov.run(entry))
            except:
                continue
            if not text:
                continue

            parsed = tuple(self.parser.parse(text))
            if not self.parser.validate(parsed):
                continue

            cls_order = [i[0] for _, i in parsed]
            score = self.score(cls_order)
            self.s_thresh = (self.s_thresh + score) / 2
            if self.s_thresh < score:
                return text, score

        return None, None

    def score(self, cls_order):
        if len(self.cls_order) <= 1:
            return 1.0
        dist = [self.distance(cls_order, order) for order in self.cls_order]
        return 1.0 / (float(sum(dist)) / len(dist))

    @property
    def entrypoints(self):
        entries = []
        for line in self.recent:
            entries.extend(self.parser.entrypoints(line))
        return entries

    @staticmethod
    def distance(a, b, op=operator.eq):
        la = len(a) + 1
        lb = len(b) + 1
        m = [[0] * lb for i in xrange(la)]

        for i in xrange(la):
            m[i][0] = i

        for j in xrange(lb):
            m[0][j] = j

        for i in xrange(1, la):
            for j in xrange(1, lb):
                x = int(not op(a[i - 1], b[j - 1]))
                m[i][j] = min(m[i - 1][j] + 1,
                              m[i][j - 1] + 1,
                              m[i - 1][j - 1] + x)

        return m[-1][-1]
