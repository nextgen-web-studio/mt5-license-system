import json

with open("frontend/public/manifest.json", "r", encoding="utf-8") as f:
    m = json.load(f)

m["orientation"] = "portrait"
m["display_override"] = ["standalone", "minimal-ui"]
m["scope"] = "/"
m["prefer_related_applications"] = False
m["categories"] = ["business", "finance", "productivity"]

with open("frontend/public/manifest.json", "w", encoding="utf-8") as f:
    json.dump(m, f, indent=2)
print("Updated manifest.json")
