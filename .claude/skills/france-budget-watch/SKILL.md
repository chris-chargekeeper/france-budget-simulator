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

### 5. Appliquer et reconstruire

```bash
python3 .claude/skills/france-budget-watch/scripts/watch.py appliquer patch.json --write
python3 build.py
```

Le patch et la trace de ce qu'il a changé sont archivés dans `dataset/veille/AAAA-MM-JJ.json`.

### 6. Rendre compte, puis committer

Dites ce qui a été ajouté, ce qui a été révisé et **avec quelle source**, et surtout ce que vous
n'avez pas trouvé. Un jour sans annonce est un résultat, pas un échec — ne comblez pas le vide.

Un commit par relève, sur la branche de travail.

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

## Lancer la veille tous les jours

Rien n'est planifié par défaut. Deux façons de le faire, au choix de l'utilisateur :

- `/loop 1d /france-budget-watch` — dans une session ouverte ;
- le skill `schedule`, pour un agent planifié qui tourne sans session ouverte.

Ne mettez pas en place une planification sans qu'on vous l'ait demandé.
