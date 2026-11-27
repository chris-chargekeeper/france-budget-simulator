"""Pages lisibles sans JavaScript, pour les moteurs de recherche et les assistants d'IA.

Le simulateur calcule tout dans le navigateur : un robot qui n'exécute pas de JavaScript n'y
trouve aucun résultat. build.py appelle ici `node moteur/resultats.js` (le même moteur que la
page, les mêmes hypothèses) et en tire, dans web/ :

  resultats.json         les résultats de chaque candidat, en données ouvertes
  comparatif.html        tous les candidats côte à côte
  candidat-<nom>.html    une page par candidat : déficit, dette, effets, mesures, sources
  llms-full.txt          le tout en texte brut, pour les assistants d'IA

Les positions sur l'Europe et l'Ukraine (dataset/simulateur/europe.json) y sont jointes, notées
comme sur la carte « Europe et Ukraine » de la page : mêmes points, même règle pour tous.

Mêmes règles pour tous : un seul gabarit, aucun chiffre que la page ne montre pas, et aucun
sondage (rien à masquer pendant le silence électoral).
"""
import html
import json
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SITE = "https://quipaie2027.fr"
LICENCE = ("Licence Ouverte / Open Licence 2.0 (Etalab)",
           "https://www.etalab.gouv.fr/licence-ouverte-open-licence/")

STATUT = {
    "partiel": "Programme en partie chiffré par le parti, complété par le simulateur",
    "reconstitution": ("Scénario reconstitué par le site : le parti n'a pas publié de chiffrage, "
                       "les mesures sont tirées de ses positions publiques"),
    "programme": "Programme chiffré publié par le parti",
    "ia": "Budget calculé par une intelligence artificielle, hors course : ce n'est le programme de personne",
}
SENS = {"dep-": "économie", "dep+": "dépense nouvelle", "rec+": "recette nouvelle", "rec-": "baisse d'impôt"}


def resultats():
    """Les résultats calculés par le moteur de la page (moteur/resultats.js)."""
    try:
        out = subprocess.run(["node", str(ROOT / "moteur" / "resultats.js")], check=True,
                             capture_output=True, text=True, cwd=ROOT).stdout
    except (OSError, subprocess.CalledProcessError) as e:
        sys.exit(f"moteur/resultats.js a échoué : {getattr(e, 'stderr', '') or e}")
    return json.loads(out)


def slug(nom):
    s = unicodedata.normalize("NFKD", nom).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def page_de(c):
    return "budget-apolitique.html" if c["horsCourse"] else f"candidat-{slug(c['candidat'])}.html"


def nf(v, d=1):
    """Nombre à la française : virgule décimale, espace fine insécable pour les milliers."""
    s = f"{abs(v):,.{d}f}".replace(",", " ").replace(".", ",")
    return ("−" if v < 0 and float(f"{abs(v):.{d}f}") != 0 else "") + s


def sg(v, d=1):
    if float(f"{abs(v):.{d}f}") == 0:
        return nf(0, d)
    return ("+" if v > 0 else "") + nf(v, d)


def md(v, d=1):
    return f"{nf(v, d)} Md€"


def mdsg(v, d=1):
    return f"{sg(v, d)} Md€"


def fourch(f, d=1, unite=""):
    return f"de {sg(f[0], d)}{unite} à {sg(f[1], d)}{unite}"


def e(s):
    return html.escape(str(s), quote=True)


