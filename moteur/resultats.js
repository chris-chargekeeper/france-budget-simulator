/* Les résultats de chaque candidat, calculés comme la page les affiche, pour les lecteurs qui
 * n'exécutent pas de JavaScript (robots des moteurs et des IA) : build.py en tire
 * web/resultats.json, les pages candidat-*.html, comparatif.html et llms-full.txt.
 *   node moteur/resultats.js     écrit le JSON sur la sortie standard
 * Même moteur que le bandeau (moteur/page.js) et que les effets en chaîne (moteur/projection.js),
 * mêmes hypothèses (contexte.json) : aucun chiffre ici que la page ne montre pas.
 */
'use strict';
const fs = require('fs'), path = require('path');
const lire = n => JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'dataset', 'simulateur', n + '.json'), 'utf8'));
const D = {baseline: lire('baseline'), measures: lire('measures'), macro: lire('macro')};
const PARTIS = lire('parties').parties.filter(p => !p.retire), CTX = lire('contexte').indicateurs;
const {creerPage, hypotheses} = require('./page.js');
const {creerMoteur} = require('./projection.js');

const P = hypotheses(D, CTX);
const PAGE = creerPage(D), MOTEUR = creerMoteur(D);
const M = PAGE.M;
const r1 = v => Math.round(v * 10) / 10, r2 = v => Math.round(v * 100) / 100;
const ameliore = m => m.g === 'dep-' || m.g === 'rec+';

const fin = active => PAGE.run(P, active).at(-1);
const traj = active => PAGE.run(P, active).map(x => ({annee: x.y, deficitPct: r1(-x.soldePct), dettePct: r1(x.dettePct)}));
const base = fin({});

function candidat(p) {
  const actR = {}, actP = {};
  for (const id in p.set) {
    const m = M[id], e = p.set[id]; if (!m) continue;
    actR[id] = m[e.sim || 'mid']; actP[id] = e.annonce != null ? e.annonce : actR[id];
  }
  const R = fin(actR), Pm = fin(actP);
  let reel = 0, promis = 0;
  const mesures = Object.keys(actR).map(id => {
    const m = M[id], e = p.set[id], sg = ameliore(m) ? 1 : -1;
    const eff = PAGE.amountAt(m, actR[id], 2032, P, actR);
    reel += sg * eff;
    promis += sg * PAGE.amountAt(m, actP[id], 2032, P, actP);
    return {id, libelle: m.lab, sens: m.g, borne: e.sim || 'mid', retenu: actR[id], bas: m.lo, centre: m.mid, haut: m.hi,
            annonce: e.annonce ?? null, montee: m.ramp, effet2032: r1(sg * eff), note: m.note, sources: m.sources || []};
  }).sort((a, b) => Math.abs(b.effet2032) - Math.abs(a.effet2032));
  const pr = MOTEUR.projeter(P, actR);
  const c = pr.centre.at(-1), f = pr.fourchette.at(-1);
  return {
    id: p.id, candidat: p.candidat, parti: p.nom, sigle: p.sigle, horsCourse: !!p.horsCourse,
    statutCandidature: p.statutCandidature || null, statutChiffrage: p.statut,
    annonce: p.annonce ? {titre: p.annonce.titre || null, texte: p.annonce.texte || null,
                          revendique: p.annonce.revendique ?? null, detaille: p.annonce.detaille ?? null} : null,
    deficit2032: r1(-R.soldePct), dette2032: r1(R.dettePct),
    deficit2032Promesses: r1(-Pm.soldePct), dette2032Promesses: r1(Pm.dettePct),
    effetNet2032: r1(reel), effetNet2032Promesses: r1(promis),
    trajectoire: traj(actR),
    effets2032: {
      pibPct: {centre: r2(c.pib), fourchette: f.pib.map(r2)},
      emplois: {centre: Math.round(c.emploi) * 1000, fourchette: f.emploi.map(x => Math.round(x) * 1000)},
      chomagePts: {centre: r1(c.chomage), fourchette: f.chomage.map(r1)},
      tauxEtatPts: {centre: r2(c.rMkt), fourchette: f.rMkt.map(r2)},
    },
    mesures, sources: p.sources || [],
  };
}

const out = {
  unites: {deficit: '% du PIB (déficit public, signe positif)', dette: '% du PIB', montants: 'Md€ par an, effet sur le solde en 2032 (positif = améliore)',
           emplois: 'écart au « si rien ne change » en 2032', chomage: "points d'écart au « si rien ne change » en 2032",
           pib: "% d'écart au « si rien ne change » en 2032", tauxEtat: "points d'écart du taux d'emprunt de l'État en 2032"},
  hypotheses: {croissance: P.g, inflation: P.infl, derive: P.drift, tauxMarche: P.rmkt, multiplicateur: P.mult, erosion: P.erosion},
  siRienNeChange: {deficit2032: r1(-base.soldePct), dette2032: r1(base.dettePct), trajectoire: traj({})},
  candidats: PARTIS.map(candidat),
};
process.stdout.write(JSON.stringify(out));
