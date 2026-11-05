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
import struct
import subprocess
import sys

ROOT = pathlib.Path(__file__).parent
DATA = ROOT / "dataset" / "simulateur"
FILES = ["baseline", "measures", "parties", "announcements", "assises", "contexte", "incidence", "histoire", "pouvoir"]
CONTRADICTION = {"non", "programme", "annonce", "inconnu"}

DERIVE = ROOT / "dataset" / "derive"
SOURCES = ROOT / "dataset" / "sources"

AVATARS = DATA / "avatars"
MARQUE = DATA / "marque"        # le coq de la marque et l'icône d'onglet qui en dérive
CADRE = "15 5.5 104 117"        # encombrement du coq entier dans le viewBox 128 de coq.svg
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


def build_marque():
    """Le coq : un symbole inline pour le bandeau, une icône pour l'onglet.

    Les deux sortent du même fichier, dataset/simulateur/marque/coq.svg, pour qu'ils ne
    puissent pas diverger. Le bandeau prend l'oiseau entier ; l'icône prend le buste
    seul — à 16 px les pattes ne pèsent rien et volent la place au reste — posé sur une
    tuile arrondie qui tient sur un onglet blanc comme sur un onglet sombre.

    Le coq du bandeau est embarqué dans la page ; les icônes, elles, sont des fichiers
    de web/, que la CI envoie à la racine du site.
    """
    brut = (MARQUE / "coq.svg").read_text(encoding="utf-8")
    corps = re.sub(r"^.*?<svg[^>]*>|</svg>\s*$", "", brut, flags=re.S)
    corps = re.sub(r"<!--.*?-->|<title>.*?</title>", "", corps, flags=re.S)
    corps = " ".join(corps.split())
    buste = re.sub(r'<path id="pattes".*?</path>', "", corps, flags=re.S)
    if buste == corps or "<path" not in buste:
        sys.exit("dataset/simulateur/marque/coq.svg : pas de <path id=\"pattes\"> à retirer "
                 "pour le buste de l'icône d'onglet")
    # Dans le bandeau seul, les trois arrêts du dégradé passent par des variables CSS :
    # sur fond sombre, le bleu nuit de la queue se confond avec la surface. Les variables
    # personnalisées traversent l'arbre d'ombre de <use>, contrairement à stop-color. Le
    # fichier, lui, garde ses couleurs en dur — c'est lui que rsvg-convert rastérise.
    plumes = corps
    for var, valeur in (("coq-corps", "#1C5CAB"), ("coq-milieu", "#164C90"),
                        ("coq-queue", "#12224E")):
        avant = f'stop-color="{valeur}"'
        if avant not in plumes:
            sys.exit(f"coq.svg : arrêt de dégradé {valeur} introuvable, le bandeau ne "
                     f"pourra pas suivre le thème")
        plumes = plumes.replace(avant, f'stop-color="var(--{var},{valeur})"')
    # Le coq du bandeau est injecté comme <svg> complet, pas comme <symbol> repris par
    # <use> : sur un symbole, <use> ouvre un viewport à x=0 y=0 du système courant, que
    # le viewBox serré décale — le bec et la crête se faisaient rogner. Un <svg> inline
    # n'a pas cette indirection, et les variables CSS l'atteignent sans arbre d'ombre.
    # Le viewBox est serré sur l'encombrement du tracé, mesuré une fois : le coq s'aligne
    # ainsi sur la marge du titre, sans blanc parasite.
    bandeau = (f'<svg class="coq" viewBox="{CADRE}" role="img" aria-label="Coq tricolore">'
               f'{plumes}</svg>')

    # le buste est centré sur son encombrement réel, mesuré une fois sur le tracé
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128">'
           '<rect width="128" height="128" rx="26" fill="#EAF3FA"/>'
           '<g transform="translate(64,64) scale(1.041) translate(-66.875,-53.625)">'
           f'{buste}</g></svg>')

    # Les icônes sont servies en fichiers, à la racine du site (web/, envoyé par la CI) :
    # Google n'affiche dans ses résultats qu'une icône qu'il peut télécharger à une
    # adresse — jamais un data URI —, carrée et d'un côté multiple de 48 px. Les PNG sont
    # régénérés quand rsvg-convert est installé, repris du dépôt sinon (cas de la CI).
    WEB.mkdir(exist_ok=True)
    (WEB / "favicon.svg").write_text(svg + "\n", encoding="utf-8")
    outil = shutil.which("rsvg-convert")
    for nom, cote in (("favicon-48.png", 48), ("favicon-192.png", 192),
                      ("apple-touch-icon.png", 180)):
        png = WEB / nom
        if outil:
            subprocess.run([outil, "-w", str(cote), "-h", str(cote), "-o", str(png)],
                           input=svg.encode("utf-8"), check=True)
        elif not png.is_file():
            sys.exit(f"web/{nom} absent et rsvg-convert introuvable : installer librsvg "
                     f"(brew install librsvg) ou récupérer le fichier depuis le dépôt")
    # favicon.ico, que certains robots demandent d'office : un ICO qui embarque le PNG 48 px
    png48 = (WEB / "favicon-48.png").read_bytes()
    ico = (struct.pack("<HHH", 0, 1, 1)
           + struct.pack("<BBBBHHII", 48, 48, 0, 0, 1, 32, len(png48), 22) + png48)
    (WEB / "favicon.ico").write_bytes(ico)
    print(f"  + coq du bandeau et icônes du site ({len(svg):,} octets de SVG, "
          f"PNG 48, 180 et 192 px, favicon.ico)")
    liens = ('<link rel="icon" href="/favicon.ico" sizes="48x48">\n'
             '<link rel="icon" type="image/svg+xml" href="/favicon.svg">\n'
             '<link rel="icon" type="image/png" sizes="192x192" href="/favicon-192.png">\n'
             '<link rel="apple-touch-icon" href="/apple-touch-icon.png">')
    return liens, bandeau


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

    verifier_incidence(payload["incidence"], ids)
    icones_ = set(re.findall(r'id="ic-([a-z-]+)"', (ROOT / "template.html").read_text(encoding="utf-8")))
    for g in payload["incidence"]["groupes"]:
        if g.get("icone") not in icones_:
            sys.exit(f"dataset/simulateur/incidence.json: le groupe {g['id']!r} pointe sur l'icône "
                     f"inconnue {g.get('icone')!r}; template.html en déclare {sorted(icones_)}")

    verifier_histoire(payload["histoire"])
    verifier_pouvoir(payload["pouvoir"], payload, ids, icones_)
    verifier_macro(ids)
    payload["macro"] = macro_embarque()

    dep = sum(x["v"] for x in payload["baseline"]["depenses"])
    rec = sum(x["v"] for x in payload["baseline"]["recettes"])
    apu = payload["baseline"]["apu"]
    for label, got, want in (("dépenses", dep, apu["depenses"]), ("recettes", rec, apu["recettes"])):
        if abs(got - want) > 1:
            sys.exit(f"dataset/simulateur/baseline.json: la ventilation des {label} ({got}) ne somme pas à {want}")
    return payload