def gabarit(titre, description, canonical, corps, jsonld, jour):
    ld = json.dumps(jsonld, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return f"""<!doctype html>
<html lang="fr">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{e(titre)}</title>
<meta name="description" content="{e(description)}">
<link rel="canonical" href="{SITE}/{canonical}">
<meta name="robots" content="index, follow, max-snippet:-1">
<meta property="og:type" content="article">
<meta property="og:locale" content="fr_FR">
<meta property="og:site_name" content="quipaie2027.fr">
<meta property="og:title" content="{e(titre)}">
<meta property="og:description" content="{e(description)}">
<meta property="og:url" content="{SITE}/{canonical}">
<meta property="og:image" content="{SITE}/partage.jpg">
<meta property="article:modified_time" content="{jour}">
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
<link rel="alternate" type="application/json" href="/resultats.json" title="Résultats en données ouvertes">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@500;600&family=IBM+Plex+Sans:wght@400;600&family=Newsreader:opsz,wght@6..72,600&display=swap">
<script type="application/ld+json">{ld}</script>
<script>
/* même thème que le simulateur : clair par défaut, sombre seulement si le visiteur l'a choisi */
(function(){{ var c = null; try {{ c = localStorage.getItem('fbs-theme'); }} catch (e) {{}}
  document.documentElement.setAttribute('data-theme', c === 'dark' ? 'dark' : 'light'); }})();
</script>
<style>
:root{{color-scheme:light;--plane:#E7EBEF;--surface:#FBFCFD;--ink:#0E1A26;--ink-2:#4A5A6B;--ink-3:#7C8C9B;--rule:#D6DDE4;--accent:#1c5cab;--good:#1d7a4f;--bad:#b4362f}}
:root[data-theme="dark"]{{color-scheme:dark;--plane:#0A0F15;--surface:#141C25;--ink:#E9EFF5;--ink-2:#9FB0C0;--ink-3:#71828F;--rule:#27323D;--accent:#6da7ec;--good:#5cc28f;--bad:#f07a70}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--plane);color:var(--ink-2);font:15px/1.6 "IBM Plex Sans",system-ui,sans-serif}}
main{{max-width:860px;margin:0 auto;padding:28px 16px 64px}}
nav{{display:flex;flex-wrap:wrap;gap:6px 16px;font:500 13px "IBM Plex Mono",monospace}}
nav a{{color:var(--accent);text-decoration:none}}
.carte{{background:var(--surface);border:1px solid var(--rule);border-radius:16px;padding:22px 24px;margin-top:16px}}
h1{{font:600 32px/1.15 Newsreader,serif;color:var(--ink);margin:18px 0 6px}}
.sous{{color:var(--ink-3);font-size:13px;margin:0}}
h2{{font:600 17px "IBM Plex Sans",sans-serif;color:var(--ink);margin:0 0 8px}}
h3{{font:600 15px "IBM Plex Sans",sans-serif;color:var(--ink);margin:14px 0 2px}}
p,li{{margin:6px 0}}
ul{{padding-left:20px}}
b,strong{{color:var(--ink)}}
a{{color:var(--accent)}}
.resume{{font-size:16.5px;color:var(--ink)}}
.chiffres{{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px;margin:14px 0 0;padding:0}}
.chiffres div{{border:1px solid var(--rule);border-radius:12px;padding:10px 12px}}
.chiffres dt{{font-size:12.5px;color:var(--ink-3)}}
.chiffres dd{{margin:2px 0 0;font:600 22px "IBM Plex Mono",monospace;color:var(--ink)}}
.chiffres small{{display:block;font:12.5px "IBM Plex Sans",sans-serif;color:var(--ink-3)}}
.table{{overflow-x:auto;margin:8px 0}}
table{{border-collapse:collapse;width:100%;font-size:14px}}
th,td{{text-align:left;padding:7px 8px;border-bottom:1px solid var(--rule);vertical-align:top}}
th{{font-weight:600;color:var(--ink);font-size:13px}}
td.n,th.n{{text-align:right;white-space:nowrap;font-family:"IBM Plex Mono",monospace;font-size:13px}}
.pos{{color:var(--good)}} .neg{{color:var(--bad)}}
details{{margin:4px 0}}
summary{{cursor:pointer;color:var(--ink)}}
.mesure p{{font-size:13.5px}}
.src{{font-size:12.5px;color:var(--ink-3)}}
footer{{margin-top:22px;font-size:12.5px;color:var(--ink-3)}}
@media (max-width:520px){{.carte{{padding:18px 16px}} h1{{font-size:26px}}}}
</style>
<main>
  <nav><a href="/">← Le simulateur</a><a href="/comparatif.html">Tous les candidats</a><a href="/resultats.json">Données (JSON)</a></nav>
{corps}
  <footer>
    <p>quipaie2027.fr est un simulateur pédagogique, gratuit et indépendant de tout parti : tous les candidats passent par les mêmes règles et les mêmes sources. Données au {jour}, recalculées chaque matin. Licence des données : <a href="{LICENCE[1]}">{LICENCE[0]}</a>, en citant « quipaie2027.fr ». <a href="/mentions-legales.html">Mentions légales et confidentialité</a>.</p>
  </footer>
</main>
</html>
"""


def methode_html(R):
    h = R["hypotheses"]
    return f"""  <section class="carte" id="methode">
    <h2>Comment ces chiffres sont calculés</h2>
    <ul>
      <li>Point de départ : la trajectoire « si rien ne change » (Insee, loi de finances, Haut Conseil des finances publiques, Commission européenne) : déficit de {nf(R['siRienNeChange']['deficit2032'])} % du PIB et dette de {nf(R['siRienNeChange']['dette2032'])} % du PIB en 2032.</li>
      <li>Chaque programme est découpé en mesures. Chaque mesure a une borne basse, une valeur centrale et une borne haute tirées de travaux publics (Cour des comptes, HCFP, OFCE, IPP, Conseil d'analyse économique, Fipeco, Banque de France, rapports parlementaires). Les montants s'appliquent progressivement, selon la montée en charge de chaque mesure.</li>
      <li>Deux lectures : les <b>chiffrages indépendants</b> (par défaut) et les <b>montants annoncés par le parti</b> quand il en publie.</li>
      <li>Hypothèses communes à tous : croissance {nf(h['croissance'])} % par an hors prévisions de la Banque de France pour 2026-2028, inflation {nf(h['inflation'])} %, taux de marché {nf(h['tauxMarche'])} %, multiplicateur budgétaire {nf(h['multiplicateur'])}, érosion de {nf(h['erosion'], 0)} % des recettes nouvelles sur les comportements.</li>
      <li>Les effets sur l'emploi, le chômage, la production et les taux viennent de multiplicateurs et de lois économiques publiés (Trésor, Banque de France, BCE, OFCE, Commission européenne). La fourchette couvre toutes les combinaisons des bornes publiées.</li>
      <li>Limites : ce sont des ordres de grandeur arrondis, pas un modèle macroéconométrique complet comme ceux du Trésor. Le détail des sources est dans la section « Méthode, sources et limites » du <a href="/">simulateur</a>.</li>
    </ul>
  </section>"""


def citer_html(titre, url, jour):
    return f"""  <section class="carte" id="citer">
    <h2>Citer cette page</h2>
    <p>« {e(titre)} », quipaie2027.fr, données au {jour}, <a href="{url}">{url}</a>.</p>
  </section>"""


def lien_source(s):
    t = e(s.get("t", "source"))
    return f'<a href="{e(s["u"])}">{t}</a>' if s.get("u") else t


def resume_candidat(c, R, jour):
    """La phrase qu'un assistant peut reprendre telle quelle."""
    base = R["siRienNeChange"]
    if c["horsCourse"]:
        sujet = "Le budget apolitique calculé par une intelligence artificielle"
    else:
        sujet = f"Le programme de {c['candidat']} ({c['parti']})"
    s = (f"{sujet} conduirait, selon le simulateur quipaie2027.fr (données au {jour}) et avec les "
         f"chiffrages indépendants, à un déficit public de {nf(c['deficit2032'])} % du PIB en 2032, "
         f"contre {nf(base['deficit2032'])} % si rien ne change, et à une dette publique de "
         f"{nf(c['dette2032'])} % du PIB.")
    if abs(c["deficit2032Promesses"] - c["deficit2032"]) >= 0.1:
        s += (f" Avec les montants annoncés par le parti, le déficit serait de "
              f"{nf(c['deficit2032Promesses'])} % du PIB : l'écart vient de mesures que le parti chiffre "
              f"à {mdsg(c['effetNet2032Promesses'])} par an en 2032, quand les chiffrages indépendants "
              f"donnent {mdsg(c['effetNet2032'])}.")
    return s


def page_candidat(c, R, jour):
    url = f"{SITE}/{page_de(c)}"
    if c["horsCourse"]:
        titre = "Le budget apolitique calculé par une IA : déficit et dette en 2032"
        h1 = "Le budget apolitique, calculé par une IA"
    else:
        titre = f"{c['candidat']} ({c['sigle']}) : ce que son programme changerait au budget d'ici 2032"
        h1 = f"{c['candidat']} : ce que son programme changerait au budget de la France"
    resume = resume_candidat(c, R, jour)
    ef = c["effets2032"]
    base = R["siRienNeChange"]
    corps = [f"""  <h1>{e(h1)}</h1>
  <p class="sous">{e(c['parti'])}{' · ' + e(c['statutCandidature']) if c['statutCandidature'] else ''}</p>
  <section class="carte">
    <p class="resume">{e(resume)}</p>
    <dl class="chiffres">
      <div><dt>Déficit public en 2032</dt><dd>{nf(c['deficit2032'])} %</dd><small>du PIB · {nf(base['deficit2032'])} % si rien ne change</small></div>
      <div><dt>Dette publique en 2032</dt><dd>{nf(c['dette2032'])} %</dd><small>du PIB · {nf(base['dette2032'])} % si rien ne change</small></div>
      <div><dt>Effet net des mesures en 2032</dt><dd>{mdsg(c['effetNet2032'])}</dd><small>par an, sur le solde public (chiffrages indépendants)</small></div>
      <div><dt>Avec les chiffres du parti</dt><dd>{nf(c['deficit2032Promesses'])} %</dd><small>de déficit en 2032 · effet net annoncé {mdsg(c['effetNet2032Promesses'])}</small></div>
    </dl>
    <p class="src">Statut : {e(STATUT.get(c['statutChiffrage'], c['statutChiffrage']))}.</p>
  </section>"""]
    a = c.get("annonce") or {}
    if a.get("titre") or a.get("texte"):
        corps.append(f"""  <section class="carte">
    <h2>{'Ce que le parti annonce' if not c['horsCourse'] else 'Le principe'}{' : ' + e(a['titre']) if a.get('titre') else ''}</h2>
    {('<p>' + e(a['texte']) + '</p>') if a.get('texte') else ''}
  </section>""")
    corps.append(f"""  <section class="carte">
    <h2>Les effets en chaîne en 2032</h2>
    <p>Écart avec la trajectoire « si rien ne change », valeur centrale et fourchette des travaux publiés :</p>
    <ul>
      <li><b>Emplois</b> : {sg(ef['emplois']['centre'], 0)} ({fourch(ef['emplois']['fourchette'], 0)})</li>
      <li><b>Chômage</b> : {sg(ef['chomagePts']['centre'])} point ({fourch(ef['chomagePts']['fourchette'], 1, ' pt')})</li>
      <li><b>Production (PIB)</b> : {sg(ef['pibPct']['centre'], 2)} % ({fourch(ef['pibPct']['fourchette'], 2, ' %')})</li>
      <li><b>Taux d'emprunt de l'État</b> : {sg(ef['tauxEtatPts']['centre'], 2)} point ({fourch(ef['tauxEtatPts']['fourchette'], 2, ' pt')})</li>
    </ul>
  </section>""")
    lignes = "".join(
        f"<tr><td>{t['annee']}</td><td class=\"n\">{nf(t['deficitPct'])} %</td><td class=\"n\">{nf(b['deficitPct'])} %</td>"
        f"<td class=\"n\">{nf(t['dettePct'])} %</td><td class=\"n\">{nf(b['dettePct'])} %</td></tr>"
        for t, b in zip(c["trajectoire"], base["trajectoire"]))
    corps.append(f"""  <section class="carte">
    <h2>La trajectoire, année par année</h2>
    <div class="table"><table>
      <thead><tr><th>Année</th><th class="n">Déficit</th><th class="n">si rien ne change</th><th class="n">Dette</th><th class="n">si rien ne change</th></tr></thead>
      <tbody>{lignes}</tbody>
    </table></div>
    <p class="src">En % du PIB. 2025 : dernier chiffre de l'Insee.</p>
  </section>""")
    rows = []
    for m in c["mesures"]:
        cls = "pos" if m["effet2032"] > 0 else "neg" if m["effet2032"] < 0 else ""
        ann = md(m["annonce"]) if m["annonce"] is not None else "—"
        src = "".join(f"<li>{lien_source(s)}</li>" for s in m["sources"])
        src = f'<ul class="src">{src}</ul>' if src else ""
        rows.append(
            f"<tr class=\"mesure\"><td><details><summary>{e(m['libelle'])}</summary><p>{e(m['note'])}</p>"
            f"{src}</details></td>"
            f"<td>{SENS.get(m['sens'], m['sens'])}</td>"
            f"<td class=\"n {cls}\">{mdsg(m['effet2032'])}</td>"
            f"<td class=\"n\">{nf(m['bas'])} à {nf(m['haut'])}</td><td class=\"n\">{ann}</td></tr>")
    corps.append(f"""  <section class="carte">
    <h2>Les {len(c['mesures'])} mesures chiffrées</h2>
    <p>Effet de chaque mesure sur le solde public en 2032 (positif : améliore le solde), au montant retenu par le simulateur ; la fourchette publiée et le montant annoncé par le parti sont en Md€ par an, une fois la mesure en place. Cliquer sur une mesure pour son explication et ses sources.</p>
    <div class="table"><table>
      <thead><tr><th>Mesure</th><th>Nature</th><th class="n">Effet 2032</th><th class="n">Fourchette</th><th class="n">Annoncé</th></tr></thead>
      <tbody>{''.join(rows)}</tbody>
    </table></div>
  </section>""")
    if c["sources"]:
        corps.append("  <section class=\"carte\">\n    <h2>Sources du scénario</h2>\n    <ul>"
                     + "".join(f"<li>{lien_source(s)}</li>" for s in c["sources"]) + "</ul>\n  </section>")
    if c.get("europeUkraine"):
        corps.append(europe_html(c, R["europeUkraine"]))
    corps += [methode_html(R), citer_html(titre, url, jour)]
    jsonld = {"@context": "https://schema.org", "@type": "WebPage", "@id": url, "url": url,
              "name": titre, "description": resume, "inLanguage": "fr-FR", "dateModified": jour,
              "isPartOf": {"@id": f"{SITE}/#site"}, "isBasedOn": f"{SITE}/resultats.json",
              "license": LICENCE[1]}
    if not c["horsCourse"]:
        jsonld["about"] = [{"@type": "Person", "name": c["candidat"],
                            "memberOf": {"@type": "PoliticalParty", "name": c["parti"]}},
                           "Élection présidentielle française de 2027", "Budget de la France"]
    return titre, gabarit(titre, resume[:300], page_de(c), "\n".join(corps), jsonld, jour)


def page_comparatif(R, jour):
    url = f"{SITE}/comparatif.html"
    titre = "Présidentielle 2027 : déficit et dette en 2032 selon le programme de chaque candidat"
    base = R["siRienNeChange"]
    course = [c for c in R["candidats"] if not c["horsCourse"]]
    ordre = sorted(course, key=lambda c: c["deficit2032"])
    desc = (f"Déficit et dette publics en 2032 pour les programmes des {len(course)} candidats suivis à la "
            f"présidentielle 2027, avec les chiffrages indépendants et avec les chiffres des partis. "
            f"Si rien ne change : {nf(base['deficit2032'])} % de déficit et {nf(base['dette2032'])} % de dette.")
    lignes = "".join(
        f"<tr><td><a href=\"/{page_de(c)}\">{e(c['candidat'])}</a><br><span class=\"src\">{e(c['parti'])}</span></td>"
        f"<td class=\"n\">{nf(c['deficit2032'])} %</td><td class=\"n\">{nf(c['dette2032'])} %</td>"
        f"<td class=\"n\">{mdsg(c['effetNet2032'])}</td><td class=\"n\">{nf(c['deficit2032Promesses'])} %</td>"
        f"<td class=\"n\">{sg(c['effets2032']['emplois']['centre'], 0)}</td>"
        f"<td>{'reconstitué' if c['statutChiffrage'] == 'reconstitution' else 'en partie chiffré' if c['statutChiffrage'] == 'partiel' else 'chiffré'}</td></tr>"
        for c in sorted(course, key=lambda c: c["candidat"].split()[-1]))
    ia = next((c for c in R["candidats"] if c["horsCourse"]), None)
    ia_txt = (f"<p>Pour repère, le <a href=\"/{page_de(ia)}\">budget apolitique calculé par une IA</a> "
              f"(ce n'est le programme de personne) donne {nf(ia['deficit2032'])} % de déficit et "
              f"{nf(ia['dette2032'])} % de dette en 2032.</p>") if ia else ""
    corps = f"""  <h1>Déficit et dette en 2032, programme par programme</h1>
  <p class="sous">Présidentielle 2027 · {len(course)} candidats suivis · données au {jour}</p>
  <section class="carte">
    <p class="resume">Selon le simulateur quipaie2027.fr (données au {jour}), avec les chiffrages indépendants, le déficit public de la France en 2032 irait de {nf(ordre[0]['deficit2032'])} % du PIB ({e(ordre[0]['candidat'])}) à {nf(ordre[-1]['deficit2032'])} % ({e(ordre[-1]['candidat'])}), contre {nf(base['deficit2032'])} % si rien ne change. Aucun programme ne ramène le déficit sous 3 % du PIB en 2032, le seuil demandé par l'Union européenne, si l'on retient les chiffrages indépendants.</p>
    <div class="table"><table>
      <thead><tr><th>Candidat</th><th class="n">Déficit 2032</th><th class="n">Dette 2032</th><th class="n">Effet net</th><th class="n">Déficit, chiffres du parti</th><th class="n">Emplois</th><th>Chiffrage</th></tr></thead>
      <tbody><tr><td><b>Si rien ne change</b></td><td class="n">{nf(base['deficit2032'])} %</td><td class="n">{nf(base['dette2032'])} %</td><td class="n">—</td><td class="n">—</td><td class="n">—</td><td></td></tr>{lignes}</tbody>
    </table></div>
    <p class="src">Déficit et dette en % du PIB. Effet net : effet des mesures sur le solde public en 2032, en Md€ par an (positif : améliore le solde). Emplois : écart avec « si rien ne change » en 2032. Candidats par ordre alphabétique.</p>
    {ia_txt}
  </section>
{comparatif_europe_html(R, R['europeUkraine']) if R.get('europeUkraine') else ''}
{methode_html(R)}
{citer_html(titre, url, jour)}"""
    if any(c["deficit2032"] < 3 for c in course):
        corps = corps.replace(" Aucun programme ne ramène le déficit sous 3 % du PIB en 2032, le seuil demandé par l'Union européenne, si l'on retient les chiffrages indépendants.", "")
    jsonld = {"@context": "https://schema.org", "@graph": [
        {"@type": "WebPage", "@id": url, "url": url, "name": titre, "description": desc, "inLanguage": "fr-FR",
         "dateModified": jour, "isPartOf": {"@id": f"{SITE}/#site"}},
        {"@type": "Dataset", "@id": f"{SITE}/resultats.json#dataset",
         "name": "Présidentielle 2027 : effets des programmes sur le budget de la France (quipaie2027.fr)",
         "description": ("Déficit et dette publics 2025-2032, effets sur l'emploi, le chômage, le PIB et les taux, "
                         "et chiffrage mesure par mesure (bornes basse, centrale, haute et montant annoncé) "
                         "pour chaque candidat suivi, recalculés chaque jour."),
         "url": url, "inLanguage": "fr-FR", "dateModified": jour, "isAccessibleForFree": True,
         "license": LICENCE[1], "creator": {"@id": f"{SITE}/#site"},
         "keywords": ["présidentielle 2027", "budget", "déficit public", "dette publique", "programmes"],
         "spatialCoverage": "France", "temporalCoverage": "2025/2032",
         "distribution": {"@type": "DataDownload", "encodingFormat": "application/json",
                          "contentUrl": f"{SITE}/resultats.json"}}]}
    return gabarit(titre, desc, "comparatif.html", corps, jsonld, jour)


def llms_full(R, jour):
    base = R["siRienNeChange"]
    out = [f"# quipaie2027.fr — résultats complets (données au {jour})", "",
           "> Simulateur budgétaire neutre de la présidentielle 2027. Pour chaque candidat : déficit et dette "
           "publics en 2032, effets sur l'emploi et le chômage, et chaque mesure avec son chiffrage. Même "
           "moteur et mêmes hypothèses que la page ; mêmes règles pour tous les candidats.", "",
           f"Licence : {LICENCE[0]} ({LICENCE[1]}), en citant « quipaie2027.fr ». Données en JSON : {SITE}/resultats.json", "",
           "## Si rien ne change", "",
           f"Déficit public de {nf(base['deficit2032'])} % du PIB et dette de {nf(base['dette2032'])} % du PIB en 2032.", ""]
    for c in R["candidats"]:
        ef = c["effets2032"]
        out += [f"## {c['candidat']} ({c['parti']})" if not c["horsCourse"] else "## Budget apolitique (calculé par une IA, hors course)", "",
                f"Page : {SITE}/{page_de(c)}", "",
                resume_candidat(c, R, jour), "",
                f"- Statut : {STATUT.get(c['statutChiffrage'], c['statutChiffrage'])}"]
        if c["statutCandidature"]:
            out.append(f"- Candidature : {c['statutCandidature']}")
        a = c.get("annonce") or {}
        if a.get("titre"):
            out.append(f"- Annonce du parti : {a['titre']}")
        out += [f"- Effets en 2032 par rapport à « si rien ne change » : emplois {sg(ef['emplois']['centre'], 0)} "
                f"({fourch(ef['emplois']['fourchette'], 0)}), chômage {sg(ef['chomagePts']['centre'])} point, "
                f"PIB {sg(ef['pibPct']['centre'], 2)} %, taux d'emprunt de l'État {sg(ef['tauxEtatPts']['centre'], 2)} point", "",
                "Mesures (effet sur le solde en 2032 ; fourchette publiée ; montant annoncé par le parti) :", ""]
        for m in c["mesures"]:
            ann = f" ; annoncé {md(m['annonce'])}" if m["annonce"] is not None else ""
            out.append(f"- {m['libelle']} ({SENS.get(m['sens'], m['sens'])}) : {mdsg(m['effet2032'])} ; "
                       f"{nf(m['bas'])} à {nf(m['haut'])} Md€{ann}")
        eu = europe_llms(c)
        if eu:
            out += ["", "Europe et Ukraine (même grille pour tous ; une case non précisée compte zéro) :", ""] + eu
        out.append("")
    out += ["## Méthode et limites", "",
            "Chaque mesure est chiffrée par une borne basse, une valeur centrale et une borne haute tirées de travaux "
            "publics (Cour des comptes, HCFP, OFCE, IPP, CAE, Fipeco, Banque de France, rapports parlementaires). "
            "Les scénarios « reconstitués » sont bâtis par le site à partir des positions publiques, faute de chiffrage "
            "publié par le parti. Ordres de grandeur arrondis, pas un modèle macroéconométrique complet.", ""]
    if R.get("europeUkraine"):
        out += ["Europe et Ukraine : " + R["europeUkraine"]["regle"] + " " + R["europeUkraine"]["votes"]["regle"], ""]
    return "\n".join(out)


# ── Europe et Ukraine ────────────────────────────────────────────────────────────────────────
MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre",
        "octobre", "novembre", "décembre"]
