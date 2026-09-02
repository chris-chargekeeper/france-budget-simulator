# Bustes de candidat

Un fichier SVG par variante. `build.py` les nettoie — feuille de style interne retirée, classes et
couleurs en dur supprimées, `currentColor` forcé — puis les injecte dans la page comme symboles, à la
place du marqueur `__AVATARS__` de `template.html`.

## Changer un avatar

Remplacer le fichier, reconstruire. C'est tout.

```bash
cp mon-buste.svg dataset/simulateur/avatars/h.svg
python3 build.py
```

**Le nom du fichier est la valeur du champ.** `h.svg` autorise `"avatar": "h"` dans
`parties.json` ; ajouter `n.svg` autoriserait `"avatar": "n"`. `build.py` refuse un `avatar` sans
fichier correspondant, et `null` retombe sur le monogramme.

Le buste prend la couleur du parti et remplit la pastille, qui le rogne en cercle. Un tracé conçu
pour déborder de son carré fonctionne donc mieux qu'un pictogramme centré avec des marges.

## Attribution

`credits.json` porte l'origine de chaque fichier. `build.py` signale à chaque construction une
licence non renseignée, et la page affiche la réserve dans « D'où viennent les chiffres » — elle bascule
toute seule sur la liste des licences dès qu'elles sont toutes remplies.

> **En attente.** Les deux bustes actuels viennent de [SVG Repo](https://www.svgrepo.com/), qui
> agrège des collections aux licences différentes (CC0, MIT, CC BY…). Les fichiers ne la déclarent
> pas. **À relever sur la page d'origine de chaque icône et à reporter dans `credits.json` avant
> toute publication.**

Ce sont des pictogrammes génériques : aucune ressemblance avec une personne réelle n'est recherchée.
C'est aussi ce qui les rend utilisables là où les portraits de presse ne le sont pas — voir
`../portraits/README.md` pour le cas des photographies.
