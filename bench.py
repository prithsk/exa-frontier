"""exa-frontier: accuracy per dollar on FRAMES across Exa's own tiers, plus one cheap pipeline.

Exa publishes FRAMES accuracy by tier (Fast 0.375, Auto 0.46 on its versus page). Step one reproduces
those with one fixed answering model, the calibration. Step two runs a pipeline built only on Exa Fast:
one LLM call splits the question into up to three searches, then answers from all of them. The result is
accuracy, cost and latency for each, so you can see where the cheap pipeline lands on Exa's own curve.

  python bench.py --n 100          # needs EXA_API_KEY and OPENAI_API_KEY in .env
"""
import argparse, concurrent.futures as cf, csv, io, json, statistics, time, urllib.request, datetime as dt
import requests
from common import ROOT, need, os

FRAMES = "https://huggingface.co/datasets/google/frames-benchmark/resolve/main/test.tsv"
PRICE = {"fast": float(os.environ.get("EXA_PRICE_FAST", "0.007")), "auto": float(os.environ.get("EXA_PRICE_AUTO", "0.007"))}
PUBLISHED = {"fast": 0.375, "auto": 0.46}

def frames(n):
    p = ROOT / "data" / "frames.tsv"; p.parent.mkdir(exist_ok=True)
    if not p.exists(): p.write_bytes(urllib.request.urlopen(FRAMES, timeout=120).read())
    rows = list(csv.DictReader(io.StringIO(p.read_text(encoding="utf-8")), delimiter="\t"))
    return [{"q": r["Prompt"], "a": r["Answer"]} for r in rows][:n]

def exa(query, kind, n=5):
    t = time.perf_counter()
    r = requests.post("https://api.exa.ai/search", timeout=120, headers={"x-api-key": os.environ["EXA_API_KEY"]},
                      json={"query": query, "type": kind, "numResults": n, "contents": {"text": {"maxCharacters": 2500}}})
    if r.status_code >= 400: raise SystemExit(f"Exa {r.status_code}: {r.text[:300]}")
    j = r.json(); docs = [f"[{x.get('title', '')}] {x.get('text', '')}" for x in j.get("results", [])]
    cost = (j.get("costDollars") or {}).get("total") or PRICE.get(kind, 0.007)
    return docs, cost, time.perf_counter() - t

def llm(prompt, model="gpt-4o-mini"):
    from openai import OpenAI
    r = OpenAI(max_retries=8).chat.completions.create(model=model, temperature=0, messages=[{"role": "user", "content": prompt}])
    u = r.usage; return r.choices[0].message.content.strip(), (u.prompt_tokens * 0.15 + u.completion_tokens * 0.6) / 1e6

def answer(q, docs):
    ctx = "\n\n".join(docs)[:30000]
    return llm(f"Answer the question using the sources. Reply with only the final answer.\n\nSources:\n{ctx}\n\nQuestion: {q}\nAnswer:")

def judge(q, gold, pred):
    v, c = llm(f"Question: {q}\nGold answer: {gold}\nPredicted: {pred}\nDoes the prediction contain the gold answer's meaning? Reply CORRECT or WRONG.")
    return int(v.upper().startswith("CORRECT")), c

def tier(item, kind):
    docs, ec, lat = exa(item["q"], kind); a, c1 = answer(item["q"], docs); ok, c2 = judge(item["q"], item["a"], a)
    return {"ok": ok, "exa_cost": ec, "llm_cost": c1 + c2, "latency": lat}

def split_fast(item):
    t = time.perf_counter()
    subs, c0 = llm("Break this question into at most 3 short web searches that together find every fact it needs. "
                   f"One per line, no numbering.\n\nQuestion: {item['q']}")
    qs = [s.strip("-• ").strip() for s in subs.splitlines() if s.strip()][:3] or [item["q"]]
    with cf.ThreadPoolExecutor(3) as ex: res = list(ex.map(lambda s: exa(s, "fast", 3), qs))
    docs = [d for r in res for d in r[0]]; ec = sum(r[1] for r in res)
    a, c1 = answer(item["q"], docs); ok, c2 = judge(item["q"], item["a"], a)
    return {"ok": ok, "exa_cost": ec, "llm_cost": c0 + c1 + c2, "latency": time.perf_counter() - t, "subqueries": len(qs)}

def summarize(rs):
    return {"acc": statistics.mean(r["ok"] for r in rs), "cost_q": statistics.mean(r["exa_cost"] + r["llm_cost"] for r in rs),
            "p50_s": statistics.median(r["latency"] for r in rs), "n": len(rs)}

def main(n, workers):
    need("EXA_API_KEY", "OPENAI_API_KEY"); items = frames(n); out = {}
    cache = ROOT / "results" / "raw.json"; cache.parent.mkdir(exist_ok=True)
    raw = json.loads(cache.read_text()) if cache.exists() else {}
    for name, fn in [("Exa Fast", lambda it: tier(it, "fast")), ("Exa Auto", lambda it: tier(it, "auto")), ("Exa Fast + 3-way split", split_fast)]:
        if name not in raw or len(raw[name]) < len(items):
            with cf.ThreadPoolExecutor(workers) as ex: raw[name] = list(ex.map(fn, items))
            cache.write_text(json.dumps(raw)); print(f"  {name}: done", flush=True)
        out[name] = summarize(raw[name][: len(items)])
    pub = {"Exa Fast": PUBLISHED["fast"], "Exa Auto": PUBLISHED["auto"]}
    md = [f"# Exa on FRAMES: accuracy, cost and latency, {dt.date.today()}", "",
          f"First {len(items)} FRAMES questions. Every row answers and judges with gpt-4o-mini, so only retrieval differs.", "",
          "| Pipeline | Accuracy | Exa published | Cost per question | p50 latency |", "|---|---|---|---|---|"]
    for k, v in out.items():
        md.append(f"| {k} | {v['acc']:.3f} | {pub.get(k, '-')} | ${v['cost_q']:.4f} | {v['p50_s']:.1f}s |")
    md += ["", "## Honest limits", "",
           f"- {len(items)} questions, so accuracy differences under about 0.07 are inside sampling noise.",
           "- Exa's published numbers use their own answering setup. If the calibration rows land far from them, the comparison below them is what matters, not the absolute level.",
           "- Costs use Exa's reported per-request cost when the API returns it, else list price, plus gpt-4o-mini token cost."]
    s = "\n".join(md); (ROOT / "results" / f"{dt.date.today()}.md").write_text(s, encoding="utf-8"); print(s)

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--n", type=int, default=100); ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args(); main(a.n, a.workers)
