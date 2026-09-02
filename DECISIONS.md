# Journal des décisions

Le *pourquoi* des choix, y compris ceux qu'on a écartés — c'est souvent l'option abandonnée qui
manque le plus quand on reprend six mois plus tard. L'état courant du chantier est dans
[REPRISE.md](REPRISE.md).

---

## 1. `dataset/` séparé en trois familles

**Contexte.** `data/` avait été renommé `dataset/`, puis des données officielles y avaient été
déposées à côté des entrées du simulateur. `build.py` lisait encore `data/` : la construction était
cassée.

**Décision.** Trois familles, avec une règle d'écriture chacune :

```
simulateur/   entrées du simulateur — éditées à la main
sources/      officiel tel que publié — jamais modifié
derive/       produit par scripts/ — jamais édité
```

**Pourquoi.** La question « ai-je le droit de corriger ce fichier ? » doit se répondre par
l'emplacement, pas par la mémoire. `build.py` a suivi vers `dataset/simulateur/`.

**Écarté.** Restaurer `data/` à la racine : cela aurait défait le renommage volontaire.

---

## 2. Aspirer budget.gouv.fr par son API interne

**Contexte.** Le site est derrière Imperva : `curl` et les récupérations automatiques reçoivent un
challenge. Les dataviz sont alimentées par une API JSON non documentée.

**Décision.** Passer le challenge dans un vrai navigateur, relever les cookies de session, et les
passer au scraper. L'API et ses identifiants de taxonomie sont documentés dans l'en-tête du script.

**Pourquoi.** Le téléchargement manuel ne donne qu'un millésime à la fois, sans les niveaux de
détail. L'API donne les 54 millésimes et les deux niveaux, avec l'URL exacte de chaque réponse
conservée dans `MANIFEST.json`.

**Conséquence.** Le scraper n'est pas autonome : il lui faut des cookies frais. C'est le prix, et
c'est écrit dans son `--help`.

---

## 3. Rattacher les CSV par la somme, pas par le nom

**Contexte.** Le bouton « télécharger les données » sert toujours le même fichier : 23 CSV nommés
`donnée (1).csv` … `donnée (18).csv`, sans rien qui dise de quel ministère ils viennent.

**Décision.** Rattacher chaque fichier en vérifiant que la somme de ses programmes retombe, colonne
par colonne, sur le montant publié par l'API.

**Pourquoi.** Deviner d'après le contenu aurait marché la plupart du temps. Le rapprochement
arithmétique, lui, se vérifie : 19 fichiers rangés, 4 doublons détectés, 0 échec, et le contrôle est
conservé dans le manifeste. Un fichier non rattaché n'est pas déplacé, il est signalé.

---

## 4. Le brut n'est jamais corrigé

**Contexte.** Les ventilations officielles par sous-secteur somment au-dessus des agrégats
(1 776,8 Md€ contre 1 670,2 pour les dépenses) parce que les transferts entre administrations y
comptent deux fois.

**Décision.** Tout conserver tel quel, et écrire l'écart dans une note.

**Pourquoi.** Un écart expliqué est une information ; un écart lissé est une perte. Même règle pour
les lacunes de l'axe « nature » (2018 absent, 1 à 2 Md€ manquants de 2019 à 2022) et pour la
distinction entre un montant `null` — ligne ouverte sans crédit — et une ligne absente.

---

## 5. Le constat officiel s'ajoute au cadrage, il ne le remplace pas

**Contexte.** Le simulateur part d'un cadrage APU 2025 ; le panorama officiel donne le constat 2024.

**Décision.** Ajouter à `baseline.json` un bloc `officiel` (agrégats, sous-secteurs, COFOG, recettes
par nature) et un bloc `etat`, sans toucher au cadrage.

**Pourquoi.** Changer le millésime de départ aurait déplacé toute la trajectoire 2025-2032. Le bloc
`officiel` sert à *vérifier* : dépenses 1 670 → 1 690 (+1,2 %), recettes 1 502 → 1 530 (+1,9 %),
dette 3 305 → 3 420 (+3,5 %). Tout tient, **aucun agrégat n'a eu besoin d'être corrigé** — et c'est
ce résultat, pas la formalité, qui a fait passer `verification.etat` de « non recoupé » à
« recoupé ».

---

## 6. Un registre de vulgarisation, tenu à sa place

**Contexte.** La page devait devenir lisible par le grand public sans perdre son identité
éditoriale. Référence : les vidéos pédagogiques de Bercy, dont les captures sont dans
`dataset/sources/economie.gouv.fr/`.

**Décision.** Un registre séparé — grand chiffre plein cadre, balance, pastille « sur 1 000 € » —
dans une palette relevée au compte-gouttes sur les captures (rouge dépense, bleu recette, ambre
argent, bleu nuit pastilles), avec trois règles :

