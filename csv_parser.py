# -*- coding: utf-8 -*-

import sys
import time
import random
import os, logging
import pandas as pd
from sqlalchemy.orm import sessionmaker

import init_bd
from init_bd import BlockedIpData, engine


logger = logging.getLogger(__name__)
Session = sessionmaker(bind=engine)


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
    session = Session()
    parse_blocked_csv(session, './data/dump.csv')
