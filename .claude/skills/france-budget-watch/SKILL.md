---
name: france-budget-watch
description: Met à jour la base d'annonces du simulateur budgétaire — recherche les déclarations chiffrées et les chiffrages nouvellement publiés par les candidats et partis pour 2027, rédige un patch JSON, le fait valider, l'applique et reconstruit la page. À utiliser pour la veille quotidienne du projet france-budget-simulator, ou quand on demande d'actualiser les annonces, les chiffrages ou les programmes.
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

Affiche, par parti, la date de la dernière annonce relevée et son statut. Les partis marqués
`RECONSTITUTION` n'ont publié aucun chiffrage : ce sont eux qu'il faut surveiller en priorité,
puisque leur scénario est aujourd'hui un assemblage de ce simulateur et non un programme.

### 2. Chercher

Ne cherchez que ce que l'étape 1 désigne, et **depuis les dates qu'elle affiche** — pas plus loin.

Trois familles, par ordre d'autorité :

1. **Les programmes officiels** déposés au ministère de l'Intérieur après validation des
   candidatures. Ils écrasent toute reprise de presse : dès qu'ils paraissent, les scénarios
   `reconstitution` sont à rebâtir à partir des textes, et il faut le signaler plutôt que de bricoler
   un patch.
2. **Les chiffrages publiés** — OFCE, Institut Montaigne, Cour des comptes, IPP, rapports
   parlementaires. Ils font bouger les bornes `lo` / `mid` / `hi` d'une mesure.
3. **Les déclarations chiffrées** en meeting, en plateau, dans la presse. Elles alimentent le journal
   des annonces.

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

```bash
git add dataset/simulateur dataset/veille index.html
git commit -m "[MOD] Veille du AAAA-MM-JJ : …"
git push origin <branche de veille>
```

**Le skill ne publie jamais.** La mise en ligne sur l'hébergement est faite par la CI
(`.github/workflows/publier.yml`), au moment où `master` bouge. Une relève poussée sur la branche de
veille est donc préparée et vérifiée, mais pas publiée : c'est la fusion dans `master` qui met en
ligne, et c'est une décision humaine.

Ne lancez pas `deploy.sh`, ne fusionnez pas dans `master`, n'ouvrez pas de pull request sans qu'on
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
  chercher → patch → valider             sur push vers master :
  → appliquer → build → contrôler          rebuild, refus si la page est périmée,
  → commit + push sur la branche           contrôle, puis envoi FTP sur TLS
                                           vers quipaie2027.fr
                    └──── fusion dans master, à la main ────┘
```

La coupure est volontaire : un agent qui tourne seul tous les jours prépare et vérifie, mais ce qui
part en ligne sur un site public passe par une décision humaine. Pour publier automatiquement à
chaque relève, il suffirait de faire pousser la veille sur `master` — c'est un choix à assumer, pas
un réglage à changer en passant.

## Planification

Rien n'est planifié par défaut. Deux façons de le faire, au choix de l'utilisateur :

- `/loop 1d /france-budget-watch` — dans une session ouverte ;
- le skill `schedule`, pour un agent planifié qui tourne sans session ouverte.

Ne mettez pas en place une planification sans qu'on vous l'ait demandé.
