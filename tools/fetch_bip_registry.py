# -*- coding: utf-8 -*-
"""Pobiera pełny rejestr JST (gminy+powiaty) z oficjalnego API podmiotów BIP
(backend aplikacji https://www.gov.pl/web/bip/spis-podmiotow)
i zapisuje do data/bip_jst.json w repo."""
import json, os, requests

BASE = "https://aplikacje.gov.pl/app/bip-back/api/subjects"
H = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
OUT = os.path.join(os.path.dirname(__file__), "..", "data", "bip_jst.json")

registry = []
for pid, kind in ((100061, "gmina"), (100062, "powiat")):
    d = requests.get(BASE, params={"archive": "false", "parentId": str(pid)},
                     headers=H, timeout=(15, 150)).json()
    lst = d if isinstance(d, list) else d.get("list") or []
    for s in lst:
        if s.get("status") == "PUBLISHED":
            registry.append({"kind": kind, "name": s["name"], "slug": s.get("url")})
    print(kind, len(lst), flush=True)

os.makedirs(os.path.dirname(os.path.abspath(OUT)), exist_ok=True)
with open(os.path.abspath(OUT), "w", encoding="utf-8") as f:
    json.dump(registry, f, ensure_ascii=False, indent=0)
print("TOTAL", len(registry))
