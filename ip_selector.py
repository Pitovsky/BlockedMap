from enum import Enum
from datetime import datetime
import pandas as pd
from sqlalchemy import create_engine
import ipaddress


local_name = 'sqlite:///roskomsvoboda.db'
engine = create_engine(local_name, echo=False)


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
	CWD = 'Валежник'


def get_bin_ip(address):
	return str(bin(int(address.packed.hex(), 16)))

def get_bin_prefix(network):
	return str(bin(int(network.network_address.packed.hex(), 16)))[:network.prefixlen]


def filter_ip(ip_df, subnet_df):
	top_level_id = []
	networks_binary = []
	# get all networks in binary format
	for index, row in subnet_df.iterrows():
		_id, subnet = row
		network = ipaddress.ip_network(subnet, strict=True)
		networks_binary.append((get_bin_ip(ipaddress.ip_address(network.network_address)), _id, network))
	networks_binary.sort(key=lambda x:x[0])
	# get top networks (sorted lexicographically)
	networks_top = []
	current_top_addr, current_top_network = None, None
	for addr, _id, network in networks_binary:
		if current_top_addr is None or not addr.startswith(current_top_addr):
			current_top_addr, current_top_network = addr, network
			networks_top.append((current_top_addr, current_top_network))
			top_level_id.append(_id)
	# get top-level individual ips
	for index, row in ip_df.iterrows():
		_id, ip = row
		bin_addr = get_bin_ip(ipaddress.ip_address(ip))
		found = False
		for addr, network in networks_top:
			if bin_addr.startswith(addr):
				found = True
		if not found:
			top_level_id.append(_id)
	return top_level_id
		

def select_ip(orgs=[], ts_low=datetime.min, ts_high=datetime.max):
	#TODO: parameterize with ?
	query = 'select distinct latitude, longitude, coalesce(sum(2 << (31 - length(prefix))), 1) from blocked_ip'
	query += ' left outer join geo_prefix on (prefix like ip_bin || \'%\')'
	query += ' join block_geo on (block_geo.id = geo_id) or (geo_id isnull and block_geo.block_id = blocked_ip.id)'
	query += ' where include_time > \'{0}\' and include_time < \'{1}\''.format(ts_low, ts_high)
	if len(orgs) > 0:
		where_query = ' and org in (\'' + str('\', \''.join([org.value for org in orgs])) + '\')'
		query += where_query
	query += ' group by geo_id'
	return engine.execute(query)


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
