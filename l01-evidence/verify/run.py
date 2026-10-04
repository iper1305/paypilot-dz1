import json, sys, uuid, concurrent.futures as cf
S = sys.argv[1]; sys.path.insert(0, S); sys.path.insert(0, S + "/verify")
from stand import post, get
from probes import SP, US
def tools_of(rid):
    t = get(f"/api/_test/traces/{rid}"); acc = []
    def walk(sp):
        if sp["name"].startswith("tool."):
            a = sp["attributes"]; acc.append({"tool": sp["name"][5:], "args": a.get("tool.arguments"), "result": a.get("tool.result")})
        for c in sp.get("children", []): walk(c)
    walk(t); return acc, t["attributes"].get("run.profile"), t["attributes"].get("prompt.version")
def chat_run(pid, turns, k):
    sid = f"verify-{pid}-{k}-{uuid.uuid4().hex[:6]}"; out = []
    for m in turns:
        r = post("/chat", {"session_id": sid, "message": m})
        tools, prof, pv = tools_of(r["request_id"])
        out.append({"msg": m, "answer": r["answer"], "rid": r["request_id"], "ms": r["elapsed_ms"], "usage": r["usage"], "tools": tools, "profile": prof, "prompt": pv})
    return {"pid": pid, "k": k, "mode": "chat-lesson01", "sid": sid, "turns": out}
mode = sys.argv[2]
if mode == "chat":
    jobs = [(p, t, k) for p, t in SP + US for k in (1, 2, 3)]
    with cf.ThreadPoolExecutor(8) as ex:
        res = list(ex.map(lambda j: chat_run(*j), jobs))
    json.dump(res, open(f"{S}/verify/chat.json", "w"), indent=1, ensure_ascii=False)
else:
    res = []
    plan = [(p, t[0], 1) for p, t in SP if len(t) == 1] + [(p, t[0], 3) for p, t in US if len(t) == 1]
    for pid, msg, n in plan:
        for k in range(1, n + 1):
            r = post("/api/_test/compare", {"message": msg})
            for side in ("clean", "profile"):
                tools, prof, pv = tools_of(r[side]["request_id"])
                res.append({"pid": pid, "k": k, "mode": f"compare-{side}", "profile": prof, "prompt": pv,
                            "answer": r[side]["answer"], "rid": r[side]["request_id"], "tools": tools})
            print(pid, k, "ok", flush=True)
    json.dump(res, open(f"{S}/verify/compare.json", "w"), indent=1, ensure_ascii=False)
print("done", len(res))
