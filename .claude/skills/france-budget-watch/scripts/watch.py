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

# Les candidatures bougent : un candidat change, se déclare, se retire. Un patch peut le dire,
# avec une source ; il ne peut pas toucher au scénario chiffré d'un parti existant.
CHAMPS_SONDAGE = {"institut", "commanditaire", "terrain_debut", "terrain_fin", "date", "echantillon",
                  "hypothese", "note", "source", "scores"}
CHAMPS_PARTI_HAUT = {"annonce", "source", "candidat", "statutCandidature", "avatar", "retrait"}
CHAMPS_NOUVEAU = {"id", "nom", "sigle", "candidat", "avatar", "couleur", "statutCandidature",
                  "statut", "annonce", "set", "source"}
STATUTS = {"publie", "partiel", "reconstitution"}
SIMS = {"lo", "mid", "hi"}
SLUG = re.compile(r"^[a-z][a-z0-9]{1,11}$")
COULEUR = re.compile(r"^#[0-9A-Fa-f]{6}$")

# Le contexte macroéconomique : des valeurs datées et sourcées. Le lien entre un indicateur et
# une hypothèse du simulateur (`hypothese`) et ses bornes de vraisemblance se règlent à la main.
CHAMPS_INDICATEUR = {"valeur", "date", "note", "source", "lab", "unite", "groupe", "detail"}
GROUPES = {"marches", "notation", "previsions", "finances"}


def charger():
    noms = ["baseline", "measures", "parties", "announcements"]
    if (DATA / "contexte.json").is_file():
        noms.append("contexte")
    return {n: json.loads((DATA / f"{n}.json").read_text(encoding="utf-8")) for n in noms}