def verifier_histoire(h):
    """L'histoire de la dette : des séries complètes, des périodes cohérentes, une source par bloc.

    Pas de champ `updated` : ce fichier se revoit une fois par an et ne doit pas faire avancer
    la date « données au … » du bandeau, qui dit la fraîcheur de la veille.
    """
    ou = "dataset/simulateur/histoire.json"
    if "updated" in h:
        sys.exit(f"{ou}: pas de champ 'updated' (il ferait avancer la date du bandeau) ; utiliser 'revu'")
    n = h["fin"] - h["debut"] + 1
    for p in h["pays"]:
        if len(p["vals"]) != n:
            sys.exit(f"{ou}: {p['nom']} a {len(p['vals'])} valeurs pour {n} années")
        if p["vals"][0] is None or p["vals"][-1] is None:
            sys.exit(f"{ou}: {p['nom']} doit avoir une valeur la première et la dernière année")
        if any(v is not None and not 0 < v < 300 for v in p["vals"]):
            sys.exit(f"{ou}: {p['nom']} a une valeur hors de 0-300 % du PIB")
    if h["pays"][0]["id"] != "fr":
        sys.exit(f"{ou}: la France doit être le premier pays")
    fr = h["pays"][0]["vals"]
    for bloc in ("crises", "presidents", "gouvernements"):
        for e in h[bloc]:
            if not (h["debut"] - 1 <= e["de"] <= e["a"] <= h["fin"] + 1):
                sys.exit(f"{ou}: {bloc} — période {e['de']}-{e['a']} hors de la série")
    for c in h["crises"]:
        if "palier" in c:
            a, b = c["palier"]
            if fr[a - h["debut"]] is None or fr[b - h["debut"]] is None:
                sys.exit(f"{ou}: palier {a}-{b} de {c['lab']!r} sans valeur pour la France")
    for p in h["presidents"]:
        if fr[max(p["de"], h["debut"]) - h["debut"]] is None or fr[p["a"] - h["debut"]] is None:
            sys.exit(f"{ou}: mandat {p['court']!r} sans valeur de dette à ses bornes")
    for e in h["presidents"] + h["gouvernements"]:
        if e.get("camp") not in ("gauche", "droite", "centre"):
            sys.exit(f"{ou}: camp attendu parmi gauche, droite, centre — {e!r}")
    for q in h["questions"]:
        if not q.get("r") or not q.get("sources") or not all(s["u"].startswith("http") for s in q["sources"]):
            sys.exit(f"{ou}: la question {q.get('q')!r} doit avoir une réponse et une source en http")
    for s in h["sources"] + [h["dernierExcedent"]["source"]]:
        if not s["u"].startswith("http"):
            sys.exit(f"{ou}: source inutilisable {s!r}")


