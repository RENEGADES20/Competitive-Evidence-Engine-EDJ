# #275 (plans/0275-reduce-speed.md step 2, 0 calls): reads saved reduce records (Q<n>-reduce-*.json); args = glob patterns.
import json, glob, re, sys, os
W="Why it might matter: "
STOP=set("a an the and or of to in on at for by with from as is are was were be been it its this that these those which who what trade press reported reports said says has have had will would its their".split())
def body(t): return t.split(W,1)[0]
def words(t): return {w for w in re.findall(r"[a-z][a-z'-]+",t.lower()) if w not in STOP and len(w)>2}
def nums(t): return set(re.findall(r"\d[\d,.]*",t))
for pat in sys.argv[1:]:
    T=R=A=0; ans_tok=0; saved_tok=0
    for f in glob.glob(pat):
        d=json.load(open(f,encoding='utf-8')); raw=d.get('raw') or {}
        u=d.get('usage') or {}; at=(u.get('output_tokens') or 0)-(u.get('reasoning_tokens') or 0)
        items=(raw.get('claims') or [])
        adj=raw.get('adjacent') or []
        allc=sum(len(c['text']) for c in items+adj)+1
        per=[c.get('part_id') for c in items]
        left={p:per.count(p) for p in set(per)}
        seen=[]; rm=0
        for c in items:
            b=body(c['text']); wb,nb,cs=words(b),nums(b),set(c.get('chunk_ids',[]))
            rep=any(cs&pc and nb<=pn and wb and len(wb&pw)/len(wb|pw)>=0.5 for pw,pn,pc in seen)
            if rep and left[c.get('part_id')]>1:
                rm+=len(c['text']); left[c.get('part_id')]-=1
            else: seen.append((wb,nb,cs))
        asp=sum(len(c['text']) for c in items if re.fullmatch(r"a\d+",str(c.get('part_id',''))))
        T+=allc; R+=rm; A+=asp; ans_tok+=at; saved_tok+=at*rm/allc
    print(pat[-40:], 'removable repeats (keep 1/cell) char share',round(R/T,3),'est answer tokens saved',round(saved_tok),'of',ans_tok,'| aspect-level (cross-firm) claim char share',round(A/T,3))
