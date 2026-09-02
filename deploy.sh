#!/usr/bin/env bash
# Régénère index.html et l'envoie sur l'hébergement Hostinger (FTP explicite sur TLS).
#
# Identifiants : hPanel > Fichiers > Comptes FTP. Copier deploy.env.example en
# deploy.env (ignoré par git) et le remplir. deploy.env n'est jamais commité.
set -euo pipefail
cd "$(dirname "$0")"

[ -f deploy.env ] || { echo "deploy.env manquant — copier deploy.env.example et le remplir." >&2; exit 1; }
# shellcheck disable=SC1091
. ./deploy.env
: "${FTP_HOST:?}" "${FTP_USER:?}" "${FTP_PASS:?}"
FTP_DIR="${FTP_DIR:-public_html}"

echo "== build =="
python3 build.py

echo "== upload vers ${FTP_HOST}/${FTP_DIR}/ =="
# --ssl-reqd : refuse d'envoyer le mot de passe si le serveur ne propose pas TLS.
curl --fail --silent --show-error --ssl-reqd \
     --user "${FTP_USER}:${FTP_PASS}" \
     --upload-file index.html \
     "ftp://${FTP_HOST}/${FTP_DIR}/index.html"

echo "== en ligne : https://quipaie2027.fr =="
