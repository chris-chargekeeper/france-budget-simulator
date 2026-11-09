/* Projection macroéconomique 2026-2032 de quipaie2027.fr.
 *
 * Les mêmes équations pour tous les programmes ; chaque coefficient vient de dataset/simulateur/macro.json,
 * où il porte sa source. Les comptes budgétaires (recettes, dépenses, charge, dette) suivent exactement le
 * moteur de la page (run) ; ce qui change :
 *   - chaque mesure a le profil d'effet sur l'activité de son type d'instrument (et non un multiplicateur
 *     unique) ;
 *   - le chômage suit l'activité (loi d'Okun) ;
 *   - les réformes qui ont un chiffrage publié à 5 ans ou moins (âge de la retraite, assurance chômage)
 *     ajoutent leur effet sur l'emploi et la production ;
 *   - la dette fait monter le taux de l'État, qui freine l'activité et renchérit le crédit aux entreprises.
 * Les effets de long terme sans horizon publié avant 2032 ne sont pas mélangés aux chiffres 2032 : ils sont
 * listés à part (apres2032, horsBudget, nonDemontre), et chiffrés en régime permanent par longTerme().
 *
 * Fonctionne dans le navigateur (global creerMoteur) et sous Node (module.exports).
 */
(function (racine) {
  'use strict';

  const DEBUT = 2025, FIN = 2032, START = 2027;

  /** Valeur d'un profil publié à l'horizon h (années depuis l'entrée en vigueur ; 1 = première année).
   *  Ligne droite entre deux horizons publiés, 0 à l'horizon 0, dernière valeur publiée au-delà. */
  function lireProfil(profil, h) {
    if (h <= 0) return 0;
    const pts = Object.keys(profil).map(Number).sort((a, b) => a - b);
    let x0 = 0, y0 = 0;
    for (const x of pts) {
      const y = profil[String(x)];
      if (h <= x) return y0 + (y - y0) * (h - x0) / (x - x0);
      x0 = x; y0 = y;
    }
    return y0;
  }

  function creerMoteur(D) {
    const BL = D.baseline.apu, MC = D.macro, MOT = MC.moteur;
    const M = Object.fromEntries(D.measures.measures.map(m => [m.id, m]));
    const COEF = Object.fromEntries(MC.coefficients.map(c => [c.id, c]));
    const popSerie = (() => {
      const dn = MC.donnees.find(x => x.id === MOT.population.donnee);
      return Object.fromEntries(dn.annees.map((a, i) => [a, dn.series[MOT.population.serie][i]]));
    })();
    const BASE = {pib0: BL.pib, dep0: BL.depenses, rec0: BL.recettes, dette0: BL.dette,
                  charge0: BL.charge, taux0: BL.tauxApparent, refi: BL.partRefinancee};

    /* ---- mêmes règles de montée en charge que la page ---- */
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
    function amountAt(m, val, y, P, active) {
      if (y < START) return 0;
      const ero = (!m.behav) ? 1 : 1 - (P.erosion / 100) * Math.min(1, (y - START + 1) / 3);
      return val * Math.min(1, (y - START + 1) / m.ramp) * ero * cumulCapital(MOT.cumulCapital, M, m, y, P, active);
    }
    /** Impulsion d'une mesure, en Md€ : positive quand elle creuse le déficit (relance). */
    function impulsion(m, a) {
      return (m.g === 'dep+' || m.g === 'rec-') ? a : -a;
    }

    /** Effet sur le PIB (points) d'une relance durable de 1 point de PIB par la mesure, à l'horizon h. */
    function multiplicateur(type, h, borne) {
      const t = MC.types[type];
      if (t.sens === 'ampleur') {
        const c = COEF[t.profilDe[0]];
        return h > 0 ? c[t.borne] : 0;
      }
      let v = lireProfil(t.profil, h);
      if (t.sens === 'hausse') v = -v;          // coefficient publié pour une hausse d'impôt
      // fourchette : rapport des bornes publiées à la valeur centrale, sur le coefficient de première année
      if (borne !== 'v') {
        const c = COEF[t.profilDe[0]];
        const r = [c.lo, c.hi].filter(x => typeof x === 'number').map(x => x / c.valeur);
        if (r.length) v *= borne === 'faible' ? Math.min(1, ...r) : Math.max(1, ...r);
      }
      return v;
    }

    function choisir(o, borne) { return borne === 'v' ? o.v : o[borne]; }

    /** Effet d'un canal d'offre à l'horizon h, dans le sens de la mesure (facteur f). Au centre : le profil
     *  publié. Aux bornes : la valeur publiée la plus basse ou la plus haute à l'horizon du profil, atteinte
     *  en ligne droite comme le profil central. */
    function canal(ca, k, h, f, borne) {
      if (borne === 'v' || ca[k + 'Lo'] == null) return f * lireProfil(ca[k], h);
      const H = Math.max(...Object.keys(ca[k]).map(Number));
      const v = [f * ca[k + 'Lo'], f * ca[k + 'Hi']];
      return (borne === 'lo' ? Math.min(...v) : Math.max(...v)) * Math.min(1, h / H);
    }

    /** Simule une trajectoire. b : bornes {demande: v|faible|fort, okun: v|lo|hi, prime: v|lo|hi,
     *  offre: v|lo|hi}. ref : trajectoire « si rien ne change » avec les mêmes bornes. */
    function simuler(P, active, b, ref) {
      /* Croissance année par année : prévisions publiées jusqu'en 2028 (P.gAn), tendance P.g ensuite. */
      const nomAn = y => (((P.gAn && P.gAn[y] != null) ? P.gAn[y] : P.g) + P.infl) / 100;
      const prime = choisir(MOT.primeDette, b.prime);
      const okun = choisir(MOT.okun, b.okun);
      let pibT = BASE.pib0, depPrim = BASE.dep0 - BASE.charge0, recBase = BASE.rec0;
      let dette = BASE.dette0, taux = BASE.taux0, prix = 1;
      const dette0Pct = BASE.dette0 / BASE.pib0 * 100;
      const hist = {};            // montants par mesure et par année
      const rows = [{y: DEBUT, pib: BASE.pib0, pibT: BASE.pib0, dette: BASE.dette0,
                     dettePct: dette0Pct, rMkt: P.rmkt, solde: BASE.rec0 - BASE.dep0,
                     soldePct: (BASE.rec0 - BASE.dep0) / BASE.pib0 * 100, charge: BASE.charge0}];
      for (let y = DEBUT + 1; y <= FIN; y++) {
        pibT *= (1 + nomAn(y));
        prix *= (1 + P.infl / 100);
        depPrim *= (1 + (P.drift + P.infl) / 100);
        recBase *= (1 + nomAn(y));
        const prev = rows[rows.length - 1];
        const rMkt = P.rmkt + (prime / 100) * Math.max(0, prev.dette / prev.pib * 100 - dette0Pct);
        taux = taux + (rMkt - taux) * BASE.refi;
        const charge = dette * taux / 100;

        // 1. mesures : comptes budgétaires et effet sur la demande
        let dDep = 0, dRec = 0, demande = 0;
        const contrib = {};        // effet de chaque mesure sur le PIB (Md€), demande et offre
        for (const id in active) {
          const m = M[id]; if (!m) continue;
          const a = amountAt(m, active[id], y, P, active);
          if (m.g === 'dep+') dDep += a; else if (m.g === 'dep-') dDep -= a;
          else if (m.g === 'rec+') dRec += a; else if (m.g === 'rec-') dRec -= a;
          (hist[id] = hist[id] || {})[y] = a;
          const type = MC.classement[id].type;
          // superposition de chocs durables : chaque variation d'impulsion agit selon le profil publié
          for (let s = START; s <= y; s++) {
            const dI = impulsion(m, (hist[id][s] || 0) - (hist[id][s - 1] || 0));
            if (dI) {
              const e = dI * multiplicateur(type, y - s + 1, b.demande) * (MC.classement[id].partDemande ?? 1);
              demande += e; contrib[id] = (contrib[id] || 0) + e;
            }
          }
        }
        // 2. taux : écart au « si rien ne change », profil Mésange pour +100 pb
        let effetTaux = 0;
        if (ref) {
          const dr = yy => (yy <= DEBUT ? 0 : (yy === y ? rMkt : rowsGet(rows, yy).rMkt) - rowsGet(ref.rows, yy).rMkt);
          for (let s = DEBUT + 1; s <= y; s++) {
            const ddr = dr(s) - dr(s - 1);
            if (ddr) effetTaux += ddr * lireProfil(MOT.tauxActivite.profil, y - s + 1) / 100 * pibT;
          }
        }
        // 3. offre : réformes avec un chiffrage publié à 5 ans ou moins
        let offrePib = 0, offreEmplois = 0, offreChomage = 0;
        const h = y - START + 1;
        for (const id in active) {
          for (const ca of MC.classement[id].canaux) {
            if (ca.moteur !== 'projection') continue;
            /* L'effet suit l'ampleur retenue : un retour partiel à 62 ans (borne basse) pèse
               moins sur l'emploi qu'un retour complet. Rapport au chiffrage central de la mesure. */
            const ampleur = M[id] && M[id].mid ? active[id] / M[id].mid : 1;
            const f = (ca.facteur == null ? 1 : ca.facteur) * ampleur;
            if (ca.pib) {
              const e = canal(ca, 'pib', h, f, b.offre) / 100 * pibT;
              offrePib += e; contrib[id] = (contrib[id] || 0) + e;
            }
            if (ca.emplois) offreEmplois += canal(ca, 'emplois', h, f, b.offre);
            if (ca.chomage) offreChomage += canal(ca, 'chomage', h, f, b.offre);
          }
        }

        const pib = pibT + demande + effetTaux + offrePib;
        const rec = recBase * (pib / pibT) + dRec;
        const dep = depPrim + dDep + charge;
        const solde = rec - dep;
        dette = dette - solde;

        const uBase = MOT.chomageBase.v[String(Math.min(y, 2028))] ?? MOT.chomageBase.v['2026'];
        const ecartCycle = (demande + effetTaux) / pibT * 100;     // points de PIB
        const chomage = uBase + okun * ecartCycle + offreChomage;
        const actifs = MOT.populationActive.v * 1000;               // milliers
        const emploi = MOT.emploi0.v - (chomage - MOT.chomageBase.v['2026']) / 100 * actifs + offreEmplois;
        const pop = popSerie[y];
        rows.push({y, pib, pibT, demande, effetTaux, offrePib, rec, dep, charge, solde, dette, rMkt, taux,
                   soldePct: solde / pib * 100, dettePct: dette / pib * 100,
                   chomage, emploi, offreEmplois, contrib,
                   pibReelHab: pib / prix / pop * 1000,          // € de 2025 par habitant (Md€ / millions × 1000)
                   creditEntreprises: MOT.creditEntreprises.base + MOT.creditEntreprises.v * (rMkt - P.rmkt),
                   chargeMenageMois: charge / BL.menages / 12 * 1000});
      }
      return {rows};
    }
    function rowsGet(rows, y) { return rows.find(r => r.y === y); }

    const CENTRE = {demande: 'v', okun: 'v', prime: 'v', offre: 'v'};
    function combinaisons() {
      const out = [];
      for (const demande of ['faible', 'fort']) for (const okun of ['lo', 'hi'])
        for (const prime of ['lo', 'hi']) for (const offre of ['lo', 'hi']) out.push({demande, okun, prime, offre});
      return out;
    }

    /** Projection d'un programme : trajectoire centrale, « si rien ne change », et fourchette (min/max
     *  sur toutes les combinaisons des bornes publiées) des écarts au « si rien ne change ». */
    function projeter(P, active) {
      const base = simuler(P, {}, CENTRE, null);
      const scen = simuler(P, active, CENTRE, base);
      const ecarts = (s, r) => s.rows.map((x, i) => {
        const z = r.rows[i];
        return {y: x.y, pib: (x.pib / z.pib - 1) * 100, chomage: (x.chomage ?? 0) - (z.chomage ?? 0),
                emploi: (x.emploi ?? 0) - (z.emploi ?? 0), dettePct: x.dettePct - z.dettePct,
                rMkt: x.rMkt - z.rMkt, soldePct: x.soldePct - z.soldePct,
                chargeMenageMois: (x.chargeMenageMois ?? 0) - (z.chargeMenageMois ?? 0),
                pibReelHab: (x.pibReelHab ?? 0) - (z.pibReelHab ?? 0)};
      });
      const centre = ecarts(scen, base);
      const fourchette = centre.map(c => Object.fromEntries(Object.keys(c).map(k => [k, [c[k], c[k]]])));
      for (const b of combinaisons()) {
        const bb = simuler(P, {}, b, null), ss = simuler(P, active, b, bb);
        ecarts(ss, bb).forEach((e, i) => {
          for (const k in e) if (k !== 'y') {
            fourchette[i][k][0] = Math.min(fourchette[i][k][0], e[k]);
            fourchette[i][k][1] = Math.max(fourchette[i][k][1], e[k]);
          }
        });
      }
      // ce qui n'entre pas dans les chiffres 2032 : listé, par mesure active
      const aPart = [];
      for (const id in active) for (const ca of MC.classement[id].canaux)
        if (ca.moteur !== 'projection') aPart.push({mesure: id, coef: ca.coef, regle: ca.moteur, quoi: ca.quoi});
      const confiance = {};
      for (const id in active) {
        const c = MC.types[MC.classement[id].type].confiance;
        (confiance[c] = confiance[c] || []).push(id);
      }
      return {base: base.rows, scen: scen.rows, centre, fourchette, aPart, confiance};
    }

    /** Effet de long terme d'une relance durable de 1 point de PIB par l'instrument (signe : relance > 0).
     *  borne : 'v' (valeur publiée de référence), 'lo' ou 'hi' (extrêmes publiés). */
    function multiplicateurLT(type, borne) {
      const lt = MC.types[type].longTerme;
      return lt[borne === 'v' ? 'v' : borne];
    }

    /** Régime permanent, une dizaine à une vingtaine d'années après l'entrée en vigueur : les effets de
     *  demande se sont dissipés ou ont laissé leur trace de long terme, les effets d'offre publiés sont
     *  installés. Rapporté au PIB d'aujourd'hui (BL.pib) : un ordre de grandeur, sans date.
     *  Renvoie, pour la valeur de référence et les bornes : écart de PIB (%), emplois (milliers),
     *  chômage (points), et solde public (points de PIB) — mesures à plein régime, plus les recettes
     *  que l'écart de PIB apporte ou retire. */
    function longTerme(P, active) {
      const part = BASE.rec0 / BASE.pib0;
      const calc = borne => {
        let pib = 0, emplois = 0, chomage = 0, budget = 0;
        const contrib = {};
        for (const id in active) {
          const m = M[id]; if (!m) continue;
          // contribution temporaire : plus perçue à long terme, donc ni recette ni effet d'offre
          if (MC.classement[id].temporaire) { contrib[id] = 0; continue; }
          const a = amountAt(m, active[id], 2100, P, active);          // plein régime, érosion comprise
          const pts = a / BASE.pib0 * 100;
          budget += (m.g === 'dep-' || m.g === 'rec+') ? pts : -pts;
          let e = 0, remplace = false;
          const ampleur = m.mid ? active[id] / m.mid : 1;
          for (const ca of MC.classement[id].canaux) {
            const lt = ca.longTerme; if (!lt) continue;
            const f = (ca.facteur == null ? 1 : ca.facteur) * ampleur;
            const lire = k => borne === 'v' ? lt[k] : (lt[k + (borne === 'lo' ? 'Lo' : 'Hi')] ?? lt[k]);
            if (lt.pibParPoint != null) {          // effet publié par point de PIB de la mesure elle-même
              e += impulsion(m, 1) * pts * lire('pibParPoint'); remplace = remplace || !!lt.remplaceType;
            }
            if (lt.pib != null) e += f * lire('pib');
            if (lt.emplois != null) emplois += f * lire('emplois');
            if (lt.chomage != null) chomage += f * lire('chomage');
          }
          if (!remplace) e += impulsion(m, pts) * multiplicateurLT(MC.classement[id].type, borne) * (MC.classement[id].partDemande ?? 1);
          pib += e; contrib[id] = e;
        }
        return {pib, emplois, chomage, soldePct: budget + part * pib, contrib};
      };
      const v = calc('v'), lo = calc('lo'), hi = calc('hi');
      const pibHab = x => x / 100 * BASE.pib0 / popSerie[FIN] * 1000 / Math.pow(1 + P.infl / 100, FIN - DEBUT);
      const f = k => [Math.min(lo[k], hi[k], v[k]), Math.max(lo[k], hi[k], v[k])];
      return {pib: v.pib, emplois: v.emplois, chomage: v.chomage, soldePct: v.soldePct,
              pibReelHab: pibHab(v.pib), contrib: v.contrib,
              fourchette: {pib: f('pib'), pibReelHab: f('pib').map(pibHab), emplois: f('emplois'), chomage: f('chomage'), soldePct: f('soldePct')}};
    }

    return {projeter, simuler, lireProfil, multiplicateur, longTerme};
  }

  if (typeof module !== 'undefined' && module.exports) module.exports = {creerMoteur};
  else racine.creerMoteur = creerMoteur;
})(typeof window !== 'undefined' ? window : globalThis);