def verifier_pouvoir(pa, payload, ids, icones):
    """Votre pouvoir d'achat : chaque chiffre qui n'est pas calculé par le site porte sa source.

    Pas de champ `updated`, comme pour l'histoire : la date du bandeau dit la fraîcheur de la veille.
    """
    ou = "dataset/simulateur/pouvoir.json"
    if "updated" in pa:
        sys.exit(f"{ou}: pas de champ 'updated' (il ferait avancer la date du bandeau) ; utiliser 'revu'")
    groupes = {g["id"]: g for g in payload["incidence"]["groupes"]}
    sources = []
    for f in pa["foyers"]:
        g = groupes.get(f.get("groupe"))
        if not g:
            sys.exit(f"{ou}: foyer {f.get('id')!r} rattaché au groupe inconnu {f.get('groupe')!r}")
        if f.get("icone") not in icones:
            sys.exit(f"{ou}: foyer {f['id']!r} — icône inconnue {f.get('icone')!r}")
        if "revenu" in f:
            if not f["revenu"] > 0 or not f.get("quoi") or "source" not in f:
                sys.exit(f"{ou}: foyer {f['id']!r} — revenu propre sans libellé ou sans source")
            sources.append(f["source"])
        elif not (g.get("revenu") or {}).get("v"):
            sys.exit(f"{ou}: foyer {f['id']!r} sans revenu de référence, ni ici ni dans incidence.json")
    for m in pa["prix"]["mesures"]:
        if m not in ids:
            sys.exit(f"{ou}: mesure de prix inconnue {m!r}")
    partis = {p["id"] for p in payload["parties"]["parties"]}
    for pid, sal in pa["salaires"].items():
        if pid not in partis:
            sys.exit(f"{ou}: salaires — parti inconnu {pid!r}")
        if not sal.get("smicNet", 0) > 0 or not re.match(r"^\d{4}-\d{2}-\d{2}$", sal.get("date", "")):
            sys.exit(f"{ou}: salaires — {pid} sans montant ou sans date")
        sources.append(sal["source"])
    if pa["inflation"]["indicateur"] not in {i["id"] for i in payload["contexte"]["indicateurs"]}:
        sys.exit(f"{ou}: l'indicateur d'inflation {pa['inflation']['indicateur']!r} n'existe pas dans contexte.json")
    sources += [pa["inflation"]["smic"]["source"], pa["inflation"]["retraites"]["source"],
                pa["petrole"]["source"], pa["credit"]["source"], pa["serie"]["source"]]
    lo, hi = pa["petrole"]["total"]
    if not 0 < pa["petrole"]["direct"] <= lo <= hi:
        sys.exit(f"{ou}: pétrole — effet direct ≤ effet total bas ≤ effet total haut attendu")
    se = pa["serie"]
    n = se["fin"] - se["debut"] + 1
    for k in ("uc", "prix"):
        if len(se[k]) != n or any(not isinstance(v, (int, float)) or abs(v) > 30 for v in se[k]):
            sys.exit(f"{ou}: série {k!r} : {n} valeurs numériques attendues, entre -30 et 30 %")
    for s_ in sources:
        if not s_.get("t") or not str(s_.get("u", "")).startswith("http"):
            sys.exit(f"{ou}: source inutilisable {s_!r}")


