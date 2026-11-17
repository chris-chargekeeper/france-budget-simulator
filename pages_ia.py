"""Pages lisibles sans JavaScript, pour les moteurs de recherche et les assistants d'IA.

Le simulateur calcule tout dans le navigateur : un robot qui n'exécute pas de JavaScript n'y
trouve aucun résultat. build.py appelle ici `node moteur/resultats.js` (le même moteur que la
page, les mêmes hypothèses) et en tire, dans web/ :

  resultats.json         les résultats de chaque candidat, en données ouvertes
  comparatif.html        tous les candidats côte à côte
  candidat-<nom>.html    une page par candidat : déficit, dette, effets, mesures, sources
  llms-full.txt          le tout en texte brut, pour les assistants d'IA

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
        out.append("")
    out += ["## Méthode et limites", "",
            "Chaque mesure est chiffrée par une borne basse, une valeur centrale et une borne haute tirées de travaux "
            "publics (Cour des comptes, HCFP, OFCE, IPP, CAE, Fipeco, Banque de France, rapports parlementaires). "
            "Les scénarios « reconstitués » sont bâtis par le site à partir des positions publiques, faute de chiffrage "
            "publié par le parti. Ordres de grandeur arrondis, pas un modèle macroéconométrique complet.", ""]
    return "\n".join(out)


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
    out = {"resultats.json": json.dumps(R, ensure_ascii=False, indent=1) + "\n",
           "comparatif.html": page_comparatif(R, jour),
           "llms-full.txt": llms_full(R, jour)}
    for c in R["candidats"]:
        out[page_de(c)] = page_candidat(c, R, jour)[1]
    return out, R
