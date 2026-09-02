# Simulateur du budget de la France

Simulateur budgétaire interactif : il projette le solde et la dette des administrations publiques de
2025 à 2032, charge le programme d'un candidat à la présidentielle 2027, et affiche côte à côte ce que
le parti **annonce** et ce que le modèle **produit**.

Hors périmètre de la plateforme EV — projet personnel, isolé dans `experiments/`.

## Architecture

```
data/baseline.json       cadrage APU 2025, ventilations dépenses / recettes / repères
data/measures.json       catalogue de 41 mesures avec bornes de chiffrage
data/parties.json        7 partis, candidat pressenti, annonces chiffrées, mesures rattachées
data/announcements.json  journal daté et sourcé des annonces médiatiques
template.html            page complète, deux marqueurs : __DATA__ et __UPDATED__
build.py                 valide les données, les injecte, écrit index.html
index.html               généré — ne pas éditer à la main
```

```bash
python3 build.py     # revalide tout et régénère index.html
open index.html      # aucun serveur nécessaire
```

Les seules ressources externes sont les polices Google Fonts.

## Le modèle

- **Tendanciel** — croissance nominale, dérive de la dépense en volume, recettes à élasticité 1.
- **Charge de la dette** — taux apparent convergeant vers le taux de marché au rythme du refinancement
  (~11 % du stock par an), plus une prime de risque indexée sur l'écart de dette.
- **Mesures** — bornes basse / centrale / haute, montée en charge propre à chacune, à partir de 2027.
- **Érosion d'assiette** — les mesures marquées « assiette mobile » (capital, profits) voient leur
  rendement réduit d'un pourcentage réglable, atteint en trois ans. C'est une convention explicite, pas
  une estimation : elle rend le désaccord manipulable au lieu de le trancher en silence.
- **Retour macroéconomique** — multiplicateur appliqué à l'impulsion budgétaire, écart de production se
  refermant à 40 % par an, effet boule de neige sur les intérêts.

## Sources officielles

