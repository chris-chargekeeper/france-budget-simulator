/* Le budget apolitique : un scénario calculé par une intelligence artificielle, à partir des chiffrages publiés,
 * avec des règles fixes appliquées mécaniquement — aucun choix au cas par cas.
 *
 *   node moteur/budget-apolitique.js            montre le calcul, n'écrit rien
 *   node moteur/budget-apolitique.js --ecrire   met à jour l'entrée « ia » de parties.json
 *
 * Relancé par la veille chaque jour, après la mise à jour des données : quand un chiffrage, une
 * hypothèse ou un effet publié change, le budget se recalcule de lui-même.
 *
 * Le principe : chercher la meilleure trajectoire d'ensemble pour le pays, pas seulement le plus petit
 * déficit. Le bilan d'un budget additionne, à parts égales :
 *   - l'amélioration du solde public (points de PIB) ;
 *   - l'écart de production (% de PIB), qui porte l'emploi et le revenu par habitant ;
 * mesurés en 2032 (moteur de la carte « effets en chaîne ») et à long terme, 10 à 20 ans
 * (MOTEUR.longTerme), à parts égales aussi. Le chômage n'est pas compté une seconde fois : il suit la
 * production (loi d'Okun).
 *
 * Garde-fous, qui priment sur le bilan :
 *   - aucun des groupes modestes ou moyens (classes moyennes, bas salaires, retraités, sans emploi) ni les
 *     petites entreprises ne perdent plus de 1 % de leur revenu (carte « qui paie, qui reçoit ») ;
 *   - pas de coupe dans l'assurance maladie, pas de hausse générale des prix (TVA) ;
 *   - rien qui distingue les personnes selon leur nationalité ; pas de mesure au rendement possiblement nul ;
 *     pas deux impôts sur la même assiette.
 *
 * La recherche part d'un budget vide et ajoute ou retire, une à une, la mesure qui améliore le plus le
 * bilan, jusqu'à ce qu'aucune n'y parvienne ; les garde-fous sont imposés par une pénalité croissante.
 * Montants : chiffrage central, ou borne basse quand les chiffrages publiés vont du simple au triple ;
 * jamais au plus favorable.
 */
'use strict';
const fs = require('fs'), path = require('path');
const {creerMoteur} = require('./projection.js');
const {creerPage, hypotheses} = require('./page.js');

const DOSSIER = path.join(__dirname, '..', 'dataset', 'simulateur');
const lire = n => JSON.parse(fs.readFileSync(path.join(DOSSIER, n + '.json'), 'utf8'));
const D = {baseline: lire('baseline'), measures: lire('measures'), macro: lire('macro')};
const PARTIES = lire('parties'), CTX = lire('contexte').indicateurs, INC = lire('incidence');
const P = hypotheses(D, CTX);
const PAGE = creerPage(D), MOTEUR = creerMoteur(D);
const M = PAGE.M, AN = 2032;

const nf = (v, d = Math.abs(v) > 0 && Math.abs(v) < 0.95 ? 2 : 1) => v.toLocaleString('fr-FR', {minimumFractionDigits: d, maximumFractionDigits: d});
const sg = (v, d = 1) => (v >= 0 ? '+' : '−') + nf(Math.abs(v), d);

/* Écartées d'office, quel que soit leur effet. */
const PRINCIPE = {
  immigration: "Elle distingue les personnes selon leur nationalité ou leur séjour : écartée au nom du principe d'égalité, quel que soit son rendement.",
  ame: "Elle distingue les personnes selon leur situation de séjour : écartée au nom du principe d'égalité, quel que soit son rendement.",
  ondam: "Garde-fou : pas de coupe dans l'assurance maladie, pour préserver l'accès aux soins.",
  tva1: "Garde-fou : pas de hausse générale des prix ; une hausse de TVA se répercute sur tous les achats."
};
/* Mêmes assiettes ou mesures contraires : une seule par groupe. */
const DOUBLONS = [['isf', 'isfclim', 'zucman'], ['retr62', 'retr60', 'age65'], ['irbaisse', 'csgbaisse']];
/* Garde-fou de pouvoir d'achat : perte maximale, en % du revenu de référence du groupe. */
const PROTEGES = ['moyens', 'smic', 'retraites', 'sansemploi', 'pme'];
const SEUIL = -1;

