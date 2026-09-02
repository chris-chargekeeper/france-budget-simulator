#!/usr/bin/env python3
"""Aspire le budget de l'État depuis budget.gouv.fr et écrit le brut sous sources/.

budget.gouv.fr sert ses dataviz par une API JSON non documentée mais stable :

    GET /depenses/{axe}/{annee}/{loi}/{type_budget}/{type_donnee}/json
        ?annee=…&loi_finances=…&type_budget=…&type_donnee=…

Les identifiants sont des termes de taxonomie Drupal (annee=247 vaut 2026), relevés
dans les <select> des pages /budget-etat/*. Un niveau de détail s'obtient en ajoutant
le type de la bulle cliquée comme paramètre : &ministere=86764 descend sur les
programmes du ministère 86764.

Le site est protégé par Imperva : une session valide est indispensable. Ouvrir
https://www.budget.gouv.fr/budget-etat dans un navigateur, recharger une fois pour
résoudre le challenge, puis relever les cookies visid_incap_* et incap_ses_* et les
passer par --cookies ou BUDGET_GOUV_COOKIES.

    python3 scrape_budget_gouv.py --cookies "visid_incap_3058694=…; incap_ses_978_…=…"

Chaque réponse est écrite telle quelle. Un fichier déjà présent n'est pas redemandé,
sauf --force : le script est donc reprenable après une coupure.
"""
import argparse
import concurrent.futures
import datetime
import gzip
import json
import os
import pathlib
import re
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "sources" / "budget.gouv.fr"
BASE = "https://www.budget.gouv.fr"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36")

# Termes de taxonomie relevés dans les <select> de /budget-etat/ministere.
ANNEES = {2018: 54, 2019: 55, 2020: 74, 2021: 118, 2022: 124,
          2023: 135, 2024: 143, 2025: 212, 2026: 247}
LOIS = {"plf": 50, "lfi": 47, "plrg": 245, "plr": 52}
LOIS_LABEL = {"plf": "Projet de loi de finances",
              "lfi": "Loi de finances initiale",
              "plrg": "Projet de loi relatif aux résultats de la gestion",
              "plr": "Projet de loi de règlement"}
TYPES_BUDGET = {"43": "Budget général", "44": "Budgets annexes",
                "45": "Comptes d'affectation spéciale",
                "46": "Comptes de concours financiers"}
DONNEES = ["ae", "cp"]  # autorisations d'engagement / crédits de paiement

# Un axe descend d'un niveau : la bulle de niveau 1 porte un `category.type`
# qu'on renvoie en paramètre pour obtenir ses enfants. Le niveau 2 est terminal
# (l'API renvoie une bulle anonyme si on insiste).
AXES = ["ministere", "mission", "nature"]

lock = threading.Lock()
stats = {"hit": 0, "cached": 0, "empty": 0, "error": 0}


def decode(raw, encoding):
    """Imperva compresse même sans que le client le demande."""
    if encoding == "gzip" or raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    return raw.decode("utf-8", errors="replace")


class Blocked(RuntimeError):
    """Imperva a repris la main : la session n'est plus valide."""


def get(url, cookies, referer=f"{BASE}/budget-etat", tries=3):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "*/*",
        "Accept-Language": "fr-FR,fr;q=0.9",
        "X-Requested-With": "XMLHttpRequest",
        "Accept-Encoding": "gzip, identity",
        "Referer": referer,
        "Cookie": cookies,
    })
    last = None
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return decode(resp.read(), resp.headers.get("Content-Encoding"))
        except urllib.error.HTTPError as exc:
            if exc.code in (403, 503):
                raise Blocked(f"HTTP {exc.code} sur {url}")
            last = exc
        except Exception as exc:  # noqa: BLE001 - réseau, on retente
            last = exc
        time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"{url}: {last}")


def depenses_url(axe, annee_tid, loi_tid, type_budget, type_donnee, extra=None):
    path = f"/depenses/{axe}/{annee_tid}/{loi_tid}/{type_budget}/{type_donnee}/json"
    params = {"annee": annee_tid, "loi_finances": loi_tid,
              "type_budget": type_budget, "type_donnee": type_donnee}
    if extra:
        params.update(extra)
    return f"{BASE}{path}?{urllib.parse.urlencode(params)}"


def fetch_json(url, dest, cookies, force=False):
    """Écrit la réponse sous dest et la renvoie. Ne redemande pas un fichier présent."""
    if dest.exists() and not force:
        with lock:
            stats["cached"] += 1
        return json.loads(dest.read_text(encoding="utf-8"))
    body = get(url, cookies)
    if not body.lstrip().startswith(("[", "{")):
        raise Blocked(f"réponse non JSON sur {url} — session expirée ?")
    data = json.loads(body)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    with lock:
        stats["hit"] += 1
        if not data:
            stats["empty"] += 1
    time.sleep(0.15)
    return data


