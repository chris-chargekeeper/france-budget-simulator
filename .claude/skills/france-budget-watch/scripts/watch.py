#!/usr/bin/env python3
"""Veille des annonces budgétaires : état des lieux, validation et application de patchs.

Le collecteur, c'est Claude ; ce script est le garde-fou. Il ne cherche rien sur le web :
il dit ce qu'il faut chercher (`etat`), refuse un patch mal formé (`valider`), et
l'applique sans jamais rien supprimer (`appliquer`).

    python3 watch.py etat
    python3 watch.py valider patch.json
    python3 watch.py appliquer patch.json --write
    python3 watch.py controler

Trois principes, dans cet ordre :

1. **Rien sans source.** Une annonce sans URL, mal datée ou datée du futur est refusée.
2. **Le modèle ne bouge pas au fil de l'eau.** Les champs structurels d'une mesure — son
   identifiant, son sens, son instrument, son intitulé, sa montée en charge, son assiette
   mobile — sont hors d'atteinte d'un patch. Seules les bornes de chiffrage publiées et
   la note peuvent bouger, et seulement avec une source.
3. **On n'efface jamais.** Le script ajoute et met à jour ; il ne retire rien. Un chiffre
   remplacé laisse une trace dans le journal.
"""
import argparse
import datetime
import json
import pathlib
import re
import sys

RACINE = pathlib.Path(__file__).resolve().parents[4]
DATA = RACINE / "dataset" / "simulateur"
JOURNAL = RACINE / "dataset" / "veille"

DATE = re.compile(r"^\d{4}-\d{2}(-\d{2})?$")
CONTRADICTION = {"non", "programme", "annonce", "inconnu"}
TYPES = {"economie", "recette", "depense", "contexte"}

# Ce qu'un patch a le droit de toucher. Tout le reste est refusé par construction.
CHAMPS_ANNONCE = {"date", "parti", "qui", "fonction", "media", "quoi", "verbatim",
                  "mesure", "montant", "type", "source", "verifie", "contredit", "ecart"}
CHAMPS_PARTI = {"titre", "texte", "revendique", "detaille", "cote"}
CHAMPS_MESURE = {"lo", "mid", "hi", "note"}
STRUCTURELS = {"id", "g", "inst", "lab", "ramp", "behav", "disp"}


def charger():
    return {n: json.loads((DATA / f"{n}.json").read_text(encoding="utf-8"))
            for n in ("baseline", "measures", "parties", "announcements")}


