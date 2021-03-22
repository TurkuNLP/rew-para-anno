import glob
import json
from collections import Counter
import random


## TODO: skip already sampled examples (based on example id)

def read_rew_batches(datadir):
    batchdict = {} # basename -> full path
    
    # collect double annotated files
    double_annotated = set()
    batchfiles=sorted(glob.glob(datadir+"/batches-Merged/rew-*.json")+glob.glob(datadir+"/batches-Merged/archived/*.json"))
    print(f"{len(batchfiles)} unique double annotated batches read.")
    for b in batchfiles:
        components=b.split("/")
        fname=components[-1]
        double_annotated.add(fname)
    
    # collect all files
    batchfiles=sorted(glob.glob(datadir+"/batches-*/rew-*.json")+glob.glob(datadir+"/batches-*/archived/*.json"))
    for b in batchfiles:
        if "Merged" in b or "Swedish" in b: # skip Merged and Swedish
            continue
        components=b.split("/")
        fname=components[-1]
        if fname in double_annotated:
            continue # skip double annotated file 
        batchdict[fname] = b
    print(f"{len(batchdict)} batches read (double annotated skipped).")    
    return batchdict
   
def get_examples(data):
    rewrites = []
    paraphrases = []
    for example in data:
        annotation = example.get("annotation", None)
        if annotation == None:
            continue
        rew1 = annotation.get("rew1", "")
        rew2 = annotation.get("rew2", "")
        if rew1 != "" and rew2 != "":
            # take rewrites!
            example["id"] = example["id"]+"-rew"
            example["txt1"] = rew1
            example["txt2"] = rew2
        # clean json
        example.pop("annotation", None)
        for key in "document_context1, document_context2, anchor1, anchor2, focus1, focus2".split(", "):
            example[key] = ""
        
        if example.get("id", "").endswith("-rew"):
            rewrites.append(example)
        else:
            paraphrases.append(example)
    return paraphrases, rewrites
    
def get_annotator(fname):

    components=fname.split("/")
    if "batches-" in components[-2]:
        user=components[-2].replace("batches-","")
    else:
        assert "batches-" in components[-3]
        user=components[-3].replace("batches-","")
    return user
    
def get_paraphrases(batchdict):
    all_paraphrases = {} # key: user, value: dict -> key: exmple_type, list od examples
    for basename, fullname in batchdict.items():
        with open(fullname, "rt", encoding="utf-8") as f:
            data = json.load(f)
        user = get_annotator(fullname)
        paraphrases, rewrites = get_examples(data) # note that original is excluded if rewrite exists!
        if user not in all_paraphrases:
            all_paraphrases[user] = {"rewrites": [], "paraphrases": []}
        all_paraphrases[user]["rewrites"] += rewrites
        all_paraphrases[user]["paraphrases"] += paraphrases
        
    print("Annotations for", all_paraphrases.keys())
    return all_paraphrases
    
def prepare_annotator_files(all_paraphrases):

    # print all stats
    for user in all_paraphrases.keys():
        print(user, len(all_paraphrases[user]["rewrites"]), "rewrites")
        print(user, len(all_paraphrases[user]["paraphrases"])+len(all_paraphrases[user]["rewrites"]), "paraphrases")
        
    from_annotators = ["HannaMari", "Jemina", "JennaS", "Maija", "Otto"] # Aurora, JennaK skipped, not enough annotations
    to_annotators = ["Aurora", "HannaMari", "Jemina", "JennaS", "Maija", "Otto"]
        
    for annotator in to_annotators:
        examples = []
        for ann in from_annotators:
            if annotator == ann:
                continue
            print(f"Getting data from {ann} to {annotator}.")
            srew = all_paraphrases[ann]["rewrites"]
            spar = all_paraphrases[ann]["paraphrases"]
            random.shuffle(srew)
            random.shuffle(spar) 
            taken_r, rest_r = srew[:20], srew[20:]
            taken_p, rest_p = spar[:20], spar[20:]
            all_paraphrases[ann]["rewrites"] = rest_r
            all_paraphrases[ann]["paraphrases"] = rest_p
            
            examples += taken_r
            examples += taken_p

            
            #print(annotator, len(examples))
            #print(ann, len(all_paraphrases[ann]["rewrites"]))
            #print(ann, len(all_paraphrases[ann]["paraphrases"]))
        print(len(examples), "examples selected for", annotator)
        random.shuffle(examples)
        
        with open(f"{annotator}-rewrite-double-batch-1.json", "wt", encoding="utf-8") as f:
            json.dump(examples, f, ensure_ascii=False, indent=2)
        
        
def main():

    batch_files = read_rew_batches("/home/ginter/ann_data/news_titles_assigned")
    all_paraphrases = get_paraphrases(batch_files)
    prepare_annotator_files(all_paraphrases)
    
    

if __name__ == '__main__':

    main()
