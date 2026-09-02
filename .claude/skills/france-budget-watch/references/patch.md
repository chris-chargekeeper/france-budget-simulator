# Format de patch

Un patch est un JSON à trois sections, toutes facultatives. Un patch qui ne contient que des
annonces est le cas courant ; toucher aux partis ou aux mesures est plus rare et exige toujours une
source.

```json
{
  "_comment": "libre, pour dire d'où vient cette relève",
  "releve": "2026-09-03",
  "annonces": [],
  "partis": {},
  "mesures": {}
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

## Ce qui ne passe pas par un patch

Retirer une annonce erronée, changer la nature d'une mesure, corriger un cadrage : ce sont des
modifications de fond. Elles se font à la main, hors veille, et elles se discutent. Le script ne
supprime jamais rien — c'est délibéré.
