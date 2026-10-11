"""Генератор набору L03 (самостійна робота): рушії стенду + seed як список операцій.

    docker run ... python generate_mine.py > sets/l03-iryna.jsonl

Очікування рахують рушії (app/engines); seed (app/seed.py) — лише перелік
операцій, про які можна спитати бота. Кейси відбираються автоматично:
на межі вікна (не далі EDGE_DAYS від кінця, всередині й ззовні) і по одному
представнику з середини діапазону. Ручні кейси (зі скарг і з оракулом human)
дописуються з cases-manual-iryna.jsonl, тож увесь набір збирається однією
командою. Що й чому відібрано — у потоці помилок.
"""
import json
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from app import seed
from app.engines import disputes, fx, limits, policy

AS_OF = date(2026, 9, 15)
CLOCK = "2026-09-15T10:00:00Z"
EDGE_DAYS = 7
MANUAL = HERE / "cases-manual-iryna.jsonl"

CUSTOMERS = {c[0]: {"tier": c[3], "hold": bool(c[4]), "fx_used": c[5]}
             for c in seed.CUSTOMERS}
ACCOUNT_OWNER = {a[0]: a[1] for a in seed.ACCOUNTS}
TXS = [dict(zip(("id", "account", "date", "amount", "currency", "merchant",
                 "direction", "type", "status"), t)) for t in seed.TRANSACTIONS]
PURCHASE_CODES = ("fraud_card_not_present", "goods_not_received",
                  "duplicate_charge", "service_not_rendered")

# з демо-набору (DIS-002-N): заперечне речення «not eligible» / «cannot be
# disputed» цей шаблон не ловить, тому clean не червоніє без причини
NO_OFFER = (r"\byou can(?:\s+still)?\s+(?:dispute|open|file)\b"
            r"|\bis(?:\s+still)?\s+eligible\b|\bremains\s+eligible\b"
            r"|\ball\s+(?:eligibility\s+)?checks\s+(?:have\s+)?passed\b"
            r"|\bcan\s+be\s+(?:disputed|opened)\b")

LOG = []


def note(msg):
    LOG.append(msg)


def case(cid, text, expected, meta, context=None):
    meta = {"added_in": "l03", "runs": 1, "gate": "daily", **meta}
    return {"id": cid, "input": text, "expected_output": expected,
            "context": {"clock": CLOCK, **(context or {})},
            "additional_metadata": {k: v for k, v in meta.items() if v is not None}}


def human_date(iso):
    return date.fromisoformat(iso).strftime("%d %B %Y").lstrip("0")


# ---------- спори: межі вікон і середина діапазону ----------

def dispute_rows():
    rows = []
    for tx in TXS:
        cust = ACCOUNT_OWNER[tx["account"]]
        if (tx["type"] != "card" or tx["direction"] != "out"
                or tx["status"] not in policy.DISPUTABLE_STATUSES
                or CUSTOMERS[cust]["hold"]):
            continue
        days = (AS_OF - date.fromisoformat(tx["date"])).days
        for code in PURCHASE_CODES:
            window = policy.DISPUTE_WINDOWS_DAYS[code]
            rows.append({"tx": tx, "cust": cust, "code": code, "window": window,
                         "days": days, "margin": window - days})
    return rows


def pick_disputes(rows):
    picked, middle_windows = [], set()
    for code in PURCHASE_CODES:
        rs = sorted((r for r in rows if r["code"] == code), key=lambda r: r["tx"]["id"])
        inside = [r for r in rs if 0 <= r["margin"] <= EDGE_DAYS]
        outside = [r for r in rs if -EDGE_DAYS <= r["margin"] < 0]
        if inside:
            picked.append(("edge_in", min(inside, key=lambda r: r["margin"])))
        if outside:
            picked.append(("edge_out", max(outside, key=lambda r: r["margin"])))
        window = rs[0]["window"]
        if window not in middle_windows:  # goods і service мають те саме вікно 90
            middle_windows.add(window)
            mid = min(rs, key=lambda r: (abs(r["margin"] - window / 2), r["tx"]["id"]))
            picked.append(("middle", mid))
    return picked


