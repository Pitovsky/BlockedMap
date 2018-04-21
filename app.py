from flask import Flask, render_template, redirect, request
from requests import get
from urllib.parse import urlencode
from PIL import Image
from io import BytesIO

from ip_selector import Org, select_ip

app = Flask(__name__, static_folder='static')

@app.route('/')
def draw_map():
    return render_template('index.html')


if __name__ == '__main__':
    app.run()