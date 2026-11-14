// Renders the blind-test results written by pipeline/validate.py. Numbers are shown as they came out.

import { json } from './data';

interface Check {
  name: string;
  passed: boolean;
  detail: string;
}

interface Validation {
  generated: string;
  earth_land_cells: number;
  chance_percent: number;
  presets: { id: string; label: string; share_top10: number; pairs: number; median_top_percent: number }[];
  targets: string[];
  analogs: { site: string; lat: number; lon: number; on_land: boolean }[];
  // top_percent[preset][analog][target]: share of Earth land area that scores higher than the analog's cell
  top_percent: Record<string, (number | null)[][]>;
  follow_up: Record<string, {
    analogs_with_a_top10_target: number;
    analogs: number;
    random_share_with_a_top10_target: number;
    random_cells: number;
    barren_share_best1: number;
    barren_share_all: number;
    median_rain_best1: number;
    median_rain_all: number;
  }>;
  tolerance_trial: { change: string; reason: string; presets: { label: string; share_top10: number }[]; kept: boolean };
  self_match: Check;
  stability: Check;
  reader_checks: Check[];
  notes: string[];
}

const esc = (s: string) => s.replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]!);
const doc = document.getElementById('doc')!;

function matrix(v: Validation, preset: string): string {
  const head = v.targets.map((t) => `<th scope="col"><span>${esc(t)}</span></th>`).join('');
  const body = v.analogs
    .map((a, i) => {
      const cells = v.top_percent[preset][i]
        .map((p) => {
          if (p === null) return '<td class="na">no data</td>';
          const cls = p <= 10 ? 'hit' : p <= 25 ? 'near' : 'miss';
          return `<td class="${cls}">${p < 1 ? p.toFixed(1) : p.toFixed(0)}</td>`;
        })
        .join('');
      return `<tr><th scope="row">${esc(a.site)}</th>${cells}</tr>`;
    })
    .join('');
  return `<div class="table-scroll"><table class="matrix"><thead><tr><th></th>${head}</tr></thead><tbody>${body}</tbody></table></div>`;
}

const check = (c: Check) => `<li class="${c.passed ? 'pass' : 'fail'}"><b>${c.passed ? 'Passed' : 'Failed'}:</b> ${esc(c.name)}. ${esc(c.detail)}</li>`;

