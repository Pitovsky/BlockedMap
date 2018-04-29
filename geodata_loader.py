# -*- coding: utf-8 -*-

import sys
import time
import random
from bs4 import BeautifulSoup as Soup
import os, logging
import json
from pprint import pprint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine, Table, Column, Integer, Float, String, Boolean, DateTime, MetaData, ForeignKey
from sqlalchemy.engine.url import URL
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy.schema import Index
from ipaddress import ip_network, ip_address
from tqdm import tqdm

from maxmind_client import get_locations_for_ip
from ip_selector import get_bin_prefix, get_bin_ip, filter_ip
from xml_parser import BlockedIpData


NUM_INDIVIDUAL_IPS = 0
logger = logging.getLogger(__name__)
local_name = 'sqlite:///roskomsvoboda_csv.db'
engine = create_engine(local_name, echo=False)
Base = declarative_base()
Session = sessionmaker(bind=engine)


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

    def __repr__(self):
        return "<IpGeoData({0}, {1})>".format(self.id, self.block_id)


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


def load_some_geodata(session, addresses, is_subnet=False):
    geo_map = dict()
    for block_id, addr in tqdm(addresses.items()):
        response = {}
        if addr.startswith('127'):
            loc = {}
            loc['latitude'] = random.uniform(52.297, 63.996)
            loc['longitude'] = random.uniform(29.307, 135.654)
            loc['covered_percentage'] = 100
            loc['prefixes'] = [addr]
            locations = [loc]
        else:
            try:
                locations = get_locations_for_ip(addr, is_subnet)
                if not locations:
                    continue
            except:
                continue
        geo_map[block_id] = locations

    for block_id, locations in geo_map.items():
        for loc in locations:
            block_geo = BlockGeoData(block_id, loc['longitude'], loc['latitude'])
            session.add(block_geo)
            session.flush()
            prefix_bins = []
            for prefix in loc['prefixes']:
                prefix_bins.append(get_bin_prefix(ip_network(prefix)))
            if is_subnet:
                prefix_bin = get_bin_prefix(ip_network(addresses[block_id]))
                if not prefix_bin in prefix_bins:
                    prefix_bins.append(prefix_bin)
            for prefix in prefix_bins:
                session.add(GeoPrefix(block_geo.id, prefix))


def load_geodata(session):
    data = session.query(BlockedIpData.id, BlockedIpData.ip, BlockedIpData.ip_subnet).all()
    session.rollback()
    subnets_data = {row[0]: row[2] for row in data if row[2]}
    load_some_geodata(session, subnets_data, True)

    ips_data = {row[0]: row[1] for row in data if row[1]}
    print(len(ips_data))
    top_level_ips = filter_ip(ips_data, {})
    print(len(top_level_ips))
    sample = {_id: top_level_ips[_id] for _id in random.sample(top_level_ips.keys(), min(NUM_INDIVIDUAL_IPS, len(top_level_ips)))}
    load_some_geodata(session, top_level_ips)
                      
    session.commit()


if __name__ == '__main__':
    # BlockGeoData.__table__.drop(engine)
    # GeoPrefix.__table__.drop(engine)
    Base.metadata.create_all(engine)
    session = Session()
    load_geodata(session)
