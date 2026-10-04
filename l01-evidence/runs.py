import json, sys, uuid
sys.path.insert(0, sys.argv[1]); from stand import post, get
q, n, tag = sys.argv[2], int(sys.argv[3]), sys.argv[4]
out = []
for i in range(1, n + 1):
    sid = f"{tag}-{i}-{uuid.uuid4().hex[:6]}"
    r = post("/chat", {"session_id": sid, "message": q})
    tr = get(f"/api/_test/traces/{r['request_id']}")
    out.append({"session_id": sid, "resp": r, "trace": tr})
    print(f"\n--- run {i} sid={sid} rid={r['request_id']} steps={r.get('step_number')} ms={r.get('elapsed_ms')} tok={r.get('usage')}")
    print(r["answer"])
json.dump(out, open(f"{sys.argv[1]}/{tag}.json", "w"), indent=1, ensure_ascii=False)
