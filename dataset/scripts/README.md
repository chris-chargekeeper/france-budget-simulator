# Scripts

Trois scripts, dans l'ordre où on les enchaîne. Chacun documente son propre fonctionnement dans son
en-tête ; ce fichier ne dit que ce qu'on oublie entre deux sessions.

| Script | Rôle |
|---|---|
| `scrape_budget_gouv.py` | aspire budget.gouv.fr vers `../sources/budget.gouv.fr/` |
| `build_dataset.py` | consolide ce brut en `../derive/` |
| `ranger_export_csv.py` | range et nomme des CSV téléchargés à la main |

## Aspirer budget.gouv.fr

Le site est derrière **Imperva**. Une requête automatique reçoit un challenge JavaScript, pas les
données. Il faut donc lui donner les cookies d'une session de navigateur qui a passé ce challenge.

1. Ouvrir <https://www.budget.gouv.fr/budget-etat> dans un navigateur.
2. **Recharger la page une fois** — le premier chargement résout le challenge, le second sert la
   vraie page.
3. Relever les deux cookies `visid_incap_*` et `incap_ses_*` (onglet Application ou Stockage des
   outils de développement ; `visid_incap_*` est `HttpOnly`, il faut le lire là et pas dans
   `document.cookie`).
4. Les passer au script :

```bash
python3 scrape_budget_gouv.py --cookies "visid_incap_3058694=…; incap_ses_978_…=…"
```

Le script est **reprenable** : un fichier déjà écrit n'est pas redemandé. Après une coupure ou des
cookies expirés, on relance la même commande avec des cookies frais et il termine ce qui manque.
`--force` réaspire tout, `--only depenses|operateurs|smb|synthese` restreint le champ.

Compter une dizaine de minutes pour un passage complet : environ 3 770 requêtes, quatre en
parallèle, avec une pause entre chacune. Si la session expire en cours de route, le script s'arrête
en le disant plutôt que d'écrire des pages de challenge à la place des données.

## Consolider

```bash
python3 build_dataset.py
```

Relit tout `../sources/budget.gouv.fr/` et réécrit `../derive/`. Sans effet de bord, idempotent, ne
demande rien au réseau. À relancer après chaque aspiration.

Le contrôle qui compte est affiché à la fin : les axes ministère et mission ventilent les mêmes
crédits, donc leurs totaux doivent coïncider sur les 54 millésimes.

## Ranger des CSV téléchargés à la main

```bash
python3 ranger_export_csv.py --source /chemin/vers/le/dossier --dry-run
python3 ranger_export_csv.py --source /chemin/vers/le/dossier
```

Rattache chaque fichier à son ministère en vérifiant que la somme de ses programmes retombe sur le
montant publié par l'API — il faut donc que l'aspiration ait déjà eu lieu. Un fichier non rattaché
n'est pas déplacé : il est signalé. Commencer par `--dry-run`.
