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
        
        
def resolve_input_edits(annotations):
        text_inp_1 = [ann["annotation"]["txt1inp"].strip() if "txt1inp" in ann["annotation"] else ann["txt1"] for ann in annotations]
        text_inp_2 = [ann["annotation"]["txt2inp"].strip() if "txt2inp" in ann["annotation"] else ann["txt2"] for ann in annotations]
        if len(set(text_inp_1)) == 1:
                text_inp_1 = text_inp_1[:1]
        text_inp_1 = "\n".join(text_inp_1)
        if len(set(text_inp_2)) == 1:
                text_inp_2 = text_inp_2[:1]
        text_inp_2 = "\n".join(text_inp_2)
        return text_inp_1, text_inp_2
        
def resolve_rewrites(annotations):
        rew1 = [a for a in [ann["annotation"].get("rew1", "") for ann in annotations] if a != ""]
        rew2 = [a for a in [ann["annotation"].get("rew2", "") for ann in annotations] if a != ""]
        rew1 = "\n".join(rew1)
        rew2 = "\n".join(rew2)
        return rew1, rew2
        
def is_flagged(annotations):
        for ann in annotations:
                if "annotation" not in ann:
                        continue
                flag = ann["annotation"].get("flagged", "false")
                if flag == "true":
                        return flag
        return "false"
                        
        
def merge(aligned_data, min_annotators=3, min_consensus=0.75):
        # min_annotators: do not automatically resolve if less than this annotated
        # min_consensus: automatically resolve if more than 75% agree
        consensus = []
        full_agreement = 0
        consensus_agreement = 0
        skipped = 0
        num_annotators = []
        for idx, annotations in aligned_data.items():
                annotated_labels = [ann["annotation"]["label"] for ann in annotations]
                text_inp_1, text_inp_2 = resolve_input_edits(annotations)
                rew1, rew2 = resolve_rewrites(annotations)
                flag = is_flagged(annotations)
                if len(annotated_labels) < min_annotators:
                        annotated_labels.append("???")
                        label = "|".join(annotated_labels)
                        skipped += 1
                else:
                        # check consensus
                        majority, count = Counter(annotated_labels).most_common(1)[0]
                        agreement_score = count/len(annotated_labels)
                        if agreement_score >= 0.75:
                                label = majority
                                if agreement_score == 1.0:
                                        full_agreement +=1
                                consensus_agreement +=1
                        else:
                                label = "|".join(annotated_labels)
                        num_annotators.append(len(annotated_labels))

                # create new json
                example = annotations[0]
                example["annotation"]["label"] = label
                example["annotation"]["txt1inp"] = text_inp_1
                example["annotation"]["txt2inp"] = text_inp_2
                example["annotation"]["rew1"] = rew1
                example["annotation"]["rew2"] = rew2
                example["annotation"]["user"] = "Merged"
                example["annotation"]["updated"] = "0001-01-01"
                example["annotation"]["flagged"] = flag
                consensus.append(example)
        return consensus, (full_agreement, consensus_agreement, skipped, num_annotators)


def main(args):

    all_files = read_files(args) # all files from different annotators
    
    aligned_examples = align(all_files)
    
    merged, stats = merge(aligned_examples, min_annotators=args.min_annotators)

    print(json.dumps(merged, sort_keys=True, indent=2, ensure_ascii=False))
    
    # print stats
    full_agreement, consensus_agreement, skipped, annotators = stats
    total = len(merged)-skipped
    if total == 0:
        print(print(f"Skipped (not enough annotations for agreement score): {skipped}", file=sys.stderr))
        print(f"Total: {total}", file=sys.stderr)
        return
        
    
    print(f"Full agreement: {full_agreement} ({full_agreement/total*100}%)", file=sys.stderr)
    print(f"Concensus agreement: {consensus_agreement} ({consensus_agreement/total*100}%)", file=sys.stderr)
    print(f"Total: {total}", file=sys.stderr)
    print(f"Average number of annotators: {sum(annotators)/len(annotators)}", file=sys.stderr)
    print(f"Skipped (not enough annotations): {skipped}", file=sys.stderr)




if __name__=="__main__":

    argparser = argparse.ArgumentParser(description='')
    argparser.add_argument('--data-dir', '-d', required=True, help='Top level directory of annotation batches (i.e. /path/to/data if data/batches-Annotator1/batch1.json)')
    argparser.add_argument('--file-name', '-f', required=True, help='Batch file name (i.e. batch1.json if data/batches-Annotator1/batch1.json)')
    argparser.add_argument('--min-annotators', type=int, default=2, help='How many annotators must be to resolve conflicts automatically if consensus found.')
    args = argparser.parse_args()

    main(args)
    
    # Usage: python merge_annotations.py -d /home/ginter/ann_data/news_titles_assigned -f sub_ann_train_000200.json > sub_ann_train_000200.json