1. **cantonné aux blocs de vulgarisation.** Les graphiques de série gardent leur palette : sept
   teintes dans une courbe ne passent aucun test de lisibilité pour daltoniens ;
2. **la balance n'est pas un décor.** Son inclinaison suit l'écart réel, plafonnée à 14° pour que les
   plateaux ne se croisent pas, et elle est affichée deux fois — aujourd'hui et en 2032 avec le
   programme chargé. C'est ce que la vidéo d'origine ne peut pas faire ;
3. **les icônes viennent des données.** Chaque poste porte un champ `icone` ; `build.py` refuse une
   icône manquante ou inconnue.

**Écarté.** Reproduire les illustrations de Bercy — droits d'auteur, et hors de proportion. Les
17 pictogrammes sont originaux.

---

## 7. Les bustes de candidat : des fichiers, pas du gabarit

**Contexte.** Trois tentatives. D'abord des bustes dessinés à la main — mauvais. Puis une recherche
de bibliothèque. Enfin deux fichiers fournis.

**Décision.** Les tracés vivent dans `dataset/simulateur/avatars/<variante>.svg`. `build.py` les
nettoie et les injecte à la place du marqueur `__AVATARS__`. Remplacer un fichier et reconstruire
suffit à changer l'avatar ; le nom du fichier définit la valeur acceptée par le champ `avatar` de
`parties.json`.

**Pourquoi.** Trois allers-retours sur le même sujet ont montré que le tracé devait sortir du
gabarit.

**Écarté**, après comparaison en clair et en sombre à 76 / 46 / 28 px :

| Piste | Pourquoi non |
|---|---|
| Font Awesome `user-tie` | Excellent, mais sans équivalent féminin — les variantes à cheveux sont réservées à l'édition Pro. |
| Remix Icon `men` / `women` | Ce sont les symboles de genre, pas des bustes. |
| Material Symbols `face_3` / `face_4` | Vrai binôme, bien dessiné, Apache 2.0 — mais ce sont des visages, sans costume. |

**Point ouvert.** La licence des fichiers retenus n'est pas déclarée. Voir `REPRISE.md`.

**Note.** Le champ `avatar` est une **donnée explicite et éditable**, pas une déduction faite au
rendu à partir du nom : une valeur absente retombe sur le monogramme.

---

## 8. `index.html` est généré, et le build le défend

**Contexte.** Le fichier généré a été retouché à la main deux fois de suite, y compris pour y ajouter
`<meta charset>` et `<meta name="viewport">` qui manquaient. La construction suivante aurait tout
effacé.

**Décision.** Outiller le cas plutôt que de compter sur la vigilance :

- `build.py --depuis-index` refait le chemin en sens inverse — il recalcule les trois valeurs
  substituées, les retrouve dans `index.html` et remet les marqueurs. **Le report est exact ou il
  échoue**, jamais approximatif ;
- la construction ordinaire compare `index.html` à l'empreinte du dernier fichier produit et refuse
  d'écraser s'il a bougé, en renvoyant vers `--depuis-index` ou `--force`.

**Pourquoi.** Le premier report a été fait à la main ; le second a montré que ça recommencerait.

---

## 9. Thème clair par défaut

**Décision.** Le sombre ne s'applique plus d'après le réglage du système : il faut le demander, et le
choix est mémorisé. Les deux blocs `@media (prefers-color-scheme: dark)` ont disparu au profit du seul
sélecteur `[data-theme="dark"]`. Un script d'amorçage pose l'attribut avant la première peinture, pour
éviter le clignotement.

---

## 10. Une branche, un commit par étape

**Décision.** Tout le travail sur `dataset-officiel-et-vulgarisation`, un commit par étape, pour
pouvoir revenir en arrière étape par étape.

**Réserve honnête.** Le premier commit (`ff9d450`) regroupe trois échanges de travail qui vivaient
encore dans l'arbre : il n'a pas pu être redécoupé proprement après coup. Les suivants sont
découpés.

---

## 11. Le trou dans la raquette : deux tests, et le plafond le plus favorable

**Contexte.** Un parti annonce 125 Md€ d'économies. La page savait déjà afficher ce qu'il revendique,
ce qu'il a détaillé et ce que le modèle en tire — trois chiffres côte à côte, sans jamais dire si les
postes annoncés existent dans le budget. Or c'est la question que tout le monde pose : couper 25 Md€
sur l'immigration, ça se prend où ?

**Décision.** Deux tests, posés à tous les partis de la même façon.

1. **Le compte y est-il ?** Somme des postes chiffrés contre le total revendiqué. L'écart est
   *jamais détaillé* : l'absence de chiffrage, pas un chiffrage contestable.
2. **Le poste existe-t-il ?** Chaque montant annoncé contre un plafond, et le dépassement est ce qui
   passe au-dessus.

Le trou est la somme des deux, affiché en grand chiffre et en barre empilée hachurée.

