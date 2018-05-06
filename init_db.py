# -*- coding: utf-8 -*-

import time
import random
import os, logging
from pprint import pprint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine, Table, Column, Integer, Float, String, Boolean, DateTime, MetaData, ForeignKey
from sqlalchemy.engine.url import URL
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy.schema import Index
from ipaddress import ip_network, ip_address

from ip_selector import get_bin_prefix, get_bin_ip


logger = logging.getLogger(__name__)
BASEDIR = os.path.abspath(os.path.dirname(__file__))
db_name = 'sqlite:///' + os.path.join(BASEDIR, 'roskomsvoboda.db')
engine = create_engine(db_name, echo=False)
Base = declarative_base()
Session = sessionmaker(bind=engine)


class BlockedIpData(Base):
    __tablename__ = 'blocked_ip'
    __table_args__ = {'sqlite_autoincrement': True}

    id = Column('id', Integer, primary_key=True)
    include_time = Column('include_time', String)
    exclude_time = Column('exclude_time', String)
    decision_date = Column('decision_date', String)
    decision_number = Column('decision_number', String)
    org = Column('org', String)
    ip = Column('ip', String)
    ip_subnet = Column('ip_subnet', String)
    ip_bin = Column('ip_bin', String)
    ip_bin_index = Index("ip_bin_index", ip_bin)
    org_index = Index("org_index", org)

    def __init__(self, data):
        self.include_time = data.get('include_time')
        self.exclude_time = data.get('exclude_time')
        self.decision_date = data.get('decision_date')
        self.decision_number = data.get('decision_number')
        self.org = data.get('org')
        self.ip = data.get('ip')
        self.ip_subnet = data.get('ip_subnet')
        self.ip_bin = get_bin_ip(ip_address(self.ip)) if self.ip else get_bin_prefix(ip_network(self.ip_subnet))

    def __repr__(self):
        return "<BlockedIpData({0}, {1})>".format(self.id, self.ip_bin)


class BlockGeoData(Base):
    __tablename__ = 'block_geo'
    __table_args__ = {'sqlite_autoincrement': True}

    id = Column('id', Integer, primary_key=True)
    block_id = Column('block_id', Integer, ForeignKey(BlockedIpData.id))
    longitude = Column('longitude', Float)
    latitude = Column('latitude', Float)

    def __init__(self, block_id, lon, lat):
        self.block_id = block_id
        self.longitude = lon
        self.latitude = lat


class GeoPrefix(Base):
    __tablename__ = 'geo_prefix'
    __table_args__ = {'sqlite_autoincrement': True}
    
    id = Column('id', Integer, primary_key=True)
    geo_id = Column('geo_id', Integer, ForeignKey('block_geo.id'))
    prefix = Column('prefix', String)
    prefix_index = Index("prefix_index", prefix)
    
    def __init__(self, geo_id, prefix):
        self.geo_id = geo_id
        self.prefix = prefix


def init():
    BlockedIpData.__table__.drop(engine, checkfirst=True)
    BlockGeoData.__table__.drop(engine, checkfirst=True)
    GeoPrefix.__table__.drop(engine, checkfirst=True)
    Base.metadata.create_all(engine)


if __name__ == '__main__':
    init()