def verifier_macro(ids):
    """Coefficients de la projection : chacun sourcé, borné dans le bon ordre, sans doublon.

    Le fichier n'est pas embarqué dans la page tant que le moteur ne s'en sert pas,
    mais il est contrôlé à chaque construction.
    """
    ou = "dataset/simulateur/macro.json"
    with (DATA / "macro.json").open(encoding="utf-8") as fh:
        mc = json.load(fh)
    if "updated" in mc:
        sys.exit(f"{ou}: pas de champ 'updated' (il ferait avancer la date du bandeau) ; utiliser 'revu'")
    def url_ok(u):
        return isinstance(u, str) and re.match(r"^https?://\S+$", u) is not None
    vus = set()
    for c in mc["coefficients"]:
        cid = c.get("id")
        if not cid or cid in vus:
            sys.exit(f"{ou}: identifiant absent ou en double {cid!r}")
        vus.add(cid)
        if not c.get("quoi") or not c.get("unite") or not c.get("horizon"):
            sys.exit(f"{ou}: {cid} — 'quoi', 'unite' et 'horizon' sont obligatoires")
        if c.get("controle") not in {"confirme", "corrige", "non_revu"}:
            sys.exit(f"{ou}: {cid} — 'controle' attendu parmi confirme, corrige, non_revu")
        v, lo, hi = c.get("valeur"), c.get("lo"), c.get("hi")
        nums = [x for x in (lo, hi) if isinstance(x, (int, float))]
        if len(nums) == 2 and lo > hi:
            sys.exit(f"{ou}: {cid} — lo ({lo}) supérieur à hi ({hi})")
        if isinstance(v, (int, float)) and len(nums) == 2 and not lo <= v <= hi:
            sys.exit(f"{ou}: {cid} — valeur {v} hors de la fourchette [{lo} ; {hi}]")
        if not c.get("sources"):
            sys.exit(f"{ou}: {cid} — aucune source")
        for s_ in c["sources"]:
            if not s_.get("t") or not s_.get("org") or not url_ok(s_.get("u")):
                sys.exit(f"{ou}: {cid} — source sans titre, organisme ou URL valide : {s_.get('u')!r}")
    for x in mc["calage"] + mc["scenarios"]:
        if not url_ok(x.get("u")) or not x.get("org") or not x.get("date"):
            sys.exit(f"{ou}: calage ou scénario sans organisme, date ou URL valide : {x!r}"[:300])

    # Types d'instrument : chaque coefficient cité existe ; un type générique dit quelle borne il prend.
    for tid, t in mc["types"].items():
        if t.get("sens") not in {"depense+", "hausse", "baisse", "ampleur"}:
            sys.exit(f"{ou}: type {tid!r} — 'sens' attendu parmi depense+, hausse, baisse, ampleur")
        if t.get("confiance") not in {"directe", "substitut", "generique"}:
            sys.exit(f"{ou}: type {tid!r} — 'confiance' attendue parmi directe, substitut, generique")
        if (t["sens"] == "ampleur") != (t.get("borne") in {"lo", "hi"}):
            sys.exit(f"{ou}: type {tid!r} — un type 'ampleur' prend la borne lo (recettes) ou hi (dépenses)")
        if t["confiance"] != "directe" and not t.get("note"):
            sys.exit(f"{ou}: type {tid!r} — un substitut ou un générique s'explique dans 'note'")
        if not t.get("demande"):
            sys.exit(f"{ou}: type {tid!r} sans coefficient de demande")
        for cid in t["demande"].values():
            if cid not in vus:
                sys.exit(f"{ou}: type {tid!r} — coefficient inconnu {cid!r}")
    # Classement : toutes les mesures du catalogue, et rien d'autre.
    cl = mc["classement"]
    if set(cl) != ids:
        sys.exit(f"{ou}: classement — manquantes {sorted(ids - set(cl))}, inconnues {sorted(set(cl) - ids)}")
    for mid, c in cl.items():
        if c.get("type") not in mc["types"]:
            sys.exit(f"{ou}: {mid} — type inconnu {c.get('type')!r}")
        for ca in c.get("canaux", []):
            if ca.get("coef") not in vus or not ca.get("quoi"):
                sys.exit(f"{ou}: {mid} — canal sans libellé ou coefficient inconnu {ca.get('coef')!r}")


