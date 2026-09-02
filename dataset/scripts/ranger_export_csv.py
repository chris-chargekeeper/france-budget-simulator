#!/usr/bin/env python3
"""Range les CSV exportés à la main depuis budget.gouv.fr et leur rend un nom.

Le bouton « télécharger les données » des dataviz sert toujours le même fichier,
`donnée.csv`, si bien qu'une série de téléchargements arrive sous la forme
`donnée (1).csv` … `donnée (18).csv` : le contenu ne dit pas de quel ministère il
vient. On le retrouve en rapprochant chaque fichier du brut aspiré par
scrape_budget_gouv.py — la somme des programmes d'un fichier doit retomber, à
l'unité de compte près, sur le montant du ministère correspondant.

    python3 ranger_export_csv.py --source ../economie.gouv/2026 [--dry-run]

Un fichier qu'on n'arrive pas à rattacher n'est pas déplacé : il est signalé.
"""
import argparse
import csv
import datetime
import hashlib
import json
import pathlib
import re
import shutil
import sys
import unicodedata

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "sources" / "budget.gouv.fr"
DEST = RAW / "export-csv" / "lfi-2026-ae"
# Le millésime des exports : ce que sert la page /budget-etat/ministere par défaut.
LOI, ANNEE, TD = "lfi", 2026, "ae"
TOLERANCE = 1e-6


def slug(nom, taille=48):
    """Nom de fichier lisible. Les intitulés de ministère sont longs : on coupe sur
    un tiret pour ne pas laisser un mot tranché en deux."""
    sans_accent = unicodedata.normalize("NFKD", nom).encode("ascii", "ignore").decode()
    s = re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", sans_accent.lower())).strip("-")
    if len(s) <= taille:
        return s
    return s[:taille].rsplit("-", 1)[0]


def lire_csv(path):
    """→ (colonnes, {intitulé: {colonne: montant}}). Séparateur ';', décimale '.'."""
    with path.open(encoding="utf-8-sig", newline="") as fh:
        lignes = list(csv.reader(fh, delimiter=";"))
    entete = [c.strip() for c in lignes[0] if c.strip()]
    colonnes = entete[1:]
    rows = {}
    for ligne in lignes[1:]:
        if not ligne or not ligne[0].strip():
            continue
        rows[ligne[0].strip()] = {
            col: float(ligne[i + 1]) for i, col in enumerate(colonnes)
            if i + 1 < len(ligne) and ligne[i + 1].strip()
        }
    return colonnes, rows


def sommes(rows):
    out = {}
    for valeurs in rows.values():
        for col, v in valeurs.items():
            out[col] = out.get(col, 0.0) + v
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", required=True, help="dossier contenant les CSV à ranger")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    source = pathlib.Path(args.source).resolve()

    niveau1 = RAW / "depenses" / "ministere" / LOI / str(ANNEE) / f"{TD}.json"
    if not niveau1.exists():
        sys.exit(f"{niveau1} absent — lancer d'abord scrape_budget_gouv.py")
    types = json.loads((RAW / "MANIFEST.json").read_text(encoding="utf-8"))
    types = types["referentiels"]["types_budget"]

    ministeres = []
    for bulle in json.loads(niveau1.read_text(encoding="utf-8")):
        ref = {}
        for part in bulle["value"]:
            if part.get("value") is not None:
                ref[types[str(part["groupe"])]] = part["value"]
        ministeres.append({"id": bulle["category"]["id"], "nom": bulle["name"], "ref": ref})
    noms_ministeres = {m["nom"] for m in ministeres}

    entrees, orphelins, vus = [], [], {}
    for path in sorted(source.glob("*.csv")):
        colonnes, rows = lire_csv(path)
        empreinte = hashlib.md5(path.read_bytes()).hexdigest()
        if not rows:
            orphelins.append((path.name, "fichier vide"))
            continue

        if set(rows) <= noms_ministeres and len(rows) > 5:
            cible, portee, ministere = "depenses-par-ministere", "tous les ministères", None
        else:
            total = sommes(rows)
            trouve = [m for m in ministeres
                      if set(m["ref"]) == set(total)
                      and all(abs(m["ref"][c] - total[c]) < TOLERANCE for c in total)]
            if len(trouve) != 1:
                orphelins.append((path.name, f"{len(trouve)} ministère(s) candidat(s) "
                                             f"pour {total}"))
                continue
            ministere = trouve[0]
            cible, portee = slug(ministere["nom"]), "programmes d'un ministère"

        # Deux téléchargements du même graphe ne diffèrent que par le tri des lignes.
        cle = (cible, tuple(sorted(rows)))
        if cle in vus:
            vus[cle]["doublons"].append(path.name)
            if not args.dry_run:
                path.unlink()
            continue

        nom_final = f"{cible}.csv"
        entree = {
            "fichier": f"{DEST.relative_to(ROOT)}/{nom_final}",
            "telecharge_sous": path.name,
            "doublons": [],
            "md5": empreinte,
            "portee": portee,
            "colonnes": colonnes,
            "lignes": len(rows),
        }
        if ministere:
            entree["ministere"] = {"id": ministere["id"], "nom": ministere["nom"]}
            entree["controle"] = {"somme_csv": {k: round(v, 9) for k, v in sommes(rows).items()},
                                  "montant_api": ministere["ref"]}
        vus[cle] = entree
        entrees.append(entree)
        if not args.dry_run:
            DEST.mkdir(parents=True, exist_ok=True)
            shutil.move(str(path), DEST / nom_final)

    couverts = {e["ministere"]["nom"] for e in entrees if "ministere" in e}
    manquants = sorted(noms_ministeres - couverts)

    manifeste = {
        "_comment": "Exports CSV téléchargés à la main depuis les dataviz de "
                    "budget.gouv.fr. Le nom d'origine ne portait aucune information : "
                    "chaque fichier a été rattaché à son ministère en vérifiant que la "
                    "somme de ses programmes retombe sur le montant publié par l'API.",
        "source": "https://www.budget.gouv.fr/budget-etat/ministere",
        "millesime": {"annee": ANNEE, "loi": "Loi de finances initiale pour 2026",
                      "type_donnee": "Autorisations d'engagement (AE)"},
        "unite": "Md€",
        "range": datetime.date.today().isoformat(),
        "ministeres_absents": manquants,
        "entrees": sorted(entrees, key=lambda e: e["fichier"]),
    }
    if not args.dry_run:
        DEST.mkdir(parents=True, exist_ok=True)
        (DEST / "MANIFEST.json").write_text(
            json.dumps(manifeste, ensure_ascii=False, indent=1), encoding="utf-8")

    for e in entrees:
        extra = f"  (+{len(e['doublons'])} doublon(s))" if e["doublons"] else ""
        print(f"  {e['telecharge_sous']:32} → {pathlib.Path(e['fichier']).name}{extra}")
    for nom, raison in orphelins:
        print(f"  ! {nom} non rattaché : {raison}")
    if manquants:
        print(f"\n  ministères sans export CSV : {', '.join(manquants)}")
    print(f"\n{len(entrees)} fichiers rangés, "
          f"{sum(len(e['doublons']) for e in entrees)} doublons supprimés, "
          f"{len(orphelins)} en échec")


if __name__ == "__main__":
    main()
