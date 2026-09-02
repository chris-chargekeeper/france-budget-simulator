#!/usr/bin/env python3
"""Assemble index.html from template.html and the JSON data files.

The template carries two placeholders: __DATA__ (the JSON payload injected into a
<script type="application/json"> tag) and __UPDATED__ (the freshness date shown in
the masthead). Run this after any change under data/.
"""
import base64
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).parent
DATA = ROOT / "data"
FILES = ["baseline", "measures", "parties", "announcements"]
CONTRADICTION = {"non", "programme", "annonce", "inconnu"}

PORTRAITS = DATA / "portraits"
PORTRAIT_TYPES = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
PORTRAIT_WARN = 120_000
PORTRAIT_MAX = 400_000


def attach_portraits(parties):
    """Inline a portrait per party as a data URI, when one has been dropped in.

    Absent, oversized or uncredited portraits are skipped with a message: the cards
    fall back to a monogram, so the page never depends on these files. Attribution is
    mandatory because the usable licences (CC BY, CC BY-SA) all require it.
    """
    if not PORTRAITS.is_dir():
        return
    credits = json.loads((PORTRAITS / "credits.json").read_text(encoding="utf-8"))["credits"]
    for party in parties:
        found = [PORTRAITS / f"{party['id']}{ext}" for ext in PORTRAIT_TYPES]
        found = [f for f in found if f.is_file()]
        if not found:
            continue
        path = found[0]
        size = path.stat().st_size
        if size > PORTRAIT_MAX:
            print(f"  ! {path.name} ignoré : {size:,} octets, au-delà de la limite de {PORTRAIT_MAX:,}")
            continue
        credit = credits.get(party["id"])
        if not credit or not credit.get("auteur") or not credit.get("licence"):
            print(f"  ! {path.name} ignoré : crédit manquant dans data/portraits/credits.json")
            continue
        if size > PORTRAIT_WARN:
            print(f"  ~ {path.name} pèse {size:,} octets — 256×256 px suffit pour un cercle de 48 px")
        mime = PORTRAIT_TYPES[path.suffix.lower()]
        blob = base64.b64encode(path.read_bytes()).decode("ascii")
        party["photo"] = f"data:{mime};base64,{blob}"
        party["photoCredit"] = credit
        print(f"  + portrait {party['id']} ({size:,} octets, {credit['licence']})")


def load():
    """Read every data file and fail loudly on a broken reference."""
    payload = {}
    for name in FILES:
        with (DATA / f"{name}.json").open(encoding="utf-8") as fh:
            payload[name] = json.load(fh)

    ids = {m["id"] for m in payload["measures"]["measures"]}
    if len(ids) != len(payload["measures"]["measures"]):
        sys.exit("data/measures.json: identifiants en double")

    for party in payload["parties"]["parties"]:
        unknown = sorted(set(party["set"]) - ids)
        if unknown:
            sys.exit(f"data/parties.json: {party['id']} référence des mesures inconnues: {unknown}")

    party_ids = {p["id"] for p in payload["parties"]["parties"]}
    for item in payload["announcements"]["items"]:
        where = f"data/announcements.json ({item.get('date')} / {item.get('qui') or item.get('fonction')})"
        if item.get("mesure") and item["mesure"] not in ids:
            sys.exit(f"{where}: mesure inconnue {item['mesure']!r}")
        if item.get("parti") and item["parti"] not in party_ids:
            sys.exit(f"{where}: parti inconnu {item['parti']!r}")
        if not re.match(r"^\d{4}-\d{2}(-\d{2})?$", str(item.get("date", ""))):
            sys.exit(f"{where}: date attendue au format AAAA-MM-JJ ou AAAA-MM")
        if item.get("contredit") not in CONTRADICTION:
            sys.exit(f"{where}: champ 'contredit' attendu parmi {sorted(CONTRADICTION)}")
        if item.get("contredit") != "non" and not item.get("ecart"):
            sys.exit(f"{where}: une contradiction doit être expliquée dans 'ecart'")
        if not str(item.get("source", "")).startswith("http"):
            sys.exit(f"{where}: source manquante ou inutilisable")
        if not item.get("qui") and not item.get("fonction"):
            sys.exit(f"{where}: renseigner 'qui' ou, à défaut, 'fonction'")

    dep = sum(x["v"] for x in payload["baseline"]["depenses"])
    rec = sum(x["v"] for x in payload["baseline"]["recettes"])
    apu = payload["baseline"]["apu"]
    for label, got, want in (("dépenses", dep, apu["depenses"]), ("recettes", rec, apu["recettes"])):
        if abs(got - want) > 1:
            sys.exit(f"data/baseline.json: la ventilation des {label} ({got}) ne somme pas à {want}")
    return payload


def main():
    payload = load()
    attach_portraits(payload["parties"]["parties"])
    template = (ROOT / "template.html").read_text(encoding="utf-8")
    blob = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    if "</script" in blob:
        sys.exit("le payload contient une balise fermante </script>")
    html = template.replace("__DATA__", blob).replace("__UPDATED__", payload["parties"]["updated"])
    (ROOT / "index.html").write_text(html, encoding="utf-8")
    print(f"index.html écrit — {len(html):,} octets, "
          f"{len(payload['measures']['measures'])} mesures, "
          f"{len(payload['parties']['parties'])} partis, "
          f"{len(payload['announcements']['items'])} annonces")


if __name__ == "__main__":
    main()
