# -*- coding: utf-8 -*-

import random
import logging
import operator
import collections

from . import db
from . import parser
from . import config

from six.moves import range


def getdb(type_, instance):
    d = config.as_dict(':'.join(('db', type_, instance)))
    c = db.getclass(type_, d.pop('type'))
    return c(**d)


def getparser(type_, instance):
    d = config.as_dict(':'.join(('parser', type_, instance)))
    c = parser.getclass(type_, d.pop('type'))
    return c(**d)


class MarkovTable(object):
    def __init__(self, db, edb, level=2, maxchain=50):
        self.db = db
        self.edb = edb
        self.level = int(level)
        self.maxchain = int(maxchain)

    @classmethod
    def getinstance(cls, instance):
        return cls(getdb(db.DBTYPE_MARKOV, instance),
                   getdb(db.DBTYPE_ENTRYPOINT, instance),
                   **config.as_dict('markov:%s' % instance))

    def learn(self, itemlist):
        def check(key):
            return len([k for k in key if k]) == len(key)

        entrypoint = None
        items = [''] * self.level

        with self.db.transaction():
            for item in itemlist:
                if check(items):
                    key = tuple(items)
                    self.db.append(key, item)

                    if not entrypoint:
                        entrypoint = key

                items.pop(0)
                items.append(item)

        if entrypoint:
            with self.edb.transaction():
                self.edb.append(entrypoint[0], entrypoint)

        self.maxchain = (self.maxchain + len(itemlist)) // 2

    def run(self, entrypoint=None):
        with self.edb.transaction():
            if entrypoint:
                items = self.edb.getrand(entrypoint)
            else:
                items = self.edb.getrandall()
        if items is None:
            return []

        items = list(items)
        data = items[:]

        with self.db.transaction():
            for x in range(self.maxchain):
                item = self.db.getrand(tuple(items))
                if item is None:
                    break

                data.append(item)
                items.pop(0)
                items.append(item)

        return data

    def keys(self):
        with self.db.transaction():
            return self.db.keys()

    def values(self, keys):
        with self.db.transaction():
            return self.db.get(tuple(keys))

    def entrypoints(self):
        with self.edb.transaction():
            return self.edb.keys()

    def key_length(self):
        with self.db.transaction():
            return len(self.db)

    def entrypoint_length(self):
        with self.edb.transaction():
            return len(self.edb)


class TextGenerator(object):
    def __init__(self, parser, markov, **kw):
        self.parser = parser
        self.markov = markov

        self.nr_retry = int(kw.get('nr_retry', 50))
        self.nr_history = int(kw.get('nr_history', 50))
        self.nr_wordclass = int(kw.get('nr_wordclass', 100))
        self.nr_entrypoint = int(kw.get('nr_entrypoint', 100))
        self.score_threshold = float(kw.get('score_threshold', 0.0))

        self.history = collections.deque(maxlen=self.nr_history)
        self.wordclass = collections.deque(maxlen=self.nr_wordclass)
        self.entrypoint = collections.deque(maxlen=self.nr_entrypoint)

    @classmethod
    def getinstance(cls, instance, markov_cls=MarkovTable):
        markov = markov_cls.getinstance(instance)
        return cls(getparser(parser.PARSERTYPE_MORPH, instance), markov,
                   **config.as_dict('textgen:%s' % instance))

    def learn(self, text):
        parsed = self.parser.strip(self.parser.parse(text))
        if len(parsed) <= self.markov.level:
            return

        self.markov.learn(list(zip(*parsed))[0])
        self.entrypoint.extend(self.parser.entrypoints(parsed))
        self.history.append(text)

        for line in self.parser.split(parsed):
            if not line:
                continue
            wordclass = list(zip(*list(zip(*line))[1]))[0]
            self.update_score_threshold(self.score(wordclass))
            self.wordclass.append(wordclass)

    def run(self, entrypoint=None):
        for x in range(self.nr_retry):
            if entrypoint:
                ep = entrypoint
            elif self.entrypoint:
                ep = random.choice(self.entrypoint)
            else:
                ep = None

            try:
                text = ''.join(self.markov.run(ep)).strip()
            except Exception:
                logging.exception('failed to generate a text (%d)', x)
                continue
            if not text:
                continue
            if self.history_contains(text):
                continue

            score = self.textscore(text)
            if score < 0:
                continue

            self.update_score_threshold(score)
            if self.score_threshold <= score:
                self.history.append(text)
                return text, score

        return None, None

    def textscore(self, text):
        parsed = self.parser.strip(self.parser.parse(text))
        if not self.parser.validate(parsed):
            return -1

        lines = tuple(line for line in self.parser.split(parsed) if line)
        if not lines:
            return -1

        score = sum(self.score(list(zip(*list(zip(*line))[1]))[0])
                    for line in lines)
        return score / len(lines)

    def score(self, wordclass):
        if len(self.wordclass) <= 1:
            return 1.0
        dist = [self.distance(wordclass, wcls) for wcls in self.wordclass]
        return 1.0 / (float(sum(dist)) / len(dist))

    def update_score_threshold(self, score):
        self.score_threshold = (self.score_threshold + score) / 2

    def history_contains(self, text):
        for line in self.history:
            if text in line:
                return True
        return False

    @staticmethod
    def distance(a, b, op=operator.eq):
        la = len(a) + 1
        lb = len(b) + 1
        m = [[0] * lb for i in range(la)]

        for i in range(la):
            m[i][0] = i

        for j in range(lb):
            m[0][j] = j

        for i in range(1, la):
            for j in range(1, lb):
                x = int(not op(a[i - 1], b[j - 1]))
                m[i][j] = min(m[i - 1][j] + 1,
                              m[i][j - 1] + 1,
                              m[i - 1][j - 1] + x)

        return m[-1][-1]