AXES = {"europe": ("L'Europe", "Moins d'Europe", "Plus d'Europe"),
        "ukraine": ("L'Ukraine", "Désengagement", "Soutien renforcé")}
VOTE = {"pour": "pour", "contre": "contre", "abstention": "abstention", "partage": "partagé"}


def fr_date(d):
    if not d:
        return ""
    p = d.split("-")
    if len(p) == 1:
        return d
    if len(p) == 2:
        return f"{MOIS[int(p[1]) - 1]} {p[0]}"
    return f"{int(p[2])}{'er' if p[2] == '01' else ''} {MOIS[int(p[1]) - 1]} {p[0]}"


def europe_ukraine(R):
    """Les positions sur l'Europe et l'Ukraine, notées comme sur la page (template.html,
    renderEuropeUkraine) : chaque réponse rapporte les points de la grille, une case non précisée
    compte zéro, et l'échelle va de la somme des minimums à la somme des maximums."""
    f = ROOT / "dataset" / "simulateur" / "europe.json"
    if not f.exists():
        return None
    EU = json.loads(f.read_text(encoding="utf-8"))
    ids = [c["id"] for c in R["candidats"] if not c["horsCourse"] and c["id"] in EU["candidats"]]
    axes = {}
    for ax, (titre, gauche, droite) in AXES.items():
        cr = EU["criteres"][ax]
        axes[ax] = {"titre": titre, "gauche": gauche, "droite": droite,
                    "min": sum(min(v["points"] for v in c["valeurs"].values()) for c in cr),
                    "max": sum(max(v["points"] for v in c["valeurs"].values()) for c in cr),
                    "questions": [c["lab"] for c in cr]}
    sc = EU["votes"]["scrutins"]
    par = {}
    for cid in ids:
        C, out = EU["candidats"][cid], {}
        for ax in AXES:
            rep, pts = [], 0
            for c in EU["criteres"][ax]:
                r = C[ax].get(c["id"]) or {}
                v = c["valeurs"].get(r.get("position"))
                pts += v["points"] if v else 0
                rep.append({"question": c["lab"], "reponse": v["lab"] if v else "Non précisé",
                            "points": v["points"] if v else None, "texte": r.get("texte") if v else None,
                            "source": r.get("source") if v else None, "auparavant": r.get("evolution")})
            connues = sum(1 for x in rep if x["points"] is not None)
            out[ax] = {"points": pts, "min": axes[ax]["min"], "max": axes[ax]["max"],
                       "connues": connues, "questions": len(rep), "provisoire": connues * 2 < len(rep),
                       "reponses": rep}
        out["russie"] = sorted(C["ukraine"].get("russie") or [], key=lambda x: x.get("date") or "", reverse=True)
        n = {k: 0 for k in VOTE}
        for s in sc:
            v = (s["votes"].get(cid) or {}).get("position")
            if v in n:
                n[v] += 1
        tot = sum(n.values())
        out["votes"] = {**n, "total": tot,
                        "assembleeNationale": any(s["assemblee"] == "AN" and (s["votes"].get(cid) or {}).get("position") in VOTE for s in sc)}
        par[cid] = out
    meta = {"date": EU["updated"], "regle": EU["regle"], "axes": axes,
            "votes": {"regle": EU["votes"]["regle"], "sources": EU["votes"]["sources"],
                      "scrutins": [{"date": s["date"], "assemblee": s["assemblee"], "numero": s.get("numero"),
                                    "intitule": s["intitule"], "resultat": s.get("resultat"), "source": s.get("source"),
                                    "positions": {cid: (s["votes"].get(cid) or {}).get("position", "absent") for cid in ids}}
                                   for s in sc]}}
    return meta, par


