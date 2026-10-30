# Format de patch

Un patch est un JSON à six sections, toutes facultatives. Un patch qui ne contient que des
annonces est le cas courant ; toucher aux partis ou aux mesures est plus rare et exige toujours une
source.

```json
{
  "_comment": "libre, pour dire d'où vient cette relève",
  "releve": "2026-09-03",
  "annonces": [],
  "partis": {},
  "nouveaux_partis": [],
  "mesures": {},
  "contexte": {},
  "sondages": []
}
```

`releve` est la date de la relève, pas celle des annonces. Elle sert à horodater l'archive et à
mettre à jour la date de fraîcheur affichée dans la page.

---

## `annonces` — une entrée par déclaration publique

Section en **ajout seul**. Une annonce déjà présente (même source, même date, même mesure, même
montant) est ignorée sans bruit.

```json
{
  "date": "2026-09-01",
  "parti": "rn",
  "qui": "Marine Le Pen",
  "fonction": "Députée, Rassemblement national",
  "media": "Grand Jury RTL / Le Figaro / M6",
  "quoi": "Chiffre l'économie attendue de la réduction des dépenses liées à l'immigration.",
  "verbatim": "On peut économiser seize milliards par an sur ce poste.",
  "mesure": "immig",
  "montant": 16,
  "type": "economie",
  "source": "https://www.example.fr/article",
  "verifie": true,
  "contredit": "annonce",
  "ecart": "Le contre-budget du parti retenait 10 Md€ pour le même poste en 2024."
}
```

| champ | règle |
|---|---|
| `date` | `AAAA-MM-JJ`, ou `AAAA-MM` si le jour n'est pas établi. Jamais dans le futur, jamais une date qui n'existe pas. |
| `parti` | identifiant connu, ou `null` si la déclaration n'engage aucun parti. |
| `qui` | la personne, ou `null` si l'auteur n'est pas identifié — mais alors `fonction` est obligatoire. |
| `fonction` | le titre de l'auteur. L'un des deux au moins doit être rempli. |
| `media` | où la déclaration a été faite. |
| `quoi` | ce qui a été annoncé, en une phrase. Obligatoire. |
| `verbatim` | citation exacte, ou `null`. À privilégier quand la formulation compte. |
| `mesure` | identifiant du catalogue, ou `null` si l'annonce ne se rattache à aucune mesure. |
| `montant` | en Md€, ou `null`. |
| `type` | `economie`, `recette`, `depense` ou `contexte`. |
| `source` | **URL obligatoire.** Pas d'URL, pas d'entrée. |
| `verifie` | `true` seulement si la source a été ouverte et lue. Dans le doute, `false`. |
| `contredit` | `non`, `programme`, `annonce` ou `inconnu`. |
| `ecart` | obligatoire dès que `contredit` vaut autre chose que `non`. |

---

## `partis` — réviser le chiffrage revendiqué

À n'utiliser que si un parti publie ou révise son chiffrage global.

```json
"partis": {
  "rn": {
    "annonce": {
      "revendique": 130,
      "detaille": 72,
      "titre": "130 Md€ d'économies",
      "texte": "Phrase de présentation reprise sur la carte du candidat."
    },
    "source": {"t": "Programme économique — dossier de presse", "u": "https://www.example.fr/prog"}
  }
}
```

Seuls `titre`, `texte`, `revendique`, `detaille` et `cote` sont modifiables. La source est
obligatoire et vient s'ajouter à la liste des sources du parti si elle n'y est pas déjà.

`revendique` est ce que le parti **annonce** ; `detaille` est la part qu'il a **chiffrée poste par
poste**. Ne jamais gonfler `detaille` pour combler l'écart : c'est précisément cet écart que la page
donne à voir.

---

## `mesures` — réviser les bornes de chiffrage

À n'utiliser que sur publication d'un chiffrage nouveau.

```json
"mesures": {
  "zucman": {
    "lo": 5,
    "mid": 9,
    "hi": 20,
    "note": "Texte refondu si le nouveau chiffrage change la lecture.",
    "source": {"t": "OFCE — Évaluation de l'impôt plancher", "u": "https://www.ofce.fr/…"}
  }
}
```

Modifiables : `lo`, `mid`, `hi`, `note`. Rien d'autre.

