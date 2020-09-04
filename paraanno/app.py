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

    @property
    def get_batch_len(self):
        batch_num = len(self.data)
        return batch_num

    @property
    def get_anno_stats(self):
        completed = 0
        skipped = 0
        left = 0
        for pair in self.data:
            if "annotation" in pair:
                if "label" in pair["annotation"]:
                    if pair["annotation"]["label"]!="x":
                        completed += 1
                    else:
                        skipped += 1
                else:
                    left += 1
            else:
                left += 1
        return (completed, skipped, left)

    @property
    def get_update_timestamp(self):
        timestamps = [datetime.datetime.fromisoformat(pair["annotation"]["updated"]) for pair in self.data if "annotation" in pair]
        if not timestamps:
            return "no updates"
        else:
            return max(timestamps).isoformat()

    
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
    batch_anno_stats = [(fname, batch.get_batch_len, batch.get_anno_stats, batch.get_update_timestamp) for fname, batch in all_batches[user].items()]
    batch_anno_stats = sorted(batch_anno_stats, key=lambda x:x[0])

    # calculate total number of annotations
    total = 0
    t_done = 0
    t_skipped = 0
    t_left = 0
    for fname, batchlen, (done,skipped,left), _ in batch_anno_stats:
        total += batchlen
        t_done += done
        t_skipped += skipped
        t_left += left
    assert t_left + t_skipped + t_done == total
    
    return render_template("batch_list.html",app_root=APP_ROOT,batches=batch_anno_stats,user=user,stats=(t_done,t_skipped,t_left,total))

@app.route("/ann/<user>/<batchfile>")
def jobsinbatch(user,batchfile):
    global all_batches
    pairs=all_batches[user][batchfile].data
    pairdata=[]
    for idx,pair in enumerate(pairs):
        text1=pair["txt1"]
        text2=pair["txt2"]
        ann=pair.get("annotation",{})
        lab=""
        if ann:
            lab=ann.get("label","?")
        pairdata.append((idx,ann.get("updated","not updated"),lab,text1[:50],text2[:50]))
    return render_template("doc_list_in_batch.html",app_root=APP_ROOT,user=user,batchfile=batchfile,pairdata=pairdata)

@app.route("/saveann/<user>/<batchfile>/<pairseq>",methods=["POST"])
def save_document(user,batchfile,pairseq):
    global all_batches
    pairseq=int(pairseq)
    annotation=request.json
    pair=all_batches[user][batchfile].data[pairseq]
    annotation["updated"]=datetime.datetime.now().isoformat()
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
    
    labels=[("4","4: Paraphrase"), ("3","3: Partial paraphrase"), ("2","2: Related but not paraphrase"), ("1","1: Unrelated"), ("x","x: Skip")]
    return render_template("doc.html",app_root=APP_ROOT,text1=text1,text2=text2,pairseq=pairseq,batchfile=batchfile,user=user,annotation=annotation,labels=labels,is_last=(pairseq==len(all_batches[user][batchfile].data)-1))