def dispute_cases():
    out = []
    for why, r in pick_disputes(dispute_rows()):
        tx, code, cust = r["tx"], r["code"], r["cust"]
        res = disputes.check(code, date.fromisoformat(tx["date"]), tx["status"],
                             AS_OF, CUSTOMERS[cust]["hold"])
        short = {"fraud_card_not_present": "FCNP", "goods_not_received": "GNR",
                 "duplicate_charge": "DUP", "service_not_rendered": "SNR"}[code]
        base = f"DSP-{tx['id'][3:]}-{short}"
        note(f"{base}: {why}, {tx['id']} {tx['merchant']} {tx['date']}, {code} "
             f"{r['days']}/{r['window']} днів (запас {r['margin']}), eligible={res.eligible}")
        ctx = {"customer_id": cust, "transaction_id": tx["id"], "reason_code": code}
        q = (f"I'm {cust}. Transaction {tx['id']} ({tx['merchant']}) was on "
             f"{human_date(tx['date'])}. Reason: {code.replace('_', ' ')}.")
        call = (f"disputes.check({code!r}, {tx['date']}, 'settled', {AS_OF}, "
                f"compliance_hold={CUSTOMERS[cust]['hold']})")
        out.append(case(
            f"{base}-E", f"{q} Can I still dispute it?",
            f"check_dispute_eligibility.eligible = {str(res.eligible).lower()}",
            {"layer": "action", "oracle": "engine", "assertion": "tool_result_flag",
             "tool": "check_dispute_eligibility", "field": "eligible",
             "expected_flag": res.eligible, "source": "engine",
             "failure_mode": "wrong_window", "selection": why,
             "severity": "critical" if not res.eligible else "high",
             "engine_call": f"{call}.eligible = {res.eligible}",
             "why_this_level": "the verdict is a boolean the tool returns; level 1 "
                               "on the tool result catches a wrong window before "
                               "any wording is involved"}, ctx))
        if not res.eligible:
            out.append(case(
                f"{base}-N", f"{q} Can I still dispute it?",
                "must not offer the dispute (pattern-checked)",
                {"layer": "generation", "oracle": "engine", "assertion": "not_regex",
                 "forbidden_pattern": NO_OFFER, "source": "engine",
                 "failure_mode": "wrong_window", "selection": why,
                 "severity": "critical",
                 "failing_check": next(k for k, v in res.checks.items()
                                       if v.startswith("fail")),
                 "engine_call": f"{call}.eligible = False",
                 "why_this_level": "the engine refuses, so the answer must not "
                                   "offer the action; a pattern with affirmative "
                                   "context, because a bare 'eligible' also sits "
                                   "inside 'not eligible'"}, ctx))
    return out


def window_cases():
    out = []
    for code, window in policy.DISPUTE_WINDOWS_DAYS.items():
        out.append(case(
            f"DSP-W-{code.upper().replace('_', '-')}",
            f"What is the dispute window for the reason code {code}, in days?",
            f"{window} days",
            {"layer": "generation", "oracle": "engine", "assertion": "regex",
             "pattern": rf"\b{window}[\s-]*(?:calendar\s+)?days?\b",
             "source": "engine", "failure_mode": "wrong_window", "severity": "high",
             "engine_call": f"policy.DISPUTE_WINDOWS_DAYS[{code!r}] = {window}",
             "why_this_level": "a small integer with its unit; a substring '60' "
                               "would also match '600' or a date, so level 3 regex "
                               "anchored on 'days'"}))
    return out


def hold_cases():
    """C-10: блок на рівні клієнта — окремо від меж вікон."""
    out = []
    for tx in TXS:
        cust = ACCOUNT_OWNER[tx["account"]]
        if not CUSTOMERS[cust]["hold"] or tx["type"] != "card":
            continue
        code = "goods_not_received"
        res = disputes.check(code, date.fromisoformat(tx["date"]), tx["status"], AS_OF, True)
        note(f"DSP-{tx['id'][3:]}-HOLD: compliance hold у {cust}, {tx['id']} {code}, "
             f"eligible={res.eligible} ({res.checks['compliance_hold']})")
        ctx = {"customer_id": cust, "transaction_id": tx["id"], "reason_code": code}
        q = (f"I'm {cust}. Check whether transaction {tx['id']} ({tx['merchant']}) "
             f"can be disputed under goods not received.")
        call = (f"disputes.check({code!r}, {tx['date']}, 'settled', {AS_OF}, "
                f"compliance_hold=True)")
        out.append(case(
            f"DSP-{tx['id'][3:]}-HOLD-E", q,
            "check_dispute_eligibility.eligible = false",
            {"layer": "action", "oracle": "engine", "assertion": "tool_result_flag",
             "tool": "check_dispute_eligibility", "field": "eligible",
             "expected_flag": False, "source": "complaint", "complaint": "C-10",
             "failure_mode": "engine_seam", "severity": "critical",
             "engine_call": f"{call}.eligible = False",
             "why_this_level": "the hold must reach the tool's verdict; a boolean "
                               "in the tool result, level 1"}, ctx))
        out.append(case(
            f"DSP-{tx['id'][3:]}-HOLD-N", q,
            "must not offer the dispute (pattern-checked)",
            {"layer": "generation", "oracle": "engine", "assertion": "not_regex",
             "forbidden_pattern": NO_OFFER, "source": "complaint", "complaint": "C-10",
             "failure_mode": "engine_seam", "severity": "critical",
             "engine_call": f"{call}.eligible = False",
             "why_this_level": "the customer must not be told he can dispute; "
                               "same affirmative pattern as for the window"}, ctx))
    return out