json<Validation>('validation.json')
  .then((v) => {
    const summary = v.presets
      .map((p) => `<tr><th scope="row">${esc(p.label)}</th><td>${p.share_top10.toFixed(0)}%</td><td>${p.median_top_percent.toFixed(0)}%</td><td>${p.pairs}</td></tr>`)
      .join('');
    const best = Math.max(...v.presets.map((p) => p.share_top10));
    const verdict =
      best > v.chance_percent * 1.5
        ? 'The engine ranks the famous sites well above chance.'
        : best >= v.chance_percent
          ? 'The engine ranks the famous sites about as well as chance would.'
          : 'The engine does not find the famous sites. It ranks them no better than land picked at random.';
    const followRows = v.presets
      .map((p) => {
        const f = v.follow_up[p.id];
        return `<tr><th scope="row">${esc(p.label)}</th>
          <td>${f.analogs_with_a_top10_target} of ${f.analogs} (${((100 * f.analogs_with_a_top10_target) / f.analogs).toFixed(0)}%)</td>
          <td>${f.random_share_with_a_top10_target.toFixed(0)}%</td>
          <td>${f.barren_share_best1.toFixed(0)}% against ${f.barren_share_all.toFixed(0)}%</td>
          <td>${f.median_rain_best1.toLocaleString('en-US')} mm against ${f.median_rain_all.toLocaleString('en-US')} mm</td></tr>`;
      })
      .join('');
    const trial = v.tolerance_trial;
    doc.innerHTML = `
      <h1>Does the engine find the famous sites by itself?</h1>
      <p>Scientists already use a handful of places on Earth as stand-ins for Mars. The engine was never told about them.
      This page tests whether it ranks those places above an average patch of land, and reports the answer exactly as it came out.</p>
      <h2>The headline number</h2>
      <p><strong>${verdict}</strong></p>
      <p>For every named Mars target and every preset, we found where each known analog site ranks among all
      ${v.earth_land_cells.toLocaleString('en-US')} Earth land cells. A site counts as a hit when it lands in the best
      ${v.chance_percent}% of Earth’s land area. Picking land at random would score ${v.chance_percent}%.</p>
      <table class="summary"><thead><tr><th scope="col">Preset</th><th scope="col">Known analogs in the top ${v.chance_percent}%</th><th scope="col">Median rank (top x% of land)</th><th scope="col">Site and target pairs</th></tr></thead><tbody>${summary}</tbody></table>
      <h2>Why the result looks like this</h2>
      <p>Mars is far colder than the famous sites. The named targets average about 190 to 225 K with a swing of
      40 to 85 K between day and night. The Atacama, Death Valley, Utah and the Pilbara sit near 290 to 300 K with a swing
      under 40 K. On temperature those sites score close to zero, and so does almost all of Earth. What is left to rank on
      is slope, relief and albedo, and on those three a famous desert is not special: plenty of ordinary land is as flat
      and as bright.</p>
      <p>The famous sites were picked for things this engine cannot see: minerals, salts, microbes, lava tubes, and a road
      to get there. So this test does not show those sites are poor analogs. It shows that five coarse physical
      measurements do not rediscover them, which limits what a match from this tool can claim.</p>
      <h2>Every site against every target</h2>
      <p>Each number is the share of Earth’s land that scores higher than the analog site for that Mars target, with ice and snow left in.
      Lower is better. Green is the top 10%, amber the top 25%.</p>
      ${v.presets.map((p) => `<h3>${esc(p.label)}</h3>${matrix(v, p.id)}`).join('')}
      <h2>Two follow-up questions</h2>
      <p>These were added after the headline number came out, so read them as checks on it and not as fresh evidence.
      First: is each famous site a top-10% match for at least one of the ten targets? Random land was put through the same
      test (${Object.values(v.follow_up)[0].random_cells.toLocaleString('en-US')} cells, drawn by area) to set the bar.
      Second: the score never sees rain or plants. Is the best-scoring 1% of land for each target drier and barer than land in general?</p>
      <div class="table-scroll"><table class="summary"><thead><tr><th scope="col">Preset</th><th scope="col">Famous sites in the top 10% for some target</th><th scope="col">Random land that manages the same</th><th scope="col">Barren share of the best 1% against all land</th><th scope="col">Median yearly rain, best 1% against all land</th></tr></thead><tbody>${followRows}</tbody></table></div>
      <p>The famous sites do no better than random land on the first question. On the second, the best matches are only
      slightly barer and drier than land in general, except under the Thermal hardware preset, where they are much drier
      because they are mostly polar ice.</p>
      <h2>The one change we tried</h2>
      <p>The plan allowed the tolerances to be revisited once after this test. ${esc(trial.reason)}
      We tried this: ${esc(trial.change.toLowerCase())}. The headline numbers became
      ${trial.presets.map((p) => `${esc(p.label)} ${p.share_top10.toFixed(0)}%`).join(', ')}.
      That is no better, so ${trial.kept ? 'the new values were kept' : 'the original tolerances were kept'}.</p>
      <h2>Other checks</h2>
      <ul class="checks-list">${[v.self_match, v.stability, ...v.reader_checks].map(check).join('')}</ul>
      <h2>How to read this</h2>
      <ul>${v.notes.map((n) => `<li>${esc(n)}</li>`).join('')}</ul>
      <p class="caveat">Generated ${esc(v.generated)} by <code>pipeline/validate.py</code>.</p>`;
  })
  .catch((e: Error) => {
    doc.innerHTML = `<h1>Validation</h1><p>${esc(e.message)}. Run <code>make data</code> to build the results.</p>`;
  });
