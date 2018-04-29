# -*- coding: utf-8 -*-

import sys
import time
import random
from bs4 import BeautifulSoup as Soup
import os, logging
import json
import pandas as pd
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
local_name = 'sqlite:///roskomsvoboda_csv.db'
engine = create_engine(local_name, echo=False)
Base = declarative_base()
Session = sessionmaker(bind=engine)


class BlockedIpData(Base):
    __tablename__ = 'blocked_ip'
    __table_args__ = {'sqlite_autoincrement': True}

    id = Column('id', Integer, primary_key=True)
    include_time = Column('include_time', String)
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
        self.decision_date = data.get('decision_date')
        self.decision_number = data.get('decision_number')
        self.org = data.get('org')
        self.ip = data.get('ip')
        self.ip_subnet = data.get('ip_subnet')
        self.ip_bin = get_bin_ip(ip_address(self.ip)) if self.ip else get_bin_prefix(ip_network(self.ip_subnet))

    def __repr__(self):
        return "<BlockedIpData({0}, {1})>".format(self.content_id, self.ip)


def parse_blocked_csv(session, csv):
    df = pd.read_csv(csv, encoding='cp1251', sep=';', skiprows=1, header=None)
    df = df[df[0].isnull() == False]
    for index, row in df.iterrows():
        # print(row)
        data = {}

        data['include_time'] = row[5]
        data['decision_date'] = data['include_time']
        data['decision_number'] = row[4]
        data['org'] = row[3]

        for ip in str(row[0]).split('|'): 
            ip = ip.strip()
            if '/' in ip:
                data['ip_subnet'] = ip
            else:
                data['ip'] = ip
            # print(data)
            # input()
            session.add(BlockedIpData(data))
    session.commit()


if __name__ == '__main__':
    BlockedIpData.__table__.drop(engine)
    Base.metadata.create_all(engine)
    session = Session()
    parse_blocked_csv(session, './data/dump.csv')
