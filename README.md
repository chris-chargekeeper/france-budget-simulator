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
dataset/simulateur/assises.json        lignes du budget qui portent chaque mesure d'économie
dataset/simulateur/avatars/            bustes de candidat, injectés par build.py
dataset/simulateur/marque/             le coq de la marque, et l'icône d'onglet qui en dérive
dataset/sources/                       données officielles aspirées, jamais éditées
dataset/derive/                        budget de l'État structuré, régénérable
template.html                          page complète ; marqueurs __DATA__, __UPDATED__, __AVATARS__,
                                       __FAVICON__, __COQ__
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

## Le trou dans la raquette

Un total annoncé se vérifie deux fois, et la section « Le trou dans la raquette » pose les deux
questions à tous les partis de la même façon :

1. **les postes chiffrés font-ils la somme revendiquée ?** Ce qui reste est *jamais détaillé* — pas un
   chiffrage contestable, mais l'absence de chiffrage ;
2. **chaque poste tient-il dans ce qui existe ?** Le plafond d'un poste est le **plus favorable** des
   deux repères disponibles : la borne haute des chiffrages publiés (`hi` du catalogue), ou les crédits
   que le budget de l'État y consacre aujourd'hui. Le dépassement est ce qui excède ce plafond.

Le trou affiché est la somme des deux. **C'est un minimum**, jamais une estimation haute : à chaque
étape, l'hypothèse retenue est celle qui arrange le parti. Il s'affiche en grand chiffre rouge et en
barre empilée où la part non adossée est hachurée — la hachure porte l'information, pas la seule
couleur, pour rester lisible en noir et blanc et pour un daltonien.

Le test porte sur la **matière** d'une économie annoncée, pas sur le **rendement** d'un impôt nouveau :
savoir ce que rapporte vraiment une taxe sur le capital est une autre question, traitée par l'érosion
d'assiette. Un parti qui n'a rien publié n'a rien à confronter, et la page le dit ainsi — ne pas
chiffrer n'est pas un bon point.

## Assises budgétaires

`dataset/simulateur/assises.json` répond à une question de fait : le poste qu'on promet de couper
existe-t-il dans le budget, et à quelle hauteur ? Une assise pose sous une mesure de redressement les
lignes budgétaires qui portent aujourd'hui la dépense visée.

| champ | sens |
|---|---|
| `dediees` | lignes entièrement comprises dans le périmètre de la mesure |
| `partielles` | lignes dont une part seulement l'est, sans être isolable dans le budget |
| `borne` | `true` si ces lignes plafonnent la mesure ; `false` si elles ne font que situer l'ordre de grandeur |
| `note` | ce que la ligne recouvre, et ce qu'une coupe y rendrait vraiment |
| `hors` | ce que les chiffrages plus élevés ajoutent, et pourquoi ce n'est pas une ligne supprimable |

**Aucun montant n'est saisi à la main.** Chaque ligne porte un `ref` — `mission:…`, `programme:…`,
`titre:…`, `operateurs:financement-public` — que `build.py` résout dans les données officielles
aspirées à **chaque construction**. Un écart de plus de 0,5 % interrompt la construction : la page ne
peut pas affirmer un chiffre que la source ne dit plus.

`borne: false` est le garde-fou du raisonnement. Les concours de l'État aux collectivités passent
pour l'essentiel par un prélèvement sur recettes, absent des crédits des missions : la mission
« Relations avec les collectivités territoriales » situe l'ordre de grandeur mais ne borne rien, et
**aucun dépassement n'est calculé contre elle**. Une mesure sans assise n'est jamais accusée de
dépasser une ligne : seule la fourchette du catalogue lui est opposée.

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

## Coq et icône d'onglet

