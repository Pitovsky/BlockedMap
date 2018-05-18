# -*- coding: utf-8 -*-

from enum import Enum
import os
from datetime import datetime
import pandas as pd
from sqlalchemy import create_engine
import ipaddress
import pickle
from init_db import engine, BASEDIR, get_bin_ip, get_bin_prefix


full_geo_cache = os.path.join(BASEDIR, 'full_geo_cache.pickle')
min_date = datetime.strptime('Jan 1 2012', '%b %d %Y').date()
max_date = datetime.today().date()


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


def where_clause(orgs, ts_low, ts_high, time, group_by='latitude, longitude'):
	#TODO: parameterize with ?
	time_field = time
	query = ' where {2} is not null and {2} >= \'{0}\' and {2} <= \'{1}\''.format(ts_low, ts_high, time_field)
	query += ' and org in (\'' + str('\', \''.join([org.value for org in orgs])) + '\')'
	return query + ' group by {}'.format(group_by)
		

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


def select_ip(orgs=[org for org in Org], ts_low=min_date, ts_high=max_date, use_cache=True):
	# sorry about that..
	if use_cache and len(orgs) == len(Org) and ts_low == min_date and ts_high == max_date and os.path.isfile(full_geo_cache):
		with open(full_geo_cache, 'rb') as cache:
			try:
				data = pickle.load(cache)
				return data
			except:
				pass
	query = 'select latitude, longitude, sum(2 << (31 - length(prefix))), 1 as type, max(include_time) as time from blocked_ip'
	query += ' join geo_prefix on (prefix between (ip_bin || \'0\') and (ip_bin || \'1\')) or (prefix = ip_bin)'
	query += ' join block_geo on (block_geo.id = geo_id)'
	query += where_clause(orgs, ts_low, ts_high, 'include_time')
	query += ' union '
	query += 'select latitude, longitude, count(*), 1 as type, max(include_time) as time from blocked_ip'
	query += ' join block_geo on (block_id = blocked_ip.id) and (ip_subnet is null)'
	query += where_clause(orgs, ts_low, ts_high, 'include_time')
	query += ' union '
	query += 'select latitude, longitude, sum(2 << (31 - length(prefix))), 0 as type, max(exclude_time) as time from blocked_ip'
	query += ' join geo_prefix on (prefix between (ip_bin || \'0\') and (ip_bin || \'1\')) or (prefix = ip_bin)'
	query += ' join block_geo on (block_geo.id = geo_id)'
	query += where_clause(orgs, ts_low, ts_high, 'exclude_time')
	query += '  union '
	query += 'select latitude, longitude, count(*), 0 as type, max(exclude_time) as time from blocked_ip'
	query += ' join block_geo on (block_id = blocked_ip.id) and (ip_subnet is null)'
	query += where_clause(orgs, ts_low, ts_high, 'exclude_time')
	query += ' order by time, type desc'
	# print(query)
	data = engine.execute(query).fetchall()
	return data


def select_stats(orgs=[org for org in Org], ts_low=min_date, ts_high=max_date):
    query = 'select date, sum(blocked_number) as blocked, sum(unlocked_number) as unlocked from stats'
    query += where_clause(orgs, ts_low, ts_high, 'date', group_by='date')
    query += ' order by date'
    data = engine.execute(query).fetchall()

    start_ts = datetime.strptime(data[0]['date'], '%Y-%m-%d').timestamp() * 1000
    stats = [('Заблокировано', '#FF0000', start_ts, [item['blocked'] for item in data]),
             ('Разблокировано', '#00FF00', start_ts, [item['unlocked'] for item in data])]
    return stats


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
