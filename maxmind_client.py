import geoip2.database
import time
import requests
import os


BASEDIR = os.path.abspath(os.path.dirname(__file__))
reader = geoip2.database.Reader(os.path.join(BASEDIR, './data/maxmind/GeoLite2-City.mmdb'))


def get_locations_for_ip(addr, try_requests=True):
	try:
		loc = reader.city(addr).location
		return [{'latitude': loc.latitude, 
			'longitude': loc.longitude,
			'covered_percentage': 100,
			'prefixes': [addr]}]
	except Exception as e:
		if try_requests:
			time.sleep(0.16) #API limitations
			return requests.get('https://stat.ripe.net/data/geoloc/data.json?resource=' + addr).json()['data']['locations']
		else:
			return None
