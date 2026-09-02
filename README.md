# Simulateur du budget de la France

Simulateur budgétaire interactif : il projette le solde et la dette des administrations publiques de
2025 à 2032, charge le programme d'un candidat à la présidentielle 2027, et affiche côte à côte ce que
le parti **annonce** et ce que le modèle **produit**.

Hors périmètre de la plateforme EV — projet personnel, isolé dans `experiments/`.

## Architecture

```
dataset/simulateur/baseline.json       cadrage APU 2025, ventilations dépenses / recettes / repères
dataset/simulateur/measures.json       catalogue de 41 mesures avec bornes de chiffrage
dataset/simulateur/parties.json        7 partis, candidat pressenti, annonces, mesures rattachées
dataset/simulateur/announcements.json  journal daté et sourcé des annonces médiatiques
dataset/sources/                       données officielles aspirées, jamais éditées
dataset/derive/                        budget de l'État structuré, régénérable
template.html                          page complète, deux marqueurs : __DATA__ et __UPDATED__
build.py                               valide les données, les injecte, écrit index.html
index.html                             généré — ne pas éditer à la main
```

`dataset/README.md` décrit l'aspiration de budget.gouv.fr et la structure des données officielles.

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

`dataset/simulateur/baseline.json` et `dataset/simulateur/parties.json` portent la liste des sources qui font foi :
`budget.gouv.fr` (budget de l'État, par ministère, données ouvertes), `economie.gouv.fr`,
l'INSEE pour le périmètre APU, et `interieur.gouv.fr` pour les programmes officiels des candidats,
publiés après validation des candidatures par le Conseil constitutionnel.

Deux états sont suivis explicitement dans la page :

- `baseline.verification.etat` — **recoupé** le 2 septembre 2026 contre le constat officiel APU 2024
  aspiré depuis `budget.gouv.fr` (bloc `baseline.officiel`). Les agrégats 2025 tiennent tous dans une
  progression annuelle plausible ; aucun n'a été corrigé. Restent hors recoupement les ventilations
  `depenses` et `recettes`, qui sont des regroupements propres à ce simulateur — la ventilation COFOG
  officielle est disponible dans `baseline.officiel.depensesFonction` pour comparaison.
- `parties.sourceOfficielle.statut` — la page programmes du ministère de l'Intérieur ne publie rien
  pour 2027 à ce jour. Dès qu'elle publie, elle écrase toute reprise de presse et les scénarios
  `reconstitution` sont rebâtis à partir des textes déposés.

**Piège de périmètre** : `budget.gouv.fr` décrit le budget de l'**État** — 760 Md€ de dépenses
totales en loi de finances 2026, dont 459 Md€ pour le seul budget général net. Ce simulateur raisonne
sur les **administrations publiques** (1 690 Md€ : État + sécurité sociale + collectivités). Les deux
chiffres sont justes et ne se comparent pas directement. `baseline.etat` porte le cadrage de l'État,
`baseline.apu` celui des APU, et les deux blocs se disent explicitement incomparables.

## Registre de vulgarisation

La section « Où va l'argent, qui le paie » ouvre sur trois blocs empruntés à la grammaire des vidéos
pédagogiques de Bercy — grand chiffre plein cadre, balance, pastille « sur 1 000 € » — dans une
palette relevée au compte-gouttes sur les captures conservées dans
`dataset/sources/economie.gouv.fr/ou-va-argent-impots/video/` : rouge pour la dépense, bleu pour la
recette, ambre pour l'argent, bleu nuit pour les pastilles chiffrées.

Trois règles tiennent ce registre à sa place :

- il est **réservé aux blocs de vulgarisation**. Les graphiques de série gardent la palette
  d'origine — sept teintes dans une courbe ne passent aucun test de lisibilité pour daltoniens ;
- la balance n'est pas un décor : son inclinaison suit l'écart réel entre dépenses et recettes,
  plafonnée à 14° pour que les plateaux ne se croisent pas. Elle est affichée deux fois, aujourd'hui
  et en 2032 avec le programme chargé, ce que la vidéo d'origine ne peut pas faire ;
- les **icônes viennent des données**, pas du gabarit. Chaque poste de `baseline.depenses`,
  `baseline.reperes` et `baseline.payeurs` porte un champ `icone` qui pointe sur un symbole du sprite
  SVG de `template.html`. `build.py` refuse un poste sans icône ou dont l'icône n'existe pas.

Le sprite compte 17 symboles en tracé seul, 24 × 24, qui héritent de la couleur du texte : une icône
est un repère de lecture, pas une couleur de plus. Aucune illustration de Bercy n'est reproduite —
seule la grammaire visuelle est reprise, les tracés sont originaux.

## Base des annonces

`dataset/simulateur/announcements.json` est une entrée par déclaration publique chiffrée : date (jour, ou mois
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

Les cartes affichent un **buste dessiné**, dans le registre de l'affiche de campagne : silhouette
pleine de trois quarts, coupée par la pastille, teintée de la couleur du parti. Deux variantes, `h`
et `f`, choisies par le champ `avatar` de `parties.json` — c'est une donnée explicite, éditable, pas
une déduction faite au rendu ; une valeur absente retombe sur le monogramme. `build.py` refuse un
`avatar` qui ne correspond à aucun symbole du gabarit.

Ce sont des pictogrammes génériques : aucune ressemblance avec une personne réelle n'est recherchée,
et le col est évidé plutôt que peint, pour que la chemise reste le fond de la pastille en clair
comme en sombre.

Déposer `dataset/simulateur/portraits/<id>.jpg` et renseigner
`dataset/simulateur/portraits/credits.json` suffit à les remplacer par des photos : `build.py` les encode en data
URI, les injecte dans la page et affiche le crédit dans la section « D'où viennent les chiffres ».

Deux contraintes, documentées dans `dataset/simulateur/portraits/README.md` :

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
