#!/usr/bin/env python3
"""Assemble index.html from template.html and the JSON data files.

The template carries two placeholders: __DATA__ (the JSON payload injected into a
<script type="application/json"> tag) and __UPDATED__ (the freshness date shown in
the masthead). Run this after any change under dataset/simulateur/.
"""
import argparse
import base64
import hashlib
import json
import pathlib
import re
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).parent
DATA = ROOT / "dataset" / "simulateur"
FILES = ["baseline", "measures", "parties", "announcements", "assises"]
CONTRADICTION = {"non", "programme", "annonce", "inconnu"}

DERIVE = ROOT / "dataset" / "derive"
SOURCES = ROOT / "dataset" / "sources"

AVATARS = DATA / "avatars"
MARQUE = DATA / "marque"        # le coq de la marque et l'icône d'onglet qui en dérive
STAMP = ROOT / ".build-stamp"   # empreinte du dernier index.html produit
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
            print(f"  ! {path.name} ignoré : crédit manquant dans dataset/simulateur/portraits/credits.json")
            continue
        if size > PORTRAIT_WARN:
            print(f"  ~ {path.name} pèse {size:,} octets — 256×256 px suffit pour un cercle de 48 px")
        mime = PORTRAIT_TYPES[path.suffix.lower()]
        blob = base64.b64encode(path.read_bytes()).decode("ascii")
        party["photo"] = f"data:{mime};base64,{blob}"
        party["photoCredit"] = credit
        print(f"  + portrait {party['id']} ({size:,} octets, {credit['licence']})")



def build_avatars():
    """Normalise les bustes de dataset/simulateur/avatars/ en symboles SVG.

    Les fichiers viennent de bibliothèques d'icônes : ils arrivent avec un DOCTYPE, une
    feuille de style interne et une couleur en dur. On ne garde que la géométrie et on
    force la couleur à currentColor, pour que le buste prenne la teinte du parti et
    fonctionne en thème clair comme en thème sombre.
    """
    symboles, noms = [], []
    for path in sorted(AVATARS.glob("*.svg")):
        variante = path.stem
        brut = path.read_text(encoding="utf-8")
        vb = re.search(r'viewBox="([^"]+)"', brut)
        if not vb:
            sys.exit(f"{path}: pas de viewBox, impossible de le cadrer")
        corps = re.sub(r"^.*?<svg[^>]*>|</svg>\s*$", "", brut, flags=re.S)
        corps = re.sub(r"<style.*?</style>", "", corps, flags=re.S)
        corps = re.sub(r"<!--.*?-->", "", corps, flags=re.S)
        corps = re.sub(r'\s*class="[^"]*"', "", corps)
        corps = re.sub(r'\s*fill="(?!none)[^"]*"', "", corps)
        corps = " ".join(corps.split())
        if "<" not in corps:
            sys.exit(f"{path}: aucune forme après nettoyage")
        symboles.append(f'<symbol id="av-{variante}" viewBox="{vb.group(1)}">{corps}</symbol>')
        noms.append(variante)

    credits = {}
    fichier = AVATARS / "credits.json"
    if fichier.is_file():
        credits = json.loads(fichier.read_text(encoding="utf-8"))["avatars"]
    for variante in noms:
        c = credits.get(variante) or {}
        if not c.get("licence"):
            print(f"  ~ avatar {variante} : licence non renseignée dans "
                  f"dataset/simulateur/avatars/credits.json")
    print(f"  + {len(noms)} bustes de candidat ({', '.join(noms)})")
    return "\n ".join(symboles), credits


