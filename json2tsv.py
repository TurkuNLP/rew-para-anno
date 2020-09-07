import json
import argparse
import glob
import os
import sys
import hashlib
# TSV fields: ID, annotator, timestamp, label, text

def read_dirs(args):
    json_files = glob.glob(os.path.join(args.directory, "**", "*.json"), recursive=True)
    return json_files

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
        text = " --- ".join([example.get("txt1", "EMPTY"), example.get("txt2", "EMPTY")])
        idx = example.get("id")
        if idx is None: # if ID missing, calculate idx using text fields
            idx = hashlib.sha224(text.encode()).hexdigest()
        yield [idx, annotation.get("user", "EMPTY"), annotation.get("updated", "EMPTY"), label, text]


def main(args):

    files = read_dirs(args)

    for fname in files:
        for annotation in yield_from_json(fname):
            print("\t".join(annotation))




if __name__=="__main__":

    argparser = argparse.ArgumentParser(description='')
    argparser.add_argument('--directory', '-d', help='Top level directory of annotation batches (.json), will read all subdirectories as well.')
    args = argparser.parse_args()

    main(args)
