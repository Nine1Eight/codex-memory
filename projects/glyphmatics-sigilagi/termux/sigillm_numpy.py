import json, random, math
from pathlib import Path
from collections import Counter
import numpy as np
from sigil_transformer import TinyTransformer
from glyph_semantic_bridge import vector_to_seed
from glyph_trainable_embedding import TrainableGlyphEmbedding

START=4094
STOP=4095
PAD=3840
MAX_LEN=128

class GlyphTokenizer:
    HANZI=list("一二三四五六七八九十百千万亿兆世")
    def encode(self,glyphs):
        return [((g["g"]&15)<<8)|(g["b"]&255) for g in glyphs]
    def decode(self,ids):
        out=[]
        for t in ids:
            g=(int(t)>>8)&15
            b=int(t)&255
            out.append({"g":g,"b":b,"h":self.HANZI[g]})
        return out

def beta_entropy(seq):
    bs=[t&255 for t in seq if ((t>>8)&15)!=15]
    if not bs: return 0.0
    c=Counter(bs); n=len(bs)
    return -sum((v/n)*math.log(v/n+1e-9) for v in c.values())

def role_histogram(seq):
    h=np.zeros(16,dtype=np.float64)
    for t in seq:
        h[(int(t)>>8)&15]+=1
    return h/max(1,h.sum())

def kl_div(p,q):
    p=np.asarray(p,dtype=np.float64)
    q=np.asarray(q,dtype=np.float64)
    return float(np.sum(p*np.log((p+1e-9)/(q+1e-9))))

def unique_ratio(seq):
    body=[t for t in seq if t not in (START,STOP,PAD)]
    return len(set(body))/max(1,len(body))

def max_token_fraction(seq):
    body=[t for t in seq if t not in (START,STOP,PAD)]
    if not body: return 1.0
    return max(Counter(body).values())/len(body)

def validate(seq):
    if not seq or seq[0]!=START: return False
    if STOP not in seq: return False
    stop_i=seq.index(STOP)
    if any(t==PAD for t in seq[:stop_i]): return False
    if beta_entropy(seq)<1.0: return False
    if max_token_fraction(seq)>0.50: return False
    return True

def tokens_to_bytes(seq):
    out=[]
    for t in seq:
        if t==STOP: break
        if ((int(t)>>8)&15)!=15:
            out.append(int(t)&255)
    return bytes(out)

