# -*- coding: utf-8 -*-
import sys
from bs4 import BeautifulSoup as Soup
import os, logging
import json
from pprint import pprint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine, Table, Column, Integer, String, Boolean, DateTime, MetaData, ForeignKey
from sqlalchemy.engine.url import URL
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from lxml import etree

logger = logging.getLogger(__name__)
local_name = 'sqlite:///roskomsvoboda.db'
engine = create_engine(local_name, echo=True)
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

    def __repr__(self):
        return "<UserData({0}, {1})>".format(self.content_id, self.ip)


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
            print(ip)
            data['ip'] = ip
            session.add(BlockedIpData(data))
        data['ip'] = None
        for ip_subnet in set(ip_subnet.text.strip('\n') for ip_subnet in root.findall('./ipsubnet')):
            data['ip_subnet'] = ip_subnet
            session.add(BlockedIpData(data))
    session.commit()
   

if __name__ == '__main__':
    Base.metadata.create_all(engine)

    session = Session()
    parse_blocked(session, 'data/dump2.xml')    