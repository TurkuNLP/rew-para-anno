import sys
import hashlib
import argparse
import glob
import os
import json
from collections import Counter
import sqlitedict




def read_annotated_files(args):
    json_files = glob.glob(os.path.join(args.annotated_batches, "**", "*.json"), recursive=True)
    json_files = [os.path.basename(fn) for fn in json_files]
    return list(set(json_files))

        
def calculate_idx(text):
        idx = hashlib.sha224(text.encode()).hexdigest()
        return idx

def yield_segments(fname):

    with open(fname, "rt", encoding="utf-8") as f:
        data = json.load(f)
        movie_meta = {"name": "", "id": "", "language": ""}
        if isinstance(data, dict): # new format
            movie_meta["name"] = data.get("name", "")
            movie_meta["id"] = data.get("id", "")
            movie_meta["language"] = data.get("language", "")
            data = data["segments"]
    for i, segment in enumerate(data): # one 15min segment of a movie
        # d1, d2, sim, (updated, annotation)
        annotation = segment.get("annotation", None)
        if segment.get("locked", False) == True:
            print(f'Segment {i} locked, annotator {segment.get("annotator")}, skipping')
            continue
        if "annotation" in segment: # if segment not annotated, skip
                    
                yield i, movie_meta, segment
        
def get_document_text(db_name, table, doc_id):

        db = sqlitedict.SqliteDict(db_name, tablename=table, flag="r")
        
        text = db.get(doc_id, "")
        
        db.close()

        return text
        
        
        
def find_span(para, doc_text):

        doc_text_alpha = "".join([c for c in doc_text.lower() if c.isalpha()])
        para_alpha = "".join([c for c in para.lower() if c.isalpha()])
        if doc_text_alpha.count(para_alpha) > 1:
                pass
                #print("Ambiguous paraphrase:", doc_text_alpha.count(para_alpha), para, file=sys.stderr)
        
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
        

def transfer(args, segment, metadata):
                
        table1, doc1 = segment.get("d1") # ["subtitle", "1955045028-001500.txt"]
        table2, doc2 = segment.get("d2")
        
        doc1_text = segment.get("d1_text", "")
        doc2_text = segment.get("d2_text", "")
        
        if doc1_text == "":
            doc1_text = get_document_text(args.text_db, table1, doc1)
        if doc2_text == "":
            doc2_text = get_document_text(args.text_db, table2, doc2)
        
        annotation = segment.get("annotation")
        annotation = list(reversed(annotation)) # fix the order
        
        metadata["source_files"] = f"{metadata['source_files']}---{doc1}---{doc2}"
        
        examples = []

        for example in yield_annotations(annotation, doc1_text, doc2_text):
                example["meta"] = metadata
                examples.append(example)
                
        return examples
                               



def main(args):


    annotated = read_annotated_files(args)


#    "meta": {
#      "A-sim": 0.5622275607964768,
#      "Score": 0.23459273771768144,
#      "T-sim": 0.5827441518780281,
#      "source_files": "/home/smp/data/news-paraphrase/hs-text/2019-02-19-11-15-15---aff63486a2d786a7006cd42c2b37eca1.txt /home/ginter/Similar-news/yle-text/2019-02-19-03-47-03--3-10652399.txt",
#      "srcinfo": "14.9.2020 python3 gather_titles.py --paired paired_news.json --titles ~/yle_rss_downloader/titles_hs_yle.json --vectorizer vectorizer.pickle"

    metadata = {"source_files": args.file_name, "srcinfo": "pick2para.py"}

    counter = 1
    for idx, movie_meta, segment in yield_segments(args.file_name):
        for key in movie_meta:
            metadata[key] = movie_meta[key]
        rew_batch = transfer(args, segment, metadata) # list of examples in rew format
        if len(rew_batch)==0:
                continue
        fname = os.path.basename(args.file_name).replace(".json", "")
        fname = f"rew-batch-{fname}-part-{idx}.json"
        if fname in annotated:
                print("Skipping already annotated file", fname, file=sys.stderr)
                continue
        
        
        with open(fname, "w", encoding="utf-8") as f:
                print(f"Saving to", fname, file=sys.stderr)
                print(json.dumps(rew_batch, sort_keys=True, indent=2, ensure_ascii=False), file=f)
        counter += 1
    




if __name__=="__main__":

    argparser = argparse.ArgumentParser(description='')
    #argparser.add_argument('--data-dir', '-d', required=True, help='Top level directory of annotation batches (i.e. /path/to/data if data/batches-Annotator1/batch1.json)')
    argparser.add_argument('--file-name', '-f', required=True, help='Batch file name (i.e. /path/to/data/batches-Annotator1/batch1.json)')
    argparser.add_argument('--text-db', required=True, help='Database name (i.e. /path/to/all-texts.sqlited)')
    argparser.add_argument('--annotated-batches', required=True, help='Top level directory of annotated batches. Do not create if already exists here. (i.e. /path/to/ann_data)')
    args = argparser.parse_args()

    main(args)
    
    # Usage: python pick2rew.py -f /home/ginter/pick_ann_data_live_old/batches-JennaK/12007.json --text-db /home/ginter/pick_ann_data_live_old/all-texts.sqlited --annotated-batches /home/ginter/ann_data > sub_ann_train_000200.json
    
    
    
    # in /home/jmnybl/git_checkout/rew-para-anno/batches-pick2rew
    
    # cd batches-HannaMari ;  for f in /home/ginter/pick_ann_data_live_old/batches-HannaMari/*.json ; do echo $f ; python ../../pick2rew.py -f $f --text-db /home/ginter/pick_ann_data_live_new/all-texts.sqlited --annotated-batches /home/ginter/ann_data ; done