def build_favicon():
    """Dérive l'icône d'onglet du coq de dataset/simulateur/marque/coq.svg.

    Deux formes, embarquées en data URI parce que deploy.sh ne met en ligne qu'un seul
    fichier : index.html. La première est le SVG lui-même, recadré sur le buste — les
    pattes sont retirées, elles ne pèsent plus rien à 16 px et volent la place au reste.
    La seconde est un PNG de repli pour les navigateurs qui ignorent les icônes SVG
    (Safari), régénéré ici quand rsvg-convert est installé, et repris du dépôt sinon.
    """
    brut = (MARQUE / "coq.svg").read_text(encoding="utf-8")
    corps = re.sub(r"^.*?<svg[^>]*>|</svg>\s*$", "", brut, flags=re.S)
    corps = re.sub(r"<!--.*?-->|<title>.*?</title>", "", corps, flags=re.S)
    corps = re.sub(r'<path id="pattes".*?</path>', "", corps, flags=re.S)
    corps = " ".join(corps.split())
    if 'id="pattes"' in corps or "<path" not in corps:
        sys.exit("dataset/simulateur/marque/coq.svg : le recadrage du buste a échoué")
    # tuile arrondie dans le bleu ciel du thème clair : l'icône tient sur un onglet
    # blanc comme sur un onglet sombre. Le buste est centré sur son encombrement réel.
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128">'
           '<rect width="128" height="128" rx="26" fill="#EAF3FA"/>'
           '<g transform="translate(64,64) scale(1.041) translate(-66.875,-53.625)">'
           f'{corps}</g></svg>')

    png = MARQUE / "favicon-32.png"
    outil = shutil.which("rsvg-convert")
    if outil:
        subprocess.run([outil, "-w", "32", "-h", "32", "-o", str(png)],
                       input=svg.encode("utf-8"), check=True)
    elif not png.is_file():
        sys.exit(f"{png.name} absent et rsvg-convert introuvable : installer librsvg "
                 f"(brew install librsvg) ou récupérer le fichier depuis le dépôt")
    else:
        print("  ~ rsvg-convert introuvable : favicon-32.png repris tel quel du dépôt")

    b64 = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    repli = base64.b64encode(png.read_bytes()).decode("ascii")
    print(f"  + icône d'onglet ({len(svg):,} octets de SVG, "
          f"{png.stat().st_size:,} octets de PNG de repli)")
    return (f'<link rel="icon" type="image/svg+xml" href="data:image/svg+xml;base64,{b64}">\n'
            f'<link rel="alternate icon" type="image/png" sizes="32x32" '
            f'href="data:image/png;base64,{repli}">')


def load():
    """Read every data file and fail loudly on a broken reference."""
    payload = {}
    for name in FILES:
        with (DATA / f"{name}.json").open(encoding="utf-8") as fh:
            payload[name] = json.load(fh)

    ids = {m["id"] for m in payload["measures"]["measures"]}
    if len(ids) != len(payload["measures"]["measures"]):
        sys.exit("dataset/simulateur/measures.json: identifiants en double")

    for party in payload["parties"]["parties"]:
        unknown = sorted(set(party["set"]) - ids)
        if unknown:
            sys.exit(f"dataset/simulateur/parties.json: {party['id']} référence des mesures inconnues: {unknown}")

    bustes = {p.stem for p in AVATARS.glob("*.svg")}
    for party in payload["parties"]["parties"]:
        av = party.get("avatar")
        if av is not None and av not in bustes:
            sys.exit(f"dataset/simulateur/parties.json: {party['id']} demande le buste {av!r}; "
                     f"dataset/simulateur/avatars/ contient {sorted(bustes)} "
                     f"(ou null pour le monogramme)")

    party_ids = {p["id"] for p in payload["parties"]["parties"]}
    for item in payload["announcements"]["items"]:
        where = f"dataset/simulateur/announcements.json ({item.get('date')} / {item.get('qui') or item.get('fonction')})"
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

    icones = set(re.findall(r'id="ic-([a-z-]+)"', (ROOT / "template.html").read_text(encoding="utf-8")))
    porteurs = [("depenses", payload["baseline"]["depenses"]),
                ("reperes", payload["baseline"]["reperes"]),
                ("payeurs", list(payload["baseline"]["payeurs"].values()))]
    for bloc, entrees in porteurs:
        for e in entrees:
            nom = e.get("nom", "?")
            if not e.get("icone"):
                sys.exit(f"dataset/simulateur/baseline.json: {bloc} — {nom!r} n'a pas d'icône")
            if e["icone"] not in icones:
                sys.exit(f"dataset/simulateur/baseline.json: {bloc} — {nom!r} pointe sur "
                         f"l'icône inconnue {e['icone']!r}; template.html en déclare "
                         f"{sorted(icones)}")

    dep = sum(x["v"] for x in payload["baseline"]["depenses"])
    rec = sum(x["v"] for x in payload["baseline"]["recettes"])
    apu = payload["baseline"]["apu"]
    for label, got, want in (("dépenses", dep, apu["depenses"]), ("recettes", rec, apu["recettes"])):
        if abs(got - want) > 1:
            sys.exit(f"dataset/simulateur/baseline.json: la ventilation des {label} ({got}) ne somme pas à {want}")
    return payload



