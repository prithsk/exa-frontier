import bench
bench.exa = lambda q, kind, n=5: ([f"doc about {q}"], 0.005, 0.4)
bench.llm = lambda p, model="gpt-4o-mini": (("CORRECT" if "Gold answer" in p and "Paris" in p.split("Predicted:")[-1] else "q1\nq2\nq3\nq4") if ("Gold" in p or "Break" in p) else "Paris", 0.0001)
r = bench.split_fast({"q": "Capital of France?", "a": "Paris"}); assert r["subqueries"] == 3 and r["ok"] == 1 and abs(r["exa_cost"] - 0.015) < 1e-9, r
t = bench.tier({"q": "Capital?", "a": "Paris"}, "fast"); s = bench.summarize([t, r]); assert s["acc"] == 1.0 and s["n"] == 2
print("all tests passed")