const GR = Object.fromEntries(INC.groupes.map(g => [g.id, g]));
const INC_ID = Object.fromEntries(INC.mesures.map(x => [x.id, x]));
const gagne = m => m.g === 'dep-' || m.g === 'rec+';
// prudence : pour ce qui rapporte, borne basse quand les chiffrages divergent du simple au triple
const niveau = m => gagne(m) && m.hi > 3 * m.lo ? 'lo' : 'mid';
const actif = ids => Object.fromEntries([...ids].map(id => [id, M[id][niveau(M[id])]]));

/** Effet sur le revenu de chaque groupe, en % de son revenu de référence (négatif : il perd). */
function pouvoirAchat(ids) {
  const G = {};
  for (const id of ids) {
    const m = M[id], k = INC_ID[id]; if (!k) continue;
    const a = PAGE.amountAt(m, m[niveau(m)], AN, P);
    for (const g in k.parts) {
      if (!GR[g] || !GR[g].revenu) continue;
      G[g] = (G[g] || 0) + (gagne(m) ? -1 : 1) * a * k.parts[g] * 1e9 / GR[g].effectif / GR[g].revenu.v * 100;
    }
  }
  return G;
}

const S0 = PAGE.run(P, {}).at(-1);
function bilan(ids, penalite = 0) {
  const a = actif(ids);
  const page = PAGE.run(P, a).at(-1), c = MOTEUR.projeter(P, a).centre.at(-1), L = MOTEUR.longTerme(P, a);
  const pa = pouvoirAchat(ids);
  const depasse = PROTEGES.reduce((t, g) => t + Math.max(0, SEUIL - (pa[g] || 0)), 0);
  const court = (page.soldePct - S0.soldePct) + c.pib, long = L.soldePct + L.pib;
  return {page, c, L, pa, depasse, court, long, note: (court + long) / 2, score: (court + long) / 2 - penalite * depasse};
}

