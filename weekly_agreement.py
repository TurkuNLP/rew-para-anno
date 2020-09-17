import sys
import hashlib
import argparse
import glob
import os
import json
from collections import Counter
import datetime
import itertools

def read_files(args):
    json_files = glob.glob(os.path.join(args.data_dir, "**", "*.json"), recursive=True)
    return json_files
    
def normalize_label(label):
        label = label.strip()
        label = "".join(label.split())
        label = "".join(sorted(label))
        return label
        
def calculate_idx(text):
        idx = hashlib.sha224(text.encode()).hexdigest()
        return idx
        
def week(timestamp):
        if timestamp == "unknown":
                return timestamp
        date = datetime.datetime.fromisoformat(timestamp)
        date = date.isocalendar()
        year = date[0]
        week = date[1]

        return f"{year} week {week}"

def yield_from_json(fname):

    with open(fname, "rt", encoding="utf-8") as f:
        data = json.load(f)
    for example in data: # one annotated example
        annotation = example.get("annotation", None)
        if not annotation:
            continue
        label = annotation.get("label")
        if not label:
            continue
        label = normalize_label(label)
        text = " --- ".join([example.get("txt1", "EMPTY"), example.get("txt2", "EMPTY")])
        idx = calculate_idx(text)
        timestamp = week(annotation.get("updated", "unknown"))
        user = annotation.get("user", "unknown")
        
        yield idx, label, timestamp, user
        
def collect_annotations(files):

        annotations = {} # key: (annotator, timestamp), value: annotations dictionary where key: idx, value: label
        for fname in files:
                for idx, label, timestamp, user in yield_from_json(fname):
                        
                        if (user, timestamp) not in annotations:
                                annotations[(user, timestamp)] = {}
                        annotations[(user,timestamp)][idx] = label
        return annotations
        
def calculate_agreement(annotations_1, annotations_2):
        # annotations --> key: idx, value: label
        if annotations_1 is None or annotations_2 is None:
                return 0, 0
        common_keys = set(annotations_1.keys()) & set(annotations_2.keys())
        agree = 0
        for key in common_keys:
                if annotations_1[key] == annotations_2[key]:
                        agree += 1
        return agree, len(common_keys)
        
def print_agreement(agree, total, ann1, ann2):
        if total == 0:
                print(f"No annotations for pair {ann1} – {ann2}.")
                return
        print(f"{ann1} – {ann2}: {agree/total*100:.2f}% (N={total})")                    
                        
        
def agreement(args, annotations):

        ann = set(args.annotators.split(",")) if args.annotators is not None else None

        annotators = set([ann for ann, time in annotations.keys()])
        if ann is not None:
                annotators = annotators & ann
        annotators = list(annotators)
        
        print("Annotators:", annotators)
        pairs = [(annotators[i], annotators[j]) for i in range(len(annotators)) for j in range(i+1,len(annotators))]

        weeks = sorted(set([w for a, w in annotations.keys()]))

        # WEEKLY #
        for w in weeks:
                print(f"\n{w}\n")
                for ann1, ann2 in pairs:
                        examples_1 = annotations.get((ann1, w), None)
                        examples_2 = annotations.get((ann2, w), None)
                        agree, total = calculate_agreement(examples_1, examples_2)
                        print_agreement(agree, total, ann1, ann2)
                        
        # TOTAL #
        print("\nTotal agreement:\n")
        for ann1, ann2 in pairs:
                examples_1 = [annotations[(a, w)] for a, w in annotations.keys() if a == ann1]
                examples_1 = {k: v for d in examples_1 for k, v in d.items()}
                
                examples_2 = [annotations[(a, w)] for a, w in annotations.keys() if a == ann2]
                examples_2 = {k: v for d in examples_2 for k, v in d.items()}
                
                agree, total = calculate_agreement(examples_1, examples_2)
                print_agreement(agree, total, ann1, ann2)

        
        


def main(args):

    all_files = read_files(args) # all files from different annotators
    
    annotations = collect_annotations(all_files)
    
    agreement(args, annotations)





if __name__=="__main__":

    argparser = argparse.ArgumentParser(description='')
    argparser.add_argument('--data-dir', '-d', required=True, help='Top level directory of annotation batches (i.e. /path/to/data if data/batches-Annotator1/batch1.json)')
    argparser.add_argument('--annotators', type=str, help='Comma separated list of annotators. If not defined, take all.')

    args = argparser.parse_args()

    main(args)
    
    # Calculate weekly agreement score between every pair of annotators.
    
    # Usage: python weekly_agreement.py -d /home/ginter/ann_data/news_titles_assigned