def scrape_depenses(cookies, force, workers):
    """Niveau 1 (par axe) puis niveau 2 (détail de chaque bulle cliquable)."""
    index = []
    combos = [(axe, an, an_tid, loi, loi_tid, td)
              for axe in AXES
              for an, an_tid in sorted(ANNEES.items())
              for loi, loi_tid in LOIS.items()
              for td in DONNEES]

    def level1(combo):
        axe, an, an_tid, loi, loi_tid, td = combo
        dest = OUT / "depenses" / axe / loi / str(an) / f"{td}.json"
        url = depenses_url(axe, an_tid, loi_tid, "all", td)
        data = fetch_json(url, dest, cookies, force)
        return combo, url, dest, data

    def level2(combo, parent):
        axe, an, an_tid, loi, loi_tid, td = combo
        cat = parent.get("category") or {}
        ptype, pid = cat.get("type"), cat.get("id")
        if not ptype or not pid:
            return None
        dest = OUT / "depenses" / axe / loi / str(an) / td / f"{ptype}-{pid}.json"
        url = depenses_url(axe, an_tid, loi_tid, "all", td, {ptype: pid})
        data = fetch_json(url, dest, cookies, force)
        return {"axe": axe, "annee": an, "loi": loi, "type_donnee": td,
                "niveau": 2, "parent": {"type": ptype, "id": pid, "nom": parent.get("name")},
                "url": url, "fichier": str(dest.relative_to(ROOT)), "n": len(data)}

    pool = concurrent.futures.ThreadPoolExecutor(max_workers=workers)
    firsts = list(pool.map(level1, combos))
    tasks = []
    for combo, url, dest, data in firsts:
        axe, an, _, loi, _, td = combo
        index.append({"axe": axe, "annee": an, "loi": loi, "type_donnee": td,
                      "niveau": 1, "url": url,
                      "fichier": str(dest.relative_to(ROOT)), "n": len(data)})
        for bubble in data:
            if bubble.get("on_click"):
                tasks.append((combo, bubble))
    print(f"  niveau 1 : {len(firsts)} requêtes, {len(tasks)} détails à descendre", flush=True)
    for i, res in enumerate(pool.map(lambda t: level2(*t), tasks), 1):
        if res:
            index.append(res)
        if i % 200 == 0:
            print(f"  niveau 2 : {i}/{len(tasks)}", flush=True)
    pool.shutdown()
    return index


def scrape_operateurs(cookies, force):
    """Financement des opérateurs de l'État : un seul niveau, en budget exécuté."""
    index = []
    for an, an_tid in sorted(ANNEES.items()):
        for loi, loi_tid in LOIS.items():
            dest = OUT / "operateurs" / loi / f"{an}.json"
            url = depenses_url("operateurs", an_tid, loi_tid, "43", "budget")
            try:
                data = fetch_json(url, dest, cookies, force)
            except Blocked:
                raise
            except Exception as exc:  # noqa: BLE001
                print(f"  ! opérateurs {loi} {an} : {exc}", flush=True)
                stats["error"] += 1
                continue
            if not data:
                dest.unlink(missing_ok=True)
                continue
            index.append({"axe": "operateurs", "annee": an, "loi": loi,
                          "type_donnee": "budget", "niveau": 1, "url": url,
                          "fichier": str(dest.relative_to(ROOT)), "n": len(data)})
    return index


SETTINGS_RE = re.compile(
    r'<script type="application/json" data-drupal-selector="drupal-settings-json">(.*?)</script>',
    re.S)
BUILD_ID_RE = re.compile(r'name="form_build_id" value="([^"]+)"')


def page_settings(html):
    m = SETTINGS_RE.search(html)
    return json.loads(m.group(1)) if m else {}


def datavizs(html):
    """Les graphes d'une page dont les données sont embarquées, pas servies par l'API."""
    dv = page_settings(html).get("dataviz", {}).get("dataviz", {})
    return [{"uuid": k, "type": v.get("type"), "unit": v.get("unit"),
             "url": v.get("url") or None, "data": v.get("graphData")}
            for k, v in dv.items()]


def scrape_page(path, dest, cookies, force):
    if dest.exists() and not force:
        stats["cached"] += 1
        return json.loads(dest.read_text(encoding="utf-8"))
    html = get(f"{BASE}{path}", cookies)
    if "Incapsula" in html and "_Incapsula_Resource" in html[:800]:
        raise Blocked(f"Imperva sur {path}")
    payload = {"url": f"{BASE}{path}", "recupere": datetime.date.today().isoformat(),
               "graphes": datavizs(html)}
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    stats["hit"] += 1
    time.sleep(0.2)
    return payload