def source_ok(src):
    src = src or {}
    return str(src.get("u", "")).startswith("http") and bool(src.get("t"))


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
    tous = d["parties"]["parties"]
    partis = [p for p in tous if not p.get("retire") and not p.get("horsCourse")]
    items = d["announcements"]["items"]
    mesures = {m["id"]: m for m in d["measures"]["measures"]}

    print("Candidatures suivies (à revérifier à chaque relève : déclarations, retraits, "
          "primaires, ralliements, nouveaux entrants) :")
    for p in tous:
        if p.get("horsCourse"):
            continue
        if p.get("retire"):
            print(f"  ✗ {p['sigle']:5} {p['candidat']:22} retiré le {p['retire']['date']} — "
                  f"{p['retire']['motif']}")
        else:
            print(f"  · {p['sigle']:5} {p['candidat']:22} {p.get('statutCandidature', '')}")
    sds = d["parties"].get("sondages") or []
    print("  Sondages dans la moyenne (le dernier de chaque institut) — chercher plus récent, "
          "et tout institut absent :" if sds else "  Aucun sondage — en chercher.")
    for sd in sorted(sds, key=lambda x: x["terrain_fin"], reverse=True):
        print(f"    - {sd['institut']:18} pour {sd.get('commanditaire') or '—':22} terrain jusqu'au "
              f"{sd['terrain_fin']}, {len(sd['scores'])} candidats testés")
    print()

    ctx = (d.get("contexte") or {}).get("indicateurs", [])
    if ctx:
        print("Contexte macroéconomique (valeur, date, âge) — à rafraîchir dès qu'une valeur "
              "plus récente est publiée :")
        for x in ctx:
            age = "—"
            if x.get("date") and date_valide(x["date"])[0]:
                d0 = datetime.date.fromisoformat(x["date"] if len(x["date"]) == 10
                                                 else x["date"] + "-01")
                age = f"{(aujourdhui() - d0).days} j"
            lien = f"  ⇒ {x['hypothese']}" if x.get("hypothese") else ""
            print(f"  {x['id']:16} {str(x.get('valeur')):>8} {x.get('unite', ''):4} "
                  f"{x.get('date', '—'):>10}  {age:>6}{lien}")
        print()

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

    inconnu = set(patch) - {"_comment", "releve", "annonces", "partis", "mesures",
                            "nouveaux_partis", "contexte", "sondages"}
    ids_partis |= {n.get("id") for n in patch.get("nouveaux_partis", [])}
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

    existants = {p["id"]: p for p in d["parties"]["parties"]}
    for pid, maj in (patch.get("partis") or {}).items():
        ou = f"partis.{pid}"
        if pid not in existants:
            erreurs.append(f"{ou} : parti inconnu — un nouveau candidat passe par "
                           f"'nouveaux_partis'")
            continue
        parti = existants[pid]
        if parti.get("horsCourse"):
            erreurs.append(f"{ou} : scénario hors course, maintenu à la main, pas par la veille")
            continue
        trop = set(maj) - CHAMPS_PARTI_HAUT
        if trop:
            erreurs.append(f"{ou} : champs non autorisés {sorted(trop)} — le scénario chiffré "
                           f"d'un parti ne se modifie pas par la veille")
        trop = set(maj.get("annonce", {})) - CHAMPS_PARTI
        if trop:
            erreurs.append(f"{ou} : champs non autorisés dans 'annonce' {sorted(trop)}")
        if not source_ok(maj.get("source")):
            erreurs.append(f"{ou} : toute révision d'un parti ou d'une candidature exige une "
                           f"source (titre + URL)")
        if "avatar" in maj and maj["avatar"] not in ("h", "f", None):
            erreurs.append(f"{ou} : 'avatar' attendu parmi 'h', 'f' ou null")
        if "retrait" in maj:
            r = maj["retrait"] or {}
            ok, pourquoi = date_valide(r.get("date"))
            if not ok:
                erreurs.append(f"{ou}.retrait : {pourquoi}")
            if not r.get("motif"):
                erreurs.append(f"{ou}.retrait : dire pourquoi dans 'motif' (renonce, battu à "
                               f"une primaire, rallié à…)")
            plan.append(f"  - {pid} retiré de la course le {r.get('date')} : {r.get('motif')} "
                        f"(masqué de la page, conservé dans les données)")
        for champ in ("candidat", "statutCandidature", "avatar"):
            if champ in maj and parti.get(champ) != maj[champ]:
                plan.append(f"  ± {pid}.{champ} : {parti.get(champ)!r} → {maj[champ]!r}")
        for champ, val in maj.get("annonce", {}).items():
            ancien = parti["annonce"].get(champ)
            if ancien != val:
                plan.append(f"  ± {pid}.annonce.{champ} : {ancien!r} → {val!r}")

    ids_mesures_cat = {m["id"] for m in d["measures"]["measures"]}
    for i, n in enumerate(patch.get("nouveaux_partis", [])):
        ou = f"nouveaux_partis[{i}]"
        manque = {"id", "nom", "sigle", "candidat", "couleur", "statutCandidature", "statut",
                  "annonce", "source"} - set(n)
        if manque:
            erreurs.append(f"{ou} : champs obligatoires manquants {sorted(manque)}")
        trop = set(n) - CHAMPS_NOUVEAU
        if trop:
            erreurs.append(f"{ou} : champs non autorisés {sorted(trop)}")
        if not SLUG.match(str(n.get("id", ""))):
            erreurs.append(f"{ou} : 'id' en minuscules sans espace, 2 à 12 caractères")
        elif n["id"] in existants:
            erreurs.append(f"{ou} : l'identifiant {n['id']!r} existe déjà — passer par 'partis'")
        if not COULEUR.match(str(n.get("couleur", ""))):
            erreurs.append(f"{ou} : 'couleur' attendue au format #RRGGBB")
        if n.get("statut") not in STATUTS:
            erreurs.append(f"{ou} : 'statut' attendu parmi {sorted(STATUTS)}")
        if n.get("avatar") not in ("h", "f", None):
            erreurs.append(f"{ou} : 'avatar' attendu parmi 'h', 'f' ou null")
        a = n.get("annonce") or {}
        if not a.get("titre") or not a.get("texte"):
            erreurs.append(f"{ou} : 'annonce' doit porter un 'titre' et un 'texte'")
        if set(a) - CHAMPS_PARTI:
            erreurs.append(f"{ou} : champs non autorisés dans 'annonce' {sorted(set(a) - CHAMPS_PARTI)}")
        for mid, s in (n.get("set") or {}).items():
            if mid not in ids_mesures_cat:
                erreurs.append(f"{ou}.set : mesure inconnue {mid!r}")
            if not isinstance(s, dict) or s.get("sim") not in SIMS:
                erreurs.append(f"{ou}.set.{mid} : 'sim' attendu parmi {sorted(SIMS)}")
        if not source_ok(n.get("source")):
            erreurs.append(f"{ou} : une candidature nouvelle exige une source (titre + URL)")
        plan.append(f"  + candidat {n.get('candidat')} ({n.get('sigle')}), "
                    f"{len(n.get('set') or {})} mesure(s) au scénario")

    ctx = {x["id"]: x for x in (d.get("contexte") or {}).get("indicateurs", [])}
    if patch.get("contexte") and not d.get("contexte"):
        erreurs.append("contexte : dataset/simulateur/contexte.json absent")
    for iid, maj in (patch.get("contexte") or {}).items():
        ou = f"contexte.{iid}"
        trop = set(maj) - CHAMPS_INDICATEUR
        if trop:
            erreurs.append(f"{ou} : champs non autorisés {sorted(trop)} — 'hypothese' et "
                           f"'bornes' se règlent à la main")
        ok, pourquoi = date_valide(maj.get("date"))
        if not ok:
            erreurs.append(f"{ou} : {pourquoi}")
        if not source_ok(maj.get("source")):
            erreurs.append(f"{ou} : un indicateur exige une source (titre + URL)")
        if "valeur" not in maj:
            erreurs.append(f"{ou} : 'valeur' manquante")
        ind = ctx.get(iid)
        if ind is None:
            if not SLUG.match(iid.replace("_", "")):
                erreurs.append(f"{ou} : identifiant en minuscules, sans espace")
            if not maj.get("lab") or "unite" not in maj or maj.get("groupe") not in GROUPES:
                erreurs.append(f"{ou} : un indicateur nouveau exige 'lab', 'unite' et un "
                               f"'groupe' parmi {sorted(GROUPES)}")
            plan.append(f"  + indicateur {iid} = {maj.get('valeur')!r} {maj.get('unite', '')}")
            continue
        v = maj.get("valeur")
        if isinstance(ind.get("valeur"), (int, float)) != isinstance(v, (int, float)):
            erreurs.append(f"{ou} : 'valeur' doit rester du même type ({type(ind['valeur']).__name__})")
        elif isinstance(v, (int, float)) and ind.get("bornes"):
            lo, hi = ind["bornes"]
            if not lo <= v <= hi:
                erreurs.append(f"{ou} : {v} hors des bornes de vraisemblance [{lo}, {hi}] — "
                               f"vérifier l'unité, ou élargir les bornes à la main")
        if ind.get("date") and maj.get("date") and maj["date"] < ind["date"]:
            erreurs.append(f"{ou} : valeur datée du {maj['date']}, plus ancienne que celle en "
                           f"base ({ind['date']})")
        if ind.get("valeur") != v or ind.get("date") != maj.get("date"):
            plan.append(f"  ± {iid} : {ind.get('valeur')!r} ({ind.get('date')}) → "
                        f"{v!r} ({maj.get('date')})"
                        + (f"  ⇒ hypothèse « {ind['hypothese']} » du simulateur"
                           if ind.get("hypothese") else ""))

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
    # Les sondages : le dernier de chaque institut, chacun entier (une seule hypothèse) ;
    # la page en fait la moyenne. Un sondage remplace le précédent du même institut.
    en_place = {x["institut"]: x for x in d["parties"].get("sondages") or []}
    suivis = {p["id"] for p in d["parties"]["parties"]
              if not p.get("horsCourse") and not p.get("retire")}
    suivis |= {n.get("id") for n in patch.get("nouveaux_partis", [])}
    lot = patch.get("sondages") or []
    if not isinstance(lot, list):
        erreurs.append("sondages : une liste est attendue, un élément par sondage")
        lot = []
    for i, sd in enumerate(lot):
        ou = f"sondages[{i}]"
        trop = set(sd) - CHAMPS_SONDAGE
        if trop:
            erreurs.append(f"{ou} : champs non autorisés {sorted(trop)}")
        if not sd.get("institut"):
            erreurs.append(f"{ou} : 'institut' obligatoire (Ifop, Ipsos BVA, Elabe…)")
        for champ in ("date", "terrain_fin"):
            ok, pourquoi = date_valide(sd.get(champ))
            if not ok:
                erreurs.append(f"{ou}.{champ} : {pourquoi}")
        if not source_ok(sd.get("source")):
            erreurs.append(f"{ou} : une source (titre + URL) est obligatoire")
        actuel = en_place.get(sd.get("institut")) or {}
        if actuel.get("terrain_fin") and str(sd.get("terrain_fin", "")) < actuel["terrain_fin"]:
            erreurs.append(f"{ou} : terrain plus ancien que le sondage {sd.get('institut')} en place "
                           f"({actuel['terrain_fin']})")
        scores = sd.get("scores") or {}
        if not scores:
            erreurs.append(f"{ou} : 'scores' vide")
        for pid, v in scores.items():
            if pid not in suivis:
                erreurs.append(f"{ou}.scores : candidat inconnu ou hors course {pid!r}")
            borne = v if isinstance(v, list) else [v]
            if not (1 <= len(borne) <= 2) or not all(isinstance(x, (int, float)) and 0 <= x <= 60
                                                     for x in borne):
                erreurs.append(f"{ou}.scores.{pid} : un nombre entre 0 et 60, ou [bas, haut]")
        verbe = "remplace" if actuel else "ajoute"
        plan.append(f"  ± sondage {sd.get('institut')} pour {sd.get('commanditaire')} ({verbe}, terrain "
                    f"jusqu'au {sd.get('terrain_fin')}) : "
                    + ", ".join(f"{k} {v}" for k, v in sorted(scores.items(),
                                key=lambda kv: -(kv[1][0] if isinstance(kv[1], list) else kv[1]))))

    return erreurs, plan


