---
name: france-budget-watch
description: Met à jour la base du simulateur budgétaire — candidatures à la présidentielle 2027 (déclarations, retraits, primaires, nouveaux entrants), déclarations chiffrées, chiffrages indépendants et contexte macroéconomique (taux, notation, prévisions) — rédige un patch JSON, le fait valider, l'applique et reconstruit la page. À utiliser pour la veille quotidienne du projet france-budget-simulator, ou quand on demande d'actualiser les annonces, les chiffrages ou les programmes.
---

# Veille des annonces budgétaires

Le collecteur, c'est vous. Le garde-fou, c'est `scripts/watch.py`. Ne modifiez jamais
`dataset/simulateur/*.json` à la main dans ce cadre : passez par un patch, qui sera refusé s'il est
mal formé et archivé s'il est appliqué.

## Procédure

### 1. Savoir quoi chercher

```bash
python3 .claude/skills/france-budget-watch/scripts/watch.py etat
```

Affiche les candidatures suivies, l'âge de chaque indicateur de contexte, puis, par parti, la
date de la dernière annonce relevée et son statut. Les partis marqués
`RECONSTITUTION` n'ont publié aucun chiffrage : ce sont eux qu'il faut surveiller en priorité,
puisque leur scénario est aujourd'hui un assemblage de ce simulateur et non un programme.

### 2. Chercher

Ne cherchez que ce que l'étape 1 désigne, et **depuis les dates qu'elle affiche** — pas plus loin.

**Chaque jour, d'abord, la liste des candidats.** Les candidatures apparaissent et disparaissent :
déclaration, désignation par une primaire, retrait, ralliement, inéligibilité. Vérifiez pour chaque
candidat suivi que son statut est toujours exact, et cherchez les **nouvelles candidatures qui
pèsent** — au moins environ 3 % dans un sondage récent nommé (institut, date), ou une couverture
nationale soutenue. Un candidat nouveau entre par `nouveaux_partis`, avec un scénario reconstitué à
partir de ses positions publiques et du catalogue existant (`statut: "reconstitution"`) ; un
candidat qui renonce sort par `retrait` — il est masqué de la page, jamais effacé. Le candidat IA
(`horsCourse`) n'est pas un candidat : la veille n'y touche pas.

**Chaque jour aussi, les sondages.** Cherchez le sondage d'intentions de vote au premier tour le
plus récent d'un institut reconnu (Ifop, Ipsos BVA, Elabe, Odoxa, OpinionWay, Harris Interactive
Toluna, Cluster17, Viavoice) dont le terrain est postérieur à celui affiché par `etat`. S'il y en a
un, il entre **entier** par la section `sondage` du patch : il classe les cartes des candidats et
s'affiche dessus. Pas de nouveau sondage, rien à faire.

**Chaque jour aussi, le contexte.** Rafraîchissez les indicateurs de `contexte.json` dont une
valeur plus récente a été publiée : taux de l'OAT à 10 ans et écart avec le Bund (Agence France
Trésor, Banque de France, presse financière datée), taux de dépôt de la BCE, notes de S&P,
Moody's et Fitch (communiqués des agences), prévisions de croissance et d'inflation (FMI, Banque de
France, Commission européenne, INSEE), déficit et dette (INSEE, PLF, avis du Haut Conseil des
finances publiques). Trois indicateurs portent une `hypothese` : leur nouvelle valeur déplace les
projections de **tous** les candidats. Ne les changez que sur une valeur publiée et datée,
jamais sur une moyenne que vous auriez calculée.

Puis trois familles, par ordre d'autorité :

1. **Les programmes officiels** déposés au ministère de l'Intérieur après validation des
   candidatures. Ils écrasent toute reprise de presse : dès qu'ils paraissent, les scénarios
   `reconstitution` sont à rebâtir à partir des textes, et il faut le signaler plutôt que de bricoler
   un patch.
2. **Les chiffrages publiés par des économistes non partisans** — Cour des comptes, Haut Conseil
   des finances publiques, OFCE, IPP, Conseil d'analyse économique, Fipeco, Banque de France,
   FMI, Commission européenne, rapports parlementaires ; Institut Montaigne et Rexecode aussi,
   en sachant leur sensibilité. Ils font bouger les bornes `lo` / `mid` / `hi` d'une mesure. Un
   think tank de parti, ou le chiffrage d'un parti par lui-même, n'en font pas partie.
3. **Les déclarations chiffrées** en meeting, en plateau, dans la presse. Elles alimentent le journal
   des annonces.

**Les grandes interviews politiques, chaque jour.** C'est là que les candidats et leurs
lieutenants lâchent des chiffres, souvent sans reprise écrite. Passez en revue les invités de la
veille et de la nuit dans ces émissions :

