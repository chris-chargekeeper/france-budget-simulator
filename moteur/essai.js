/* Essai du moteur de projection : calage du « si rien ne change » sur les prévisions officielles,
 * puis chaque programme, comparé au moteur actuel de la page.
 *   node moteur/essai.js            tableau lisible
 *   node moteur/essai.js --verifier sort en échec si le calage dérive au-delà des tolérances
 */
'use strict';
const fs = require('fs'), path = require('path');
const {creerMoteur} = require('./projection.js');
const lire = n => JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'dataset', 'simulateur', n + '.json'), 'utf8'));
const D = {baseline: lire('baseline'), measures: lire('measures'), macro: lire('macro')};
const PARTIS = lire('parties').parties, CTX = lire('contexte').indicateurs;

// mêmes hypothèses que la page : valeurs par défaut, remplacées par les indicateurs de contexte
const P = {g: 1.0, infl: 1.6, drift: 0.7, rmkt: 3.4, mult: 0.9, spread: 2, erosion: 25};
CTX.forEach(x => { if (x.hypothese && typeof x.valeur === 'number') P[x.hypothese] = x.valeur; });
// croissance 2026-2028 : Banque de France, 2027 : consensus (même règle que la page)
P.gAn = {};
D.macro.calage.filter(c => /^Banque de France/.test(c.org) && c.pib != null && c.annee >= 2026 && c.annee <= 2028)
  .sort((a, b) => a.date < b.date ? -1 : 1).forEach(c => { P.gAn[c.annee] = c.pib; });
if (P.g27 != null) { P.gAn[2027] = P.g27; delete P.g27; }
P.spread = D.macro.moteur.primeDette.v;

const M = Object.fromEntries(D.measures.measures.map(m => [m.id, m]));
const actif = p => Object.fromEntries(Object.entries(p.set).map(([id, e]) => [id, M[id][e.sim || 'mid']]));

/* moteur actuel de la page, recopié pour comparaison (multiplicateur unique) */
function runPage(P, active) {
  const BL = D.baseline.apu, START = 2027;
  const amountAt = (m, val, y) => y < START ? 0 : val * Math.min(1, (y - START + 1) / m.ramp)
    * ((!m.behav) ? 1 : 1 - (P.erosion / 100) * Math.min(1, (y - START + 1) / 3));
  const nomAn = y => (((P.gAn && P.gAn[y] != null) ? P.gAn[y] : P.g) + P.infl) / 100, RHO = 0.6;
  let pibBase = BL.pib, depPrim = BL.depenses - BL.charge, recBase = BL.recettes;
  let dette = BL.dette, taux = BL.tauxApparent, gap = 0, impPrev = 0, pib = BL.pib, out;
  const d0 = BL.dette / BL.pib * 100;
  for (let y = 2026; y <= 2032; y++) {
    pibBase *= 1 + nomAn(y); depPrim *= 1 + (P.drift + P.infl) / 100; recBase *= 1 + nomAn(y);
    const rMkt = P.rmkt + P.spread / 100 * Math.max(0, dette / pib * 100 - d0);
    taux += (rMkt - taux) * BL.partRefinancee;
    const charge = dette * taux / 100;
    let dDep = 0, dRec = 0, impDep = 0, impTax = 0;
    for (const id in active) {
      const m = M[id], a = amountAt(m, active[id], y);
      if (m.g === 'dep+') { dDep += a; impDep += a; } else if (m.g === 'dep-') { dDep -= a; impDep -= a; }
      else if (m.g === 'rec+') { dRec += a; impTax -= a; } else { dRec -= a; impTax += a; }
    }
    const imp = P.mult * impDep + P.mult * 0.6 * impTax;
    gap = RHO * gap + (imp - impPrev); impPrev = imp;
    pib = pibBase + gap;
    const solde = recBase * (pib / pibBase) + dRec - (depPrim + dDep + charge);
    dette -= solde;
    out = {y, soldePct: solde / pib * 100, dettePct: dette / pib * 100, pib, rMkt};
    if (y === 2027) out.y27 = {soldePct: solde / pib * 100, dettePct: dette / pib * 100};
  }
  return out;
}

const moteur = creerMoteur(D);
const f = (v, d = 1) => (v >= 0 ? '+' : '') + v.toFixed(d);
const fr = (a, d = 1) => `[${f(a[0], d)} ; ${f(a[1], d)}]`;

/* 1. calage */
const base = moteur.projeter(P, {}).base;
const r = y => base.find(x => x.y === y);
console.log('Hypothèses :', JSON.stringify(P));
console.log('\n== « Si rien ne change » contre les prévisions officielles ==');
console.log('année  déficit  dette  chômage  OAT   | prévisions (org : déficit / dette / chômage)');
const cal = D.macro.calage;
const ecartsCalage = [];
// La référence est la prévision « à politiques inchangées » (Commission) : les autres incluent des mesures
// déjà décidées (budget 2027) ; elles sont affichées pour information. La zone euro est écartée.
for (const y of [2026, 2027, 2028, 2030]) {
  const x = r(y);
  const fr_ = cal.filter(c => c.annee === y && !c.zone);
  const prev = fr_.map(c => `${c.politiquesInchangees ? '*' : ''}${c.org.split(' (')[0].split(',')[0]} ${c.deficit ?? '–'}/${c.dette ?? '–'}/${c.chomage ?? '–'}`);
  console.log(`${y}   ${(-x.soldePct).toFixed(1)}    ${x.dettePct.toFixed(1)}  ${x.chomage.toFixed(1)}     ${x.rMkt.toFixed(2)} | ${prev.join(' ; ')}`);
  for (const c of fr_.filter(c => c.politiquesInchangees)) {
    if (c.deficit != null) ecartsCalage.push({y, org: c.org, k: 'déficit', ecart: -x.soldePct - c.deficit});
    if (c.dette != null) ecartsCalage.push({y, org: c.org, k: 'dette', ecart: x.dettePct - c.dette});
  }
}
console.log('(* : à politiques inchangées, sert de référence au calage)');

