/* Le budget apolitique : un scénario calculé par une machine, à partir des chiffrages publiés,
 * avec des règles fixes appliquées mécaniquement — aucun choix au cas par cas.
 *
 *   node moteur/budget-apolitique.js            montre le calcul, n'écrit rien
 *   node moteur/budget-apolitique.js --ecrire   met à jour l'entrée « ia » de parties.json
 *
 * Relancé par la veille chaque jour, après la mise à jour des données : quand un chiffrage, une
 * hypothèse ou un effet publié change, le budget se recalcule de lui-même.
 *
 * Les règles (reprises telles quelles sur la page) :
 *  1. viser un déficit sous 3 % du PIB en 2032, la limite des traités européens ;
 *  2. moitié en économies, moitié en recettes : une convention pour ne pencher d'aucun côté ;
 *  3. dans chaque moitié, d'abord les mesures qui freinent le moins l'activité pour chaque euro
 *     rapporté, d'après les effets publiés (moteur de la carte « effets en chaîne ») ;
 *  4. chaque mesure à son chiffrage central, ou à sa borne basse quand les chiffrages publiés vont
 *     du simple au triple ; jamais au plus favorable ; aucune dépense nouvelle ;
 *  5. écarter les mesures dont le rendement peut être nul, celles qui distinguent les personnes
 *     selon leur nationalité (principe d'égalité), et les doublons (deux impôts sur la même assiette).
 */
'use strict';
const fs = require('fs'), path = require('path');
const {creerMoteur} = require('./projection.js');
const {creerPage, hypotheses} = require('./page.js');

const DOSSIER = path.join(__dirname, '..', 'dataset', 'simulateur');
const lire = n => JSON.parse(fs.readFileSync(path.join(DOSSIER, n + '.json'), 'utf8'));
const D = {baseline: lire('baseline'), measures: lire('measures'), macro: lire('macro')};
const PARTIES = lire('parties'), CTX = lire('contexte').indicateurs;
const P = hypotheses(D, CTX);
const PAGE = creerPage(D), MOTEUR = creerMoteur(D);
const M = PAGE.M, AN = 2032, CIBLE = -3;

const nf = (v, d = 1) => v.toLocaleString('fr-FR', {minimumFractionDigits: d, maximumFractionDigits: d});

/* Mesures qui distinguent les personnes selon leur nationalité ou leur séjour : écartées au nom du
   principe d'égalité, quel que soit leur rendement. */
const EGALITE = {
  immigration: "Elle distingue les personnes selon leur nationalité ou leur séjour : écartée au nom du principe d'égalité, quel que soit son rendement.",
  ame: "Elle distingue les personnes selon leur situation de séjour : écartée au nom du principe d'égalité, quel que soit son rendement."
};
/* Impôts sur la même assiette : un seul peut être retenu, sinon le même argent serait compté deux fois. */
const DOUBLONS = [['isf', 'isfclim', 'zucman']];

function calculer() {
  const ecartees = {}, notes = {};
  // prudence : borne basse quand les chiffrages divergent du simple au triple
  const niveau = m => m.hi > 3 * m.lo ? 'lo' : 'mid';
  const gain = id => PAGE.amountAt(M[id], M[id][niveau(M[id])], AN, P);
  const candidates = [];
  for (const m of D.measures.measures) {
    if (m.g === 'dep+' || m.g === 'rec-') continue;               // aucune dépense ni baisse d'impôt
    if (EGALITE[m.id]) { ecartees[m.id] = EGALITE[m.id]; continue; }
    if (!(m.lo > 0)) {
      ecartees[m.id] = `Rendement possiblement nul : les chiffrages publiés vont de ${nf(m.lo)} à ${nf(m.hi)} Md€.`;
      continue;
    }
    // coût pour l'activité : écart de PIB en 2032 pour cette mesure seule, au niveau retenu
    const res = MOTEUR.projeter(P, {[m.id]: m[niveau(m)]});
    const pib = res.centre.at(-1).pib, g = gain(m.id);
    candidates.push({id: m.id, m, niv: niveau(m), gain: g, pib, cout: -pib / g * 10});   // points de PIB pour 10 Md€
  }
  // doublons : on garde, dans chaque groupe, celui qui pèse le moins sur l'activité
  for (const groupe of DOUBLONS) {
    const la = candidates.filter(c => groupe.includes(c.id)).sort((a, b) => a.cout - b.cout);
    for (const c of la.slice(1)) {
      ecartees[c.id] = `Même assiette que « ${la[0].m.lab} », retenue à sa place parce qu'elle pèse moins sur l'activité : les deux ensemble compteraient deux fois le même argent.`;
      candidates.splice(candidates.indexOf(c), 1);
    }
  }
  const pools = {
    dep: candidates.filter(c => c.m.g === 'dep-').sort((a, b) => a.cout - b.cout),
    rec: candidates.filter(c => c.m.g === 'rec+').sort((a, b) => a.cout - b.cout)
  };
  const rang = Object.fromEntries(Object.values(pools).flatMap(l => l.map((c, i) => [c.id, [i + 1, l.length]])));
  const set = {}, somme = {dep: 0, rec: 0};
  const actif = () => Object.fromEntries(Object.keys(set).map(id => [id, M[id][set[id].sim]]));
  const deficit = () => PAGE.run(P, actif()).at(-1).soldePct;
  while (deficit() < CIBLE && (pools.dep.length || pools.rec.length)) {
    const cote = !pools.rec.length ? 'dep' : !pools.dep.length ? 'rec' : (somme.dep <= somme.rec ? 'dep' : 'rec');
    const c = pools[cote].shift();
    set[c.id] = {sim: c.niv}; somme[cote] += c.gain;
    const [k, n] = rang[c.id];
    const effet = c.pib >= 0
      ? `elle soutient même l'activité (${nf(c.pib, 2)} % de PIB en 2032)`
      : `elle freine l'activité de ${nf(c.cout, 2)} point de PIB pour 10 Md€ rapportés`;
    const niv = c.niv === 'lo'
      ? `à sa borne basse (${nf(M[c.id].lo)} Md€ par an), par prudence : les chiffrages publiés vont jusqu'à ${nf(M[c.id].hi)} Md€`
      : `à son chiffrage central (${nf(M[c.id].mid)} Md€ par an)`;
    notes[c.id] = `Retenue ${niv}. D'après les effets publiés, ${effet} : `
      + `${k === 1 ? 'la moins pénalisante' : `la ${k}e moins pénalisante`} des ${n} ${cote === 'dep' ? "mesures d'économies" : 'mesures de recettes'} retenables.`;
  }
  for (const c of [...pools.dep, ...pools.rec])
    ecartees[c.id] = "Pèse davantage sur l'activité que les mesures retenues, et l'objectif est atteint sans elle.";

  const fin = PAGE.run(P, actif()).at(-1);
  return {set, notes, ecartees, somme, fin, atteint: fin.soldePct >= CIBLE};
}

