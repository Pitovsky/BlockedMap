from flask import Flask, render_template
from requests import get
from urllib.parse import urlencode
from PIL import Image
from io import BytesIO

app = Flask(__name__, static_folder='static')


MAPVIEW_URL = 'https://image.maps.cit.api.here.com/mia/1.6/mapview'

'''
def get_map_img():
    params = urlencode(
    {
        'vt': 1,
        'z': 2,
        'w': 1600,
        'h': 900,
    })
    response = get('{}?{}'.format(MAPVIEW_URL, params))
    if response.status_code != 200:
        raise Exception("bad response code while map retrieval: code {}".format(response.status_code))
    img = Image.open(BytesIO(response.content))
    name = "tmpimg" + ".jpg"
    img.save("static/" + name, "JPEG")
    return name
'''


@app.route('/')
def draw_map():
    # global_map_name = get_map_img()
    return render_template('index.html')


if __name__ == '__main__':
    app.run()