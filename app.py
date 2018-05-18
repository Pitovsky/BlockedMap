from flask import Flask, render_template, redirect, request, url_for, jsonify
from requests import get
from urllib.parse import urlencode
from PIL import Image
from io import BytesIO
from datetime import datetime
import json
import locale

from ip_selector import Org, select_ip, select_stats
from update_from_repo import get_repo_state

locale.setlocale(locale.LC_ALL, 'ru_RU.UTF-8')

blocked_color = 'rgba(200, 10, 0, {})'
unlocked_color = 'rgba(40, 200, 0, {})'

app = Flask(__name__, static_folder='static')
gps = []

@app.route('/', methods=['GET'])
def draw_map():
    commit = get_repo_state()
    commit_time = datetime.fromtimestamp(commit.committed_date).strftime("%d.%m.%Y, %H:%M (UTC)")
    commit_sha = commit.hexsha[:7]
    link = 'https://github.com/zapret-info/z-i/commit/' + commit.hexsha
    return render_template('index.html',
                           app_id=app.app_id,
                           app_code=app.app_code,
                           last_updated_time=commit_time,
                           last_updated_sha=commit_sha,
                           last_updated_link=link)

@app.route('/filter',  methods=['POST'])
def make_info():
    data = request.form
    orgs = []
    ts_low = None
    ts_high = None
    for key in data:
        if key == "range":
            tss = data[key].split(" - ")
            ts_low = datetime.strptime(tss[0], "%d.%m.%Y").date()
            ts_high = datetime.strptime(tss[1], "%d.%m.%Y").date()
        else:
            orgs.append(getattr(Org, key))
    gps = [{'lat': p[0] if p[0] else 0, 
        'lng': p[1] if p[1] else 0, 
        'count': p[2] if p[2] else 0, 
        'fill_color': unlocked_color.format(0.9) if p[3] == 1 else blocked_color.format(0.9)}
        for p in select_ip(orgs, ts_low, ts_high)]
    stats = [{'name': kind, 'color': color, 'pointStart': start, 'pointInterval': 24 * 3600 * 1000, 'data': stat} for kind, color, start, stat in select_stats(orgs, ts_low, ts_high)]

    data = {'gps': gps, 'stats': stats}
    return jsonify(data)


try:
    with open('credentials.json') as fin:
        credentials = json.loads(fin.read())
        app.app_id, app.app_code = credentials['app_id'], credentials['app_code']
except (KeyError, FileNotFoundError, json.decoder.JSONDecodeError) as e:
    print("Error while reading HERE API credentials, proceed on your own risk!")
    print(e)


if __name__ == '__main__':
    app.run()
