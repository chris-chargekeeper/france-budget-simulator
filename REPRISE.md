# Reprise de session

À lire en premier après une interruption. Le *pourquoi* des choix est dans [DECISIONS.md](DECISIONS.md) ;
la carte des données est dans [dataset/README.md](dataset/README.md).

## Où en est le travail

Branche de travail : **`dataset-officiel-et-vulgarisation`**, poussée sur
`origin`. `master` est resté au commit initial — **rien n'a encore été fusionné**.

```
acc2426  Recentrage des pastilles du rappel
3782a2b  build.py --depuis-index, et refus d'écraser un index.html retouché
447bc86  Bascule de thème et barre de rappel, remontées dans le gabarit
c06726f  Bustes de candidat : fichiers SVG sources injectés par build.py
ff9d450  Dataset officiel budget.gouv.fr, registre de vulgarisation, bustes
eaaa27e  Initialized                                            ← master
```

Ce qui a été fait, en une phrase chacun :

- **Données officielles.** 3 762 réponses de l'API de budget.gouv.fr aspirées (2018 → 2026, PLF /
  LFI / PLRG / PLR, AE et CP), consolidées en 54 millésimes et un export à plat de 20 789 lignes.
- **Recoupement.** Le cadrage APU 2025 du simulateur a été confronté au constat officiel 2024 :
  tout tient dans une progression plausible, aucun agrégat corrigé.
- **Vulgarisation.** Grandes masses, balance pilotée par l'écart réel, pastilles « sur 1 000 € »,
  17 pictogrammes de poste, bustes de candidat.
- **Ergonomie.** Thème clair par défaut avec bascule mémorisée, barre de rappel du candidat chargé.

## Relancer chaque chaîne

```bash
python3 build.py                    # reconstruit index.html depuis template.html
python3 build.py --depuis-index     # remonte dans le gabarit ce qui a été retouché dans index.html
python3 build.py --force            # écrase index.html sans sommation

cd dataset/scripts
python3 scrape_budget_gouv.py --cookies "…"   # ré-aspire budget.gouv.fr (voir le README du dossier)
python3 build_dataset.py                      # reconstruit dataset/derive/
```

## Ce qui reste ouvert

| Sujet | État |
|---|---|
| Fusion dans `master` | La branche n'est pas fusionnée. Aucune PR ouverte. |
| Licence des bustes | `dataset/simulateur/avatars/credits.json` porte `"licence": null`. SVG Repo agrège des collections aux licences différentes et les fichiers ne la déclarent pas. `build.py` le signale à chaque construction. **À lever avant toute publication.** |
| Skill de veille | **N'existe pas.** Voir ci-dessous. |
| Ventilations `depenses` / `recettes` | Regroupements maison, non recoupés : ils ne correspondent à aucune nomenclature officielle. La COFOG publiée est dans `baseline.officiel.depensesFonction` pour comparaison. |
| Axe « nature » 2018-2022 | Lacunaire à la source (1 à 2 Md€ manquants de 2019 à 2022, absent en 2018). Non corrigé. |
| Poids du dépôt | 44 Mo, dont 17 Mo de captures vidéo entièrement retranscrites dans `reperes-2023.json` — supprimables sans perte. |

## La veille automatique n'existe pas

Le README a longtemps décrit un skill `france-budget-watch` dans `.claude/skills/`, avec un
`watch.py` et sa ligne de commande. **Rien de tout cela n'est présent** : ni dans le dépôt, ni dans
`~/.claude/skills/`, ni ailleurs sur la machine. La section a été corrigée ; il ne reste rien à
exécuter.

Concrètement, `announcements.json` est alimenté à la main. Ce qu'il faudrait construire pour
automatiser, et qui n'existe pas encore :

1. un collecteur — recherche des déclarations chiffrées et des chiffrages publiés, avec leur URL ;
2. un format de patch et un applicateur contrôlé — refus d'une annonce sans source, sans date valide
   ou datée du futur, déduplication, interdiction de toucher aux champs structurels d'une mesure ;
3. un déclencheur périodique.

Les garde-fous de `build.py` (source obligatoire, date au bon format, contradiction expliquée)
existent déjà et vaudraient pour ce flux : ils sont la moitié du travail.

## Pièges qui font perdre du temps

- **`index.html` est généré.** L'éditer directement marche jusqu'à la prochaine construction. Depuis
  `3782a2b`, `build.py` refuse de l'écraser s'il a bougé et renvoie vers `--depuis-index`.
- **Trois périmètres circulent** et ne se comparent pas : 1 670 Md€ (APU 2024, le périmètre du
  simulateur), 851 Md€ (axes ministère / mission en AE, **brut**), 760 Md€ (synthèse budget.gouv.fr,
  **net**). Détail en fin de `dataset/README.md`.
- **budget.gouv.fr est derrière Imperva.** `curl` et les récupérations automatiques reçoivent un
  challenge. Il faut passer au scraper les cookies d'une session de navigateur valide ; la marche à
  suivre est dans `dataset/scripts/README.md`.
- **Les sommes officielles ne bouclent pas** sur les agrégats, et c'est normal : les ventilations par
  sous-secteur sont publiées sans consolidation. Ne pas « corriger ».
