#!/usr/bin/env bash
set -e

mkdir -p ~/glyph_chat_linux
cd ~/glyph_chat_linux

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install numpy pillow

cat > glyph_linux_chat.py <<'PYEOF'
import json, math, random, time, hashlib
from pathlib import Path
from collections import Counter
import numpy as np
from PIL import Image, ImageDraw

START=4094
STOP=4095
PAD=3840
MAX_LEN=512
HANZI=list("一二三四五六七八九十百千万亿兆世")

ROLES={
0:"Origin",1:"Split",2:"Bind",3:"Flow",4:"Gate",5:"Memory",6:"Signal",7:"Transform",
8:"Anchor",9:"Cycle",10:"Collapse",11:"Expand",12:"Sync",13:"Drift",14:"Lock",15:"Key"
}

class GlyphTokenizer:
    def encode(self,glyphs):
        return [((g["g"]&15)<<8)|(g["b"]&255) for g in glyphs]
    def decode(self,tokens):
        return [{"g":(int(t)>>8)&15,"b":int(t)&255,"h":HANZI[(int(t)>>8)&15],"role":ROLES[(int(t)>>8)&15]} for t in tokens]

def token(g,b): return ((g&15)<<8)|(b&255)

def beta_entropy(seq):
    bs=[t&255 for t in seq if ((t>>8)&15)!=15]
    if not bs: return 0.0
    c=Counter(bs); n=len(bs)
    return -sum((v/n)*math.log(v/n+1e-9) for v in c.values())

def tokens_to_bytes(seq):
    out=[]
    for t in seq:
        if t==STOP: break
        if ((t>>8)&15)!=15: out.append(t&255)
    return bytes(out)

