/* Le calcul du bandeau de la page (fonction run() de template.html), recopié pour Node :
 * mêmes hypothèses, même trajectoire. Sert à l'essai du moteur et au budget apolitique.
 * Toute modification de run() dans template.html doit être reportée ici, et inversement ;
 * `node moteur/essai.js --verifier` compare les deux moteurs, pas cette copie à la page.
 */
'use strict';

const START = 2027;

/** Hypothèses par défaut de la page, remplacées par les indicateurs de contexte. */
function hypotheses(D, indicateurs) {
  const P = {g: 1.0, infl: 1.6, drift: 0.7, rmkt: 3.4, mult: 0.9, spread: 2, erosion: 25};
  (indicateurs || []).forEach(x => { if (x.hypothese && typeof x.valeur === 'number') P[x.hypothese] = x.valeur; });
  // croissance 2026-2028 : Banque de France, 2027 : consensus (même règle que la page)
  P.gAn = {};
  D.macro.calage.filter(c => /^Banque de France/.test(c.org) && c.pib != null && c.annee >= 2026 && c.annee <= 2028)
    .sort((a, b) => a.date < b.date ? -1 : 1).forEach(c => { P.gAn[c.annee] = c.pib; });
  if (P.g27 != null) { P.gAn[2027] = P.g27; delete P.g27; }
  if (D.macro.moteur && D.macro.moteur.primeDette) P.spread = D.macro.moteur.primeDette.v;
  return P;
}

function creerPage(D) {
  const BL = D.baseline.apu;
  const M = Object.fromEntries(D.measures.measures.map(m => [m.id, m]));
  /* Cumul des impôts sur les très hauts patrimoines (macro.json, moteur.cumulCapital) : même code que
     cumulCapital() dans template.html. */
  function cumulCapital(C, M, m, y, P, active) {
    if (!C || !active || !m || m.behav !== 'capital' || y < START) return 1;
    const Dd = C.deduction, ded = id => (id === Dd.mesure && Dd.si.some(x => active[x] != null)) ? 1 - Dd.part : 1;
    let tot = 0;
    for (const id in active) if (M[id] && M[id].behav === 'capital') tot += active[id] * ded(id);
    let net = 0, bas = 0;
    for (const p of C.paliers) {
      const haut = p.jusqua == null ? Infinity : p.jusqua;
      net += Math.max(0, Math.min(tot, haut) - bas) * p.rendement; bas = haut;
      if (tot <= haut) break;
    }
    const k = tot > 0 ? net / tot : 1;
    const kk = 1 - (1 - k) * Math.min(1, P.erosion / C.erosionRef);
    return ded(m.id) * (1 - (1 - kk) * Math.min(1, (y - START + 1) / 3));
  }
  const CUMUL = D.macro && D.macro.moteur ? D.macro.moteur.cumulCapital : null;
  const amountAt = (m, val, y, P, active) => y < START ? 0 : val * Math.min(1, (y - START + 1) / m.ramp)
    * ((!m.behav) ? 1 : 1 - (P.erosion / 100) * Math.min(1, (y - START + 1) / 3))
    * cumulCapital(CUMUL, M, m, y, P, active);

  /** Trajectoire 2025-2032, comme run() dans la page. */
  function run(P, active) {
    const RHO = 0.6, rows = [];
    const nomAn = y => (((P.gAn && P.gAn[y] != null) ? P.gAn[y] : P.g) + P.infl) / 100;
    let pibBase = BL.pib, depPrim = BL.depenses - BL.charge, recBase = BL.recettes;
    let dette = BL.dette, taux = BL.tauxApparent, gap = 0, impPrev = 0, pibPrev = BL.pib;
    const d0 = BL.dette / BL.pib * 100;
    rows.push({y: 2025, pib: BL.pib, solde: BL.recettes - BL.depenses, dette: BL.dette,
               soldePct: (BL.recettes - BL.depenses) / BL.pib * 100, dettePct: d0});
    for (let y = 2026; y <= 2032; y++) {
      pibBase *= 1 + nomAn(y); depPrim *= 1 + (P.drift + P.infl) / 100; recBase *= 1 + nomAn(y);
      const rMkt = P.rmkt + P.spread / 100 * Math.max(0, dette / pibPrev * 100 - d0);
      taux += (rMkt - taux) * BL.partRefinancee;
      const charge = dette * taux / 100;
      let dDep = 0, dRec = 0, impDep = 0, impTax = 0;
      for (const id in active) {
        const m = M[id]; if (!m) continue;
        const a = amountAt(m, active[id], y, P, active);
        if (m.g === 'dep+') { dDep += a; impDep += a; } else if (m.g === 'dep-') { dDep -= a; impDep -= a; }
        else if (m.g === 'rec+') { dRec += a; impTax -= a; } else { dRec -= a; impTax += a; }
      }
      const imp = P.mult * impDep + P.mult * 0.6 * impTax;
      gap = RHO * gap + (imp - impPrev); impPrev = imp;
      const pib = pibBase + gap;
      const solde = recBase * (pib / pibBase) + dRec - (depPrim + dDep + charge);
      dette -= solde; pibPrev = pib;
      rows.push({y, pib, solde, dette, rMkt, soldePct: solde / pib * 100, dettePct: dette / pib * 100});
    }
    return rows;
  }
  return {run, amountAt, M, START};
}

module.exports = {creerPage, hypotheses, START};