def macro_embarque():
    """Ce que la page embarque de macro.json : les coefficients que le moteur ou la carte citent (valeur,
    bornes, sources), les types, le classement, les règles du moteur, la population, le calage et les
    scénarios. Les citations et notes longues restent dans le fichier, qui fait foi."""
    with (DATA / "macro.json").open(encoding="utf-8") as fh:
        mc = json.load(fh)
    cites = {mot["coef"] for mot in mc["moteur"].values() if isinstance(mot, dict) and mot.get("coef")}
    for t in mc["types"].values():
        cites |= set(t.get("profilDe") or []) | set(t["demande"].values())
        cites |= set((t.get("longTerme") or {}).get("coef") or [])
    for c in mc["classement"].values():
        for ca in c["canaux"]:
            cites.add(ca["coef"])
            if ca.get("recoupementDe"):
                cites.add(ca["recoupementDe"])
    garder = ("id", "quoi", "valeur", "lo", "hi", "unite", "horizon", "controle")
    return {
        "revu": mc["revu"],
        "coefficients": [{**{k: c[k] for k in garder if k in c},
                          "sources": [{k: s[k] for k in ("t", "org", "date", "u") if k in s}
                                      for s in c["sources"]]}
                         for c in mc["coefficients"] if c["id"] in cites],
        "types": mc["types"], "classement": mc["classement"], "moteur": mc["moteur"],
        "donnees": [x for x in mc["donnees"] if x["id"] == mc["moteur"]["population"]["donnee"]],
        "calage": mc["calage"], "scenarios": mc["scenarios"],
    }


def verifier_incidence(inc, ids):
    """Qui paie, qui reçoit : chaque mesure du catalogue a une clé complète et lisible."""
    ou = "dataset/simulateur/incidence.json"
    groupes = {g["id"] for g in inc["groupes"]}
    for g in inc["groupes"]:
        if not g.get("effectif") or g["effectif"] <= 0 or not g.get("lab") or not g.get("par"):
            sys.exit(f"{ou}: groupe {g.get('id')!r} sans libellé, unité ou effectif")
        rv = g.get("revenu")
        if rv is not None and (not isinstance(rv.get("v"), (int, float)) or rv["v"] <= 0 or not rv.get("quoi")
                               or not str((rv.get("source") or {}).get("u", "")).startswith("http")):
            sys.exit(f"{ou}: groupe {g['id']!r} — revenu de référence sans montant, sans libellé ou sans source")
    vus = set()
    for m in inc["mesures"]:
        mid = m["id"]
        if mid not in ids:
            sys.exit(f"{ou}: mesure inconnue {mid!r}")
        if mid in vus:
            sys.exit(f"{ou}: mesure {mid!r} en double")
        vus.add(mid)
        parts = m["parts"]
        inconnus = set(parts) - groupes - {"nonreparti"}
        if inconnus:
            sys.exit(f"{ou}: {mid} répartit sur des groupes inconnus {sorted(inconnus)}")
        if abs(sum(parts.values()) - 1) > 1e-6 or any(v <= 0 for v in parts.values()):
            sys.exit(f"{ou}: les parts de {mid} doivent être positives et sommer à 1")
        if "etrangers" in parts and mid not in ("immigration", "ame"):
            sys.exit(f"{ou}: {mid} — le groupe 'etrangers' est réservé aux mesures immigration et ame")
        if m.get("fiabilite") not in ("sourcee", "convention"):
            sys.exit(f"{ou}: {mid} — fiabilite attendue 'sourcee' ou 'convention'")
        if m["fiabilite"] == "sourcee" and not m.get("sources"):
            sys.exit(f"{ou}: {mid} se dit sourcée sans source")
        if not m.get("explication"):
            sys.exit(f"{ou}: {mid} sans explication")
        for s in m.get("sources", []):
            if not s.get("t") or not str(s.get("u", "")).startswith("http"):
                sys.exit(f"{ou}: {mid} — source sans titre ou sans URL")
    manquent = ids - vus
    if manquent:
        sys.exit(f"{ou}: aucune clé pour {sorted(manquent)}")


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


