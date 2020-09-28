import sys
import hashlib
import argparse
import glob
import os
import json
from collections import Counter
import sqlitedict



def read_files(args):
    json_files = glob.glob(os.path.join(args.data_dir, "**", args.file_name), recursive=True)
    return json_files

        
def calculate_idx(text):
        idx = hashlib.sha224(text.encode()).hexdigest()
        return idx

def yield_segments(fname):

    with open(fname, "rt", encoding="utf-8") as f:
        data = json.load(f)
    for segment in data: # one 15min segment of a movie
        # d1, d2, sim, (updated, annotation)
        annotation = segment.get("annotation", None)
        if "annotation" in segment: # if segment not annotated, skip
                yield segment
        
def get_document_text(table, doc_id):

        #db = sqlitedict.SqliteDict("/home/ginter/pick_ann_data_live_new/all-texts.sqlited", tablename=table, flag="r")
        db = sqlitedict.SqliteDict("/home/lhchan/data-all-movie/data-15-assigned/all-texts.sqlited", tablename=table, flag="r")
        
        text = db.get(doc_id, "")
        
        db.close()

        return text
        
        
        
def find_span(para, doc_text):

        doc_text_alpha = "".join([c for c in doc_text.lower() if c.isalpha()])
        para_alpha = "".join([c for c in para.lower() if c.isalpha()])
        if doc_text_alpha.count(para_alpha) > 1:
                print("Ambiguous paraphrase:", doc_text_alpha.count(para_alpha), para, file=sys.stderr)
        
def yield_annotations(annotation, document_context1, document_context2):

# {
#    "id": "yle_hs_13808",
#    "meta": {
#      "A-sim": 0.5622275607964768,
#      "Score": 0.23459273771768144,
#      "T-sim": 0.5827441518780281,
#      "source_files": "/home/smp/data/news-paraphrase/hs-text/2019-02-19-11-15-15---aff63486a2d786a7006cd42c2b37eca1.txt /home/ginter/Similar-news/yle-text/2019-02-19-03-47-03--3-10652399.txt",
#      "srcinfo": "14.9.2020 python3 gather_titles.py --paired paired_news.json --titles ~/yle_rss_downloader/titles_hs_yle.json --vectorizer vectorizer.pickle"
#    },
#    "txt1": "Poliitikkojen vastuusta saarnannut Viiden tähden liike haluaa sisäministeri Salvinille syytesuojan",
#    "txt2": "Viiden tähden liike puolustaa Italian sisäministerin syytesuojaa"
#  }


        

        for example in annotation:
                text = example.get("txt")
                if len(text.strip().split("\n")) != 2:
                        print("WHAAAAAAT????", text, file=sys.stderr)
                para1, para2 = text.strip().split("\n", 1)
                focus1 = example.get("focusid_left", "")
                focus2 = example.get("focusid_right", "")
                anchor1 = example.get("anchorid_left", "")
                anchor2 = example.get("anchorid_right", "")
                
                find_span(para1, document_context1)
                find_span(para2, document_context2)
                
                d = {"id": calculate_idx(para1+para2), "txt1": para1, "txt2": para2, "document_context1": document_context1, "document_context2": document_context2, "focus1": focus1, "focus2": focus2, "anchor1": anchor1, "anchor2":anchor2, "local_context1": "", "local_context2": ""}
                yield d
        

def transfer(segment, metadata):
                
        table1, doc1 = segment.get("d1") # ["subtitle", "1955045028-001500.txt"]
        table2, doc2 = segment.get("d2")
        
        doc1_text = get_document_text(table1, doc1)
        doc2_text = get_document_text(table2, doc2)
        
        annotation = segment.get("annotation")
        annotation = list(reversed(annotation)) # fix the order
        
        metadata["source_files"] = f"{metadata['source_files']}---{doc1}---{doc2}"
        
        examples = []

        for example in yield_annotations(annotation, doc1_text, doc2_text):
                example["meta"] = metadata
                examples.append(example)
                
        return examples
                               



def main(args):


#    "meta": {
#      "A-sim": 0.5622275607964768,
#      "Score": 0.23459273771768144,
#      "T-sim": 0.5827441518780281,
#      "source_files": "/home/smp/data/news-paraphrase/hs-text/2019-02-19-11-15-15---aff63486a2d786a7006cd42c2b37eca1.txt /home/ginter/Similar-news/yle-text/2019-02-19-03-47-03--3-10652399.txt",
#      "srcinfo": "14.9.2020 python3 gather_titles.py --paired paired_news.json --titles ~/yle_rss_downloader/titles_hs_yle.json --vectorizer vectorizer.pickle"

    metadata = {"source_files": args.file_name, "srcinfo": "pick2para.py"}

    counter = 1
    for segment in yield_segments(args.file_name):
        rew_batch = transfer(segment, metadata) # list of examples in rew format
        fname = os.path.basename(args.file_name).replace(".json", "")
        
        with open(f"rew-batch-{fname}-part{counter}.json", "w", encoding="utf-8") as f:
                print(f"Saving to rew-batch-{fname}-part{counter}.json", file=sys.stderr)
                print(json.dumps(rew_batch, sort_keys=True, indent=2, ensure_ascii=False), file=f)
        counter += 1
    




if __name__=="__main__":

    argparser = argparse.ArgumentParser(description='')
    #argparser.add_argument('--data-dir', '-d', required=True, help='Top level directory of annotation batches (i.e. /path/to/data if data/batches-Annotator1/batch1.json)')
    argparser.add_argument('--file-name', '-f', required=True, help='Batch file name (i.e. /path/to/data/batches-Annotator1/batch1.json)')
    args = argparser.parse_args()

    main(args)
    
    # Usage: python pick2rew.py -f /home/ginter/pick_ann_data_live_old/batches-JennaK/12007.json > sub_ann_train_000200.json
