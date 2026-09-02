# Simulateur du budget de la France

Simulateur budgétaire interactif : il projette le solde et la dette des administrations publiques de
2025 à 2032, charge le programme d'un candidat à la présidentielle 2027, et affiche côte à côte ce que
le parti **annonce** et ce que le modèle **produit**.

Hors périmètre de la plateforme EV — projet personnel, isolé dans `experiments/`.

- **[REPRISE.md](REPRISE.md)** — où en est le travail, comment relancer chaque chaîne, ce qui reste
  ouvert. À lire en premier après une interruption.
- **[DECISIONS.md](DECISIONS.md)** — le pourquoi des choix, y compris les options écartées.

## Architecture

```
dataset/simulateur/baseline.json       cadrage APU 2025, ventilations dépenses / recettes / repères
dataset/simulateur/measures.json       catalogue de 41 mesures avec bornes de chiffrage
dataset/simulateur/parties.json        7 partis, candidat pressenti, annonces, mesures rattachées
dataset/simulateur/announcements.json  journal daté et sourcé des annonces médiatiques
dataset/simulateur/avatars/            bustes de candidat, injectés par build.py
dataset/sources/                       données officielles aspirées, jamais éditées
dataset/derive/                        budget de l'État structuré, régénérable
template.html                          page complète ; marqueurs __DATA__, __UPDATED__, __AVATARS__
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

Les cartes affichent un **buste** teinté de la couleur du parti. Deux variantes, `h` et `f`, choisies
par le champ `avatar` de `parties.json` — c'est une donnée explicite, éditable, pas une déduction faite
au rendu ; une valeur absente retombe sur le monogramme.

Les tracés ne sont pas dans le gabarit : ce sont les fichiers de `dataset/simulateur/avatars/<variante>.svg`,
que `build.py` nettoie (feuille de style interne retirée, couleur forcée à `currentColor`) et injecte dans
la page comme symboles SVG. **Remplacer un fichier et relancer `build.py` suffit à changer l'avatar** — le
nom du fichier donne la valeur acceptée par le champ `avatar`, et `build.py` refuse un `avatar` sans
fichier correspondant.

Les bustes actuels viennent de [SVG Repo](https://www.svgrepo.com/) et sont recolorés, pas redessinés.
`dataset/simulateur/avatars/credits.json` porte leur origine. **Leur licence n'y est pas encore
renseignée** : SVG Repo agrège des collections aux licences différentes et le fichier ne la porte pas.
`build.py` le signale à chaque construction, et la page affiche la réserve telle quelle dans « D'où
viennent les chiffres » plutôt que de laisser croire que le point est réglé. À vérifier sur la page
d'origine de chaque icône avant toute publication.

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

`dataset/simulateur/announcements.json` est **alimenté à la main**. Il n'y a pas d'automatisation.

> Les versions précédentes de ce fichier décrivaient un skill `france-budget-watch` dans
> `.claude/skills/`, avec un `watch.py` et sa ligne de commande. Vérification faite, **rien de tout
> cela n'existe** : ni dans le dépôt, ni dans `~/.claude/skills/`, ni ailleurs sur la machine. La
> description a été retirée plutôt que laissée à induire en erreur.

Ce qu'il faudrait construire pour automatiser la veille — collecteur de déclarations chiffrées avec
leurs URL, format de patch et applicateur contrôlé, déclencheur périodique — est détaillé dans
[REPRISE.md](REPRISE.md). Les garde-fous existent déjà côté `build.py`, et vaudraient tels quels pour
ce flux : source obligatoire, date au bon format et jamais dans le futur, contradiction expliquée,
auteur ou fonction renseignés.

## Travailler sur le projet

```bash
python3 build.py                    # reconstruit index.html
python3 build.py --depuis-index     # remonte dans template.html ce qui a été retouché dans index.html
python3 build.py --force            # écrase index.html sans sommation
```

**`index.html` est généré.** L'éditer directement marche jusqu'à la prochaine construction, qui
l'écrase. `build.py` compare le fichier à l'empreinte du dernier qu'il a produit et refuse de
l'écraser s'il a bougé : `--depuis-index` remonte alors les retouches dans le gabarit, exactement ou
pas du tout.

Ce que `build.py` refuse de construire : une mesure inconnue référencée par un parti, une annonce
sans source ou mal datée, une contradiction non expliquée, une ventilation qui ne somme pas à son
agrégat, un poste sans icône ou avec une icône inconnue, un `avatar` sans fichier correspondant.

Le travail vit sur la branche `dataset-officiel-et-vulgarisation`, un commit par étape.

## Limites

Pas de bouclage macroéconomique, multiplicateur unique, érosion d'assiette conventionnelle, incidence
fiscale non modélisée (qui verse ≠ qui supporte), aucune contrainte juridique ni parlementaire.
Détaillées dans la page, section « Méthode, sources et limites ».