**Le plafond retenu est le plus favorable au parti** : la borne haute des chiffrages publiés, ou les
crédits inscrits au budget, le plus élevé des deux. Le trou qui en sort est donc un **minimum**. Pour
le RN : 76,4 Md€ sur 125, dont 59,4 jamais détaillés et 17,0 au-delà des plafonds. Pour LFI : 14,0 sur
90, entièrement portés par la taxe sur les transactions financières annoncée à 20 Md€ quand le
chiffrage le plus haut du catalogue en retient 6.

**Pourquoi ce choix.** Un plafond serré donnerait un trou plus spectaculaire et une conclusion
attaquable. Un plafond généreux donne un plancher indiscutable : même en accordant au parti tout ce
qu'on peut lui accorder, il reste ça.

**Périmètre ≠ assiette.** La première version prenait pour plafond le total des lignes citées, quelle
que soit la mesure. La masse salariale de l'État (160,4 Md€) devenait alors le plafond d'une coupe de
5 % des effectifs — un parti aurait pu annoncer 100 Md€ sans être signalé. D'où le champ `role` :
`perimetre` (on supprime la dépense, son total plafonne) contre `assiette` (on en rabote une part, le
total ne plafonne rien).

**Écarté.**

- *Chiffrer nous-mêmes le coût de l'immigration.* Ce serait prendre parti dans une controverse
  ouverte. La page dit ce que le budget contient — mission « Immigration, asile et intégration »,
  2,13 Md€ ; hébergement d'urgence, 3,07 Md€, non isolable — et pourquoi les chiffrages à 20 ou
  40 Md€ ne sont pas des lignes supprimables : ils agrègent des prestations de droit commun versées
  à des personnes en situation régulière, sans déduire ce qu'elles cotisent.
- *Le plus petit plafond des deux.* Voir plus haut : spectaculaire et attaquable.
- *Étendre le test aux recettes nouvelles.* Le rendement d'un impôt n'est pas une ligne du budget.
  Il a déjà sa section, « Et si les riches partent ? ». La page le dit dans le bloc, pour qu'on ne
  lise pas l'absence de test comme un blanc-seing.
- *Saisir les montants à la main.* Chaque ligne d'assise porte un renvoi (`mission:…`, `programme:…`,
  `titre:…`) que `build.py` résout dans les données officielles à chaque construction. Un écart de
  plus de 0,5 % arrête la construction.

**Réserve.** Un parti qui ne publie rien ne peut pas être pris en défaut : les cinq scénarios
`reconstitution` n'ont pas de total à confronter. La page l'écrit — *ce n'est pas un bon point* —
plutôt que de laisser un blanc passer pour un satisfecit.

---

## 12. Le coq : un seul fichier, trois usages

**Contexte.** Un coq récupéré sur SVG Repo, déposé à la racine. La page n'avait ni marque ni icône
d'onglet — l'onglet montrait le globe par défaut.

**Décision.** `dataset/simulateur/marque/coq.svg` est la seule source. Le fichier d'origine reste à
côté sous le nom `coq-source.svg`, intact : `coq.svg` en reprend la géométrie trait pour trait et ne
change que les remplissages, pour que la recoloration soit vérifiable d'un `diff`. `build.py` en tire
le symbole du bandeau (`__COQ__`) et l'icône d'onglet (`__FAVICON__`).

**Les couleurs sortent du thème**, pas d'un tricolore générique : blanc `--surface`, rouge `--dep`,
bleu `--accent` filant vers `--pastille`, ambre `--coin` pour le bec et les pattes. L'oiseau se lit
blanc, rouge, bleu de gauche à droite. Le bec et les pattes restent ambre : sans eux il cesse de se
lire comme un coq.

**Écarté**, après comparaison à 16 / 32 / 64 px sur onglet clair et sur onglet sombre :

| Piste | Pourquoi non |
|---|---|
| L'oiseau entier comme icône | À 16 px les pattes et la marge mangent la moitié du carré ; il ne reste qu'une tache. Le buste seul tient. |
| Tuile bleu nuit | Le corps bleu et la queue s'y noient. |
| Aucune tuile | Sur un onglet sombre, la queue `--pastille` disparaît dans le fond. |
| Un `favicon.svg` écrit à côté | Deux fichiers qui divergent à la première retouche. Le recadrage est calculé à la construction. |
| Des fichiers déposés sur l'hébergement | `deploy.sh` n'envoie qu'`index.html`. D'où les data URI. |
| SVG seul | Safari ignore les icônes SVG. D'où `favicon-32.png`, commité pour que la construction tienne sans `librsvg`, et réécrit quand `rsvg-convert` est là. |

**Point ouvert.** Même réserve que pour les bustes : SVG Repo ne déclare pas la licence. La classe
`iconify--noto` du fichier d'origine désigne la collection Noto de Google, publiée sous Apache 2.0,
mais la mention n'est pas dans le fichier. `credits.json` le dit, la page l'écrit. À confirmer avant
d'en faire une marque publique.
