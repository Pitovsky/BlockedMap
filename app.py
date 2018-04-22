from flask import Flask, render_template, redirect, request, url_for
from requests import get
from urllib.parse import urlencode
from PIL import Image
from io import BytesIO
from datetime import datetime

from ip_selector import Org, select_ip

app = Flask(__name__, static_folder='static')
gps = []

@app.route('/', methods=['GET'])
def draw_map():
    return render_template('index.html', points=gps)

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
    gps = select_ip(orgs, ts_low, ts_high)
    valezhnik = select_ip([Org('Валежник')], ts_low, ts_high)
    return render_template('index.html', points=gps, valezhnik=valezhnik)
    # return redirect("")

if __name__ == '__main__':
    app.run()