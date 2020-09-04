from werkzeug.middleware.dispatcher import DispatcherMiddleware
import flask
from flask import Flask
from flask import render_template, request
import os
import glob
from sqlitedict import SqliteDict
import json
import datetime
import difflib
import html


app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True
APP_ROOT = os.environ.get('PARAANN_APP_ROOT',"")
app.config["APPLICATION_ROOT"] = APP_ROOT

DATADIR=os.environ["PARAANN_DATA"]

def read_batches():
    batchdict={} #user -> batchfile -> Batch
    batchfiles=sorted(glob.glob(DATADIR+"/batches-*/*.json"))
    for b in batchfiles:
        dirname,fname=b.split("/")[-2:]
        user=dirname.replace("batches-","")
        batchdict.setdefault(user,{})[fname]=Batch(b)
    return batchdict
        
       
class Batch:

    def __init__(self,batchfile):
        self.batchfile=batchfile
        with open(batchfile) as f:
            self.data=json.load(f) #this is a list of sentence pairs to annotate

    def save(self):
        s=json.dumps(self.data,ensure_ascii=False,indent=2,sort_keys=True)
        with open(self.batchfile,"wt") as f:
            print(s,file=f)
        
def init():
    global all_batches
    all_batches=read_batches()

init()            

@app.route('/')
def hello_world():
    global all_batches
    return render_template("index.html",app_root=APP_ROOT,users=sorted(all_batches.keys()))

@app.route("/ann/<user>")
def batchlist(user):
    global all_batches
    return render_template("batch_list.html",app_root=APP_ROOT,batches=sorted(all_batches[user].keys()),user=user)

@app.route("/ann/<user>/<batchfile>")
def jobsinbatch(user,batchfile):
    global all_batches
    pairs=all_batches[user][batchfile].data
    pairdata=[]
    for idx,pair in enumerate(pairs):
        text1=pair["txt1"]
        text2=pair["txt2"]
        pairdata.append((idx,pair.get("updated","not updated"),text1[:50],text2[:50]))
    return render_template("doc_list_in_batch.html",app_root=APP_ROOT,user=user,batchfile=batchfile,pairdata=pairdata)

@app.route("/saveann/<user>/<batchfile>/<pairseq>",methods=["POST"])
def save_document(user,batchfile,pairseq):
    global all_batches
    pairseq=int(pairseq)
    annotation=request.json
    pair=all_batches[user][batchfile].data[pairseq]
    pair["updated"]=datetime.datetime.now().isoformat()
    pair["annotation"]=annotation
    all_batches[user][batchfile].save()
    return "",200

@app.route("/ann/<user>/<batchfile>/<pairseq>")
def fetch_document(user,batchfile,pairseq):
    global all_batches
    pairseq=int(pairseq)
    pair=all_batches[user][batchfile].data[pairseq]
    
    # {
    # "d1": [
    #   "hs",
    #   "2020-01-08-23-00-04---84c7baba125d4592e300ffbe5e04396a.txt"
    # ],
    # "d2": [
    #   "yle",
    #   "2020-01-08-21-03-47--3-11148909.txt"
    # ],
    # "sim": 0.9922545481090577
    # }

    text1=pair["txt1"]
    text2=pair["txt2"]

    annotation=pair.get("annotation",{})

    labels=[("4","Paraphrase"), ("3","Near paraphrase"), ("2","Related but not paraphrase"), ("1","Unrelated")]
    return render_template("doc.html",app_root=APP_ROOT,text1=text1,text2=text2,pairseq=pairseq,batchfile=batchfile,user=user,annotation=annotation,labels=labels,is_last=(pairseq==len(all_batches[user][batchfile].data)-1))

