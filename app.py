from flask import Flask, render_template, redirect, request
from requests import get
from urllib.parse import urlencode
from PIL import Image
from io import BytesIO
from datetime import datetime

from ip_selector import Org, select_ip

app = Flask(__name__, static_folder='static')

@app.route('/', methods=['GET'])
def draw_map():
    return render_template('index.html')

@app.route('/filter',  methods=['POST'])
def make_info():
    data = request.form
    orgs = []
    orgs.append(Org('Валежник'))
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
    for gp in gps:
        print(gp)
    return ""

if __name__ == '__main__':
    app.run()