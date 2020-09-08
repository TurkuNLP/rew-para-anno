import sys
import hashlib
import argparse
import glob
import os
import json
from collections import Counter

def read_files(args):
    json_files = glob.glob(os.path.join(args.data_dir, "**", args.file_name), recursive=True)
    return json_files
    
def normalize_label(label):
        label = label.strip()
        label = "".join(label.split())
        label = "".join(sorted(label))
        return label
        
def calculate_idx(text):
        idx = hashlib.sha224(text.encode()).hexdigest()
        return idx

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
        if annotation.get("user") == "Merged": # skip Merged annotation
                continue
        label = normalize_label(label)
        text = " --- ".join([example.get("txt1", "EMPTY"), example.get("txt2", "EMPTY")])
        idx = example.get("id")
        if idx is None:
            idx = calculate_idx(text)
        annotation["label"] = label
        example["id"] = idx
        example["annotation"] = annotation
        yield idx, example
        
def align(files):

        examples = {}
        for fname in files:
                for idx, example in yield_from_json(fname):
                        if idx not in examples:
                                examples[idx] = []
                        examples[idx].append(example)
        return examples
        
def merge(aligned_data, min_annotators=3, min_consensus=0.75):
        # min_annotators: do not automatically resolve if less than this annotated
        # min_consensus: automatically resolve if more than 75% agree
        consensus = []
        for idx, annotations in aligned_data.items():
                annotated_labels = [ann["annotation"]["label"] for ann in annotations]
                if len(annotated_labels) < min_annotators:
                        annotated_labels.append("???")
                        label = "|".join(annotated_labels)
                else:
                        # check consensus
                        majority, count = Counter(annotated_labels).most_common(1)[0]
                        if count/len(annotated_labels) >= 0.75:
                                label = majority
                        else:
                                label = "|".join(annotated_labels)

                # create new json
                example = annotations[0]
                example["annotation"]["label"] = label
                example["annotation"]["rew1"] = ""
                example["annotation"]["rew2"] = ""
                example["annotation"]["user"] = "Merged"
                example["annotation"]["updated"] = "0001-01-01"
                consensus.append(example)
        return consensus


def main(args):

    all_files = read_files(args) # all files from different annotators
    
    aligned_examples = align(all_files)
    
    merged = merge(aligned_examples)

    print(json.dumps(merged, sort_keys=True, indent=2, ensure_ascii=False))




if __name__=="__main__":

    argparser = argparse.ArgumentParser(description='')
    argparser.add_argument('--data-dir', '-d', required=True, help='Top level directory of annotation batches (i.e. /path/to/data if data/batches-Annotator1/batch1.json)')
    argparser.add_argument('--file-name', '-f', required=True, help='Batch file name (i.e. batch1.json if data/batches-Annotator1/batch1.json)')
    args = argparser.parse_args()

    main(args)
    
    # Usage: python merge_annotations.py -d /home/ginter/ann_data/news_titles_assigned -f sub_ann_train_000200.json > sub_ann_train_000200.json
