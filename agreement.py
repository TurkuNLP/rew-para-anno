import sys
import hashlib
import argparse
import glob
import os
import json
from collections import Counter
import datetime
import itertools
import re
from sklearn.metrics import confusion_matrix
from natsort import natsorted


sort_order = ['4', '4s', '4i', '4A', '4<', '4>','4<i', '4>i','4<s', '4>s','4<is', '4>is', '3', '2', '1']

def read_files(args):
    json_files = glob.glob(os.path.join(args.data_dir, "**", "*.json"), recursive=True)
    
    # remove archived files
    json_files = [f for f in json_files if "archived-" not in f]
    
    # remove files from 'wrong' annotators
    if args.annotators:
        annotators_regex = re.compile("|".join(a for a in args.annotators.split(",")))
        json_files = [f for f in json_files if annotators_regex.search(f) is not None]
        
    # remove single annotated files (not appearing twice in json_list)
    basenames = [os.path.basename(f) for f in json_files]
    json_files = [f for f in json_files if basenames.count(os.path.basename(f)) > 1]
        
    for f in json_files:
        print(f)
    return json_files
    
def normalize_label(args, label):
        label = label.lower().strip()
        label = "".join(label.split())
        label = "".join(sorted(label))
        if args.relaxed is False:
                return label
        label = label.replace("s", "")
        label = label.replace("i", "")
        label = label.replace("<", "A")
        label = label.replace(">", "A")
        print(label)
        return label
         
        
def calculate_idx(example):

        annotation = example.get("annotation")
        if annotation.get("txt1inp") is not None and annotation.get("txt2inp") is not None:
                text = " --- ".join([annotation.get("txt1inp"), annotation.get("txt2inp")])
        else:
                text = " --- ".join([example.get("txt1"), example.get("txt2")])

        idx = hashlib.sha224(text.encode()).hexdigest()
        return text, idx
        
def week(timestamp):
        if timestamp == "unknown":
                return timestamp
        date = datetime.datetime.fromisoformat(timestamp)
        date = date.isocalendar()
        year = date[0]
        week = date[1]

        return f"{year} week {week}"
        

def yield_from_json(args, fname):

    with open(fname, "rt", encoding="utf-8") as f:
        data = json.load(f)
    for example in data: # one annotated example
        annotation = example.get("annotation", None)
        if not annotation:
            continue
        label = annotation.get("label")
        if not label or label.lower() == "x":
            continue
        label = normalize_label(args, label)
        #text = " --- ".join([example.get("txt1", "EMPTY"), example.get("txt2", "EMPTY")])
        text, idx = calculate_idx(example)
        timestamp = week(annotation.get("updated", "unknown"))
        user = annotation.get("user", "unknown")
        
        yield idx, label, timestamp, os.path.basename(fname), user
        
def collect_annotations(args, files):

        annotations = {} # key: (annotator, timestamp), value: annotations dictionary where key: idx, value: label
        for fname in files:
                for idx, label, timestamp, file_name, user in yield_from_json(args, fname):
                
                        if args.weekly:
                                key = timestamp
                        else:
                                key = file_name
                        
                        if (user, key) not in annotations:
                                annotations[(user, key)] = {}
                        annotations[(user,key)][idx] = label
        return annotations
        
def calculate_agreement(annotations_1, annotations_2):
        # annotations --> key: idx, value: label
        if annotations_1 is None or annotations_2 is None:
                return 0, 0, (None, None)
        common_keys = set(annotations_1.keys()) & set(annotations_2.keys())
        agree = 0
        labels_1 = []
        labels_2 = []
        for key in common_keys:
                labels_1.append(annotations_1[key])
                labels_2.append(annotations_2[key])
                if annotations_1[key] == annotations_2[key]:
                        agree += 1
        all_labels = list(set(labels_1+labels_2))
        all_labels.sort(key = lambda i: sort_order.index(i))
        return agree, len(common_keys), (confusion_matrix(labels_1, labels_2, labels=all_labels), all_labels)
        
def print_agreement(agree, total, ann1, ann2, conf):
        if total == 0:
                print(f"No annotations for pair {ann1} – {ann2}.")
                return
        print(f"{ann1} – {ann2}: {agree/total*100:.2f}% (N={total})")
        conf, all_labels = conf
        print(all_labels) 
        print(conf)                  
                        
        
def agreement(args, annotations):

        ann = set(args.annotators.split(",")) if args.annotators is not None else None

        annotators = set([ann for ann, time in annotations.keys()])
        if ann is not None:
                annotators = annotators & ann
        annotators = list(annotators)
        
        print("Annotators:", annotators)
        pairs = [(annotators[i], annotators[j]) for i in range(len(annotators)) for j in range(i+1,len(annotators))]

        weeks = sorted(set([w for a, w in annotations.keys()]))

        # KEY BASED (WEEK or FILE) #
        for w in weeks:
                print(f"\n{w}\n")
                for ann1, ann2 in pairs:
                        examples_1 = annotations.get((ann1, w), None)
                        examples_2 = annotations.get((ann2, w), None)
                        agree, total, conf = calculate_agreement(examples_1, examples_2)
                        print_agreement(agree, total, ann1, ann2, conf)
                        
        # TOTAL #
        print("\nTotal agreement:\n")
        for ann1, ann2 in pairs:
                examples_1 = [annotations[(a, w)] for a, w in annotations.keys() if a == ann1]
                examples_1 = {k: v for d in examples_1 for k, v in d.items()}
                
                examples_2 = [annotations[(a, w)] for a, w in annotations.keys() if a == ann2]
                examples_2 = {k: v for d in examples_2 for k, v in d.items()}
                
                agree, total, conf = calculate_agreement(examples_1, examples_2)
                print_agreement(agree, total, ann1, ann2, conf)

        
        


def main(args):

    all_files = read_files(args) # all files from different annotators
    
    annotations = collect_annotations(args, all_files)
    
    agreement(args, annotations)





if __name__=="__main__":

    argparser = argparse.ArgumentParser(description='')
    argparser.add_argument('--data-dir', '-d', required=True, help='Top level directory of annotation batches (i.e. /path/to/data if data/batches-Annotator1/batch1.json)')
    argparser.add_argument('--annotators', type=str, help='Comma separated list of annotators. If not defined, take all.')
    argparser.add_argument('--weekly', action="store_true", default=False, help='Print weekly statistics (not file based).')
    argparser.add_argument('--relaxed', action="store_true", default=False, help='Relaxed label comparison (4 / 4 arrow / 3 / 2 / 1)')

    args = argparser.parse_args()

    main(args)
    
    # Calculate weekly agreement score between every pair of annotators.
    
    # Usage: python weekly_agreement.py -d /home/ginter/ann_data/news_titles_assigned
