import json
import locale
from datetime import datetime

from flask import Flask, render_template, request, jsonify

from ip_selector import Org, select_ip, select_stats
from update_from_repo import get_repo_state

locale.setlocale(locale.LC_ALL, 'ru_RU.UTF-8')


BLOCKED_COLOR = 'rgba(200, 10, 0, {})'
UNLOCKED_COLOR = 'rgba(40, 200, 0, {})'

app = Flask(__name__, static_folder='static')
gps = []

@app.route('/', methods=['GET'])
def draw_map():
    commit = get_repo_state()
    commit_time = datetime.fromtimestamp(commit.authored_date).strftime("%d.%m.%Y, %H:%M (UTC)")
    commit_sha = commit.hexsha[:7]
    link = 'https://github.com/zapret-info/z-i/commit/' + commit.hexsha
    return render_template('index.html',
                           app_id=app.app_id,
                           app_code=app.app_code,
                           last_updated_time=commit_time,
                           last_updated_sha=commit_sha,
                           last_updated_link=link)

@app.route('/filter', methods=['POST'])
def make_info():
    data = request.form
    print(data)
    orgs = []
    ts_low = None
    ts_high = None
    only_locked = False
    for key in data:
        if key == "range":
            tss = data[key].split(" - ")
            ts_low = datetime.strptime(tss[0], "%d.%m.%Y").date()
            ts_high = datetime.strptime(tss[1], "%d.%m.%Y").date()
        elif key == "only_locked":
            only_locked = True
        else:
            orgs.append(getattr(Org, key))
    gps = [
        {
            'lat': p[0] if p[0] else 0,
            'lng': p[1] if p[1] else 0,
            'count': p[2] if p[2] else 0,
            'fill_color': UNLOCKED_COLOR.format(0.9) if p[3] == 0 else BLOCKED_COLOR.format(0.9)
        }
        for p in select_ip(orgs, ts_low, ts_high, only_locked=only_locked)]

    stats = [
        {
            'name': kind,
            'color': color,
            'pointStart': start,
            'pointInterval': 24 * 3600 * 1000,
            'data': stat,
        }
        for kind, color, start, stat in select_stats(orgs, ts_low, ts_high, only_locked=only_locked)
    ]

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
