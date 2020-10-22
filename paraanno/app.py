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
                    if pair["annotation"]["label"]=="x":
                        skipped += 1
                    elif "|" in pair["annotation"]["label"] or pair["annotation"]["label"].strip() == "": # label not completed
                        left+=1
                    else:
                        completed += 1
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
        flag="false"
        if ann:
            lab=ann.get("label","?")
            flag=ann.get("flagged", "false")
        pairdata.append((idx,ann.get("updated","not updated"),flag,lab,text1[:50],text2[:50]))
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
    
    return render_template("doc.html",app_root=APP_ROOT,text1=text1,text2=text2,pairseq=pairseq,batchfile=batchfile,user=user,annotation=annotation,is_last=(pairseq==len(all_batches[user][batchfile].data)-1))
    


@app.route("/flags")
def flags():
    global all_batches
    pairdata=[]
    for user in all_batches.keys():
        for batchfile in all_batches[user].keys():
            pairs=all_batches[user][batchfile].data
            for idx,pair in enumerate(pairs):
                text1=pair["txt1"]
                text2=pair["txt2"]
                ann=pair.get("annotation",{})
                if ann:
                    lab=ann.get("label","?")
                    flag=ann.get("flagged", "false")
                    if flag=="true":
                        pairdata.append((user, batchfile, idx,ann.get("updated","not updated"),flag,lab,text1[:50],text2[:50]))
    pairdata = sorted(pairdata, key = lambda x: (x[3],x[1]), reverse=True)
    return render_template("all_flags.html",app_root=APP_ROOT,pairdata=pairdata)

@app.route("/ann/<user>/flags")
def user_flags(user):
    global all_batches
    pairdata=[]
    for batchfile in all_batches[user].keys():
        pairs=all_batches[user][batchfile].data
        for idx,pair in enumerate(pairs):
            text1=pair["txt1"]
            text2=pair["txt2"]
            ann=pair.get("annotation",{})
            if ann:
                lab=ann.get("label","?")
                flag=ann.get("flagged", "false")
                if flag=="true":
                    pairdata.append((user, batchfile, idx,ann.get("updated","not updated"),flag,lab,text1[:50],text2[:50]))
    pairdata = sorted(pairdata, key = lambda x: x[3], reverse=True)
    return render_template("user_flags.html",app_root=APP_ROOT,user=user,pairdata=pairdata)
 
    
@app.route("/ann/<user>/<batchfile>/<pairseq>/context")
def fetch_context(user,batchfile,pairseq):
    global all_batches
    pairseq=int(pairseq)
    pair=all_batches[user][batchfile].data[pairseq]

    text1=pair.get("document_context1", "")
    text2=pair.get("document_context2", "")

    blocks=matches(text1,text2,15) #matches are (idx1,idx2,len)
    spandata1,min1,max1=build_spans(text1,list((b[0],b[2]) for b in blocks))
    spandata2,min2,max2=build_spans(text2,list((b[1],b[2]) for b in blocks))
    
    
    return render_template("context.html", app_root=APP_ROOT, left_text=text1, right_text=text2, left_spandata=spandata1, right_spandata=spandata2, pairseq=pairseq, batchfile=batchfile, user=user, min_mlen=min(min1,min2), max_mlen=max(max1,max2)+1, mlenv=min(max(max1,max2),30), is_last=(pairseq==len(all_batches[user][batchfile].data)-1), focus_left=pair.get("focus1", ""), focus_right=pair.get("focus2", ""))
    
   



def matches(s1,s2,minlen=5):
    m=difflib.SequenceMatcher(None,s1,s2,autojunk=False)

    #returns list of (idx1,idx2,len) perfect matches
    return sorted(matches_r(m,s1,s2,minlen,0,len(s1),0,len(s2)), key=lambda match: (match[2], match[0]))

def matches_r(m,s1,s2,min_len,s1_beg,s1_end,s2_beg,s2_end):
    lm=m.find_longest_match(s1_beg,s1_end,s2_beg,s2_end)
    if lm.size<min_len:
        return []
    else:
        s1_left=s1_beg,lm.a
        s1_right=lm.a+lm.size,s1_end
        s1_all=(s1_beg,s1_end)
        
        s2_left=s2_beg,lm.b
        s2_right=lm.b+lm.size,s2_end
        s2_all=(s2_beg,s2_end)
        
        matches=[(lm.a,lm.b,lm.size)]
        for i1,i2 in ((s1_left,s2_left),(s1_left,s2_right),(s1_right,s2_left),(s1_right,s2_right)):
            #try all combinations of what remains
            if i1[1]-i1[0]<min_len:
                continue #too short to produce match
            if i2[1]-i2[0]<min_len:
                continue #too short to produce match
            sub=matches_r(m,s1,s2,min_len,*i1,*i2)
            matches.extend(sub)
        return matches

def build_spans(s,blocks):
    """s:string, blocks are pairs of (idx,len) of perfect matches"""
    if not blocks:
        return [], 0, 0
    #allright, this is pretty dumb alg!
    matched_indices=[0]*len(s)
    for i,l in blocks:
        for idx in range(i,i+l):
            matched_indices[idx]=max(matched_indices[idx],l)
    spandata=[]
    for c,matched_len in zip(s,matched_indices):
        #matched_len=(matched_len//5)*5
        if not spandata or spandata[-1][1]!=matched_len: #first or span with opposite match polarity -> must make new!
            spandata.append(([],matched_len))
        spandata[-1][0].append(c)
    merged_spans=[(html.escape("".join(chars)),matched_len) for chars,matched_len in spandata]
    return merged_spans, min(matched_indices),max(matched_indices) #min is actually always 0, but it's here for future need

#matches("Minulla on koira mutta sinulla on kissa.","Sinulla on kissa ja minulla on koira.")

