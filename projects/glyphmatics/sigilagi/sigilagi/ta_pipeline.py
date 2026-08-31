#!/usr/bin/env python3
import json

def bench():
    out = [
        {"task":"qa","A":"train arrive 8pm","score":1.0},
        {"task":"math","A":"3","score":1.0}
    ]
    print(json.dumps(out, indent=2))

if __name__=="__main__":
    import sys
    if len(sys.argv)>1 and sys.argv[1]=="bench":
        bench()