def render_tokens_png(tokens,path,cell=32,grid=16):
    from PIL import Image,ImageDraw
    hanzi=GlyphTokenizer.HANZI
    img=Image.new("RGB",(cell*grid,cell*grid),"white")
    d=ImageDraw.Draw(img)
    padded=list(tokens[:grid*grid])+[PAD]*(grid*grid-len(tokens))
    for idx,t in enumerate(padded):
        x=idx%grid; y=idx//grid; cx=x*cell; cy=y*cell
        g=(int(t)>>8)&15; b=int(t)&255
        d.rectangle([cx,cy,cx+cell-1,cy+cell-1],outline="black")
        d.text((cx+3,cy+3),f"G{g}",fill="black")
        d.text((cx+3,cy+18),hanzi[g],fill="gray")
        bx,by=cx+18,cy+4
        for i in range(8):
            px=bx+(i%2)*7; py=by+(i//2)*7
            if (b>>i)&1:
                d.rectangle([px,py,px+5,py+5],fill="black")
            else:
                d.rectangle([px,py,px+5,py+5],outline="lightgray")
    img.save(path)
    print("[PNG]",path)

def load_dataset(tok):
    ds=[]
    for p in Path(".").glob("*.json"):
        try:
            data=json.loads(p.read_text())
            if not isinstance(data,dict) or "glyphs" not in data: continue
            g=data["glyphs"]
            if not isinstance(g,list) or len(g)<8: continue
            if g[0].get("g")!=15 or g[0].get("b")!=254:
                g=[{"g":15,"b":254,"h":"世"}]+g
            if g[-1].get("g")!=15 or g[-1].get("b")!=255:
                g=g+[{"g":15,"b":255,"h":"世"}]
            if sum(1 for q in g if q.get("g")!=15)<8: continue
            t=tok.encode(g)[:MAX_LEN]
            if t[-1]!=STOP: t.append(STOP)
            ds.append(t[:MAX_LEN])
            print("[DATA]",p.name,len(t))
        except Exception as e:
            print("[WARN]",p.name,e)
    if not ds:
        g=[{"g":15,"b":254,"h":"世"}]
        g += [{"g":i%15,"b":(i*17)%256,"h":tok.HANZI[i%15]} for i in range(64)]
        g += [{"g":15,"b":255,"h":"世"}]
        ds=[tok.encode(g)]
        print("[DATASET] fallback")
    print("[DATASET]",len(ds))
    return ds

class NGramSigilLM:
    def __init__(self):
        self.transformer = TinyTransformer()
        self.use_transformer = False

    def __init__(self):
        self.tri={}
        self.bi={}
        self.uni=Counter()
    def fit(self,ds,epochs=10):
        for ep in range(epochs):
            for s in ds:
                if len(s)<2: continue
                self.uni[s[0]]+=1; self.uni[s[1]]+=1
                self.bi.setdefault(s[0],Counter())[s[1]]+=1
                for i in range(2,len(s)):
                    a,b,t=s[i-2],s[i-1],s[i]
                    self.tri.setdefault((a,b),Counter())[t]+=1
                    self.bi.setdefault(b,Counter())[t]+=1
                    self.uni[t]+=1
            print("[EPOCH]",ep+1,"bi",len(self.bi),"tri",len(self.tri))
    def next(self,hist,banned,target_roles=None,steer=1.5):
        if self.use_transformer and len(hist) > 4:
            try:
                return self.transformer.next_token(hist[-16:])
            except:
                pass

        c=self.tri.get((hist[-2],hist[-1])) if len(hist)>=2 else None
        if not c: c=self.bi.get(hist[-1])
        if not c: c=self.uni
        items=[]
        for k,v in c.items():
            if k==PAD or k in banned: continue
            g=(int(k)>>8)&15
            w=float(v)
            if target_roles is not None:
                w *= 1.0 + steer*float(target_roles[g])
            items.append((k,w))
        if not items: return STOP
        toks=[k for k,_ in items]
        vals=np.array([v for _,v in items],dtype=np.float64)
        vals=np.power(vals,1/0.95)
        probs=vals/vals.sum()
        return int(np.random.choice(toks,p=probs))
    def generate(self,seed,max_new=128,target_roles=None):
        out=list(seed)
        for _ in range(max_new):
            banned=set()
            recent=out[-6:]
            for t,n in Counter(recent).items():
                if n>=2: banned.add(t)
            if len(out)>=4 and out[-2:]==out[-4:-2]:
                banned.update(out[-2:])
            if len(out)>=6 and out[-3:]==out[-6:-3]:
                banned.update(out[-3:])
            nxt=self.next(out,banned,target_roles=target_roles)
            out.append(nxt)
            if nxt==STOP: break
        if out[-1]!=STOP:
            out.append(STOP)
        return out

def score(tokens,target=None):
    H=beta_entropy(tokens)
    B=len(tokens_to_bytes(tokens))
    ok=validate(tokens)
    U=unique_ratio(tokens)
    M=max_token_fraction(tokens)
    base=(2 if ok else 0)+min(H/4,1)*2+min(B/32,1)+U-max(0,M-0.25)*2
    meta={"valid":ok,"entropy":H,"bytes":B,"length":len(tokens),"unique_ratio":U,"max_token_fraction":M,"score":base}
    if target:
        hist=role_histogram(tokens)
        role_loss=kl_div(hist,target["roles"])
        entropy_loss=abs(H-target.get("entropy",H))
        length_loss=abs(len(tokens)-target.get("length",len(tokens)))*0.03
        meta.update({"role_hist":hist.tolist(),"role_loss":role_loss,"entropy_loss":entropy_loss,"length_loss":length_loss})
        meta["score"]=base-role_loss-entropy_loss-length_loss
    return meta

def generate_multi(model,seed,N=24,target=None):
    target_roles=target["roles"] if target else None
    results=[]
    for _ in range(N):
        t=model.generate(seed,target_roles=target_roles)
        t=[x for x in t if x!=PAD]
        if t[-1]!=STOP: t.append(STOP)
        results.append((t,score(t,target)))
    return sorted(results,key=lambda x:x[1]["score"],reverse=True)

def export_ranked(results,tok,prefix="rank",top_k=5):
    Path("exports").mkdir(exist_ok=True)
    report=[]
    seen=set()
    r=0
    for tokens,meta in results:
        key=tuple(tokens)
        if key in seen: continue
        seen.add(key)
        b=tokens_to_bytes(tokens)
        open(f"exports/{prefix}_{r}.bin","wb").write(b)
        render_tokens_png(tokens,f"exports/{prefix}_{r}.png")
        item={"rank":r,"meta":meta,"tokens":tokens,"glyphs":tok.decode(tokens)}
        Path(f"exports/{prefix}_{r}.json").write_text(json.dumps(item,indent=2))
        report.append(item)
        print(f"[{prefix.upper()} {r}] score={meta['score']:.3f} H={meta['entropy']:.3f} valid={meta['valid']} bytes={meta['bytes']}")
        r+=1
        if r>=top_k: break
    Path(f"exports/{prefix}ed.json").write_text(json.dumps(report,indent=2))
    return report

def target_profile(kind="balanced"):
    if kind=="flow":
        arr=np.ones(16)*0.03
        arr[3]=0.20; arr[6]=0.15; arr[7]=0.15; arr[12]=0.16
    elif kind=="water":
        arr=np.ones(16)*0.03
        arr[7]=0.25; arr[12]=0.25; arr[3]=0.12
    elif kind=="transform":
        arr=np.ones(16)*0.03
        arr[7]=0.30; arr[11]=0.18; arr[13]=0.13
    else:
        arr=np.ones(16)/16
    arr=arr/arr.sum()
    return {"roles":arr,"entropy":3.0,"length":28}

def influence_report(model,tok):
    tests=["water flow","𓈖 flow","ꙹ flow","semantic glyph compression active","𓋹 power","꙰꙱ cycle"]
    rows=[]
    for text in tests:
        seed=vector_to_seed(text,START,8)
        gen=model.generate(seed,target_roles=target_profile("water")["roles"])
        meta=score(gen,target_profile("water"))
        rows.append({"input":text,"seed":seed,"tokens":gen,"glyphs":tok.decode(gen),"meta":meta})
    shifts=[]
    for i in range(len(rows)):
        for j in range(i+1,len(rows)):
            a=np.array(rows[i]["meta"]["role_hist"])
            b=np.array(rows[j]["meta"]["role_hist"])
            shifts.append({"a":rows[i]["input"],"b":rows[j]["input"],"kl_ab":kl_div(a,b),"kl_ba":kl_div(b,a),"entropy_delta":abs(rows[i]["meta"]["entropy"]-rows[j]["meta"]["entropy"])})
    Path("exports/influence_report.json").write_text(json.dumps({"rows":rows,"shifts":shifts},indent=2))
    print("[INFLUENCE] exports/influence_report.json")

def sync_exports_to_downloads():
    src = Path("exports")
    dst = Path.home() / "storage" / "downloads" / "glyph_exports"
    try:
        dst.mkdir(parents=True, exist_ok=True)
        for f in src.glob("*"):
            if f.is_file():
                (dst / f.name).write_bytes(f.read_bytes())
        print("[DOWNLOADS]", dst)
    except Exception as e:
        print("[DOWNLOADS-WARN]", e)


def archive_elites():
    import time, shutil
    src = Path("exports")
    dst = Path.home() / "storage" / "downloads" / "glyph_exports" / ("run_" + time.strftime("%Y%m%d_%H%M%S"))
    dst.mkdir(parents=True, exist_ok=True)
    for f in src.glob("*"):
        if f.is_file():
            shutil.copy2(f, dst / f.name)
    print("[ARCHIVE]", dst)

def main():
    tok=GlyphTokenizer()
    emb=TrainableGlyphEmbedding()
    emb.load()
    ds=load_dataset(tok)
    model=NGramSigilLM()
    model.fit(ds,epochs=10)

    seed=[START,0,2,4,6,8,10,12,14]
    normal=generate_multi(model,seed,N=24)
    export_ranked(normal,tok,prefix="rank",top_k=5)

    water_target=target_profile("water")
    controlled=generate_multi(model,emb.vector_to_seed("water 𓈖 ꙹ flow",START,8),N=24,target=water_target)
    export_ranked(controlled,tok,prefix="controlled",top_k=5)

    semantic=model.generate(emb.vector_to_seed("semantic glyph compression active",START,8))
    semantic_meta=score(semantic)
    Path("exports/semantic_aligned.json").write_text(json.dumps({"input":"semantic glyph compression active","tokens":semantic,"glyphs":tok.decode(semantic),"meta":semantic_meta},indent=2))
    render_tokens_png(semantic,"exports/semantic_aligned.png")

    influence_report(model,tok)

    emb.update("semantic glyph compression active", reward=semantic_meta["score"] if "semantic_meta" in locals() else 1.0)
    emb.save()
    Path("sigillm_state.json").write_text(json.dumps({"status":"controlled_semantic_steering_active_trainable_embedding","best":normal[0][1],"controlled_best":controlled[0][1]},indent=2))
    sync_exports_to_downloads()
    archive_elites()
    print("[DONE] controlled semantic steering + influence measurement complete")

if __name__=="__main__":
    main()
