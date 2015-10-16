# -*- coding: utf-8 -*-

import random
import contextlib

from sqlalchemy import create_engine, Column, ForeignKey, Integer, Text
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql.expression import func

from .. import db


Base = declarative_base()


class MarkovKey(Base):
    __tablename__ = 'markov_key'

    id = Column(Integer, primary_key=True)
    key = Column(Text)
    values = relationship('MarkovValue', uselist=True,
                          cascade='all, delete-orphan')


class MarkovValue(Base):
    __tablename__ = 'markov_value'

    id = Column(Integer, primary_key=True)
    key_id = Column(Integer, ForeignKey('markov_key.id'))
    value = Column(Text)


@db.dbclass(db.DBTYPE_MARKOV, db.DBTYPE_ENTRYPOINT)
class SQL(db.Database):
    def __init__(self, url, encoding='utf-8', **kw):
        kw['echo'] = kw.get('echo', 'false').lower() == 'true'
        self.url = url
        self.current_session = None
        self.Engine = create_engine(url, encoding=encoding, **kw)
        self.Session = sessionmaker(bind=self.Engine)
        Base.metadata.create_all(self.Engine)

    @contextlib.contextmanager
    def transaction(self):
        self.current_session = self.Session()
        try:
            yield
            self.current_session.commit()
        except:
            self.current_session.rollback()
            raise
        finally:
            self.current_session.close()
            self.current_session = None

    def append(self, key, item):
        key = self.serialize(key)
        item = self.serialize(item)

        krow = self.current_session.query(MarkovKey).filter_by(key=key).first()
        if not krow:
            krow = MarkovKey(key=key)
            self.current_session.add(krow)

        vrow = MarkovValue(value=item)
        krow.values.append(vrow)
        self.current_session.add(vrow)

    def get(self, key):
        key = self.serialize(key)

        krow = self.current_session.query(MarkovKey).filter_by(key=key).first()
        if not krow:
            return None

        return [self.deserialize(vrow.value) for vrow in krow.values]

    def getrand(self, key):
        try:
            return random.choice(self.get(key))
        except:
            return None

    def getrandall(self):
        vrow = self.current_session.query(MarkovValue).order_by(self.r).first()
        if vrow:
            return self.deserialize(vrow.value)

        return None

    def keys(self):
        return [self.deserialize(krow.key)
                for krow in self.current_session.query(MarkovKey).all()]

    def length(self):
        return self.current_session.query(MarkovKey).count()

    @property
    def r(self):
        if self.url.startswith('sqlite'):
            return func.random()
        if self.url.startswith('mysql'):
            return func.rand()
        if self.url.startswith('postgresql'):
            return func.random()
        if self.url.startswith('oracle'):
            return 'dbms_random.value'
        raise NotImplementedError()