def place_txt(a, ax):
    _, gauche, droite = AXES[ax]
    s = (f"{sg(a['points'], 0)} point{'s' if abs(a['points']) > 1 else ''} sur une échelle de "
         f"{sg(a['min'], 0)} ({gauche[0].lower() + gauche[1:]}) à {sg(a['max'], 0)} ({droite[0].lower() + droite[1:]}), "
         f"{a['connues']} réponses connues sur {a['questions']}")
    return s + (" : place provisoire" if a["provisoire"] else "")


def votes_txt(v):
    if not v["total"]:
        return "Aucun élu, ni député ni député européen : pas de vote à relever."
    s = (f"{v['pour']} pour, {v['abstention']} abstention{'s' if v['abstention'] > 1 else ''}, {v['contre']} contre"
         + (f", {v['partage']} partagé{'s' if v['partage'] > 1 else ''}" if v["partage"] else "")
         + f", sur {v['total']} votes où le parti avait des élus")
    return s + ("" if v["assembleeNationale"] else " (au Parlement européen seulement : aucun député)") + "."


def europe_html(c, EUM):
    E = c.get("europeUkraine")
    if not E:
        return ""
    blocs = []
    for ax in AXES:
        a = E[ax]
        lignes = "".join(
            f"<tr><td>{e(r['question'])}</td><td>{e(r['reponse'])}</td><td>"
            + (e(r['texte']) if r['texte'] else "")
            + (f" Source : {lien_source(r['source'])}." if r['source'] else "")
            + (f" Auparavant : {e(r['auparavant'])}" if r['auparavant'] and r['points'] is not None else "")
            + "</td></tr>" for r in a["reponses"])
        blocs.append(f"""    <h3>{e(AXES[ax][0])} : {e(place_txt(a, ax))}</h3>
    <div class="table"><table>
      <thead><tr><th>Question</th><th>Réponse</th><th>Ce qui l'établit</th></tr></thead>
      <tbody>{lignes}</tbody>
    </table></div>""")
    faits = "".join(f"<li><b>{e(fr_date(f.get('date')))}</b> — {e(f['fait'])}"
                    + (f" ({lien_source(f['source'])})" if f.get("source") else "") + "</li>" for f in E["russie"])
    faits = f"    <h3>Son rapport à la Russie : les faits relevés</h3>\n    <ul>{faits}</ul>\n" if faits else ""
    return f"""  <section class="carte">
    <h2>Europe et Ukraine</h2>
    <p>Même grille de questions pour tous les candidats ; « non précisé » signifie qu'aucune source fiable n'a été trouvée. {e(EUM['regle'])}</p>
{chr(10).join(blocs)}
{faits}    <h3>Ce que son parti a voté sur l'Ukraine et la Russie depuis 2022</h3>
    <p>{e(votes_txt(E['votes']))} {e(EUM['votes']['regle'])} Liste des {len(EUM['votes']['scrutins'])} votes : <a href="/comparatif.html#europe">comparatif</a>.</p>
    <p class="src">Positions relevées le {e(fr_date(EUM['date']))}. Votes : {' ; '.join(lien_source(s) for s in EUM['votes']['sources'])}.</p>
  </section>"""


