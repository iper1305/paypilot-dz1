import json, sys
sys.path.insert(0, sys.argv[1]); from stand import post
qs = [
"I'm CUS-0008. What is the fee for a SWIFT transfer at Verta?",
"I'm CUS-0001. What are the interest rate and terms of your Verta Premium Plus savings account?",
"I'm CUS-0001. I lost my card, what should I do?",
"I'm CUS-0001. What is my balance?",
"Can you give me tax advice on my savings?",
]
out = []
for i, q in enumerate(qs, 1):
    r = post("/api/_test/compare", {"message": q})
    out.append({"q": q, "r": r})
    print(f"\n=================== Q{i}: {q}")
    for side in ("clean", "profile"):
        s = r[side]
        print(f"\n--- {side} [{s['profile']} {s['active_defects']}] rid={s['request_id']} tok={s['usage']}")
        print(s["answer"])
json.dump(out, open(sys.argv[1] + "/step1/all.json", "w"), indent=1, ensure_ascii=False)