def ecrire(nom, obj):
    (DATA / f"{nom}.json").write_text(
        json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def aujourdhui():
    return datetime.date.today()


def date_valide(s):
    """→ (ok, raison). Une date de patch est bien formée, réelle, et pas dans le futur."""
    if not DATE.match(str(s or "")):
        return False, "format attendu AAAA-MM-JJ, ou AAAA-MM si le jour n'est pas établi"
    parties = str(s).split("-")
    try:
        jour = datetime.date(int(parties[0]), int(parties[1]),
                             int(parties[2]) if len(parties) == 3 else 1)
    except ValueError:
        return False, "date inexistante au calendrier"
    if jour > aujourdhui():
        return False, f"datée du futur ({s})"
    return True, ""


# ---------------------------------------------------------------- état des lieux

def etat(d):
    """Ce qu'il y a, et surtout ce qui manque — le brief de la recherche à mener."""
    partis = d["parties"]["parties"]
    items = d["announcements"]["items"]
    mesures = {m["id"]: m for m in d["measures"]["measures"]}

    print(f"Base au {d['announcements']['updated']} — {len(items)} annonces, "
          f"{len(partis)} partis, {len(mesures)} mesures.\n")

    print("Dernière annonce relevée, par parti :")
    for p in sorted(partis, key=lambda x: x["nom"]):
        siennes = [a for a in items if a.get("parti") == p["id"]]
        dernier = max((a["date"] for a in siennes), default=None)
        age = ""
        if dernier:
            ok, _ = date_valide(dernier)
            if ok:
                d0 = datetime.date.fromisoformat(dernier if len(dernier) == 10 else dernier + "-01")
                age = f", il y a {(aujourdhui() - d0).days} jours"
        etat_p = {"publie": "chiffré", "partiel": "partiel",
                  "reconstitution": "RECONSTITUTION"}.get(p["statut"], p["statut"])
        print(f"  {p['sigle']:5} {p['candidat']:22} {len(siennes):>2} annonce(s)"
              f"  {dernier or 'aucune':>10}{age}  [{etat_p}]")

    manque = [p for p in partis if p["statut"] == "reconstitution"]
    if manque:
        print(f"\nÀ surveiller en priorité — aucun chiffrage publié, le scénario est un "
              f"assemblage de ce simulateur :\n  "
              + ", ".join(f"{p['sigle']} ({p['candidat']})" for p in manque))

    contredits = [a for a in items if a.get("contredit") != "non"]
    print(f"\n{len(contredits)} annonce(s) en contradiction ou non vérifiables, "
          f"{sum(1 for a in items if not a.get('verifie'))} dont la source n'a pas été lue.")

    sans_source = [m for m in mesures.values() if not m.get("sources")]
    print(f"{len(sans_source)} mesure(s) sur {len(mesures)} sans source de chiffrage attachée.")

    off = d["parties"].get("sourceOfficielle")
    if off:
        print(f"\nSource qui fait foi : {off.get('u') or off.get('url', '—')}\n"
              f"  statut : {off.get('statut', '—')}")
    print("\nÀ chercher : déclarations chiffrées depuis les dates ci-dessus, chiffrages "
          "nouvellement publiés (OFCE, Institut Montaigne, Cour des comptes, IPP),\n"
          "et surtout la publication des programmes officiels, qui écrase toute reprise "
          "de presse.")


# ------------------------------------------------------------------- validation

def valider(d, patch):
    """→ (erreurs, plan). N'écrit rien. Une erreur suffit à tout refuser."""
    erreurs, plan = [], []
    ids_mesures = {m["id"] for m in d["measures"]["measures"]}
    ids_partis = {p["id"] for p in d["parties"]["parties"]}
    existantes = d["announcements"]["items"]

    inconnu = set(patch) - {"_comment", "releve", "annonces", "partis", "mesures"}
    if inconnu:
        erreurs.append(f"clés inconnues dans le patch : {sorted(inconnu)}")

    for i, a in enumerate(patch.get("annonces", [])):
        ou = f"annonces[{i}]"
        trop = set(a) - CHAMPS_ANNONCE
        if trop:
            erreurs.append(f"{ou} : champs non autorisés {sorted(trop)}")
        ok, pourquoi = date_valide(a.get("date"))
        if not ok:
            erreurs.append(f"{ou} : {pourquoi}")
        if not str(a.get("source", "")).startswith("http"):
            erreurs.append(f"{ou} : source manquante ou inutilisable — une annonce sans URL "
                           f"n'entre pas dans la base")
        if a.get("contredit") not in CONTRADICTION:
            erreurs.append(f"{ou} : 'contredit' attendu parmi {sorted(CONTRADICTION)}")
        elif a["contredit"] != "non" and not a.get("ecart"):
            erreurs.append(f"{ou} : une contradiction doit être expliquée dans 'ecart'")
        if not a.get("qui") and not a.get("fonction"):
            erreurs.append(f"{ou} : renseigner 'qui' ou, à défaut, 'fonction'")
        if a.get("type") not in TYPES:
            erreurs.append(f"{ou} : 'type' attendu parmi {sorted(TYPES)}")
        if a.get("parti") and a["parti"] not in ids_partis:
            erreurs.append(f"{ou} : parti inconnu {a['parti']!r}")
        if a.get("mesure") and a["mesure"] not in ids_mesures:
            erreurs.append(f"{ou} : mesure inconnue {a['mesure']!r}")
        if not a.get("quoi"):
            erreurs.append(f"{ou} : 'quoi' vide — dire ce qui a été annoncé")

        double = [b for b in existantes
                  if b.get("source") == a.get("source")
                  and b.get("date") == a.get("date")
                  and b.get("mesure") == a.get("mesure")
                  and b.get("montant") == a.get("montant")]
        if double:
            plan.append(f"  ~ annonce ignorée, déjà présente : {a.get('date')} "
                        f"{a.get('parti') or '—'} {str(a.get('quoi'))[:50]}")
        else:
            plan.append(f"  + annonce {a.get('date')} {a.get('parti') or '—'} "
                        f"{str(a.get('quoi'))[:60]}")

    for pid, maj in (patch.get("partis") or {}).items():
        ou = f"partis.{pid}"
        if pid not in ids_partis:
            erreurs.append(f"{ou} : parti inconnu")
            continue
        trop = set(maj.get("annonce", {})) - CHAMPS_PARTI
        if trop:
            erreurs.append(f"{ou} : champs non autorisés dans 'annonce' {sorted(trop)}")
        src = maj.get("source") or {}
        if not str(src.get("u", "")).startswith("http") or not src.get("t"):
            erreurs.append(f"{ou} : une révision du chiffrage d'un parti exige une source "
                           f"(titre + URL)")
        parti = next(p for p in d["parties"]["parties"] if p["id"] == pid)
        for champ, val in maj.get("annonce", {}).items():
            ancien = parti["annonce"].get(champ)
            if ancien != val:
                plan.append(f"  ± {pid}.annonce.{champ} : {ancien!r} → {val!r}")

    for mid, maj in (patch.get("mesures") or {}).items():
        ou = f"mesures.{mid}"
        if mid not in ids_mesures:
            erreurs.append(f"{ou} : mesure inconnue")
            continue
        touche = set(maj) - {"source"}
        fige = touche & STRUCTURELS
        if fige:
            erreurs.append(f"{ou} : champs structurels intouchables par un patch {sorted(fige)} — "
                           f"ils décrivent le modèle, pas l'actualité")
        trop = touche - CHAMPS_MESURE
        if trop - fige:
            erreurs.append(f"{ou} : champs non autorisés {sorted(trop - fige)}")
        src = maj.get("source") or {}
        if not str(src.get("u", "")).startswith("http") or not src.get("t"):
            erreurs.append(f"{ou} : une révision de chiffrage exige une source (titre + URL)")
        m = next(x for x in d["measures"]["measures"] if x["id"] == mid)
        bornes = {**{k: m[k] for k in ("lo", "mid", "hi")},
                  **{k: v for k, v in maj.items() if k in ("lo", "mid", "hi")}}
        if not bornes["lo"] <= bornes["mid"] <= bornes["hi"]:
            erreurs.append(f"{ou} : bornes incohérentes, lo ≤ mid ≤ hi attendu "
                           f"({bornes['lo']} / {bornes['mid']} / {bornes['hi']})")
        for champ, val in maj.items():
            if champ != "source" and m.get(champ) != val:
                plan.append(f"  ± {mid}.{champ} : {m.get(champ)!r} → {val!r}")

    if not plan:
        plan.append("  (patch sans effet : rien à ajouter ni à modifier)")
    return erreurs, plan


# ------------------------------------------------------------------ application

def appliquer(d, patch, ecrire_vraiment):
    releve = patch.get("releve") or aujourdhui().isoformat()
    trace = {"releve": releve, "applique": aujourdhui().isoformat(),
             "ajouts": [], "revisions": []}

    existantes = d["announcements"]["items"]
    for a in patch.get("annonces", []):
        if any(b.get("source") == a.get("source") and b.get("date") == a.get("date")
               and b.get("mesure") == a.get("mesure") and b.get("montant") == a.get("montant")
               for b in existantes):
            continue
        item = {c: a.get(c) for c in
                ("date", "parti", "qui", "fonction", "media", "quoi", "verbatim",
                 "mesure", "montant", "type", "source", "verifie", "contredit", "ecart")}
        item["verifie"] = bool(a.get("verifie"))
        existantes.append(item)
        trace["ajouts"].append({"date": item["date"], "parti": item["parti"],
                                "quoi": item["quoi"], "source": item["source"]})
    existantes.sort(key=lambda x: (x["date"], x.get("parti") or ""), reverse=True)
    d["announcements"]["updated"] = releve

    for pid, maj in (patch.get("partis") or {}).items():
        parti = next(p for p in d["parties"]["parties"] if p["id"] == pid)
        for champ, val in maj.get("annonce", {}).items():
            if parti["annonce"].get(champ) != val:
                trace["revisions"].append({"quoi": f"parties.{pid}.annonce.{champ}",
                                           "avant": parti["annonce"].get(champ), "apres": val,
                                           "source": maj["source"]["u"]})
                parti["annonce"][champ] = val
        src = maj["source"]
        parti.setdefault("sources", [])
        if not any(s["u"] == src["u"] for s in parti["sources"]):
            parti["sources"].append({"t": src["t"], "u": src["u"]})
    if patch.get("partis"):
        d["parties"]["updated"] = releve

    for mid, maj in (patch.get("mesures") or {}).items():
        m = next(x for x in d["measures"]["measures"] if x["id"] == mid)
        for champ, val in maj.items():
            if champ == "source":
                continue
            if m.get(champ) != val:
                trace["revisions"].append({"quoi": f"measures.{mid}.{champ}",
                                           "avant": m.get(champ), "apres": val,
                                           "source": maj["source"]["u"]})
                m[champ] = val
        src = maj["source"]
        m.setdefault("sources", [])
        if not any(s["u"] == src["u"] for s in m["sources"]):
            m["sources"].append({"t": src["t"], "u": src["u"], "d": releve})

    if not ecrire_vraiment:
        print("\nRien n'a été écrit — relancer avec --write pour appliquer.")
        return trace

    ecrire("announcements", d["announcements"])
    if patch.get("partis"):
        ecrire("parties", d["parties"])
    if patch.get("mesures"):
        ecrire("measures", d["measures"])

    JOURNAL.mkdir(parents=True, exist_ok=True)
    archive = JOURNAL / f"{releve}.json"
    n = 2
    while archive.exists():
        archive = JOURNAL / f"{releve}-{n}.json"
        n += 1
    archive.write_text(json.dumps({"patch": patch, "trace": trace},
                                  ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\n{len(trace['ajouts'])} annonce(s) ajoutée(s), "
          f"{len(trace['revisions'])} révision(s).")
    print(f"Patch et trace archivés dans {archive.relative_to(RACINE)}")
    print("Reconstruire ensuite : python3 build.py")
    return trace


# ------------------------------------------------------------------- contrôle

def controler(d):
    """La page servie dit-elle exactement ce que disent les fichiers de données ?

    Se lance après `build.py`. Ne reconstruit rien : c'est un contrôle, et un contrôle
    qui répare ne contrôle plus. Sort en échec si la page a divergé — la CI publie ce
    fichier, il ne doit pas partir en avance ou en retard sur ses sources.
    """
    index = RACINE / "index.html"
    if not index.is_file():
        sys.exit("index.html absent — lancer python3 build.py")
    html = index.read_text(encoding="utf-8")
    ennuis = []

    restants = [m for m in ("__DATA__", "__UPDATED__", "__AVATARS__",
                            "__FAVICON__", "__COQ__") if m in html]
    if restants:
        ennuis.append(f"marqueurs non substitués dans index.html : {restants}")

    m = re.search(r'<script id="payload" type="application/json">(.*?)</script>', html, re.S)
    if not m:
        sys.exit("payload introuvable dans index.html — la page n'est pas exploitable")
    try:
        embarque = json.loads(m.group(1))
    except json.JSONDecodeError as exc:
        sys.exit(f"le payload d'index.html n'est pas du JSON valide : {exc}")

    for nom in ("announcements", "parties", "measures"):
        if embarque.get(nom) != d[nom]:
            ennuis.append(f"{nom}.json a changé depuis la dernière construction — "
                          f"la page ne dit plus ce que disent les données")

    # La date du bandeau est la plus récente des dates de mise à jour des fichiers, pas
    # celle de parties.json seule : une relève qui n'ajoute que des annonces ne touche
    # pas les partis, et la page annoncerait des données plus anciennes qu'elle n'en
    # porte. Ce contrôle lit la date réellement écrite dans la page.
    attendue = max(bloc["updated"] for bloc in d.values()
                   if isinstance(bloc, dict) and bloc.get("updated"))
    vue = re.search(r"données au (\d{4}-\d{2}-\d{2})", html)
    if not vue:
        ennuis.append("date de fraîcheur introuvable dans le bandeau d'index.html")
    elif vue.group(1) != attendue:
        ennuis.append(f"le bandeau annonce des données au {vue.group(1)}, "
                      f"les fichiers vont jusqu'au {attendue}")

    items = d["announcements"]["items"]
    sans_url = [a for a in items if not str(a.get("source", "")).startswith("http")]
    if sans_url:
        ennuis.append(f"{len(sans_url)} annonce(s) sans URL source dans la base")
    futures = [a for a in items if not date_valide(a.get("date"))[0]]
    if futures:
        ennuis.append(f"{len(futures)} annonce(s) mal datée(s) : "
                      + ", ".join(str(a.get("date")) for a in futures[:3]))

    if ennuis:
        print("Contrôle en échec :")
        for e in ennuis:
            print(f"  ! {e}")
        sys.exit("\nLa page ne peut pas être publiée en l'état.")

    non_lues = sum(1 for a in items if not a.get("verifie"))
    print(f"Contrôle passé — index.html ({len(html):,} octets) dit exactement ce que disent "
          f"les données.".replace(",", " "))
    print(f"  {len(items)} annonces, {len(d['parties']['parties'])} partis, "
          f"{len(d['measures']['measures'])} mesures")
    print(f"  fraîcheur affichée : {vue.group(1)}")
    if non_lues:
        print(f"  ~ {non_lues} annonce(s) dont la source n'a pas été lue "
              f"(champ 'verifie' à false)")



def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("etat", help="ce qu'il y a dans la base, et ce qu'il faut chercher")
    v = sub.add_parser("valider", help="contrôler un patch sans rien écrire")
    v.add_argument("patch")
    a = sub.add_parser("appliquer", help="appliquer un patch")
    a.add_argument("patch")
    a.add_argument("--write", action="store_true", help="écrire pour de bon")
    sub.add_parser("controler", help="vérifier que index.html est en phase avec les données")
    args = ap.parse_args()

    d = charger()
    if args.cmd == "etat":
        etat(d)
        return
    if args.cmd == "controler":
        controler(d)
        return

    patch = json.loads(pathlib.Path(args.patch).read_text(encoding="utf-8"))
    erreurs, plan = valider(d, patch)
    print("Ce que ce patch ferait :")
    print("\n".join(plan))
    if erreurs:
        print(f"\n{len(erreurs)} refus :")
        for e in erreurs:
            print(f"  ! {e}")
        sys.exit("\nPatch refusé. Rien n'a été écrit.")
    print("\nPatch valide.")
    if args.cmd == "appliquer":
        appliquer(d, patch, args.write)


if __name__ == "__main__":
    main()