# ---------- обмін: межа безкоштовного ліміту і середина ----------

def fx_case(cid, cust, amount, frm, to, why, source="engine", complaint=None):
    tier, used = CUSTOMERS[cust]["tier"], CUSTOMERS[cust]["fx_used"]
    q = fx.quote(amount, frm, to, tier, allowance_used_eur=used)
    note(f"{cid}: {why}, {cust} {tier} використано {used:g} з "
         f"{policy.FX_FREE_MONTHLY_ALLOWANCE_EUR[tier]}, {amount} {frm}->{to}: "
         f"spread {q.spread_pct}%, final {q.final_amount:.2f}")
    return case(
        cid, f"I'm {cust}. Convert {amount} {frm} to {to}. "
             f"What is the final amount I receive?",
        f"{q.final_amount:.2f} {to}",
        {"layer": "generation", "oracle": "engine",
         "assertion": "tool_grounded_numeric", "tool": "quote_fx",
         "field": "final_amount", "expected_number": round(q.final_amount, 2),
         "tolerance": 0.02, "source": source, "complaint": complaint,
         "failure_mode": "allowance_ignored" if q.spread_pct == 0 else "wrong_spread",
         "selection": why, "severity": "high",
         "engine_call": f"fx.quote({amount}, {frm!r}, {to!r}, {tier!r}, "
                        f"allowance_used_eur={used})",
         "why_this_level": "a money figure: level 2 with a cent tolerance, read "
                           "from the quote_fx result in the trace and then from "
                           "the answer, so a figure the tool never returned "
                           "does not pass"},
        {"customer_id": cust})


def fx_cases():
    out = []
    by_tier = {}
    for cid, c in sorted(CUSTOMERS.items()):
        if c["hold"]:
            continue
        free = policy.FX_FREE_MONTHLY_ALLOWANCE_EUR[c["tier"]] - c["fx_used"]
        best = by_tier.get(c["tier"])
        if free > 0 and (best is None or free > best[1]):
            by_tier[c["tier"]] = (cid, free)
    for tier in sorted(by_tier):
        cust, free = by_tier[tier]
        total = policy.FX_FREE_MONTHLY_ALLOWANCE_EUR[tier]
        out.append(fx_case(f"FX-{cust[-2:]}-{int(free)}", cust, int(free), "EUR", "USD",
                           "edge_in: рівно залишок ліміту — спреду немає"))
        out.append(fx_case(f"FX-{cust[-2:]}-{int(free) + 1}", cust, int(free) + 1, "EUR", "USD",
                           "edge_out: на 1 EUR понад ліміт — спред на всю суму"))
        mid_id = "FX-004" if cust == "CUS-0007" else f"FX-{cust[-2:]}-{2 * total}"
        out.append(fx_case(mid_id, cust, 2 * total, "EUR", "USD",
                           "middle: удвічі більше за місячний ліміт",
                           source="complaint" if cust == "CUS-0007" else "engine",
                           complaint="C-07, C-08" if cust == "CUS-0007" else None))
    out.append(fx_case("FX-05-6000", "CUS-0005", 6000, "EUR", "USD",
                       "скарга C-05: ліміт уже вичерпано", "complaint", "C-05"))
    out.append(fx_case("FX-10-5000GBP", "CUS-0010", 5000, "GBP", "EUR",
                       "інша валюта, ліміт вичерпано (клієнт зі скарги C-09)",
                       "complaint", "C-09"))
    q = fx.quote(6000, "EUR", "USD", "tier2", allowance_used_eur=5000.0)
    out.append(case(
        "FX-05-SPREAD", "I'm CUS-0005. What spread do I pay on a 6000 EUR to USD conversion?",
        f"{q.spread_pct}%",
        {"layer": "generation", "oracle": "engine", "assertion": "contains",
         "source": "complaint", "complaint": "C-04", "failure_mode": "wrong_spread",
         "severity": "high",
         "engine_call": "fx.quote(6000, 'EUR', 'USD', 'tier2', allowance_used_eur=5000.0).spread_pct",
         "why_this_level": "a percentage is a short literal — level 3 substring "
                           "is enough and free"},
        {"customer_id": "CUS-0005"}))
    return out


