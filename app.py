from flask import Flask, render_template, redirect, request, url_for, jsonify
from requests import get
from urllib.parse import urlencode
from PIL import Image
from io import BytesIO
from datetime import datetime
import json
import locale

from ip_selector import Org, select_ip

locale.setlocale(locale.LC_ALL, 'ru_RU.UTF-8')

app = Flask(__name__, static_folder='static')
gps = []

@app.route('/', methods=['GET'])
def draw_map():
    return render_template('index.html', app_id=app.app_id, app_code=app.app_code)

@app.route('/filter',  methods=['POST'])
def make_info():
    data = request.form
    orgs = []
    ts_low = None
    ts_high = None
    for key in data:
        if key == "range":
            tss = data[key].split(" - ")
            ts_low = datetime.strptime(tss[0], "%B %d, %Y")
            ts_high = datetime.strptime(tss[1], "%B %d, %Y")
        else:
            orgs.append(getattr(Org, key))
    gps = [{'lat': p[0] or 0, 'lng': p[1] if p[1] else 0, 'count': p[2] if p[2] else 0, 'color': 'rgba(200, 10, 0, 0.5'} for p in select_ip(orgs, ts_low, ts_high, blocked=True)] \
     + [{'lat': p[0], 'lng': p[1], 'count': p[2], 'color': 'rgba(40, 160, 0, 0.9'} for p in select_ip(orgs, ts_low, ts_high, blocked=False)]
    return jsonify(gps)

if __name__ == '__main__':
    try:
        with open('credentials.json') as fin:
            credentials = json.loads(fin.read())
            app.app_id, app.app_code = credentials['app_id'], credentials['app_code']
    except (KeyError, FileNotFoundError, json.decoder.JSONDecodeError) as e:
        print("Error while reading HERE API credentials, proceed on your own risk!")
        print(e)

    app.run()