def scrape_smb(cookies, force):
    """Situation mensuelle du budget : formulaire POST, données embarquées dans la page.

    Le millésime et le mois ne passent pas en GET — il faut rejouer le formulaire
    Drupal avec son form_build_id, relevé sur un GET préalable.
    """
    index = []
    html = get(f"{BASE}/budget-etat/smb", cookies)
    build_id = BUILD_ID_RE.search(html)
    if not build_id:
        print("  ! SMB : form_build_id introuvable, seul l'état courant est capturé", flush=True)
        dest = OUT / "smb" / "courant.json"
        scrape_page("/budget-etat/smb", dest, cookies, force)
        return [{"axe": "smb", "fichier": str(dest.relative_to(ROOT))}]

    for an, an_tid in sorted(ANNEES.items()):
        for type_budget in ("recettes", "depenses", "solde"):
            dest = OUT / "smb" / str(an) / f"{type_budget}.json"
            if dest.exists() and not force:
                stats["cached"] += 1
                index.append({"axe": "smb", "annee": an, "type_budget": type_budget,
                              "fichier": str(dest.relative_to(ROOT))})
                continue
            fresh = get(f"{BASE}/budget-etat/smb", cookies)
            bid = BUILD_ID_RE.search(fresh)
            body = urllib.parse.urlencode({
                "type_budget": type_budget, "annee": an_tid, "mois": "decembre",
                "op": "Valider", "form_build_id": bid.group(1) if bid else "",
                "form_id": "budget_etat_smb_form"}).encode()
            req = urllib.request.Request(f"{BASE}/budget-etat/smb", data=body, headers={
                "User-Agent": UA, "Cookie": cookies, "Referer": f"{BASE}/budget-etat/smb",
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept-Language": "fr-FR,fr;q=0.9"})
            try:
                with urllib.request.urlopen(req, timeout=60) as resp:
                    page = decode(resp.read(), resp.headers.get("Content-Encoding"))
            except Exception as exc:  # noqa: BLE001
                print(f"  ! SMB {an} {type_budget} : {exc}", flush=True)
                stats["error"] += 1
                continue
            graphes = datavizs(page)
            if not graphes:
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(json.dumps(
                {"url": f"{BASE}/budget-etat/smb", "methode": "POST",
                 "parametres": {"annee": an, "type_budget": type_budget, "mois": "decembre"},
                 "recupere": datetime.date.today().isoformat(), "graphes": graphes},
                ensure_ascii=False, indent=1), encoding="utf-8")
            stats["hit"] += 1
            index.append({"axe": "smb", "annee": an, "type_budget": type_budget,
                          "fichier": str(dest.relative_to(ROOT))})
            time.sleep(0.3)
    return index


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cookies", default=os.environ.get("BUDGET_GOUV_COOKIES", ""),
                    help="cookies Imperva d'une session navigateur valide")
    ap.add_argument("--force", action="store_true", help="réaspirer même si le fichier existe")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--only", choices=["depenses", "operateurs", "smb", "synthese"],
                    action="append")
    args = ap.parse_args()
    if not args.cookies:
        sys.exit("cookies manquants : voir --help")

    only = set(args.only or ["depenses", "operateurs", "smb", "synthese"])
    started = time.time()
    index = []
    try:
        if "synthese" in only:
            print("→ synthèse budget de l'État", flush=True)
            for path, name in (("/budget-etat", "budget-etat"),
                               ("/panorama-finances-publiques", "panorama-finances-publiques")):
                dest = OUT / "synthese" / f"{name}.json"
                try:
                    scrape_page(path, dest, args.cookies, args.force)
                    index.append({"axe": "synthese", "page": path,
                                  "fichier": str(dest.relative_to(ROOT))})
                except Blocked:
                    raise
                except Exception as exc:  # noqa: BLE001
                    print(f"  ! {path} : {exc}", flush=True)
        if "depenses" in only:
            print("→ dépenses (ministère, mission, nature)", flush=True)
            index += scrape_depenses(args.cookies, args.force, args.workers)
        if "operateurs" in only:
            print("→ opérateurs", flush=True)
            index += scrape_operateurs(args.cookies, args.force)
        if "smb" in only:
            print("→ situation mensuelle budgétaire", flush=True)
            index += scrape_smb(args.cookies, args.force)
    except Blocked as exc:
        sys.exit(f"\nsession invalide : {exc}\nRecharger budget.gouv.fr dans un navigateur "
                 f"et repasser des cookies frais. Les fichiers déjà écrits sont conservés.")

    manifest = OUT / "MANIFEST.json"
    previous = json.loads(manifest.read_text(encoding="utf-8"))["entrees"] if manifest.exists() else []
    merged = {e["fichier"]: e for e in previous}
    merged.update({e["fichier"]: e for e in index})
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps({
        "source": BASE + "/budget-etat",
        "licence": "Licence Ouverte / Open Licence (Etalab)",
        "recupere": datetime.date.today().isoformat(),
        "referentiels": {
            "annees": {str(k): v for k, v in ANNEES.items()},
            "lois_finances": {k: {"tid": v, "libelle": LOIS_LABEL[k]} for k, v in LOIS.items()},
            "types_budget": TYPES_BUDGET,
            "types_donnee": {"ae": "Autorisations d'engagement",
                             "cp": "Crédits de paiement",
                             "budget": "Budget de l'opérateur"},
        },
        "entrees": sorted(merged.values(), key=lambda e: e["fichier"]),
    }, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"\n{stats['hit']} requêtes, {stats['cached']} déjà en cache, "
          f"{stats['empty']} vides, {stats['error']} en échec — "
          f"{time.time() - started:.0f} s\n{manifest.relative_to(ROOT)} : "
          f"{len(merged)} fichiers")


if __name__ == "__main__":
    main()