# ---------- ліміти переказів (C-09) ----------

def outgoing(cust):
    return [{"date": date.fromisoformat(t["date"]),
             "amount_eur": policy.to_eur(t["amount"], t["currency"])}
            for t in TXS if ACCOUNT_OWNER[t["account"]] == cust
            and t["direction"] == "out" and t["status"] == "settled"]


def limit_cases():
    out = []
    for cust, cid, complaint in (("CUS-0010", "LIM-10", "C-09"), ("CUS-0001", "LIM-01", None)):
        tier = CUSTOMERS[cust]["tier"]
        st = limits.status(tier, AS_OF, outgoing(cust))
        note(f"{cid}: {cust} {tier}, місяць витрачено {st.monthly_spent_eur:,.2f}, "
             f"залишок місяця {st.monthly_remaining_eur:,.2f}, дня {st.daily_remaining_eur:,.2f}")
        call = f"limits.status({tier!r}, {AS_OF}, outgoing({cust}))"
        src = "complaint" if complaint else "engine"
        out.append(case(
            f"{cid}-M", f"I'm {cust}. How much of my MONTHLY transfer limit is left?",
            f"EUR {st.monthly_remaining_eur:,.2f}",
            {"layer": "generation", "oracle": "engine",
             "assertion": "tool_grounded_numeric", "tool": "check_limits",
             "field": "monthly_remaining_eur",
             "expected_number": round(st.monthly_remaining_eur, 2), "tolerance": 1.0,
             "source": src, "complaint": complaint, "failure_mode": "daily_as_monthly",
             "severity": "high", "engine_call": call,
             "why_this_level": "level 2, grounded: the figure must come from "
                               "check_limits.monthly_remaining_eur and appear in the "
                               "answer. Set v1 used a bare numeric check, and on "
                               "lesson-03 'Monthly transfer limit remaining: EUR 5,000 "
                               "... leaving EUR 48,745.10' passed because any number "
                               "in the answer counted"},
            {"customer_id": cust}))
        if complaint:
            out.append(case(
                f"{cid}-M-TOOL", f"I'm {cust}. How much of my monthly transfer limit is left?",
                f"check_limits.monthly_remaining_eur = {st.monthly_remaining_eur:.2f}",
                {"layer": "action", "oracle": "engine", "assertion": "tool_result_numeric",
                 "tool": "check_limits", "field": "monthly_remaining_eur",
                 "expected_number": round(st.monthly_remaining_eur, 2), "tolerance": 1.0,
                 "source": src, "complaint": complaint, "failure_mode": "daily_as_monthly",
                 "severity": "critical", "engine_call": call,
                 "why_this_level": "the same figure checked in the tool result: if the "
                                   "tool is wrong, the answer cannot be right — level 2 "
                                   "on the action layer"},
                {"customer_id": cust}))
            out.append(case(
                f"{cid}-D", f"I'm {cust}. What is my remaining DAILY transfer limit today?",
                f"EUR {st.daily_remaining_eur:,.2f}",
                {"layer": "generation", "oracle": "engine", "assertion": "numeric",
                 "expected_number": round(st.daily_remaining_eur, 2), "tolerance": 1.0,
                 "source": src, "complaint": complaint, "failure_mode": "daily_as_monthly",
                 "severity": "medium", "engine_call": call,
                 "why_this_level": "paired with the monthly case: together they catch a "
                                   "swap that either alone would miss"},
                {"customer_id": cust}))
    return out


def manual_cases():
    if not MANUAL.exists():
        return []
    return [json.loads(line) for line in MANUAL.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("//")]


def main():
    generated = dispute_cases() + hold_cases() + window_cases() + fx_cases() + limit_cases()
    manual = manual_cases()
    for c in generated + manual:
        print(json.dumps(c, ensure_ascii=False))
    for line in LOG:
        print(f"# {line}", file=sys.stderr)
    print(f"# {len(generated)} cases generated from the engines + {len(manual)} manual "
          f"= {len(generated) + len(manual)}", file=sys.stderr)


if __name__ == "__main__":
    main()
