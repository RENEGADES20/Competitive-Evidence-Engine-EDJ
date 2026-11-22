# #275 (plans/0275-reduce-speed.md step 2, 0 calls): reads saved reduce records (Q<n>-reduce-*.json); args = glob patterns.
import json, glob, re, sys, os, statistics as st
W="Why it might matter: "
STOP=set("a an the and or of to in on at for by with from as is are was were be been it its this that these those which who what trade press reported reports said says has have had will would its their".split())
def body(t): return t.split(W,1)[0]
def words(t): return {w for w in re.findall(r"[a-z][a-z'-]+",t.lower()) if w not in STOP and len(w)>2}
def nums(t): return set(re.findall(r"\d[\d,.]*",t))
for pat in sys.argv[1:]:
    tot_rep=tot_cl=tot_chars=rep_chars=why_chars=0; rows=[]
    for f in sorted(glob.glob(pat), key=lambda p:int(re.search(r'Q(\d+)-',os.path.basename(p)).group(1))):
        d=json.load(open(f,encoding='utf-8')); raw=d.get('raw') or {}
        items=(raw.get('claims') or [])+(raw.get('adjacent') or [])
        if not items: continue
        seen=[]; rep=0; rc=0; ch=0; wc=0; parts_rep=set()
        for c in items:
            t=c['text']; b=body(t); ch+=len(t)
            if W in t: wc+=len(t)-len(b)
            wb,nb,cs=words(b),nums(b),set(c.get('chunk_ids',[]))
            hit=None
            for (pw,pn,pc,pp) in seen:
                if cs&pc and nb<=pn and wb and len(wb&pw)/len(wb|pw)>=0.5: hit=pp;break
            if hit is not None and hit!=c.get('part_id'): rep+=1; rc+=len(t)
            elif hit is not None: rep+=1; rc+=len(t)
            seen.append((wb,nb,cs,c.get('part_id')))
        rows.append((d['question_id'],len(items),rep,round(rc/ch,2),round(wc/ch,2)))
        tot_rep+=rep; tot_cl+=len(items); tot_chars+=ch; rep_chars+=rc; why_chars+=wc
    print('##',pat)
    print(' '.join(f"{q}:{n}/{r}/{s}/{w}" for q,n,r,s,w in rows))
    print('items',tot_cl,'repeats',tot_rep,'repeat char share',round(rep_chars/tot_chars,3),'why-line char share',round(why_chars/tot_chars,3))
    big=sorted(rows,key=lambda x:-x[3])[:6]; print('top repeat share', big)
