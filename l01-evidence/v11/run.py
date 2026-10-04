import json, sys, uuid, urllib.request, concurrent.futures as cf
S, base, tag = sys.argv[1], sys.argv[2], sys.argv[3]
Q = {
 "T1": "I'm CUS-0001. I lost my card, what should I do?",
 "T2": "I'm CUS-0001. Is it free for me to convert EUR 500 to USD this month?",
 "T3": "I'm CUS-0008. What is the fee for a SWIFT transfer at Verta?",
 "T4": "I'm CUS-0001. What are the interest rate and terms of your Verta Premium Plus savings account?",
 "T5": "I'm CUS-0001. What interest rate does my current account pay?",
 "T6": "I'm CUS-0001. How much USD will I get if I convert EUR 500 right now?",
 "T7": "I'm CUS-0001. I want to talk to a human, please.",
}
only = sys.argv[4].split(",") if len(sys.argv) > 4 else list(Q)
def req(path, body=None):
    r = urllib.request.Request(base + path, data=json.dumps(body).encode() if body else None, headers={"content-type": "application/json"}, method="POST" if body else "GET")
    with urllib.request.urlopen(r, timeout=240) as f: return json.loads(f.read())
def one(qid, k):
    sid = f"{tag}-{qid}-{k}-{uuid.uuid4().hex[:6]}"
    r = req("/chat", {"session_id": sid, "message": Q[qid]})
    t = req(f"/api/_test/traces/{r['request_id']}")
    tools = []
    def walk(sp):
        if sp["name"].startswith("tool."): tools.append({"tool": sp["name"][5:], "args": sp["attributes"].get("tool.arguments"), "result": sp["attributes"].get("tool.result")})
        for c in sp.get("children", []): walk(c)
    walk(t)
    return {"qid": qid, "q": Q[qid], "k": k, "sid": sid, "rid": r["request_id"], "answer": r["answer"], "ms": r["elapsed_ms"], "tools": tools,
            "profile": t["attributes"].get("run.profile"), "defects": t["attributes"].get("run.active_defects"), "prompt": t["attributes"].get("prompt.version")}
jobs = [(q, k) for q in only for k in range(1, 6)]
with cf.ThreadPoolExecutor(6) as ex: res = list(ex.map(lambda j: one(*j), jobs))
json.dump(res, open(f"{S}/v11/runs/{tag}.json", "w"), indent=1, ensure_ascii=False)
print(tag, len(res), "runs;", {r["prompt"] for r in res}, {tuple(r["defects"]) for r in res})