`dataset/simulateur/marque/coq.svg` est le coq de la page, en bleu-blanc-rouge. Sa géométrie est
celle de `coq-source.svg`, gardé intact à côté : **rien n'est redessiné, seuls les remplissages
changent**, et ils sortent du thème clair — blanc `--surface` pour la tête et le poitrail, rouge
`--dep` pour la crête et l'aile, bleu `--accent` filant vers le bleu nuit `--pastille` pour le corps
et la queue, ambre `--coin` pour le bec et les pattes. L'oiseau se lit blanc, rouge, bleu de gauche à
droite ; le bec et les pattes restent ambre, sans quoi il cesse de se lire comme un coq.

Le coq est injecté deux fois dans la page, toujours depuis ce fichier. À la place du marqueur
`__COQ__`, comme symbole SVG : il tient la gauche du titre dans le bandeau, aligné sur la première
ligne, et passe au-dessus d'elle sous 520 px. Contrairement aux bustes de candidat, il garde ses
couleurs — c'est un dessin, pas un pictogramme.

À la place du marqueur `__FAVICON__`, comme icône d'onglet : il retire les pattes
— à 16 px elles ne pèsent rien et volent la place au reste — recadre sur le buste et le pose sur une
tuile arrondie `--ciel`, qui tient sur un onglet blanc comme sur un onglet sombre. Deux liens sont
écrits dans la page, tous deux en data URI puisque `deploy.sh` ne met en ligne que `index.html` :
le SVG, et `favicon-32.png` en repli pour les navigateurs qui ignorent les icônes SVG. Ce PNG est
régénéré à chaque construction quand `rsvg-convert` est installé (`brew install librsvg`), et repris
du dépôt sinon — il y est commité pour cette raison, pas pour être retouché à la main.

Même réserve de licence que pour les bustes : le fichier vient de [SVG Repo](https://www.svgrepo.com/),
il porte la classe `iconify--noto` — donc la collection Noto de Google, publiée sous Apache 2.0 — mais
la mention n'est pas dans le fichier. `dataset/simulateur/marque/credits.json` le dit, et la page
l'écrit dans « D'où viennent les chiffres ». À confirmer avant d'en faire une marque publique.

## Veille

Le skill `france-budget-watch` (`.claude/skills/france-budget-watch/`) tient à jour la base
d'annonces : il dit ce qu'il faut chercher, valide un patch, l'applique et archive la trace.

```bash
python3 .claude/skills/france-budget-watch/scripts/watch.py etat
python3 .claude/skills/france-budget-watch/scripts/watch.py valider patch.json
python3 .claude/skills/france-budget-watch/scripts/watch.py appliquer patch.json --write
python3 build.py
```

La collecte est faite par Claude, qui lit les sources ; le script ne va rien chercher sur le web. Il
refuse toute annonce sans URL, sans date valide ou datée du futur, déduplique, exige qu'une
contradiction soit expliquée, interdit de modifier les champs structurels d'une mesure — `id`, `g`,
`inst`, `lab`, `ramp`, `behav` décrivent le modèle, pas l'actualité — et ne supprime jamais rien.
Chaque patch appliqué est archivé dans `dataset/veille/` avec la trace de ce qu'il a changé.

Le format de patch est décrit dans
`.claude/skills/france-budget-watch/references/patch.md`.

**Rien n'est planifié.** La veille se lance à la demande, ou se programme avec `/loop` ou le skill
`schedule`.

## Publication

`.github/workflows/publier.yml` met la page en ligne sur `quipaie2027.fr` à chaque poussée sur
`master`. Il reconstruit la page, **refuse de publier si `index.html` ne correspond plus à ses
données**, la contrôle, puis l'envoie par FTP explicite sur TLS.

Quatre secrets à renseigner dans GitHub (Settings › Secrets and variables › Actions) :
`FTP_HOST`, `FTP_USER`, `FTP_PASS`, `FTP_DIR`. `deploy.sh` fait la même chose depuis un poste, avec
`deploy.env`.

La veille ne publie pas : elle pousse sur sa branche, et c'est la fusion dans `master` qui met en
ligne.

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
