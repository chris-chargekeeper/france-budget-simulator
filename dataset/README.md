# Données

Trois familles de fichiers, séparées parce qu'elles n'ont ni la même origine ni les mêmes règles
d'écriture.

```
simulateur/   entrées du simulateur — lues par ../build.py, éditées à la main
sources/      données officielles telles que publiées — jamais modifiées à la main
derive/       JSON et CSV structurés, produits par scripts/ — jamais édités à la main
scripts/      aspiration et consolidation
```

Règle : on n'édite que `simulateur/`. `sources/` est un dépôt d'archives, `derive/` se régénère.

```bash
python3 scripts/scrape_budget_gouv.py --cookies "…"   # (ré)aspire budget.gouv.fr
python3 scripts/build_dataset.py                      # reconstruit derive/
python3 ../build.py                                   # reconstruit ../index.html
```

## simulateur/

`baseline.json`, `measures.json`, `parties.json`, `announcements.json`, `portraits/` — décrits dans
le README à la racine. Ces fichiers raisonnent sur les **administrations publiques** (1 690 Md€) ;
tout ce qui suit décrit le **budget de l'État** (851 Md€ en AE pour 2026). Voir le piège de
périmètre plus bas.

`baseline.json` porte trois blocs alimentés par les sources ci-dessous :

- `officiel` — le constat APU 2024 relevé sur le panorama des finances publiques : agrégats,
  ventilation par sous-secteur, dépenses par fonction (COFOG) et recettes par nature. Il sert à
  vérifier le cadrage `apu`, pas à le remplacer ;
- `etat` — le budget de l'État voté pour 2026, avec le rappel de périmètre ;
- `verification` — le résultat du recoupement, daté.

Chaque poste de `depenses`, `reperes` et `payeurs` porte aussi un champ `icone`, qui pointe sur un
symbole du sprite SVG de `template.html`. `build.py` refuse une icône manquante ou inconnue.

## sources/budget.gouv.fr/

Aspiré le 2 septembre 2026 depuis <https://www.budget.gouv.fr/budget-etat>, sous Licence Ouverte
(Etalab). 3 760 réponses d'API brutes, recensées dans `MANIFEST.json` avec l'URL exacte de chacune.

| dossier | contenu |
|---|---|
| `depenses/{ministere,mission,nature}/{loi}/{année}/` | ventilation des crédits, niveau 1 dans `ae.json` / `cp.json`, niveau 2 dans le sous-dossier `ae/` ou `cp/` (un fichier par ministère, mission ou titre) |
| `operateurs/{loi}/{année}.json` | financement des opérateurs de l'État, avec ressources et part de financement public |
| `smb/{année}/{recettes,depenses,solde}.json` | situation mensuelle budgétaire, cumul mois par mois |
| `synthese/` | chiffres-clés des pages « Budget de l'État » et « Panorama des finances publiques » |
| `export-csv/lfi-2026-ae/` | les CSV téléchargés à la main depuis les dataviz, rangés et nommés |

Couverture : 2018 → 2026, quatre textes financiers — `plf` (projet de loi de finances), `lfi` (loi de
finances initiale), `plrg` (projet de loi relatif aux résultats de la gestion), `plr` (projet de loi
de règlement) — et deux types de crédits, AE (autorisations d'engagement) et CP (crédits de
paiement). Toutes les combinaisons n'existent pas : 2018 n'a que le PLR, et le PLRG des exercices
2019 à 2022 ne porte que les opérateurs.

**L'API.** Non documentée mais stable, et lisible :

```
GET /depenses/{axe}/{annee}/{loi}/{type_budget}/{type_donnee}/json?annee=…&loi_finances=…
```

Les identifiants sont des termes de taxonomie Drupal (`annee=247` vaut 2026) ; le référentiel
complet est dans `MANIFEST.json`. On descend d'un niveau en ajoutant le type de la bulle cliquée :
`&ministere=86764` rend les programmes de ce ministère. Le site est derrière Imperva — il faut
passer au scraper les cookies d'une session navigateur valide, la marche à suivre est dans
l'en-tête du script.

