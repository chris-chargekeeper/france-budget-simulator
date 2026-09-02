#!/usr/bin/env python3
"""Consolide le brut de sources/budget.gouv.fr en un dataset structuré sous derive/.

Le brut est une arborescence de réponses d'API, une par (axe, loi, année, type de
donnée) et une par bulle de détail. On en tire trois sorties :

    derive/budget-etat.json         tous les millésimes, arborescents
    derive/budget-etat-lfi-2026.json le millésime courant seul, pour un usage direct
    derive/budget-etat.csv          la même chose à plat, une ligne par montant

Les montants sont en milliards d'euros, tels que publiés. Un montant nul et un
montant absent sont deux choses différentes : budget.gouv.fr renvoie `null` pour
une ligne qui existe sans crédit ouvert, et n'émet rien du tout sinon. On garde
la distinction.
"""
import collections
import csv
import datetime
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "sources" / "budget.gouv.fr"
OUT = ROOT / "derive"

# Le niveau 2 d'un axe n'a pas le même nom selon l'axe qu'on descend.
ENFANT = {"ministere": "programmes", "mission": "programmes", "nature": "categories"}
AXE_CLE = {"ministere": "ministeres", "mission": "missions", "nature": "titres"}


def charger(path):
    return json.loads(path.read_text(encoding="utf-8"))


def montants(bulle):
    """{type_budget: montant} — les clés sont des int côté API, des str côté manifeste."""
    out = {}
    for part in bulle.get("value") or []:
        out[str(part.get("groupe"))] = part.get("value")
    return out


def total(m):
    connus = [v for v in m.values() if isinstance(v, (int, float))]
    return round(sum(connus), 9) if connus else None


def noeud(bulle):
    cat = bulle.get("category") or {}
    m = montants(bulle)
    return {"id": cat.get("id"), "nom": bulle.get("name"), "montants": m, "total": total(m)}


def lire_axe(axe, loi, annee, td):
    """Reconstruit l'arbre d'un (axe, loi, année, type de donnée), ou None s'il est vide."""
    base = RAW / "depenses" / axe / loi / str(annee)
    niveau1 = base / f"{td}.json"
    if not niveau1.exists():
        return None
    bulles = charger(niveau1)
    if not bulles:
        return None
    arbre = []
    for bulle in bulles:
        n = noeud(bulle)
        cat = bulle.get("category") or {}
        detail = base / td / f"{cat.get('type')}-{cat.get('id')}.json"
        if bulle.get("on_click") and detail.exists():
            enfants = [noeud(b) for b in charger(detail)]
            # L'API répond par une bulle anonyme quand il n'y a plus de niveau à ouvrir.
            enfants = [e for e in enfants if e["nom"]]
            if enfants:
                n[ENFANT[axe]] = enfants
        arbre.append(n)
    return arbre


def lire_operateurs(loi, annee):
    path = RAW / "operateurs" / loi / f"{annee}.json"
    if not path.exists():
        return None
    out = []
    for bulle in charger(path):
        n = noeud(bulle)
        # Le site accroche ressources et part de financement public au survol.
        extra = {}
        for paire in bulle.get("additional_data") or []:
            if len(paire) == 2:
                extra[paire[0]["text"].strip()] = paire[1]["text"].strip()
        if extra:
            n["complements"] = extra
        out.append(n)
    return out or None


def main():
    manifeste = RAW / "MANIFEST.json"
    if not manifeste.exists():
        sys.exit(f"{manifeste} absent — lancer d'abord scrape_budget_gouv.py")
    meta = charger(manifeste)
    annees = sorted(int(a) for a in meta["referentiels"]["annees"])
    lois = list(meta["referentiels"]["lois_finances"])

    millesimes = []
    for annee in annees:
        for loi in lois:
            for td in ("ae", "cp"):
                bloc = {"annee": annee, "loi": loi, "type_donnee": td}
                vide = True
                for axe in ("ministere", "mission", "nature"):
                    arbre = lire_axe(axe, loi, annee, td)
                    if arbre:
                        bloc[AXE_CLE[axe]] = arbre
                        vide = False
                if td == "ae":  # les opérateurs ne sont pas ventilés en AE/CP
                    ops = lire_operateurs(loi, annee)
                    if ops:
                        bloc["operateurs"] = ops
                        vide = False
                if vide:
                    continue
                for cle in ("ministeres", "missions"):
                    if cle in bloc:
                        bloc[f"total_{cle}"] = round(
                            sum(n["total"] or 0 for n in bloc[cle]), 6)
                millesimes.append(bloc)

    dataset = {
        "_comment": "Budget de l'État tel que publié par budget.gouv.fr. Montants en "
                    "milliards d'euros. Un millésime = une année, un texte financier "
                    "(PLF, LFI, PLRG, PLR) et un type de crédit (AE ou CP). Les mêmes "
                    "crédits sont ventilés trois fois : par ministère, par mission et "
                    "par nature de dépense — ne pas additionner les axes entre eux.",
        "source": meta["source"],
        "licence": meta["licence"],
        "aspire": meta["recupere"],
        "genere": datetime.date.today().isoformat(),
        "unite": "Md€",
        "referentiels": meta["referentiels"],
        "millesimes": millesimes,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "budget-etat.json").write_text(
        json.dumps(dataset, ensure_ascii=False, indent=1), encoding="utf-8")

    courant = [m for m in millesimes if m["annee"] == 2026 and m["loi"] == "lfi"]
    (OUT / "budget-etat-lfi-2026.json").write_text(json.dumps(
        {**{k: v for k, v in dataset.items() if k != "millesimes"}, "millesimes": courant},
        ensure_ascii=False, indent=1), encoding="utf-8")

    # Mise à plat : une ligne par montant élémentaire, prête pour un tableur.
    types = meta["referentiels"]["types_budget"]
    lignes = []
    for m in millesimes:
        for axe, cle in (("ministere", "ministeres"), ("mission", "missions"),
                         ("nature", "titres"), ("operateurs", "operateurs")):
            for parent in m.get(cle, []):
                enfants = parent.get("programmes") or parent.get("categories") or [None]
                for enfant in enfants:
                    cible = enfant or parent
                    for tb, montant in cible["montants"].items():
                        lignes.append({
                            "annee": m["annee"], "loi": m["loi"],
                            "type_donnee": m["type_donnee"], "axe": axe,
                            "niveau1_id": parent["id"], "niveau1": parent["nom"],
                            "niveau2_id": enfant["id"] if enfant else "",
                            "niveau2": enfant["nom"] if enfant else "",
                            "type_budget": types.get(tb, tb),
                            "montant_md_euros": montant,
                        })
    with (OUT / "budget-etat.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(lignes[0]), delimiter=";")
        w.writeheader()
        w.writerows(lignes)

    par_loi = collections.Counter(m["loi"] for m in millesimes)
    print(f"derive/budget-etat.json : {len(millesimes)} millésimes "
          f"({', '.join(f'{k} {v}' for k, v in sorted(par_loi.items()))})")
    print(f"derive/budget-etat.csv  : {len(lignes):,} lignes".replace(",", " "))


if __name__ == "__main__":
    main()
