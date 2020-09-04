import json

data=[{"txt1":"Some text 1","txt2":"Some text 2","metadata":"something"},{"txt1":"Some text 3","txt2":"Some text 4","metadata":"something"},{"txt1":"Some text 5","txt2":"Some text 6","metadata":"something"},{"txt1":"Some text 7","txt2":"Some text 8","metadata":"something"},{"txt1":"Some text 9","txt2":"Some text 10","metadata":"something"},{"txt1":"Some text 11","txt2":"Some text 12","metadata":"something"}]

for i in range(len(data)):
    del data[i]["metadata"]
    data[i]["id"]="idx"+str(i)

s=json.dumps(data,ensure_ascii=False,indent=2,sort_keys=True)
print(s)