**Les CSV rangés.** Le bouton « télécharger les données » sert toujours le même fichier, si bien
qu'une série de téléchargements arrive en `donnée (1).csv` … `donnée (18).csv`, sans rien qui dise
de quel ministère elle vient. `scripts/ranger_export_csv.py` les rattache en vérifiant que la somme
des programmes de chaque fichier retombe exactement sur le montant publié par l'API, puis les
renomme. Le rapprochement, colonne par colonne, est conservé dans
`export-csv/lfi-2026-ae/MANIFEST.json`. 19 fichiers rangés, 4 doublons supprimés, aucun échec ; seul
« Services du Premier ministre » n'avait pas été téléchargé. Ces CSV n'apportent rien que le brut
n'ait déjà — ils sont gardés comme trace de la collecte manuelle.

## sources/economie.gouv.fr/

`ou-va-argent-impots/` — les repères pédagogiques de <https://www.economie.gouv.fr/aqsmi>,
millésime 2023 (source INSEE) : deux infographies transcrites en texte, seize captures de la vidéo,
et `reperes-2023.json` qui normalise le tout. Périmètre APU, pas budget de l'État.

Les images pèsent 17 Mo pour un contenu entièrement retranscrit dans le JSON : elles sont
supprimables sans perte de données.

## derive/

Produit par `scripts/build_dataset.py` à partir du brut. À ne pas éditer.

| fichier | contenu |
|---|---|
| `budget-etat.json` | 54 millésimes, arborescents : ministères → programmes, missions → programmes, titres → catégories, opérateurs |
| `budget-etat-lfi-2026.json` | le millésime courant seul, 155 Ko, directement exploitable |
| `budget-etat.csv` | 20 693 lignes à plat — une par montant élémentaire, pour un tableur |

Structure d'un millésime :

```json
{"annee": 2026, "loi": "lfi", "type_donnee": "ae",
 "ministeres": [{"id": 86764, "nom": "Justice",
                 "montants": {"43": 12.589503218}, "total": 12.589503218,
                 "programmes": [{"id": 91522, "nom": "Accès au droit et à la justice", …}]}],
 "missions": [...], "titres": [...], "operateurs": [...]}
```

Les clés de `montants` sont des types de budget : `43` budget général, `44` budgets annexes, `45`
comptes d'affectation spéciale, `46` comptes de concours financiers. Un montant `null` et un montant
absent ne disent pas la même chose : `null` est une ligne ouverte sans crédit, l'absence est
l'absence de ligne. Les deux sont conservés tels quels.

## Contrôles

Les axes ministère et mission ventilent les mêmes crédits : leurs totaux coïncident au centime sur
les 54 millésimes. L'axe nature coïncide aussi, sauf de 2019 à 2022 où il manque 1 à 2 Md€, et sauf
2018 où il est absent — lacunes de la source, non corrigées.

Le cadrage APU 2025 de `simulateur/baseline.json` a été recoupé contre le constat officiel 2024 :
dépenses 1 670 → 1 690 (+1,2 %), recettes 1 502 → 1 530 (+1,9 %), dette 3 305 → 3 420 (+3,5 %), PIB
implicite 2 925 → 2 950 (+0,9 %). Aucun agrégat n'a eu besoin d'être corrigé.

## Pièges de périmètre

Trois chiffres circulent et ne se comparent pas :

- **1 670 Md€** — dépenses des administrations publiques constatées en 2024, le périmètre du
  simulateur. La vidéo d'economie.gouv.fr en cite 1 610 pour 2023 : c'est le même agrégat, un an plus tôt.
- **851 Md€** — total des axes ministère / mission en AE pour la LFI 2026. Montants **bruts**.
- **760 Md€** — dépenses totales affichées par la page de synthèse de budget.gouv.fr, en **net**.

L'écart entre les deux derniers est mécanique : les 141 Md€ de remboursements et dégrèvements
d'impôts d'État sont comptés dans le brut et retranchés du net, tandis que les comptes de commerce
et opérations monétaires (~70 Md€) figurent dans la synthèse mais pas dans les axes. En CP 2026 :
budget général brut 593,9 − 141,2 + 6 de fonds de concours ≈ 459 Md€ nets, le chiffre de la page.
