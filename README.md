# exa-frontier

Exa-frontier: accuracy per dollar on FRAMES across Exa's own tiers, plus one cheap pipeline.

Exa publishes FRAMES accuracy by tier (Fast 0.375, Auto 0.46 on its versus page). Step one reproduces
those with one fixed answering model, the calibration. Step two runs a pipeline built only on Exa Fast:
one LLM call splits the question into up to three searches, then answers from all of them. The result is
accuracy, cost and latency for each, so you can see where the cheap pipeline lands on Exa's own curve.

## Results

<!-- results:start -->
_Run it to populate._
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
