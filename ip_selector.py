from enum import Enum
from datetime import datetime
import pandas as pd
from sqlalchemy import create_engine

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

def select_ip(orgs=[], ts_low=datetime.min, ts_high=datetime.max):
	query = 'select ip from blocked_ip'
	if len(orgs) > 0:
		where_query = ' where org in (\'' + str('\', \''.join([org.value for org in orgs])) + '\')'
		query += where_query

	return pd.read_sql_query(query, engine)


if __name__ == '__main__':
	print(select_ip().shape)
	print(select_ip([Org.RPN]).shape)
	print(select_ip([Org.MGCOURT]).shape)
	print(select_ip([Org.MKS]).shape)
	print(select_ip([Org.RPN, Org.MGCOURT, Org.MKS]).shape)
