# Portraits des candidats

Déposez ici un fichier par parti, nommé avec l'identifiant du parti dans `data/parties.json` :

```
data/portraits/rn.jpg      data/portraits/ren.jpg
data/portraits/lfi.jpg     data/portraits/hor.jpg
data/portraits/lr.jpg      data/portraits/ps.jpg
                           data/portraits/eco.jpg
```

Formats acceptés : `.jpg`, `.jpeg`, `.png`, `.webp`. `build.py` les encode en data URI et les
injecte dans la page — le site reste un fichier unique, sans requête externe.

## Contrainte de taille

Les cartes affichent un cercle de 48 px : **256 × 256 px suffit largement**. `build.py` avertit
au-delà de 120 Ko par fichier et refuse au-delà de 400 Ko. Sans portrait, la carte retombe
proprement sur un monogramme — le site fonctionne dans les deux cas.

## Contrainte juridique — à lire avant de déposer un fichier

Les portraits de presse (AFP, Reuters, Getty, photographes de presse) sont protégés par le droit
d'auteur. **Ne déposez pas une image trouvée dans un article de presse ou via une recherche
d'images.** Utilisez une source dont la licence autorise explicitement la réutilisation :

- **Wikimedia Commons** — filtrer sur les licences CC BY, CC BY-SA, CC0 ou domaine public.
  Le portrait officiel d'un parlementaire européen y est souvent sous licence libre.
- Une photo diffusée par le parti ou le candidat sous une licence de réutilisation explicite.
- Une photo dont vous détenez les droits.

Pour toute licence CC BY ou CC BY-SA, **l'attribution est obligatoire** : renseignez
`credits.json` à côté des fichiers. Le crédit est affiché dans la section « D'où viennent les
chiffres » de la page ; `build.py` refuse un portrait sans crédit renseigné.

```json
{
  "rn": {"auteur": "Prénom Nom", "licence": "CC BY-SA 4.0",
         "url": "https://commons.wikimedia.org/wiki/File:…"}
}
```

## Pourquoi les fichiers ne sont pas récupérés automatiquement

La politique de sortie réseau de cet environnement bloque `fr.wikipedia.org` et
`upload.wikimedia.org` (refus 403 au niveau du proxy). Aucune image ne peut être téléchargée
depuis une session Claude Code ici : le dépôt des fichiers est une opération manuelle.
