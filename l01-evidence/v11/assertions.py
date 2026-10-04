"""Програмні перевірки трьох переформульованих вимог base.v1.1 (R1a, R1b, R1c, R2, R3)."""
import re, os
CORPUS = set(os.listdir(os.path.join(os.environ.get("STAND_DIR", "../paypilot-stand"), "app/rag/corpus")))
EMOJI = re.compile("[\U0001F000-\U0001FAFF✅✨❤⭐]")
def first_sentence(a):
    t = re.sub(r"[*_#`>]", "", a).strip()
    return re.split(r"(?<=[.!?])\s+|\n", t, maxsplit=1)[0]
SITUATION = re.compile(r"\b(lost|stolen|fraud|unrecogni[sz]e\w*|don'?t recogni[sz]e|didn'?t make)\b", re.I)
INSTRUCTION = re.compile(r"\b(please|you should|you need to|you must|make sure|call|contact|go to|log in|open the app|freeze|report)\b", re.I)
NEG = re.compile(r"\b(no|not|isn'?t|won'?t|can'?t|cannot|doesn'?t|unable)\b", re.I)
POS_OPEN = re.compile(r"^\W*(good news|great news|yes)\b", re.I)
NOINFO = re.compile(r"(no information|don'?t have (any )?(information|details|data)|not (able to )?find|couldn'?t find|isn'?t (a|an)\b|does ?n[o']t (exist|offer)|not offer|no (details|data|record)|unable to find|not aware of|not part of)", re.I)
OFFER = re.compile(r"(search|escalat|human agent|specialist)", re.I)
def results(tools): return [t.get("result") for t in tools if isinstance(t.get("result"), dict)]
def r1a(a, tools):  # T1: перше речення називає ситуацію і не містить інструкції
    fs = first_sentence(a); return bool(SITUATION.search(fs)) and not INSTRUCTION.search(fs)
def r1b(a, tools):  # будь-яка відповідь: немає емодзі
    return not EMOJI.search(a)
YESNO = re.compile(r"^(?:I'm CUS-\d+\.\s*)?(is|are|can|do|does|will)\b", re.I)
def r1c_applies(tools, q=''):
    if q and not YESNO.search(q): return False
    return any(r.get("allowance_applied") is False or r.get("eligible") is False for r in results(tools))
def r1c(a, tools):  # якщо allowance_applied=false або eligible=false: без позитивного відкриття + заперечення в першому реченні
    fs = first_sentence(a); return not POS_OPEN.search(fs) and bool(NEG.search(fs))
def pcts(a): return {float(x) for x in re.findall(r"(\d+(?:\.\d+)?)\s?%", a)}
def r2(a, tools, qid):
    """Обов'язкові цифри з джерел присутні; жодного 'чужого' відсотка; фінальна сума = оракул."""
    srcs = results(tools); txt = " ".join(f["text"] for r in srcs for f in r.get("fragments", []))
    allowed_pct = {float(x) for x in re.findall(r"(\d+(?:\.\d+)?)\s?%", txt)}
    q = next((r for r in srcs if "final_amount" in r), None)
    if q: allowed_pct.add(float(q["spread_pct"]))
    extra = pcts(a) - allowed_pct
    if qid == "T3":
        need = [r"15(\.00)?\b", r"0\.3\s?%"]
        finals_ok = all(abs(15 + float(amt.replace(",", "")) * 0.003 - float(fin.replace(",", ""))) < 0.01
                        for amt, fin in re.findall(r"EUR ([\d,]+(?:\.\d+)?) (?:SWIFT )?transfer[^=]*?= EUR ([\d,]+\.\d{2})", a))
    else:
        if not q: return False
        need = [re.escape(f"{q['spread_pct']:g}") + r"\s?%", re.escape(f"{q['spread_amount']:.2f}"), re.escape(f"{q['final_amount']:.2f}"), r"\b" + f"{q['allowance_total_eur']:g}" + r"\b", r"\b" + f"{q['allowance_used_before_eur']:g}" + r"\b"]
        finals_ok = True
    return all(re.search(n, a) for n in need) and not extra and finals_ok
def r3(a, tools, product_pat):
    """Якщо жоден фрагмент КОРПУСУ і жоден результат інструмента не містить умов продукту — 'немає інформації' в першому реченні, без %, з пропозицією."""
    kb_called = any(t["tool"] == "search_knowledge_base" for t in tools)
    corpus_txt = " ".join(f["text"] for r in results(tools) for f in r.get("fragments", []) if f["doc"] in CORPUS)
    if re.search(product_pat, corpus_txt, re.I): return None  # вимога не застосовна
    return kb_called and bool(NOINFO.search(first_sentence(a))) and "%" not in a and bool(OFFER.search(a))
