import json
with open("agent_cache/sector_predictions.json", encoding="utf-8") as f:
    d = json.load(f)
print("Keys:", list(d.keys()))
preds = d.get("predictions", {})
print("Prediction keys:", list(preds.keys()))
for tf in ["1M","3M","6M","12M"]:
    items = preds.get(tf, [])
    print(f"{tf}: {len(items)} items")
    if items:
        print(f"  First: {items[0].get('sector')} ({items[0].get('predicted_return')})")

if "error" in d:
    print("ERROR:", d["error"])
