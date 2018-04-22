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


def where_clause(orgs, ts_low, ts_high):
	#TODO: parameterize with ?
	query = ' where include_time > \'{0}\' and include_time < \'{1}\''.format(ts_low, ts_high)
	if len(orgs) > 0:
		query += ' and org in (\'' + str('\', \''.join([org.value for org in orgs])) + '\')'
	return query + ' group by latitude, longitude'
		

def select_ip(orgs=[], ts_low=datetime.min, ts_high=datetime.max):
	query = 'select latitude, longitude, sum(2 << (31 - length(prefix))) from blocked_ip'
	query += ' join geo_prefix on (prefix between (ip_bin || \'0\') and (ip_bin || \'1\')) or (prefix = ip_bin)'
	query += ' join block_geo on (block_geo.id = geo_id)'
	query += where_clause(orgs, ts_low, ts_high)
	query += '  union '
	query += 'select latitude, longitude, count(*) from blocked_ip'
	query += ' join block_geo on (block_id = blocked_ip.id) and (ip_subnet is null)'
	query += where_clause(orgs, ts_low, ts_high)
	#print(query)
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