def comparatif_europe_html(R, EUM):
    course = [c for c in R["candidats"] if c.get("europeUkraine")]
    if not course:
        return ""
    course.sort(key=lambda c: c["candidat"].split()[-1])
    ax = EUM["axes"]
    lignes = "".join(
        f"<tr><td><a href=\"/{page_de(c)}\">{e(c['candidat'])}</a></td>"
        + "".join(f"<td class=\"n\">{sg(c['europeUkraine'][k]['points'], 0)}{' *' if c['europeUkraine'][k]['provisoire'] else ''}</td>"
                  f"<td class=\"n\">{c['europeUkraine'][k]['connues']}/{c['europeUkraine'][k]['questions']}</td>" for k in AXES)
        + f"<td class=\"n\">{c['europeUkraine']['votes']['pour']}/{c['europeUkraine']['votes']['total']}</td></tr>"
        for c in course)
    ids = [c["id"] for c in course]
    sig = {c["id"]: c["sigle"] for c in course}
    code = {"pour": "P", "contre": "C", "abstention": "A", "partage": "½"}
    sc = "".join(
        f"<tr><td>{e(fr_date(s['date']))} · {'Assemblée nationale' if s['assemblee'] == 'AN' else 'Parlement européen'} · "
        f"{lien_source({'t': s['intitule'], 'u': (s.get('source') or {}).get('u')})}</td>"
        + "".join(f"<td class=\"n\">{code.get(s['positions'][i], '–')}</td>" for i in ids) + "</tr>"
        for s in EUM["votes"]["scrutins"])
    return f"""  <section class="carte" id="europe">
    <h2>Europe et Ukraine : où se situe chaque candidat</h2>
    <p>Même grille pour tous : {len(ax['europe']['questions'])} questions sur l'Europe ({e(', '.join(q.lower() for q in ax['europe']['questions']))}) et {len(ax['ukraine']['questions'])} sur l'Ukraine ({e(', '.join(q.lower() for q in ax['ukraine']['questions']))}). {e(EUM['regle'])}</p>
    <div class="table"><table>
      <thead><tr><th>Candidat</th><th class="n">Europe ({sg(ax['europe']['min'], 0)} à {sg(ax['europe']['max'], 0)})</th><th class="n">réponses connues</th><th class="n">Ukraine ({sg(ax['ukraine']['min'], 0)} à {sg(ax['ukraine']['max'], 0)})</th><th class="n">réponses connues</th><th class="n">Votes « pour » du parti</th></tr></thead>
      <tbody>{lignes}</tbody>
    </table></div>
    <p class="src">Europe : négatif = moins d'Europe, positif = plus d'Europe. Ukraine : négatif = désengagement, positif = soutien renforcé. * place provisoire : moins de la moitié des réponses sont connues. Le détail de chaque réponse, avec sa source, est sur la page de chaque candidat. Positions relevées le {e(fr_date(EUM['date']))}.</p>
    <h3>Les {len(EUM['votes']['scrutins'])} votes sur l'Ukraine et la Russie depuis 2022</h3>
    <div class="table"><table>
      <thead><tr><th>Vote</th>{''.join(f'<th class="n">{e(sig[i])}</th>' for i in ids)}</tr></thead>
      <tbody>{sc}</tbody>
    </table></div>
    <p class="src">P pour, C contre, A abstention, ½ partagé, – pas d'élu. {e(EUM['votes']['regle'])} Sources : {' ; '.join(lien_source(s) for s in EUM['votes']['sources'])}.</p>
  </section>"""