# ------------------------------------------------------------------ application

def appliquer(d, patch, ecrire_vraiment):
    releve = patch.get("releve") or aujourdhui().isoformat()
    trace = {"releve": releve, "applique": aujourdhui().isoformat(),
             "ajouts": [], "revisions": []}

    # Les nouveaux candidats d'abord : les annonces du même patch peuvent s'y rattacher.
    for n in patch.get("nouveaux_partis", []):
        entree = {k: n.get(k) for k in ("id", "nom", "sigle", "candidat", "avatar", "couleur",
                                         "statutCandidature", "statut")}
        entree["annonce"] = dict(n["annonce"])
        entree["set"] = n.get("set") or {}
        entree["sources"] = [{"t": n["source"]["t"], "u": n["source"]["u"]}]
        entree["depuis"] = releve
        d["parties"]["parties"].append(entree)
        trace["ajouts"].append({"candidat": entree["candidat"], "parti": entree["id"],
                                "source": n["source"]["u"]})

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
        for champ in ("candidat", "statutCandidature", "avatar"):
            if champ in maj and parti.get(champ) != maj[champ]:
                trace["revisions"].append({"quoi": f"parties.{pid}.{champ}",
                                           "avant": parti.get(champ), "apres": maj[champ],
                                           "source": maj["source"]["u"]})
                parti[champ] = maj[champ]
        if "retrait" in maj:
            parti["retire"] = {"date": maj["retrait"]["date"], "motif": maj["retrait"]["motif"],
                               "u": maj["source"]["u"]}
            trace["revisions"].append({"quoi": f"parties.{pid}.retire", "avant": None,
                                       "apres": parti["retire"], "source": maj["source"]["u"]})
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
    if patch.get("partis") or patch.get("nouveaux_partis") or patch.get("sondages"):
        d["parties"]["updated"] = releve

    if patch.get("contexte"):
        inds = d["contexte"]["indicateurs"]
        for iid, maj in patch["contexte"].items():
            ind = next((x for x in inds if x["id"] == iid), None)
            src = {"t": maj["source"]["t"], "u": maj["source"]["u"]}
            if ind is None:
                ind = {"id": iid, "lab": maj["lab"], "unite": maj["unite"],
                       "groupe": maj["groupe"], "historique": []}
                inds.append(ind)
            elif ind.get("valeur") != maj["valeur"] or ind.get("date") != maj["date"]:
                # l'ancienne valeur part dans l'historique : rien ne s'efface
                ind.setdefault("historique", []).insert(
                    0, {"valeur": ind.get("valeur"), "date": ind.get("date"),
                        "u": (ind.get("source") or {}).get("u")})
                trace["revisions"].append({"quoi": f"contexte.{iid}", "avant": ind.get("valeur"),
                                           "apres": maj["valeur"], "source": src["u"]})
            for champ in ("valeur", "date", "note", "lab", "unite", "detail"):
                if champ in maj:
                    ind[champ] = maj[champ]
            ind["source"] = src
        d["contexte"]["updated"] = releve

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

    for sd in patch.get("sondages") or []:
        liste = d["parties"].setdefault("sondages", [])
        ancien = next((x for x in liste if x["institut"] == sd["institut"]), None)
        if ancien:
            liste.remove(ancien)
            d["parties"].setdefault("sondages_historique", []).insert(
                0, {k: ancien.get(k) for k in ("institut", "commanditaire", "terrain_fin", "scores")}
                   | {"u": (ancien.get("source") or {}).get("u")})
        liste.append({k: sd[k] for k in CHAMPS_SONDAGE if k in sd})
        liste.sort(key=lambda x: x["terrain_fin"], reverse=True)
        trace["revisions"].append({"quoi": f"parties.sondages.{sd['institut']}",
                                   "avant": (ancien or {}).get("scores"), "apres": sd["scores"],
                                   "source": sd["source"]["u"]})

    if not ecrire_vraiment:
        print("\nRien n'a été écrit — relancer avec --write pour appliquer.")
        return trace

    ecrire("announcements", d["announcements"])
    if patch.get("partis") or patch.get("nouveaux_partis") or patch.get("sondages"):
        ecrire("parties", d["parties"])
    if patch.get("contexte"):
        ecrire("contexte", d["contexte"])
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

    for nom in ("announcements", "parties", "measures", "contexte"):
        if nom in d and embarque.get(nom) != d[nom]:
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