def render(tokens,path,cell=32,grid=16):
    img=Image.new("RGB",(cell*grid,cell*grid),"white")
    d=ImageDraw.Draw(img)
    padded=tokens[:grid*grid]+[PAD]*(grid*grid-len(tokens))
    for i,t in enumerate(padded):
        x=i%grid; y=i//grid; cx=x*cell; cy=y*cell
        g=(t>>8)&15; b=t&255
        d.rectangle([cx,cy,cx+cell-1,cy+cell-1],outline="black")
        d.text((cx+3,cy+3),f"G{g}",fill="black")
        d.text((cx+3,cy+18),HANZI[g],fill="gray")
        bx,by=cx+18,cy+4
        for k in range(8):
            px=bx+(k%2)*7; py=by+(k//2)*7
            if (b>>k)&1: d.rectangle([px,py,px+5,py+5],fill="black")
            else: d.rectangle([px,py,px+5,py+5],outline="lightgray")
    img.save(path)

def semantic_seed(text,n=16):
    raw=hashlib.sha256(text.encode("utf-8")).digest()
    out=[START]
    for i in range(n):
        h=raw[i%len(raw)]
        g=(h+i*7)%15
        b=(h*31+i*17)%256
        out.append(token(g,b))
    return out

def build_large_dataset():
    ds=[]

    # canonical sweeps
    for mul in range(1,65):
        seq=[START]
        for i in range(96):
            seq.append(token(i%15,(i*mul+mul*7)%256))
        seq.append(STOP)
        ds.append(seq)

    # reverse sweeps
    for mul in range(1,65):
        seq=[START]
        for i in range(96):
            g=14-(i%15)
            seq.append(token(g,(255-(i*mul))%256))
        seq.append(STOP)
        ds.append(seq)

    # role-specialized corpora
    profiles={
        "signal":[6,12,8,3,6,5,14],
        "memory":[5,8,12,0,5,10,14],
        "transform":[7,11,13,3,7,12,14],
        "flow":[3,6,12,9,3,8,14],
        "legal":[4,5,8,10,14,15,12],
        "bail":[6,5,4,8,12,14,10],
        "chat":[6,3,2,5,8,12,7],
        "mayan":[0,9,11,3,4,5,12,14],
        "hieroglyph":[0,2,7,10,12,14,15]
    }

    for name,roles in profiles.items():
        seed=sum(ord(c) for c in name)
        for r in range(80):
            seq=[START]
            for i in range(64):
                g=roles[(i+r)%len(roles)]
                b=(seed+i*17+r*31+g*11)%256
                seq.append(token(g,b))
            seq.append(STOP)
            ds.append(seq)

    # phrase semantic seeds
    phrases=[
        "hello world","build system","semantic glyph compression","water flow","memory lock",
        "controlled generation","legal bail bond data","court ready export","mayan cycle",
        "hieroglyph water power","signal sync anchor","transform drift expand","chat response",
        "origin split bind flow","gate memory signal","collapse expand sync","lock key access"
    ]
    for p in phrases:
        for k in range(25):
            seq=semantic_seed(p+str(k),16)
            for i in range(48):
                seq.append(token((i+k)%15,(sum(seq)+i*13+k*19)%256))
            seq.append(STOP)
            ds.append(seq)

    print("[DATASET]",len(ds),"sequences")
    return ds

class NGram:
    def __init__(self):
        self.tri={}
        self.bi={}
        self.uni=Counter()

    def fit(self,ds,epochs=3):
        for ep in range(epochs):
            for s in ds:
                self.uni[s[0]]+=1
                for i in range(1,len(s)):
                    self.bi.setdefault(s[i-1],Counter())[s[i]]+=1
                    self.uni[s[i]]+=1
                for i in range(2,len(s)):
                    self.tri.setdefault((s[i-2],s[i-1]),Counter())[s[i]]+=1
            print("[EPOCH]",ep+1,"bi",len(self.bi),"tri",len(self.tri))

    def next(self,hist,banned=None,target=None):
        banned=banned or set()
        c=self.tri.get((hist[-2],hist[-1])) if len(hist)>=2 else None
        if not c: c=self.bi.get(hist[-1])
        if not c: c=self.uni
        items=[]
        for k,v in c.items():
            if k==PAD or k in banned: continue
            g=(k>>8)&15
            w=float(v)
            if target is not None:
                w*=1.0+2.0*target[g]
            items.append((k,w))
        if not items: return STOP
        toks=[k for k,_ in items]
        vals=np.array([v for _,v in items],dtype=np.float64)
        vals=np.power(vals,1/0.9)
        probs=vals/vals.sum()
        return int(np.random.choice(toks,p=probs))

    def generate(self,seed,max_new=128,target=None):
        out=list(seed)
        for _ in range(max_new):
            banned=set()
            recent=out[-8:]
            for t,n in Counter(recent).items():
                if n>=2: banned.add(t)
            nxt=self.next(out,banned,target)
            out.append(nxt)
            if nxt==STOP: break
        if out[-1]!=STOP: out.append(STOP)
        return out

def target_profile(mode):
    arr=np.ones(16)*0.03
    if mode=="water":
        arr[7]=.25; arr[12]=.25; arr[3]=.15
    elif mode=="chat":
        arr[6]=.25; arr[3]=.18; arr[5]=.18; arr[12]=.15
    elif mode=="build":
        arr[2]=.18; arr[7]=.22; arr[11]=.18; arr[14]=.15
    else:
        arr=np.ones(16)/16
    return arr/arr.sum()

def score(tokens):
    H=beta_entropy(tokens)
    B=len(tokens_to_bytes(tokens))
    valid=bool(tokens and tokens[0]==START and STOP in tokens)
    return {"valid":valid,"entropy":H,"bytes":B,"length":len(tokens),"score":(2 if valid else 0)+min(H/4,1)*2+min(B/64,1)}

def reply_from_tokens(user,tokens,meta):
    glyphs=GlyphTokenizer().decode(tokens)
    body=[f"G{x['g']}:{x['b']:02X}" for x in glyphs if x["g"]!=15][:28]
    if any(w in user.lower() for w in ["build","make","create","write"]):
        lead="Execution path"
    elif any(w in user.lower() for w in ["why","what","how"]):
        lead="Decoded answer"
    else:
        lead="Glyph response"
    return f"{lead}: {' '.join(body)} | H={meta['entropy']:.3f} bytes={meta['bytes']}"

def chat():
    Path("chat_exports").mkdir(exist_ok=True)
    ds=build_large_dataset()
    model=NGram()
    model.fit(ds,epochs=3)

    print("[GLYPH CHAT LINUX READY]")
    print("type exit to quit")

    while True:
        user=input("\nYou> ").strip()
        if user.lower() in ("exit","quit"): break

        mode="chat"
        if "water" in user.lower(): mode="water"
        if any(w in user.lower() for w in ["build","make","create"]): mode="build"

        seed=semantic_seed(user,16)
        target=target_profile(mode)
        candidates=[model.generate(seed,target=target) for _ in range(16)]
        ranked=sorted([(c,score(c)) for c in candidates],key=lambda x:x[1]["score"],reverse=True)
        tokens,meta=ranked[0]

        stamp=str(int(time.time()))
        render(tokens,f"chat_exports/reply_{stamp}.png")
        render(tokens,"chat_exports/latest_reply.png")
        Path("chat_exports/latest_reply.json").write_text(json.dumps({
            "user":user,
            "reply_tokens":tokens,
            "meta":meta,
            "glyphs":GlyphTokenizer().decode(tokens)
        },indent=2))

        reply=reply_from_tokens(user,tokens,meta)
        with open("chat_memory.jsonl","a") as f:
            f.write(json.dumps({"time":time.time(),"user":user,"reply":reply,"meta":meta})+"\n")

        print("SigilAGI>",reply)
        print("[PNG] chat_exports/latest_reply.png")

if __name__=="__main__":
    chat()
PYEOF

python glyph_linux_chat.py