| média | émissions à regarder |
|---|---|
| franceinfo | l'invité politique de la matinale (vers 8 h 30), le « 8h30 franceinfo » |
| France Inter | le grand entretien de la matinale (vers 7 h 50 et 8 h 20) |
| TF1 | les invités du 13 h et du 20 h, les interviews politiques du week-end |
| France 2 | « Les 4 Vérités » (7 h 40), les invités du 20 h, « L'Événement » |
| RTL | l'invité de la matinale (7 h 40) ; le Grand Jury RTL / Le Figaro / M6 le dimanche |
| BFMTV / RMC | l'interview politique de la matinale (8 h 30), « BFM Politique » le dimanche |
| Europe 1 / CNews | la grande interview de la matinale (8 h 15) |
| LCI | l'invité politique du matin et du soir |
| Sud Radio | l'invité politique de la matinale (8 h 15) |

Pour savoir qui guetter, la liste des porte-parole, directeurs de campagne et spécialistes du
budget de chaque camp est dans [references/porte-voix.md](references/porte-voix.md) : quand l'un
d'eux est invité, son chiffre engage le candidat. Tenez-la à jour quand une source la contredit.

Ne relevez que ce qui est **chiffré** ou qui engage un programme. La source est la page de
l'émission ou sa retranscription (le replay ou l'article du média lui-même), avec la date,
l'invité et sa fonction ; une reprise par un autre média n'est qu'un indice pour trouver
l'original. Une interview de la matinée du jour sera relevée le lendemain : la relève de 6 h
ne court pas après l'antenne.

**Le Parlement, chaque jour de séance.** Ce qui s'y dit est retranscrit mot pour mot, daté, et
les votes montrent ce que les partis font, pas seulement ce qu'ils disent. À parcourir :

- les **comptes rendus intégraux** des séances de l'Assemblée nationale
  (assemblee-nationale.fr, rubrique comptes rendus) et du Sénat (senat.fr) — surtout pendant
  l'examen du budget (PLF, PLFSS) ;
- les **questions au gouvernement** (mardi et mercredi après-midi à l'Assemblée, mercredi au
  Sénat), où les groupes avancent souvent un chiffre ;
- les **amendements** déposés par les groupes sur le budget, avec leur chiffrage, et les
  **scrutins publics** : un groupe qui vote contre une mesure de son propre programme, c'est
  une `contredit: "programme"` ;
- les auditions de la **commission des finances** (rapporteur général, Cour des comptes, HCFP).

La source est le compte rendu, l'amendement ou la fiche de scrutin officiels, pas leur reprise
dans la presse. Un député n'engage son parti que s'il en est porte-parole, président de groupe
ou responsable du programme ; sinon renseignez `fonction` et rattachez l'annonce au parti
avec prudence, en le disant dans `quoi`.

Pour chaque trouvaille, il faut **une URL**, une date, un auteur ou au moins sa fonction. Sans ça,
n'entrez rien : le script refusera, et il aura raison.

Ouvrez la source et lisez-la avant de porter `"verifie": true`. Une reprise d'agence qui cite un
chiffre n'est pas la source du chiffre.

### 3. Rédiger le patch

Format complet et exemple commenté dans [references/patch.md](references/patch.md). En résumé :

```json
{
  "releve": "2026-09-03",
  "annonces": [ { … une entrée par déclaration … } ],
  "partis":  { "rn": { "annonce": {"revendique": 130}, "source": {"t": "…", "u": "https://…"} } },
  "mesures": { "zucman": { "mid": 9, "source": {"t": "…", "u": "https://…"} } }
}
```

Le champ `contredit` est le cœur du dispositif — c'est lui qui fait la valeur du journal :

| valeur | quand |
|---|---|
| `non` | cohérent avec le programme écrit |
| `programme` | contredit le programme, ou lui est juridiquement / arithmétiquement incompatible |
| `annonce` | en tension avec une autre déclaration du même camp |
| `inconnu` | non vérifiable : pas de programme publié, ou détail insuffisant |

Toute valeur autre que `non` exige une explication dans `ecart`. Ne mettez pas `non` par défaut :
`inconnu` est la valeur honnête quand le parti n'a rien publié.

### 4. Valider

```bash
python3 .claude/skills/france-budget-watch/scripts/watch.py valider patch.json
```

Le script montre ce que le patch ferait, puis refuse en bloc s'il trouve quoi que ce soit. Corrigez
le patch, jamais le script.

### 5. Appliquer, reconstruire, contrôler

```bash
python3 .claude/skills/france-budget-watch/scripts/watch.py appliquer patch.json --write
python3 build.py
python3 .claude/skills/france-budget-watch/scripts/watch.py controler
```