function calculer() {
  const ecartees = {};
  const pool = [];
  for (const m of D.measures.measures) {
    if (PRINCIPE[m.id]) { ecartees[m.id] = PRINCIPE[m.id]; continue; }
    if (!(m.lo > 0)) {
      ecartees[m.id] = `Rendement possiblement nul : les chiffrages publiés vont de ${nf(m.lo)} à ${nf(m.hi)} Md€.`;
      continue;
    }
    pool.push(m.id);
  }
  const conflit = (ids, id) => DOUBLONS.find(g => g.includes(id) && g.some(o => o !== id && ids.has(o)));
  let ids = new Set(), cur;
  for (const pen of [0.3, 1, 3, 10, 100]) {
    cur = bilan(ids, pen);
    for (let tour = 0; tour < 100; tour++) {
      let mieux = null;
      for (const id of pool) {
        const essai = new Set(ids);
        if (essai.has(id)) essai.delete(id);
        else { if (conflit(essai, id)) continue; essai.add(id); }
        const b = bilan(essai, pen);
        if (b.score > cur.score + 1e-6 && (!mieux || b.score > mieux.b.score)) mieux = {essai, b};
      }
      if (!mieux) break;
      ids = mieux.essai; cur = mieux.b;
    }
  }
  if (cur.depasse > 1e-6) throw new Error('garde-fous de pouvoir d\'achat non tenus');

  // pourquoi chaque mesure retenue : ce que le budget perdrait sans elle
  const notes = {}, set = {};
  for (const id of ids) {
    const m = M[id], sans = new Set(ids); sans.delete(id);
    const b = bilan(sans);
    const dS = cur.page.soldePct - b.page.soldePct, dP = cur.c.pib - b.c.pib, dL = cur.L.pib - b.L.pib;
    const niv = niveau(m) === 'lo'
      ? `à sa borne basse (${nf(m.lo)} Md€ par an), par prudence : les chiffrages publiés vont jusqu'à ${nf(m.hi)} Md€`
      : `à son chiffrage central (${nf(m.mid)} Md€ par an)`;
    notes[id] = `Retenue ${niv}. Dans ce budget, elle ${dS >= 0 ? 'améliore' : 'dégrade'} le solde public 2032 de ${nf(Math.abs(dS), 2)} point de PIB ; `
      + `effet sur la production : ${sg(dP, 2)} % en 2032, ${sg(dL, 2)} % à long terme, d'après les effets publiés.`;
    set[id] = {sim: niveau(m)};
  }
  // pourquoi chaque mesure laissée de côté
  const noms = {moyens: 'les classes moyennes', smic: 'les bas salaires', retraites: 'les retraités',
                sansemploi: 'les personnes sans emploi', pme: 'les petites entreprises'};
  for (const id of pool) {
    if (ids.has(id)) continue;
    const m = M[id], g = conflit(ids, id);
    if (g) {
      const o = g.find(x => ids.has(x));
      ecartees[id] = `Fait double emploi avec « ${M[o].lab} », retenue à sa place : elle donne un meilleur bilan d'ensemble.`;
      continue;
    }
    const avec = new Set(ids); avec.add(id);
    const b = bilan(avec);
    const lese = PROTEGES.filter(x => (b.pa[x] || 0) < SEUIL && !((cur.pa[x] || 0) < SEUIL));
    if (lese.length) {
      ecartees[id] = `Garde-fou : ${lese.map(x => noms[x]).join(' et ')} y perdraient plus de 1 % de leur revenu.`;
      continue;
    }
    const dP = b.c.pib - cur.c.pib, dL = b.L.pib - cur.L.pib, dS = b.page.soldePct - cur.page.soldePct;
    const chiffres = `solde public 2032 ${sg(dS, 2)} point de PIB, production ${sg(dP, 2)} % en 2032 et ${sg(dL, 2)} % à long terme`;
    ecartees[id] = dS < 0
      ? `Coûte davantage aux finances publiques qu'elle n'apporte en activité : ${chiffres}.`
      : `Rapporte moins qu'elle ne coûte en activité, surtout à long terme : ${chiffres}.`;
  }
  const somme = g => [...ids].filter(id => M[id].g === g).reduce((t, id) => t + PAGE.amountAt(M[id], M[id][niveau(M[id])], AN, P), 0);
  return {set, notes, ecartees, ids, fin: cur.page, c: cur.c, L: cur.L, pa: cur.pa,
          somme: {dep: somme('dep-'), rec: somme('rec+'), depPlus: somme('dep+'), recMoins: somme('rec-')}};
}