def fraicheur(payload):
    """La date affichée au bandeau : la plus récente des quatre sources de données.

    Une relève qui n'ajoute que des annonces ne touche pas parties.json. Lire la seule
    date de ce fichier faisait vieillir le bandeau d'autant, et la page annonçait des
    données plus anciennes que celles qu'elle portait.
    """
    return max(payload[bloc]["updated"] for bloc in FILES
               if isinstance(payload.get(bloc), dict) and payload[bloc].get("updated"))


SITE = "https://quipaie2027.fr"
# Clé IndexNow (Bing, Yandex, Seznam…, et par Bing ChatGPT, DuckDuckGo, Qwant, Ecosia) :
# publique par construction — le fichier web/<clé>.txt prouve que le site en est le
# propriétaire. La CI s'en sert pour signaler chaque publication.
INDEXNOW_CLE = "bc390a87cc157f6e7e0faa701998cc8a"
WEB = ROOT / "web"
# Robots d'indexation et d'IA explicitement invités : moteurs (Google, Bing — dont se
# sert ChatGPT —, Qwant, DuckDuckGo, Ecosia s'appuient sur l'un des deux) et assistants.
ROBOTS_IA = ["Googlebot", "Bingbot", "Google-Extended", "GPTBot", "OAI-SearchBot",
             "ChatGPT-User", "ClaudeBot", "Claude-SearchBot", "Claude-User",
             "PerplexityBot", "Perplexity-User", "Applebot", "Applebot-Extended",
             "MistralAI-User", "CCBot", "DuckAssistBot", "Qwantbot"]


def fichiers_web(payload):
    """robots.txt, sitemap.xml et llms.txt, servis à côté de la page.

    Générés ici pour suivre les données : la date du sitemap est celle de la relève, et
    la liste des candidats de llms.txt celle de parties.json (les retirés n'y sont plus).
    """
    jour = fraicheur(payload)
    robots = ["# quipaie2027.fr — tout le site peut être lu et cité, par les moteurs comme par les IA.",
              "User-agent: *", "Allow: /", ""]
    for ua in ROBOTS_IA:
        robots += [f"User-agent: {ua}", "Allow: /", ""]
    robots += [f"Sitemap: {SITE}/sitemap.xml", ""]
    sitemap = ('<?xml version="1.0" encoding="UTF-8"?>\n'
               '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
               f"  <url><loc>{SITE}/</loc><lastmod>{jour}</lastmod>"
               "<changefreq>daily</changefreq><priority>1.0</priority></url>\n"
               f"  <url><loc>{SITE}/llms.txt</loc><lastmod>{jour}</lastmod>"
               "<changefreq>daily</changefreq><priority>0.5</priority></url>\n"
               "</urlset>\n")
    cands = [x for x in payload["parties"]["parties"] if not x.get("retire")]
    course = [x for x in cands if not x.get("horsCourse")]
    lignes = [f"- {x['candidat']} ({x['nom']}) : {x['statutCandidature']}" for x in course]
    annonces = [f"- {x['candidat']} : {x['annonce']['titre']}" for x in course
                if isinstance(x.get("annonce"), dict) and x["annonce"].get("titre")]
    llms = f"""# quipaie2027.fr

> Simulateur budgétaire neutre et gratuit pour l'élection présidentielle française de 2027. On choisit un candidat et on voit ce que son programme changerait au budget de la France d'ici 2032 : déficit public, dette publique, qui paie et qui reçoit, effets sur l'emploi, le chômage, la richesse par habitant et les taux d'intérêt, et l'écart entre ce que le candidat annonce et ce que donnent des chiffrages indépendants.

Données au {jour}, mises à jour chaque matin (veille des déclarations chiffrées, des chiffrages indépendants, des sondages et du contexte économique).

## Ce que fait le site

- Point de départ : la trajectoire des finances publiques « si rien ne change » (Insee, PLF, Haut Conseil des finances publiques, Commission européenne).
- Chaque programme est découpé en mesures ({len(payload['measures']['measures'])} au total), chacune chiffrée par une borne basse, une valeur centrale et une borne haute tirées de travaux publics : Cour des comptes, HCFP, OFCE, IPP, Conseil d'analyse économique, Fipeco, Banque de France, rapports parlementaires.
- Deux lectures côte à côte : « Leurs promesses » (les chiffres annoncés par les partis) et « Bas les masques » (ce que disent les chiffrages indépendants).
- Effets en chaîne en 2032 : emploi, chômage, PIB par habitant, taux d'emprunt de l'État, intérêts de la dette, à partir de multiplicateurs et de lois économiques publiés (Trésor, Banque de France, BCE, OFCE, Commission européenne), avec une fourchette.
- Journal des annonces : chaque déclaration chiffrée relevée, datée, sourcée, et marquée quand elle contredit le programme écrit.
- Le site ne soutient aucun candidat. Quand un parti n'a pas publié de chiffrage, son scénario est une reconstitution à partir de ses positions publiques, signalée comme telle.

## Candidats suivis

{chr(10).join(lignes)}

## Dernières annonces chiffrées par candidat

{chr(10).join(annonces)}

## Limites

- Ordres de grandeur arrondis, pas un modèle macroéconométrique complet : un chiffrage officiel se fait avec un modèle bouclé (type Mésange à la direction générale du Trésor).
- Les montants de chaque mesure sont réglables entre leurs bornes, parce que le chiffrage lui-même est souvent l'objet du désaccord.

## Liens

- [Le simulateur]({SITE}/) : toutes les données, la méthode et les sources sont dans la page (section « Méthode, sources et limites »).
"""
    return {"robots.txt": "\n".join(robots), "sitemap.xml": sitemap, "llms.txt": llms,
            f"{INDEXNOW_CLE}.txt": INDEXNOW_CLE}


