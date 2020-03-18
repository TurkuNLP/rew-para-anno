from flask import Flask
from flask import render_template
app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True

@app.route('/')
def hello_world():
    return render_template("index.html")

@app.route("/ann/<user>/<docpair>")
def fetch_document(user,docpair):
    return render_template("doc.html",user=user,docpair=docpair)