const R = calculer();
const aujourdhui = new Date().toISOString().slice(0, 10);
const CRITERES = [
  "Chercher la meilleure trajectoire d'ensemble pour le pays : l'état des finances publiques et la richesse produite (qui porte l'emploi et le revenu par habitant) comptent à parts égales, en 2032 comme à long terme (10 à 20 ans).",
  "Toutes les mesures chiffrées du simulateur sont permises : économies, recettes, dépenses ou baisses d'impôts. Les effets sur l'activité sont ceux publiés par le Trésor, la Banque de France, la BCE, l'OFCE, France Stratégie, le CAE et le COR.",
  "Garde-fous : ni les classes moyennes, ni les bas salaires, ni les retraités, ni les personnes sans emploi, ni les petites entreprises ne perdent plus de 1 % de leur revenu ; pas de coupe dans l'assurance maladie ; pas de hausse générale des prix.",
  "Chaque mesure à son chiffrage central, ou à sa borne basse quand les chiffrages publiés vont du simple au triple ; jamais au plus favorable.",
  "Écarter les mesures dont le rendement peut être nul, celles qui distinguent les personnes selon leur nationalité (principe d'égalité), et les doublons.",
  "Le calcul ne juge que les effets sur les finances publiques et sur l'activité : la sécurité, l'environnement ou la justice sociale relèvent d'autres choix, qu'il ne tranche pas.",
  "Recalculer chaque jour, avec les chiffrages et les prévisions du moment."
];
const texte = `Ce budget n'est le programme de personne. Il est calculé par une intelligence artificielle, qui cherche `
  + `la meilleure trajectoire d'ensemble pour le pays, et pas seulement le plus petit déficit : elle applique les règles ci-dessous `
  + `aux ${D.measures.measures.length} mesures chiffrées du simulateur, aux mêmes chiffrages que pour les candidats, sans aucun choix au cas par cas. `
  + `Il est recalculé chaque jour. Résultat : ${nf(R.somme.dep)} Md€ d'économies et ${nf(R.somme.rec)} Md€ de recettes en 2032`
  + (R.somme.depPlus || R.somme.recMoins ? `, dont une partie rendue en ${[R.somme.depPlus ? `dépenses (${nf(R.somme.depPlus)} Md€)` : '', R.somme.recMoins ? `baisses d'impôts (${nf(R.somme.recMoins)} Md€)` : ''].filter(Boolean).join(' et ')}` : '')
  + `, pour un déficit de ${nf(-R.fin.soldePct)} % du PIB en 2032 et une production ${R.L.pib >= 0 ? 'plus élevée' : 'plus faible'} à long terme (${sg(R.L.pib, 1)} %). `
  + `Avec les effets publiés, on ne peut pas à la fois ramener vite le déficit sous 3 % et préserver l'activité : ce budget cherche l'équilibre entre les deux. `
  + `Les règles elles-mêmes sont des conventions : elles sont écrites ici pour être discutées.`;

console.log(`Budget apolitique au ${aujourdhui} : déficit 2032 ${nf(-R.fin.soldePct)} %, dette ${nf(R.fin.dettePct, 0)} %, `
  + `PIB/hab 2032 ${sg(R.c.pibReelHab, 0)} €, long terme ${sg(R.L.pib, 2)} % (${sg(R.L.pibReelHab, 0)} €/hab)`);
console.log(`  économies ${nf(R.somme.dep)} Md€, recettes ${nf(R.somme.rec)} Md€, dépenses ${nf(R.somme.depPlus)} Md€, baisses d'impôts ${nf(R.somme.recMoins)} Md€`);
for (const id in R.set) console.log(`  + ${id.padEnd(13)} ${R.notes[id]}`);
for (const id in R.ecartees) console.log(`  − ${id.padEnd(13)} ${R.ecartees[id]}`);

if (process.argv.includes('--ecrire')) {
  const ia = PARTIES.parties.find(p => p.horsCourse);
  const sansDate = x => JSON.stringify({...x, calcul: {...(x.calcul || {}), date: null}});
  const ancien = sansDate(ia), dateAvant = ia.calcul && ia.calcul.date;
  Object.assign(ia, {
    candidat: "Le budget apolitique",
    nom: "Calculé par une intelligence artificielle",
    statutCandidature: "Pas un candidat : un budget calculé par l'intelligence artificielle, à partir des chiffrages publiés",
    criteres: CRITERES, set: R.set, pourquoi: R.notes, ecartees: R.ecartees,
    calcul: {date: aujourdhui, deficit2032: +(-R.fin.soldePct).toFixed(2), dette2032: +R.fin.dettePct.toFixed(1),
             economies: +R.somme.dep.toFixed(1), recettes: +R.somme.rec.toFixed(1),
             depenses: +R.somme.depPlus.toFixed(1), baissesImpots: +R.somme.recMoins.toFixed(1),
             pibLongTerme: +R.L.pib.toFixed(2)}
  });
  ia.annonce = {...ia.annonce, titre: "Un budget calculé, pas promis", texte};
  // la date ne bouge que si le résultat bouge : une relève sans changement n'écrit rien
  if (dateAvant && sansDate(ia) === ancien) ia.calcul.date = dateAvant;
  const avant = fs.readFileSync(path.join(DOSSIER, 'parties.json'), 'utf8');
  const apres = JSON.stringify(PARTIES, null, 2) + '\n';
  if (avant !== apres) {
    fs.writeFileSync(path.join(DOSSIER, 'parties.json'), apres);
    console.log('parties.json mis à jour (entrée « ia »). Reconstruire : python3 build.py');
  } else console.log('Rien de changé.');
}