def moteur_js():
    """Le moteur de projection, inséré tel quel dans la page (moteur/projection.js fait foi)."""
    js = (ROOT / "moteur" / "projection.js").read_text(encoding="utf-8")
    if "</script" in js:
        sys.exit("moteur/projection.js contient une balise fermante </script>")
    return js


def rendu(payload, template):
    """La substitution des six marqueurs, au même endroit pour les deux sens."""
    avatars, payload["avatars"] = build_avatars()
    favicon, coq = build_marque()
    moteur = moteur_js()
    blob = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    if "</script" in blob:
        sys.exit("le payload contient une balise fermante </script>")
    return (template.replace("__DATA__", blob)
                    .replace("__UPDATED__", fraicheur(payload))
                    .replace("__AVATARS__", avatars)
                    .replace("__FAVICON__", favicon)
                    .replace("__COQ__", coq)
                    .replace("__MOTEUR__", moteur), blob, avatars, favicon, coq, moteur)


def depuis_index(payload):
    """Remonte dans template.html des retouches faites à la main dans index.html.

    index.html n'est que le gabarit avec six substitutions : on refait le chemin en
    sens inverse en recalculant les valeurs injectées, en les retrouvant dans le fichier
    édité, et en remettant les marqueurs. Le report est exact ou il échoue — jamais
    approximatif.
    """
    index = ROOT / "index.html"
    if not index.is_file():
        sys.exit("index.html absent : rien à remonter")
    _, blob, avatars, favicon, coq, moteur = rendu(payload, "")
    html = index.read_text(encoding="utf-8")
    for quoi, valeur, marqueur in (("le payload", blob, "__DATA__"),
                                   ("les bustes", avatars, "__AVATARS__"),
                                   ("l'icône d'onglet", favicon, "__FAVICON__"),
                                   ("le coq du bandeau", coq, "__COQ__"),
                                   ("le moteur de projection", moteur, "__MOTEUR__"),
                                   ("la date de fraîcheur", fraicheur(payload),
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
    html, *_ = rendu(payload, template)
    index.write_text(html, encoding="utf-8")
    STAMP.write_text(hashlib.sha256(html.encode("utf-8")).hexdigest() + "\n", encoding="utf-8")
    WEB.mkdir(exist_ok=True)
    for nom, contenu in fichiers_web(payload).items():
        (WEB / nom).write_text(contenu, encoding="utf-8")
    print(f"index.html écrit — {len(html):,} octets, "
          f"{len(payload['measures']['measures'])} mesures, "
          f"{len(payload['parties']['parties'])} partis, "
          f"{len(payload['announcements']['items'])} annonces")


if __name__ == "__main__":
    main()
