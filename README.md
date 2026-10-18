# exa-frontier

Exa-frontier: accuracy per dollar on FRAMES across Exa's own tiers, plus one cheap pipeline.

Exa publishes FRAMES accuracy by tier (Fast 0.375, Auto 0.46 on its versus page). Step one reproduces
those with one fixed answering model, the calibration. Step two runs a pipeline built only on Exa Fast:
one LLM call splits the question into up to three searches, then answers from all of them. The result is
accuracy, cost and latency for each, so you can see where the cheap pipeline lands on Exa's own curve.

## Results

<!-- results:start -->
# Exa on FRAMES: accuracy, cost and latency, 2026-10-18

First 100 FRAMES questions. Every row answers and judges with gpt-4o-mini, so only retrieval differs.

| Pipeline | Accuracy | Exa published | Cost per question | p50 latency |
|---|---|---|---|---|
| Exa Fast | 0.400 | 0.375 | $0.0075 | 0.5s |
| Exa Auto | 0.440 | 0.46 | $0.0075 | 6.2s |
| Exa Fast + 3-way split | 0.310 | - | $0.0219 | 2.8s |

## Honest limits

- 100 questions, so accuracy differences under about 0.07 are inside sampling noise.
- Exa's published numbers use their own answering setup. If the calibration rows land far from them, the comparison below them is what matters, not the absolute level.
- Costs use Exa's reported per-request cost when the API returns it, else list price, plus gpt-4o-mini token cost.
<!-- results:end -->

## Run it

```
pip install -r requirements.txt
cp .env.example .env    # keys: EXA_API_KEY, OPENAI_API_KEY
python bench.py --n 100
```

Every run writes `results/<date>.md` with the numbers and an honest-limits section.

## License

MIT