def resoudre(ref, src):
    """Retrouve dans les données officielles le montant qu'une ligne d'assise prétend citer.

    Une assise n'est jamais un chiffre saisi à la main : c'est un pointeur vers une ligne
    du budget aspiré. Le pointeur est résolu ici, à chaque construction, et le montant
    du fichier n'est qu'un cache — s'il diverge, la construction échoue plutôt que de
    laisser la page affirmer un chiffre que la source ne dit plus.
    """
    quoi, _, reste = ref.partition(":")
    if src == "lfi2026cp":
        d = json.loads((DERIVE / "budget-etat-lfi-2026.json").read_text(encoding="utf-8"))
        mil = next(m for m in d["millesimes"] if m["type_donnee"] == "cp")
        if quoi == "mission":
            for m in mil["missions"]:
                if m["nom"] == reste:
                    return m["total"]
        elif quoi == "programme":
            for m in mil["missions"]:
                for p in m.get("programmes", []):
                    if p["nom"] == reste:
                        return p["total"]
        elif quoi == "titre":
            nom, _, groupe = reste.rpartition(":")
            for t in mil["titres"]:
                if t["nom"] == nom:
                    return t["montants"].get(groupe)
        return None
    if src == "plrg2024":
        ops = json.loads((SOURCES / "budget.gouv.fr" / "operateurs" / "plrg" / "2024.json")
                         .read_text(encoding="utf-8"))
        if quoi != "operateurs" or reste != "financement-public":
            return None
        total = 0.0
        for o in ops:
            ressources = sum(v["value"] for v in o["value"] if isinstance(v["value"], (int, float)))
            for ligne in o.get("additional_data", []):
                if ligne and "financement public" in ligne[0]["text"]:
                    part = re.search(r"([\d.]+)\s*%", ligne[1]["text"])
                    if part:
                        total += ressources * float(part.group(1)) / 100
        return total
    return None


def verifier_assises(payload):
    """Croise les assises avec le catalogue, les partis et les données officielles."""
    bloc = payload["assises"]
    ids = {m["id"] for m in payload["measures"]["measures"]}
    par_id = {m["id"]: m for m in payload["measures"]["measures"]}
    controles = 0
    for mid, a in bloc["assises"].items():
        ou = f"dataset/simulateur/assises.json: {mid}"
        if mid not in ids:
            sys.exit(f"{ou} ne correspond à aucune mesure du catalogue")
        if par_id[mid]["g"] not in ("dep-", "rec+"):
            sys.exit(f"{ou}: une assise ne se pose que sous une mesure de redressement, "
                     f"pas sous {par_id[mid]['g']!r}")
        if not a.get("note"):
            sys.exit(f"{ou}: une assise sans note ne dit pas ce qu'elle recouvre")
        if a.get("role") not in ("perimetre", "assiette"):
            sys.exit(f"{ou}: 'role' attendu — 'perimetre' si la mesure supprime cette dépense "
                     f"(son total plafonne alors l'économie), 'assiette' si elle en rabote une part")
        if not isinstance(a.get("complet"), bool):
            sys.exit(f"{ou}: 'complet' doit dire si les lignes citées couvrent tout le périmètre")
        lignes = a.get("dediees", []) + a.get("partielles", [])
        if not lignes:
            sys.exit(f"{ou}: aucune ligne budgétaire")
        for l in lignes:
            if l.get("src") not in bloc["sources"]:
                sys.exit(f"{ou}: source inconnue {l.get('src')!r}; "
                         f"connues: {sorted(bloc['sources'])}")
            trouve = resoudre(l.get("ref", ""), l["src"])
            if trouve is None:
                sys.exit(f"{ou}: le renvoi {l.get('ref')!r} ne se retrouve pas dans "
                         f"{bloc['sources'][l['src']]['f']}")
            if abs(trouve - l["v"]) > max(0.01, abs(trouve) * 0.005):
                sys.exit(f"{ou}: {l['nom']} porte {l['v']} Md€, la source en donne "
                         f"{trouve:.3f}. Corriger le fichier, pas la source.")
            controles += 1
    for cle, s in bloc["sources"].items():
        if not s.get("t") or not str(s.get("u", "")).startswith("http"):
            sys.exit(f"dataset/simulateur/assises.json: source {cle} sans titre ou sans URL")
    print(f"  + {controles} lignes d'assise recoupées contre les données officielles")