**Intouchables par un patch** : `id`, `g` (le sens de la mesure), `inst` (l'instrument), `lab`
(l'intitulé), `ramp` (la montée en charge), `behav` (l'assiette mobile), `disp`. Ces champs décrivent
le modèle, pas l'actualité — les changer par le canal de la veille reviendrait à modifier
silencieusement ce que la page calcule.

Les bornes doivent rester ordonnées : `lo ≤ mid ≤ hi`. Un chiffrage qui sort de la fourchette
actuelle l'élargit, il ne la remplace pas : c'est le désaccord entre chiffrages que les bornes
représentent, pas une incertitude statistique.

La source est ajoutée à la liste `sources` de la mesure, avec la date de relève.

---

## `partis` — suivre les candidatures

Le même bloc `partis` tient aussi l'état des candidatures. Toujours avec une `source`.

```json
"partis": {
  "ps":  {"statutCandidature": "Investi : vainqueur de la primaire (66 %, 11 octobre 2026)",
          "source": {"t": "…", "u": "https://…"}},
  "rn":  {"candidat": "Jordan Bardella", "avatar": "h",
          "statutCandidature": "Candidat, en remplacement de Marine Le Pen",
          "source": {"t": "…", "u": "https://…"}},
  "eco": {"retrait": {"date": "2026-12-13", "motif": "Se retire au profit de Raphaël Glucksmann"},
          "source": {"t": "…", "u": "https://…"}}
}
```

| champ | règle |
|---|---|
| `candidat`, `statutCandidature` | texte libre ; le statut dit où en est la candidature, daté. |
| `avatar` | `h`, `f` ou `null`. |
| `retrait` | `date` et `motif` obligatoires. Le candidat disparaît de la page ; ses annonces et ses données restent. |

Le scénario d'un parti existant (`set`, `statut`) ne se modifie pas par la veille. Le candidat IA
(`horsCourse`) non plus : il est maintenu à la main.

---

## `nouveaux_partis` — une candidature qui pèse

Une entrée par candidat nouveau, au moins environ 3 % dans un sondage récent nommé, ou une
couverture nationale soutenue.

```json
"nouveaux_partis": [{
  "id": "ne", "nom": "Nouvelle Énergie", "sigle": "NE", "candidat": "David Lisnard",
  "avatar": "h", "couleur": "#0E7C86",
  "statutCandidature": "Candidat déclaré (31 mars 2026) ; 6,5 % chez Ipsos (21-22 octobre 2026)",
  "statut": "partiel",
  "annonce": {"titre": "200 Md€ d'économies d'ici 2032", "texte": "…", "revendique": 200, "detaille": 2.5, "cote": "economie"},
  "set": {"effectifs": {"sim": "hi"}, "immigration": {"sim": "lo", "annonce": 2.5}},
  "source": {"t": "…", "u": "https://…"}
}]
```

`id` : minuscules, 2 à 12 caractères, inédit. `couleur` : `#RRGGBB`, distincte des autres.
`statut` : `publie`, `partiel` ou `reconstitution`. `set` : uniquement des mesures du catalogue, avec
`sim` parmi `lo`, `mid`, `hi`. Sans chiffrage publié, `statut: "reconstitution"`, un `set` bâti sur
ses positions publiques constantes, et un `texte` qui le dit.

---

## `contexte` — les indicateurs macroéconomiques

```json
"contexte": {
  "oat10": {"valeur": 4.93, "date": "2026-10-30",
            "detail": "Plus haut à 5,14 % le 22 octobre.",
            "source": {"t": "…", "u": "https://…"}}
}
```

Modifiables : `valeur`, `date`, `note`, `detail`, `source`. L'ancienne valeur part dans `historique`.
Une valeur plus ancienne que celle en base est refusée ; une valeur hors des `bornes` aussi.
Un indicateur nouveau exige en plus `lab`, `unite` et `groupe` (`marches`, `notation`,
`previsions`, `finances`).

`hypothese` et `bornes` ne passent jamais par un patch. Trois indicateurs portent une hypothèse :
`oat10` → taux de marché, `pib27` → croissance, `infl27` → inflation. Les changer déplace les
projections de tous les candidats : seulement sur une valeur publiée et datée.

---

## `sondages` — les intentions de vote au premier tour

La page affiche la **moyenne** des derniers sondages, un par institut, pour qu'aucun institut ni
aucun média commanditaire ne fasse à lui seul le classement. La section est une liste : chaque
sondage **remplace le précédent du même institut**, ou s'ajoute si l'institut n'y est pas encore.
Chaque sondage entre **entier** : une seule hypothèse, tous ses scores.

```json
"sondages": [{
  "institut": "Ipsos BVA", "commanditaire": "Le Parisien",
  "terrain_debut": "2026-10-21", "terrain_fin": "2026-10-22", "date": "2026-10-24",
  "echantillon": 1500,
  "hypothese": "Le Pen candidate, Glucksmann pour le PS, Attal et Philippe présents",
  "scores": {"rn": 33.5, "lfi": 17, "rec": [4, 4.5]},
  "source": {"t": "…", "u": "https://…"}
}]
```

| champ | règle |
|---|---|
| `institut`, `source` | obligatoires ; la source est la page de l'institut ou du média commanditaire, lue |
| `terrain_fin`, `date` | fin du terrain et publication ; jamais plus ancien que le sondage en place du même institut |
| `scores` | en %, de 0 à 60, ou `[bas, haut]` si seule une fourchette est publiée ; uniquement des candidats suivis |
| `hypothese` | celle qui colle le mieux au champ réel (le plus de candidats suivis, les bons titulaires) |

La page ne moyenne que les sondages achevés moins de 21 jours avant le plus récent, et chaque
candidat sur les sondages qui l'ont testé. Ne calculez jamais de moyenne vous-même : la page le fait.
Le sondage remplacé part dans `sondages_historique`.

---

## Ce qui ne passe pas par un patch

Retirer une annonce erronée, changer la nature d'une mesure, corriger un cadrage : ce sont des
modifications de fond. Elles se font à la main, hors veille, et elles se discutent. Le script ne
supprime jamais rien — c'est délibéré.
