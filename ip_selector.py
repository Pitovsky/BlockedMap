# -*- coding: utf-8 -*-

from enum import Enum
import os
from datetime import datetime
import pandas as pd
from sqlalchemy import create_engine
import ipaddress
import pickle
from init_db import engine, BASEDIR


full_geo_cache = os.path.join(BASEDIR, 'full_geo_cache.pickle')


class Org(Enum):
	FSKN = 'ФСКН'
	RPN = 'Роспотребнадзор'
	RKN = 'Роскомнадзор'
	COURT = 'суд'
	GP = 'Генпрокуратура'
	MGCOURT = 'Мосгорсуд'
	FNS = 'ФНС'
	MVD = 'МВД'
	MKS = 'Минкомсвязь'
	# CWD = 'Валежник'


def where_clause(orgs, ts_low, ts_high, blocked):
	#TODO: parameterize with ?
	time_field = "include_time" if blocked else "exclude_time"
	query = ' where {2} is not null and {2} >= \'{0}\' and {2} <= \'{1}\''.format(ts_low, ts_high, time_field)
	if len(orgs) > 0:
		query += ' and org in (\'' + str('\', \''.join([org.value for org in orgs])) + '\')'
	return query + ' group by latitude, longitude'
		

def filter_ip(ip_dict, subnet_dict):
	top_level_ip = {}
	networks_binary = []
	# get all networks in binary format
	for _id, subnet in subnet_dict.items():
		network = ipaddress.ip_network(subnet, strict=True)
		networks_binary.append((get_bin_ip(ipaddress.ip_address(network.network_address)).rstrip('0'), _id, network))
	networks_binary.sort(key=lambda x:x[0])
	# get top networks (sorted lexicographically)
	networks_top = []
	current_top_addr, current_top_network = None, None
	for addr, _id, network in networks_binary:
		if current_top_addr is None or not addr.startswith(current_top_addr):
			current_top_addr, current_top_network = addr, network
			networks_top.append((current_top_addr, current_top_network))
			# top_level_id.append(_id)
	# get top-level individual ips
	top_level_set = set()
	for _id, ip in ip_dict.items():
		bin_addr = get_bin_ip(ipaddress.ip_address(ip)).rstrip('0')
		found = False
		for addr, network in networks_top:
			if bin_addr.startswith(addr):
				found = True
		if not found and ip not in top_level_set:
			top_level_ip[_id] = ip
			top_level_set.add(ip)
	return top_level_ip


def select_ip(orgs=[], ts_low=datetime.min, ts_high=datetime.max, use_cache=True):
	# sorry about that..
	if use_cache and len(orgs) in (0, len(Org)) and ts_low == datetime.min and ts_high == datetime.max and os.path.isfile(full_geo_cache):
		with open(full_geo_cache, 'rb') as cache:
			return pickle.load(cache)
	query = 'select latitude, longitude, sum(2 << (31 - length(prefix))), 1 as type, max(include_time) as time from blocked_ip'
	query += ' join geo_prefix on (prefix between (ip_bin || \'0\') and (ip_bin || \'1\')) or (prefix = ip_bin)'
	query += ' join block_geo on (block_geo.id = geo_id)'
	query += where_clause(orgs, ts_low, ts_high, True)
	query += ' union '
	query += 'select latitude, longitude, count(*), 1 as type, max(include_time) as time from blocked_ip'
	query += ' join block_geo on (block_id = blocked_ip.id) and (ip_subnet is null)'
	query += where_clause(orgs, ts_low, ts_high, True)
	query += ' union '
	query += 'select latitude, longitude, sum(2 << (31 - length(prefix))), 0 as type, max(exclude_time) as time from blocked_ip'
	query += ' join geo_prefix on (prefix between (ip_bin || \'0\') and (ip_bin || \'1\')) or (prefix = ip_bin)'
	query += ' join block_geo on (block_geo.id = geo_id)'
	query += where_clause(orgs, ts_low, ts_high, False)
	query += '  union '
	query += 'select latitude, longitude, count(*), 0 as type, max(exclude_time) as time from blocked_ip'
	query += ' join block_geo on (block_id = blocked_ip.id) and (ip_subnet is null)'
	query += where_clause(orgs, ts_low, ts_high, False)
	query += ' order by time, type desc'
	# print(query)
	data = engine.execute(query)
	return data


def smart_print(orgs):
	pass
	#print('{0} : {1}'.format(orgs, len(select_ip(orgs))))


if __name__ == '__main__':
	smart_print([])	
	smart_print([Org.FSKN])
	smart_print([Org.RPN])
	smart_print([Org.RKN])
	smart_print([Org.COURT])
	smart_print([Org.GP])
	smart_print([Org.MGCOURT])
	smart_print([Org.FNS])
	smart_print([Org.MVD])
	smart_print([Org.MKS])
	
	res = select_ip()
	for row in res:
		print(row)