def rendu(payload, template):
    """La substitution des quatre marqueurs, au même endroit pour les deux sens."""
    avatars, payload["avatars"] = build_avatars()
    favicon = build_favicon()
    blob = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    if "</script" in blob:
        sys.exit("le payload contient une balise fermante </script>")
    return (template.replace("__DATA__", blob)
                    .replace("__UPDATED__", payload["parties"]["updated"])
                    .replace("__AVATARS__", avatars)
                    .replace("__FAVICON__", favicon), blob, avatars, favicon)


def depuis_index(payload):
    """Remonte dans template.html des retouches faites à la main dans index.html.

    index.html n'est que le gabarit avec quatre substitutions : on refait le chemin en
    sens inverse en recalculant les valeurs injectées, en les retrouvant dans le fichier
    édité, et en remettant les marqueurs. Le report est exact ou il échoue — jamais
    approximatif.
    """
    index = ROOT / "index.html"
    if not index.is_file():
        sys.exit("index.html absent : rien à remonter")
    _, blob, avatars, favicon = rendu(payload, "")
    html = index.read_text(encoding="utf-8")
    for quoi, valeur, marqueur in (("le payload", blob, "__DATA__"),
                                   ("les bustes", avatars, "__AVATARS__"),
                                   ("l'icône d'onglet", favicon, "__FAVICON__"),
                                   ("la date de fraîcheur", payload["parties"]["updated"],
                                    "__UPDATED__")):
        n = html.count(valeur)
        if n != 1:
            sys.exit(f"impossible de remonter {quoi} : {n} occurrence(s) dans index.html, "
                     f"attendu exactement 1. Le fichier a divergé trop loin du gabarit.")
        html = html.replace(valeur, marqueur)
    (ROOT / "template.html").write_text(html, encoding="utf-8")
    print("template.html mis à jour depuis index.html")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--depuis-index", action="store_true",
                    help="remonter dans template.html les retouches faites dans index.html")
    ap.add_argument("--force", action="store_true",
                    help="écraser index.html même s'il a été modifié à la main")
    args = ap.parse_args()

    payload = load()
    verifier_assises(payload)
    attach_portraits(payload["parties"]["parties"])
    if args.depuis_index:
        depuis_index(payload)
        payload = load()
        attach_portraits(payload["parties"]["parties"])

    index = ROOT / "index.html"
    # index.html est généré. S'il a bougé sans passer par ici, on refuse de l'écraser :
    # le report se fait avec --depuis-index, l'abandon avec --force.
    if not (args.depuis_index or args.force) and index.is_file() and STAMP.is_file():
        actuel = hashlib.sha256(index.read_bytes()).hexdigest()
        if actuel != STAMP.read_text(encoding="utf-8").strip():
            sys.exit("index.html a été modifié à la main depuis la dernière construction.\n"
                     "  python3 build.py --depuis-index   remonte ces retouches dans template.html\n"
                     "  python3 build.py --force          les écrase")

    template = (ROOT / "template.html").read_text(encoding="utf-8")
    html, _, _, _ = rendu(payload, template)
    index.write_text(html, encoding="utf-8")
    STAMP.write_text(hashlib.sha256(html.encode("utf-8")).hexdigest() + "\n", encoding="utf-8")
    print(f"index.html écrit — {len(html):,} octets, "
          f"{len(payload['measures']['measures'])} mesures, "
          f"{len(payload['parties']['parties'])} partis, "
          f"{len(payload['announcements']['items'])} annonces")


if __name__ == "__main__":
    main()
