# -*- coding: utf-8 -*-

import contextlib

from sqlalchemy import create_engine
from sqlalchemy import Integer, String
from sqlalchemy import Column, ForeignKey
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql.expression import func

from .. import db


Base = declarative_base()


class MarkovKey(Base):
    __tablename__ = 'markov_key'

    id = Column(Integer, primary_key=True)
    key = Column(String(255), unique=True, nullable=False)
    values = relationship('MarkovValue', uselist=True, backref='key',
                          cascade='all, delete-orphan')


class MarkovValue(Base):
    __tablename__ = 'markov_value'

    id = Column(Integer, primary_key=True)
    key_id = Column(Integer, ForeignKey(MarkovKey.id), nullable=False)
    value = Column(String(255), nullable=False)


class EntrypointKey(Base):
    __tablename__ = 'entrypoint_key'

    id = Column(Integer, primary_key=True)
    key = Column(String(255), unique=True, nullable=False)
    values = relationship('EntrypointValue', uselist=True, backref='key',
                          cascade='all, delete-orphan')


class EntrypointValue(Base):
    __tablename__ = 'entrypoint_value'

    id = Column(Integer, primary_key=True)
    key_id = Column(Integer, ForeignKey(EntrypointKey.id), nullable=False)
    value = Column(String(255), nullable=False)


@db.dbclass(db.DBTYPE_MARKOV)
class MarkovSQL(db.Database):
    TABLE_KEY = MarkovKey
    TABLE_VALUE = MarkovValue

    def __init__(self, url, echo='false', **kw):
        echo = echo.lower() == 'true'
        self.url = url
        self.current_session = None
        self.Engine = create_engine(url, encoding='utf-8', echo=echo, **kw)
        self.Session = sessionmaker(bind=self.Engine)
        Base.metadata.create_all(self.Engine, [self.TABLE_KEY.__table__,
                                               self.TABLE_VALUE.__table__])

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

        q = self.current_session.query(self.TABLE_KEY)
        krow = q.filter_by(key=key).first()
        if not krow:
            krow = self.TABLE_KEY(key=key)
            self.current_session.add(krow)

        krow.values.append(self.TABLE_VALUE(value=item))

    def get(self, key):
        key = self.serialize(key)

        q = self.current_session.query(self.TABLE_KEY)
        krow = q.filter_by(key=key).first()
        if not krow:
            return None

        return [self.deserialize(vrow.value) for vrow in krow.values]

    def getrand(self, key):
        subq = self.current_session.query(self.TABLE_VALUE)
        subq = subq.join(self.TABLE_VALUE.key)
        subq = subq.filter(self.TABLE_KEY.key == self.serialize(key))
        subq = subq.order_by(self.r).limit(1).subquery()
        q = self.current_session.query(self.TABLE_VALUE, subq)
        q = q.filter(self.TABLE_VALUE.id == subq.c.id)
        vrows = q.first()
        return self.deserialize(vrows[0].value) if vrows else None

    def getrandall(self):
        subq = self.current_session.query(self.TABLE_VALUE.id)
        subq = subq.order_by(self.r).limit(1).subquery()
        q = self.current_session.query(self.TABLE_VALUE, subq)
        q = q.filter(self.TABLE_VALUE.id == subq.c.id)
        vrows = q.first()
        return self.deserialize(vrows[0].value) if vrows else None

    def keys(self):
        return [self.deserialize(krow.key)
                for krow in self.current_session.query(self.TABLE_KEY).all()]

    def length(self):
        return self.current_session.query(self.TABLE_KEY).count()

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


@db.dbclass(db.DBTYPE_ENTRYPOINT)
class EntrypointSQL(MarkovSQL):
    TABLE_KEY = EntrypointKey
    TABLE_VALUE = EntrypointValue