const R = calculer();
const aujourdhui = new Date().toISOString().slice(0, 10);
const CRITERES = [
  "Viser un déficit sous 3 % du PIB en 2032, la limite fixée par les traités européens.",
  "Moitié en économies, moitié en recettes : une convention, pour ne pencher d'aucun côté.",
  "Dans chaque moitié, prendre d'abord les mesures qui freinent le moins l'activité pour chaque euro rapporté, d'après les effets publiés par le Trésor, la BCE et l'OFCE.",
  "Chaque mesure à son chiffrage central, ou à sa borne basse quand les chiffrages publiés vont du simple au triple ; jamais au plus favorable ; aucune dépense nouvelle, aucune promesse.",
  "Écarter les mesures dont le rendement peut être nul, celles qui distinguent les personnes selon leur nationalité (principe d'égalité), et les doublons.",
  "Recalculer chaque jour, avec les chiffrages et les prévisions du moment."
];
const texte = `Ce budget n'est le programme de personne. Il est calculé par une intelligence artificielle : `
  + `une machine applique les règles ci-dessous aux ${D.measures.measures.length} mesures chiffrées du simulateur, `
  + `aux mêmes chiffrages que pour les candidats, sans aucun choix au cas par cas. Il est recalculé chaque jour. `
  + (R.atteint
    ? `Résultat : ${nf(R.somme.dep)} Md€ d'économies et ${nf(R.somme.rec)} Md€ de recettes en 2032, pour un déficit de ${nf(-R.fin.soldePct)} % du PIB. `
    : `Même en retenant toutes les mesures permises par ses règles (${nf(R.somme.dep)} Md€ d'économies, ${nf(R.somme.rec)} Md€ de recettes), le déficit reste à ${nf(-R.fin.soldePct)} % du PIB en 2032. `)
  + `Les règles elles-mêmes sont des conventions : elles sont écrites ici pour être discutées.`;

console.log(`Budget apolitique au ${aujourdhui} : déficit 2032 ${nf(-R.fin.soldePct)} %, dette ${nf(R.fin.dettePct, 0)} %${R.atteint ? '' : ' (cible non atteinte)'}`);
console.log(`  économies ${nf(R.somme.dep)} Md€, recettes ${nf(R.somme.rec)} Md€`);
for (const id in R.set) console.log(`  + ${id.padEnd(13)} ${R.notes[id]}`);
for (const id in R.ecartees) console.log(`  − ${id.padEnd(13)} ${R.ecartees[id]}`);

if (process.argv.includes('--ecrire')) {
  const ia = PARTIES.parties.find(p => p.horsCourse);
  const sansDate = x => JSON.stringify({...x, calcul: {...(x.calcul || {}), date: null}});
  const ancien = sansDate(ia), dateAvant = ia.calcul && ia.calcul.date;
  Object.assign(ia, {
    candidat: "Le budget apolitique",
    nom: "Calculé par une intelligence artificielle",
    statutCandidature: "Pas un candidat : un budget calculé par une machine, à partir des chiffrages publiés",
    criteres: CRITERES, set: R.set, pourquoi: R.notes, ecartees: R.ecartees,
    calcul: {date: aujourdhui, deficit2032: +(-R.fin.soldePct).toFixed(2), dette2032: +R.fin.dettePct.toFixed(1),
             economies: +R.somme.dep.toFixed(1), recettes: +R.somme.rec.toFixed(1), cibleAtteinte: R.atteint}
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