/* 2. programmes */
console.log('\n== 2032, écart au « si rien ne change » : centre [fourchette] ; page actuelle ==');
console.log('parti | PIB % | chômage pt | emplois (milliers) | dette pts | OAT pts | intérêts €/ménage/mois | déficit 2032 nouveau / page');
const pageBase = runPage(P, {});
for (const p of PARTIS) {
  const a = actif(p), res = moteur.projeter(P, a);
  const c = res.centre.at(-1), q = res.fourchette.at(-1), pg = runPage(P, a);
  const s = res.scen.at(-1);
  console.log(`${p.id.padEnd(4)} | ${f(c.pib, 2)} ${fr(q.pib, 2)} | ${f(c.chomage, 2)} ${fr(q.chomage, 2)} | ` +
    `${f(c.emploi, 0)} ${fr(q.emploi, 0)} | ${f(c.dettePct)} ${fr(q.dettePct)} | ${f(c.rMkt, 2)} | ` +
    `${f(c.chargeMenageMois, 0)} | ${(-s.soldePct).toFixed(1)} / ${(-pg.soldePct).toFixed(1)} ` +
    `(PIB page ${f((pg.pib / pageBase.pib - 1) * 100, 2)})`);
  const pibB = res.base.at(-1).pib;
  const top = Object.entries(s.contrib).sort((x, y) => Math.abs(y[1]) - Math.abs(x[1])).slice(0, 4)
    .map(([id, v]) => `${id} ${f(v / pibB * 100, 2)}`).join(', ');
  console.log(`       PIB, principales contributions (pts) : ${top} ; effet des taux ${f(s.effetTaux / pibB * 100, 2)}`);
  const conf = Object.entries(res.confiance).map(([k, v]) => `${k} ${v.length}`).join(', ');
  const ap = [...new Set(res.aPart.map(x => `${x.mesure}:${x.regle}`))].join(' ');
  console.log(`       confiance : ${conf}${ap ? ' ; à part : ' + ap : ''}`);
}

/* 3. sensibilité de la charge d'intérêts : +1 point de taux de marché, comparé à l'AFT et au Trésor */
const chargeDe = rmkt => moteur.simuler({...P, rmkt}, {}, {demande: 'v', okun: 'v', prime: 'v', offre: 'v'}, null).rows;
const c0 = chargeDe(P.rmkt), c1 = chargeDe(P.rmkt + 1);
const sens = h => c1[h].charge - c0[h].charge;
const AFT = {1: 3.4, 2: 8.1, 5: 19.2};
console.log('\nCharge pour +1 pt de taux (Md€) : moteur ' +
  Object.keys(AFT).map(h => `${h} an(s) ${sens(+h).toFixed(1)}`).join(', ') +
  ' ; AFT/Trésor ' + Object.entries(AFT).map(([h, v]) => `${h} an(s) ${v}`).join(', '));

if (process.argv.includes('--verifier')) {
  const erreurs = [];
  // a. calage sur la référence à politiques inchangées
  // Strict jusqu'en 2027 (prévision de printemps 2026) ; au-delà, la seule référence publiée date d'avant la
  // hausse des taux de 2026 et l'écart dépend surtout de la dérive des dépenses supposée par le site :
  // il est signalé, pas bloquant.
  const TOL = {'déficit': 1.0, 'dette': 3.0};
  console.log('Calage :', ecartsCalage.map(e => `${e.y} ${e.k} ${f(e.ecart)}`).join(' ; '));
  ecartsCalage.filter(e => Math.abs(e.ecart) > TOL[e.k]).forEach(e => {
    const msg = `calage ${e.y} ${e.k} : écart ${f(e.ecart)} (tolérance ${TOL[e.k]})`;
    if (e.y <= 2027) erreurs.push(msg); else console.log('  avertissement — ' + msg);
  });
  // b. sans mesure, aucun écart
  const vide = moteur.projeter(P, {});
  if (vide.centre.some(c => Object.entries(c).some(([k, v]) => k !== 'y' && Math.abs(v) > 1e-9)))
    erreurs.push('sans mesure, la projection devrait être identique au « si rien ne change »');
  // c. signes et valeurs publiées des multiplicateurs (dans le sens d'une relance)
  const ATT = [['invest_public', 1, 1.31], ['invest_public', 4, (1.22 + 0.93) / 2], ['tva', 1, 0.32],
               ['benefices', 2, 0.61], ['ir', 2, 0.83], ['patrimoine', 1, 0.5], ['generique_depense', 1, 1.0],
               ['defense', 4, 1.0], ['prestations', 3, 0.95]];
  for (const [t, h, v] of ATT) {
    const m = moteur.multiplicateur(t, h, 'v');
    if (Math.abs(m - v) > 1e-9) erreurs.push(`multiplicateur ${t} à ${h} an(s) : ${m}, attendu ${v}`);
  }
  // d. charge d'intérêts : même ordre de grandeur que l'AFT (±35 %)
  for (const [h, v] of Object.entries(AFT))
    if (Math.abs(sens(+h) / v - 1) > 0.35) erreurs.push(`charge +1 pt à ${h} an(s) : ${sens(+h).toFixed(1)} contre ${v} (AFT)`);
  if (erreurs.length) { console.error('\nÉCHEC :\n  ' + erreurs.join('\n  ')); process.exit(1); }
  console.log('\nVérifications passées.');
}
