# -*- coding: utf-8 -*-

import random
import logging
from ipaddress import ip_network

from sqlalchemy.orm import sessionmaker

from maxmind_client import get_locations_for_ip
from ip_selector import filter_ip
from init_db import BlockedIpData, GeoPrefix, BlockGeoData, engine, get_bin_prefix


NUM_INDIVIDUAL_IPS = 0
logger = logging.getLogger(__name__)
Session = sessionmaker(bind=engine)


def load_some_geodata(session, addresses, is_subnet=False):
    geo_map = dict()
    for block_id, addr in addresses.items():
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
    top_level_ips = filter_ip(ips_data, {})
    load_some_geodata(session, top_level_ips)

    session.commit()


if __name__ == '__main__':
    session = Session()
    load_geodata(session)