def europe_llms(c):
    E = c.get("europeUkraine")
    if not E:
        return []
    out = []
    for ax in AXES:
        a = E[ax]
        out.append(f"- {AXES[ax][0]} : {place_txt(a, ax)}")
        for r in a["reponses"]:
            src = f" ({r['source'].get('t')}, {r['source'].get('u')})" if r["source"] else ""
            out.append(f"  - {r['question']} : {r['reponse']}{' — ' + r['texte'] if r['texte'] else ''}{src}")
    if E["russie"]:
        out.append("- Rapport à la Russie, faits relevés :")
        out += [f"  - {fr_date(f.get('date'))} : {f['fait']}" + (f" ({f['source'].get('u')})" if f.get("source") else "") for f in E["russie"]]
    out.append(f"- Votes de son parti sur l'Ukraine et la Russie depuis 2022 : {votes_txt(E['votes'])}")
    return out


def tableau_llms(R):
    """Le tableau des résultats repris dans llms.txt."""
    lignes = ["| Candidat | Déficit 2032 (% PIB) | Dette 2032 (% PIB) | Déficit avec les chiffres du parti | Page |",
              "|---|---|---|---|---|",
              f"| Si rien ne change | {nf(R['siRienNeChange']['deficit2032'])} | {nf(R['siRienNeChange']['dette2032'])} | — | — |"]
    for c in R["candidats"]:
        nom = "Budget apolitique (IA, hors course)" if c["horsCourse"] else f"{c['candidat']} ({c['sigle']})"
        lignes.append(f"| {nom} | {nf(c['deficit2032'])} | {nf(c['dette2032'])} | {nf(c['deficit2032Promesses'])} | {SITE}/{page_de(c)} |")
    return "\n".join(lignes)


def fichiers(jour):
    """Les fichiers à écrire dans web/ : {nom: contenu}."""
    R = resultats()
    R = {"site": SITE, "date": jour, "licence": {"nom": LICENCE[0], "url": LICENCE[1]},
         "citation": f"quipaie2027.fr, données au {jour}", **R}
    for c in R["candidats"]:
        c["page"] = f"{SITE}/{page_de(c)}"
    eu = europe_ukraine(R)
    if eu:
        R["europeUkraine"], par = eu
        for c in R["candidats"]:
            if c["id"] in par:
                c["europeUkraine"] = par[c["id"]]
    out = {"resultats.json": json.dumps(R, ensure_ascii=False, indent=1) + "\n",
           "comparatif.html": page_comparatif(R, jour),
           "llms-full.txt": llms_full(R, jour)}
    for c in R["candidats"]:
        out[page_de(c)] = page_candidat(c, R, jour)[1]
    return out, R
