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
from tqdm import tqdm
import glob
import zipfile

from ip_selector import Org, get_bin_prefix, get_bin_ip


logger = logging.getLogger(__name__)
local_name = 'sqlite:///roskomsvoboda.db'
engine = create_engine(local_name, echo=False)
Base = declarative_base()
Session = sessionmaker(bind=engine)


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


def parse_blocked_xml(session, xml):
    soup = Soup(xml, "lxml")
    for content in soup.select("content"):
        xml = content.__str__()
        root = etree.fromstring(xml)
        data = {}

        data['content_id'] = root.attrib.get('id', '')
        data['include_time'] = root.attrib.get('includetime', '')
        data['entry_type'] = root.attrib.get('entrytype', '')
        data['block_type'] = root.attrib.get('blocktype', '')

        decision = root.find('./decision')
        data['decision_date'] = decision.attrib.get('date', '')
        data['decision_number'] = decision.attrib.get('number', '')
        data['org'] = decision.attrib.get('org', '')

        for ip in set(ip.text.strip('\n') for ip in root.findall('./ip')):
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


def parse_all_zips(session, archive_dir):
    for zip_path in tqdm(glob.glob(archive_dir + '/*.zip')):
        try:
            zip_dump = zipfile.ZipFile(zip_path)
            parse_blocked_xml(session, zip_dump.open('dump.xml').read())  
        except:
            print('ERROR: ' + zip_path)
            continue


if __name__ == '__main__':
    # BlockedIpData.__table__.drop(engine)
    Base.metadata.create_all(engine)
    session = Session()
    parse_all_zips(session, './data/dump_zip')
