import glob
import json
from collections import Counter
import sys
import argparse
import datetime

def read_all_labels(datadir):
    label_dict = {} # key: id, value: list of labels
    
    # collect all files
    batchfiles=sorted(glob.glob(datadir+"/batches-*/rew-*.json")+glob.glob(datadir+"/batches-*/archived/*.json"))
    for b in batchfiles:
        with open(b, "rt", encoding="utf-8") as f:
            data = json.load(f)
        
        for example in data:
            annotation = example.get("annotation", None)
            if annotation == None:
                continue
            example_idx = example.get("id")
            label = annotation.get("label")
            if example_idx not in label_dict:
                label_dict[example_idx] = []
            label_dict[example_idx].append(label)
    print(f"{len(label_dict)} unique IDs read.", file=sys.stderr)    
    return label_dict

def resolve_prev(example_idx, all_labels):

    if example_idx.endswith("-rew"):
        return "4"

    if example_idx not in all_labels:
        print("Previous label does not exist???!!!", example_idx, file=sys.stderr)
        sys.exit()

    if len(set(all_labels[example_idx])) == 1:
        return all_labels[example_idx][0]
        
    print("Warning! More than one previous label found.", example_idx, all_labels[example_idx], file=sys.stderr)
        
    majority, count = Counter(all_labels[example_idx]).most_common(1)[0]
    agreement_score = count/len(all_labels[example_idx])
    if agreement_score >= 0.6:
        print("Taking concensus:", majority, all_labels[example_idx], file=sys.stderr)
        return majority
        
    prev_label = "|".join(set(all_labels[example_idx]))
    print("Returning all labels:", prev_label, all_labels[example_idx], file=sys.stderr)
    return prev_label
        
         
    
    
def merge_labels(fname, all_labels):
        
    timestamp = datetime.datetime.now().isoformat()
    merged = []
    
    agreement_all = 0
    agreement_rew = 0
    total = 0
    
    with open(fname, "rt", encoding="utf-8") as f:
        data = json.load(f)

    for example in data:
        example_idx = example.get("id")
        annotation = example.get("annotation")
        if not annotation:
            print("None annotation found, file not ready. Exiting!", file=sys.stderr)
            sys.exit()
        label = annotation.get("label")
        
        # get previous label
        prev_label = resolve_prev(example_idx, all_labels)
            
                        
        if label == prev_label:
            agreement_all += 1
            if example_idx.endswith("-rew"):
                agreement_rew += 1

        # create new json
        example["annotation"]["label"] = f"{prev_label}|{label}"
        example["annotation"]["user"] = "Merged"
        example["annotation"]["updated"] = timestamp

        merged.append(example)
        
    print(f"Agreement (all): {agreement_all/len(merged)*100} % ({agreement_all}/{len(merged)})", file=sys.stderr)
    print(f"Agreement (rewrites): {agreement_rew/(len(merged)/2)*100} % ({agreement_rew}/{int(len(merged)/2)})", file=sys.stderr)
    
    return merged

    
    
    
def main(args):

    all_labels = read_all_labels("/home/ginter/ann_data/news_titles_assigned")
    merged = merge_labels(args.file_name, all_labels)
    
    print(json.dumps(merged, sort_keys=True, indent=2, ensure_ascii=False))

if __name__ == '__main__':

    argparser = argparse.ArgumentParser(description='')
    argparser.add_argument('--file-name', '-f', required=True, help='Batch file name (i.e. data/batches-Annotator1/batch1.json)')
    args = argparser.parse_args()

    main(args)
    
    # usage:
    # python merge_rewrite_batches.py --file-name /home/ginter/ann_data/news_titles_assigned/batches-Otto/Otto-rewrite-double-batch-1.json > merged/Otto-rewrite-double-batch-1.json

    
