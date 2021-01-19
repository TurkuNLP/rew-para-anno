import json
import glob

def read_files():
    json_files = glob.glob("*.json")
    return sorted(json_files)
    
    
def is_completed(fname):

    with open(fname, "rt", encoding="utf-8") as f:
        data = json.load(f)
        
    # data is a list of examples
    for example in data:
        if "annotation" not in example:
            return False
        if "label" not in example["annotation"]:
            return False
        if "flagged" in example["annotation"] and (example["annotation"]["flagged"] == "true" or example["annotation"]["flagged"] == True):
            return False
        label = example["annotation"]["label"]
        if label.strip() == "" or "|" in label:
            return False
            
    #all examples pass the criteria        
    return True


def main():

    files = read_files()
    completed_files = []
    for fname in files:
        completed = is_completed(fname)
        if completed == True:
            completed_files.append(fname)
    print(f"Completed {len(completed_files)} out of {len(files)} total files.")
    print("Archive completed:")
    print()
    print(f"mv {' '.join(completed_files)} archived/ ; git add {' '.join(completed_files)} ; git add archived/* ; git commit -m 'Jenna, archive completed'")
    print()
                
main()


# cd batches-JennaK
# python3 /home/jmnybl/git_checkout/rew-para-anno/archive_data.py




