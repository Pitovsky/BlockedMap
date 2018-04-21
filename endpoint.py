from ip_selector import Org, select_ip

app = Flask(__name__)

@app.route('/')
def make_info():
    data = request.form
    return ""


if __name__ == '__main__':
    app.run()