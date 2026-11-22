# #275 (plans/0275-reduce-speed.md step 2, 0 calls): reads saved reduce records (Q<n>-reduce-*.json); args = glob patterns.
import json, glob, sys, re, statistics as st, os
def norm(t): return re.sub(r'\W+',' ',t.lower()).strip()
def rows(pat):
    out=[]
    for f in sorted(glob.glob(pat), key=lambda p:int(re.search(r'Q(\d+)-',os.path.basename(p)).group(1))):
        d=json.load(open(f,encoding='utf-8'))
        u=d.get('usage') or {}
        o=u.get('output_tokens') or 0; r=u.get('reasoning_tokens') or 0
        raw=d.get('raw') or {}
        cl=raw.get('claims') or []
        txt=[norm(c.get('text','')) for c in cl]
        dup=len(txt)-len(set(txt))
        # near-dup: same first 12 words
        heads=[ ' '.join(t.split()[:12]) for t in txt]
        ndup=len(heads)-len(set(heads))
        # same chunk set repeated
        cs=[tuple(sorted(c.get('chunk_ids',[]))) for c in cl]
        cdup=len(cs)-len(set(cs))
        js=len(json.dumps(raw,ensure_ascii=False))
        out.append(dict(q=d['question_id'],out=o,reas=r,ans=o-r,claims=len(cl),adj=len(raw.get('adjacent') or []),gaps=len(raw.get('gaps') or []),
            dup=dup,ndup=ndup,cdup=cdup,chars=js,wall=d.get('wall_s'),ttft=d.get('ttft_s'),stop=d.get('stop_reason'),beh=raw.get('behavior') or d.get('behavior'),err=d.get('error') or d.get('status')))
    return out
for pat in sys.argv[1:]:
    R=rows(pat); print('##',pat,len(R))
    print('q out reas ans claims adj gaps dupExact dupHead12 sameChunks jsonChars wall ttft stop beh')
    for x in R: print(x['q'],x['out'],x['reas'],x['ans'],x['claims'],x['adj'],x['gaps'],x['dup'],x['ndup'],x['cdup'],x['chars'],x['wall'],x['ttft'],x['stop'],x['beh'], x['err'] if x['err'] else '')
    ok=[x for x in R if x['out']]
    for k in ('out','reas','ans','claims','chars','wall'):
        v=sorted(x[k] for x in ok if x[k] is not None)
        if v: print(k,'p50',st.median(v),'p90',v[int(0.9*(len(v)-1))],'max',v[-1],'sum',round(sum(v),1))
    print('reasoning share of output', round(sum(x['reas'] for x in ok)/sum(x['out'] for x in ok),3))
    print('ans tokens per claim median', st.median([x['ans']/x['claims'] for x in ok if x['claims']]))
