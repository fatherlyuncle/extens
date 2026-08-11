import json
from pathlib import Path

collection_file = Path(__file__).parent / "moxfield" / "collection.json"

with collection_file.open("r", encoding="utf-8") as f:
    collection = json.load(f)

print("Root fields:")
for key in collection:
    print(f"  {key}")

print()
print(f"Collection entries: {len(collection['data'])}")

print()
print("First collection entry:")
print(json.dumps(collection["data"][0], indent=2))