`data/baseline.json` et `data/parties.json` portent la liste des sources qui font foi :
`budget.gouv.fr` (budget de l'État, par ministère, données ouvertes), `economie.gouv.fr`,
l'INSEE pour le périmètre APU, et `interieur.gouv.fr` pour les programmes officiels des candidats,
publiés après validation des candidatures par le Conseil constitutionnel.

Deux états sont suivis explicitement dans la page :

- `baseline.verification.etat` — le cadrage n'a pas encore été recoupé ligne à ligne contre les
  portails officiels. C'est l'étape 1 bis du skill.
- `parties.sourceOfficielle.statut` — la page programmes du ministère de l'Intérieur ne publie rien
  pour 2027 à ce jour. Dès qu'elle publie, elle écrase toute reprise de presse et les scénarios
  `reconstitution` sont rebâtis à partir des textes déposés.

**Piège de périmètre** : `budget.gouv.fr` décrit le budget de l'**État** (~500 Md€ de dépenses), ce
simulateur raisonne sur les **administrations publiques** (1 690 Md€ : État + sécurité sociale +
collectivités). Les deux chiffres sont justes et ne se comparent pas directement.

## Base des annonces

`data/announcements.json` est une entrée par déclaration publique chiffrée : date (jour, ou mois
quand le jour n'est pas établi), parti, auteur et sa fonction, média où elle a été faite, verbatim,
mesure du catalogue concernée, montant, source (URL obligatoire), `verifie` (la source a-t-elle été
ouverte et lue), et surtout `contredit` :

| valeur | sens |
|---|---|
| `non` | cohérent avec le programme écrit |
| `programme` | contredit le programme, ou lui est juridiquement / arithmétiquement incompatible |
| `annonce` | en tension avec une autre déclaration du même camp |
| `inconnu` | non vérifiable : pas de programme publié, ou détail insuffisant |

`build.py` refuse une contradiction non expliquée dans `ecart`, une source manquante, une date mal
formée, ou une annonce sans auteur ni fonction.

## Comparaison des programmes

La section « Les sept programmes côte à côte » exécute le modèle pour chaque parti et affiche, sur
une échelle commune : la trajectoire du déficit en mini-courbe (avec le tendanciel en gris comme
repère), le déficit 2032 en barre avec le repère des 3 %, la dette et l'effort net. Trié du meilleur
au pire, cliquable pour charger un programme.

Les couleurs de parti ne servent que de pastilles d'identité — jamais de codage de série dans un
graphique, où sept teintes ne passeraient aucun test de lisibilité pour daltoniens.

## Vue simple et mode avancé

La page s'ouvre en **vue simple** : choix du candidat, verdict en langage courant, deux graphiques,
comparaison annonce / calcul, huit mesures principales, répartition des dépenses et des recettes,
veille. Aucun curseur, aucun jargon — les montants sont doublés en euros par habitant et en euros
« sur 1 000 € de dépense publique ».

Le **mode avancé** ouvre les 41 mesures avec leurs fourchettes, les six hypothèses macroéconomiques,
le curseur fin d'érosion d'assiette et le tableau année par année. Le choix est mémorisé dans le
navigateur (`localStorage`, sans effet si le stockage est indisponible).

## Traitement des programmes

Trois chiffres, jamais confondus : ce qu'un parti **revendique**, la part qu'il a **détaillée** poste par
poste, et ce que le simulateur obtient en reprenant ces postes. La case « retenir les montants annoncés
par le parti » substitue les chiffres du parti aux bornes du catalogue, y compris au-delà de la borne
haute — c'est la lecture la plus favorable possible au programme.

Les scénarios marqués `reconstitution` ne sont pas des programmes : ce sont des assemblages du
simulateur pour les partis qui n'ont pas publié de chiffrage 2027. Aucune photographie de candidat n'est
reproduite (droit d'auteur sur les portraits de presse).

## Portraits des candidats

Les cartes affichent un monogramme par défaut. Déposer `data/portraits/<id>.jpg` et renseigner
`data/portraits/credits.json` suffit à les remplacer par des photos : `build.py` les encode en data
URI, les injecte dans la page et affiche le crédit dans la section « D'où viennent les chiffres ».

Deux contraintes, documentées dans `data/portraits/README.md` :

- **Licence** — les portraits de presse sont protégés. Seules des images sous CC BY, CC BY-SA, CC0
  ou domaine public sont utilisables, et l'attribution est obligatoire. `build.py` refuse un
  portrait dont le crédit n'est pas renseigné.
- **Récupération manuelle** — la politique de sortie réseau des sessions Claude Code bloque
  `fr.wikipedia.org` et `upload.wikimedia.org` (403 au niveau du proxy). Le dépôt des fichiers ne
  peut pas être automatisé depuis une session.

L'affichage en data URI est de toute façon obligatoire : le visualiseur d'artefacts bloque les
images externes, quelle que soit leur origine.

## Veille

Le skill `france-budget-watch` (dans `.claude/skills/`) met les données à jour quotidiennement :
recherche des chiffrages nouvellement publiés et des annonces faites dans les médias, rédaction d'un
patch JSON, application contrôlée, reconstruction et republication.

```bash
python3 ../../.claude/skills/france-budget-watch/scripts/watch.py status
python3 ../../.claude/skills/france-budget-watch/scripts/watch.py apply patch.json --write
python3 build.py
```

Le script refuse toute annonce sans URL source, sans date valide ou datée du futur, déduplique, interdit
la modification des champs structurels d'une mesure, et ne supprime jamais rien.

## Limites

Pas de bouclage macroéconomique, multiplicateur unique, érosion d'assiette conventionnelle, incidence
fiscale non modélisée (qui verse ≠ qui supporte), aucune contrainte juridique ni parlementaire.
Détaillées dans la page, section « Méthode, sources et limites ».
