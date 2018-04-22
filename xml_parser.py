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
from lxml import etree
from ipaddress import ip_network, ip_address
import requests
from tqdm import tqdm

from ip_selector import Org, get_bin_prefix, get_bin_ip, filter_ip

logger = logging.getLogger(__name__)
local_name = 'sqlite:///roskomsvoboda.db'
engine = create_engine(local_name, echo=False)
Base = declarative_base()
Session = sessionmaker(bind=engine)

count = 0

class BlockedIpData(Base):
    __tablename__ = 'blocked_ip'
    __table_args__ = {'sqlite_autoincrement': True}

    id = Column('id', Integer, primary_key=True)
    content_id = Column('content_id', String)
    include_time = Column('include_time', String)
    entry_type = Column('entry_type', String)
    block_type = Column('block_type', String)
    decision_date = Column('decision_date', String)
    decision_number = Column('decision_number', String)
    org = Column('org', String)
    # url = Column('url', String)
    # domain = Column('domain', String)
    ip = Column('ip', String)
    ip_subnet = Column('ip_subnet', String)
    ip_bin = Column('ip_bin', String)
    
    ip_bin_index = Index("ip_bin_index", ip_bin)

    def __init__(self, data):
        # self.id = count
        # count += 1
        self.content_id = data.get('content_id')
        self.include_time = data.get('include_time')
        self.entry_type = data.get('entry_type')
        self.block_type = data.get('block_type')
        self.decision_date = data.get('decision_date')
        self.decision_number = data.get('decision_number')
        self.org = data.get('org')
        # self.url = data.get('url')
        # self.domain = data.get('domain')
        self.ip = data.get('ip')
        self.ip_subnet = data.get('ip_subnet')
        self.ip_bin = get_bin_ip(ip_address(self.ip)) if self.ip else get_bin_prefix(ip_network(self.ip_subnet))

    def __repr__(self):
        return "<BlockedIpData({0}, {1})>".format(self.content_id, self.ip)


class BlockGeoData(Base):
    __tablename__ = 'block_geo'
    __table_args__ = {'sqlite_autoincrement': True}

    id = Column('id', Integer, primary_key=True)
    block_id = Column('block_id', Integer, ForeignKey('blocked_ip.id'))
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


def parse_blocked(session, xml_path):
    handler = open(xml_path).read()
    soup = Soup(handler, "lxml")
    for content in soup.select("content"):
        xml = content.__str__()
        root = etree.fromstring(xml)
        data = {}

        # print(root.attrib)
        data['content_id'] = root.attrib.get('id', '')
        data['include_time'] = root.attrib.get('includetime', '')
        data['entry_type'] = root.attrib.get('entrytype', '')
        data['block_type'] = root.attrib.get('blocktype', '')

        decision = root.find('./decision')
        data['decision_date'] = decision.attrib.get('date', '')
        data['decision_number'] = decision.attrib.get('number', '')
        data['org'] = decision.attrib.get('org', '')

        for ip in set(ip.text.strip('\n') for ip in root.findall('./ip')):
            #print(ip)
            data['ip'] = ip
            session.add(BlockedIpData(data))
        data['ip'] = None
        for ip_subnet in set(ip_subnet.text.strip('\n') for ip_subnet in root.findall('./ipsubnet')):
            data['ip_subnet'] = ip_subnet
            session.add(BlockedIpData(data))
    session.commit()

def generate_cwd(session):
    CWD_COUNT = 255
    CWD_SIZE_MIN = 2
    CWD_SIZE_MAX = 10
    for i in range(CWD_COUNT):
        data = {}
        data['content_id'] = 'cwd' + str(i)
        data['include_time'] = '2018-04-18T08:00:00'
        data['entry_type'] = 7
        data['block_type'] = 'domain'
        
        data['decision_date'] = '2018-04-18'
        data['decision_number'] = '77-ФЗ'
        data['org'] = Org.CWD.value
        
        if random.random() > 0.0:
            data['ip_subnet'] = '127.' + str(i) + '.0.0/' + str(32 - random.randint(CWD_SIZE_MIN, CWD_SIZE_MAX))
        else:
            data['ip'] = '127.15.' + str(i) + '.1'
        session.add(BlockedIpData(data))
    session.commit()
    
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
            response = {'data':{'locations':[loc]}}
        else:
            time.sleep(0.16) #API limitations
            response = requests.get('https://stat.ripe.net/data/geoloc/data.json?resource=' + addr).json()
        geo_map[block_id] = response['data']['locations']

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
                print(block_geo.id, prefix)
                session.add(GeoPrefix(block_geo.id, prefix))

def load_geodata(session):
    data = session.query(BlockedIpData.id, BlockedIpData.ip, BlockedIpData.ip_subnet).all()
    session.rollback()
    subnets_data = {row[0]: row[2] for row in data if row[2]}
    load_some_geodata(session, subnets_data, True)

    ips_data = {row[0]: row[1] for row in data if row[1]}
    top_level_ips = filter_ip(ips_data, subnets_data)
    sample = {_id: top_level_ips[_id] for _id in random.sample(top_level_ips.keys(), 10)}
    load_some_geodata(session, sample)
                      
    session.commit()


if __name__ == '__main__':
    Base.metadata.create_all(engine)

    session = Session()
    parse_blocked(session, 'data/dump2.xml')  
    generate_cwd(session)
    load_geodata(session)  