`appliquer` archive le patch et la trace de ce qu'il a changé dans `dataset/veille/AAAA-MM-JJ.json`.

`controler` vérifie que `index.html` dit **exactement** ce que disent les fichiers de données :
marqueurs tous substitués, payload lisible, données embarquées identiques à celles du disque, aucune
annonce sans URL ni mal datée. Il sort en échec si quoi que ce soit a divergé. **S'il échoue, on
s'arrête là** : on ne committe pas une page qui ne correspond plus à ses sources.

### 6. Regarder la page

Ouvrez `index.html` et vérifiez de vos yeux que la relève a atterri : les nouvelles annonces dans la
veille, les chiffres révisés là où ils doivent être, aucune erreur en console. Le contrôle
automatique vérifie la cohérence, pas la lisibilité.

Si un chiffrage révisé a déplacé le déficit 2032 d'un parti, relevez le montant avant et après :
c'est l'information la plus utile du compte rendu.

### 7. Committer, et s'arrêter là

La relève vit sur la branche **`veille`**, jamais ailleurs :

```bash
git fetch origin
git checkout veille 2>/dev/null || git checkout -b veille origin/master
git merge --ff-only origin/master        # repartir de ce qui est en ligne
# … relève, build, contrôle …
git add dataset/simulateur dataset/veille index.html
git commit -m "[MOD] Veille du AAAA-MM-JJ : …"
git push origin veille
```

Si le `merge --ff-only` échoue, la branche a divergé : dites-le et arrêtez-vous, ne forcez rien.

**Le skill ne publie pas lui-même, mais pousser, c'est publier.** Depuis le 30 octobre 2026, la
CI (`.github/workflows/publier.yml`) met en ligne sur quipaie2027.fr chaque relève poussée sur
`veille`, dès qu'elle passe les contrôles, puis avance `master`. Personne ne relit avant la mise en
ligne : le seul filet, c'est `valider`, `controler`, et votre rigueur sur les sources. Dans le doute
sur une source, `"verifie": false` ou rien.

Ne lancez pas `deploy.sh`, ne poussez pas sur `master`, n'ouvrez pas de pull request sans qu'on
vous l'ait demandé.

### 8. Rendre compte

Dites ce qui a été ajouté, ce qui a été révisé et **avec quelle source**, ce que ça déplace dans les
chiffres, et surtout **ce que vous n'avez pas trouvé**. Un jour sans annonce est un résultat, pas un
échec — ne comblez pas le vide, ne remontez pas d'une déclaration ancienne pour avoir quelque chose à
dire.

Terminez par une phrase qui dit si la relève mérite d'être mise en ligne, et pourquoi.

## Ce qu'un patch n'a pas le droit de faire

Le script l'applique, ce n'est pas une question de discipline :

- **Rien sans source.** Une annonce sans URL, mal datée ou datée du futur est refusée.
- **Le modèle ne bouge pas au fil de l'eau.** `id`, `g`, `inst`, `lab`, `ramp`, `behav`, `disp` sont
  intouchables par un patch : ils décrivent le modèle, pas l'actualité. Seules `lo`, `mid`, `hi` et
  `note` peuvent bouger, avec une source, et en respectant `lo ≤ mid ≤ hi`.
- **On n'efface jamais.** Le script ajoute et met à jour. Un chiffre remplacé laisse son ancienne
  valeur dans la trace archivée.
- **Pas de doublon.** Une annonce de même source, même date, même mesure et même montant est ignorée
  silencieusement — le patch peut donc être rejoué sans dégât.

Si une correction sort de ce cadre — retirer une annonce erronée, changer la nature d'une mesure —
c'est une modification de fond : elle se fait à la main, hors veille, et elle se discute.

## La chaîne complète

```
  veille quotidienne (ce skill)          CI (.github/workflows/publier.yml)
  ────────────────────────────           ──────────────────────────────────
  chercher → patch → valider             sur push vers veille :
  → appliquer → build → contrôler          rebuild, refus si la page est périmée,
  → commit + push sur `veille`  ───────►   contrôle, envoi FTP sur TLS,
                                           vérification de la page servie,
                                           puis master ← veille
```

La publication est automatique depuis le 30 octobre 2026, à la demande du propriétaire du site.

## Planification

Relève quotidienne à **06h00 Europe/Paris** : elle balaie la soirée de la veille et la nuit —
meetings, plateaux de fin de soirée, éditions du matin — et elle est prête à l'ouverture de la
journée.

Cadence et horaire arbitrés le 3 septembre 2026. Ne les changez pas, et ne mettez pas en place
d'autre planification, sans qu'on vous l'ait demandé.
