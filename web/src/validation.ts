// Renders the blind-test results written by pipeline/validate.py. Numbers are shown as they came out.

import { json } from './data';

interface Check {
  name: string;
  passed: boolean;
  detail: string;
}

interface Follow {
  analogs_with_a_top10_target: number;
  analogs: number;
  random_share_with_a_top10_target: number;
  random_cells: number;
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
  follow_up: Record<string, Follow>;
  first_version: {
    presets: Validation['presets'];
    follow_up: Record<string, Follow>;
    tolerance_trial: { change: string; presets: { label: string; share_top10: number }[]; kept: boolean };
  };
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
    const pct = (x: number) => `${x.toFixed(0)}%`;
    const first = v.first_version;
    const lowest = Math.min(...v.presets.map((p) => p.share_top10));
    const highest = Math.max(...v.presets.map((p) => p.share_top10));
    const verdict =
      lowest > v.chance_percent
        ? `The engine now ranks the famous sites above chance, by a modest margin: ${pct(lowest)} to ${pct(highest)} of them land in the best ${v.chance_percent}% of Earth’s land, where chance gives ${v.chance_percent}%.`
        : `The engine ranks the famous sites no better than chance: ${pct(lowest)} to ${pct(highest)} of them land in the best ${v.chance_percent}% of Earth’s land, where chance gives ${v.chance_percent}%.`;
    const compare = v.presets
      .map((p, i) => {
        const f = v.follow_up[p.id];
        const f1 = first.follow_up[p.id];
        return `<tr><th scope="row">${esc(p.label)}</th>
          <td>${pct(first.presets[i].share_top10)}</td><td><b>${pct(p.share_top10)}</b></td>
          <td>${pct(first.presets[i].median_top_percent)}</td><td><b>${pct(p.median_top_percent)}</b></td>
          <td>${f1.analogs_with_a_top10_target} of ${f1.analogs}</td>
          <td><b>${f.analogs_with_a_top10_target} of ${f.analogs}</b> (random land: ${pct(f.random_share_with_a_top10_target)})</td></tr>`;
      })
      .join('');
    const trial = first.tolerance_trial;
    doc.innerHTML = `
      <h1>Does the engine find the famous sites by itself?</h1>
      <p>Scientists already use a handful of places on Earth as stand-ins for Mars. The engine was never told about them.
      This page tests whether it ranks those places above an average patch of land, and reports what happened, including
      a first attempt that failed.</p>
      <h2>The headline number</h2>
      <p><strong>${verdict}</strong></p>
      <p>For every named Mars target and every preset, we found where each known analog site ranks among all
      ${v.earth_land_cells.toLocaleString('en-US')} Earth land cells. A site counts as a hit when it lands in the best
      ${v.chance_percent}% of Earth’s land area. There are ${v.presets[0].pairs} site and target pairs per preset.</p>
      <div class="table-scroll"><table class="summary"><thead>
        <tr><th scope="col" rowspan="2">Preset</th><th scope="colgroup" colspan="2">Famous sites in the top ${v.chance_percent}% (chance ${v.chance_percent}%)</th><th scope="colgroup" colspan="2">Median rank (top x% of land)</th><th scope="colgroup" colspan="2">Sites in the top ${v.chance_percent}% for at least one target</th></tr>
        <tr><th scope="col">First version</th><th scope="col">Now</th><th scope="col">First version</th><th scope="col">Now</th><th scope="col">First version</th><th scope="col">Now</th></tr>
      </thead><tbody>${compare}</tbody></table></div>
      <h2>What happened, in order</h2>
      <p><strong>The first version failed.</strong> It scored five measurements: slope, relief, mean temperature, day-night
      temperature range and albedo. It placed ${first.presets.map((p) => `${pct(p.share_top10)} (${esc(p.label)})`).join(', ')}
      of the famous sites in the top ${v.chance_percent}%, which is below chance. The reason is that Mars is far colder than
      those sites. The named targets average about 190 to 225 K with a swing of 40 to 85 K between day and night; the
      Atacama, Death Valley, Utah and the Pilbara sit near 290 to 300 K with a swing under 40 K. On temperature those
      sites score close to zero, and so does almost all of Earth. That left slope, relief and albedo to do the ranking,
      and on those three a famous desert is not special.</p>
      <p><strong>One tolerance change did not help.</strong> The plan allowed the tolerances to be revisited once.
      We tried this: ${esc(trial.change.toLowerCase())}. The numbers became
      ${trial.presets.map((p) => `${esc(p.label)} ${pct(p.share_top10)}`).join(', ')}, so the original tolerances were kept.</p>
      <p><strong>Then we changed the method.</strong> The first version had no way to tell a desert from a rainforest.
      Mars and the Moon have no rain and no plants, so we added two measurements with a target of zero: yearly rain and
      snowfall, and plant cover. Their tolerances are standard thresholds chosen before the test was re-run: 250 mm a
      year, the usual limit of a desert, and a vegetation index of 0.2, the usual limit of barren land. We ran the test
      once with these and did not adjust anything afterwards.</p>
      <h2>How much to trust the second result</h2>
      <p>Less than a test planned in advance. The change was made after seeing a failure, and the famous sites are
      mostly deserts, so adding dryness was always likely to help them. The margin is also modest: about one and a half
      times chance, and most site and target pairs still fall outside the top ${v.chance_percent}%. What the result
      supports is that the engine now points toward dry, bare, Mars-like land. It does not show that a high score
      makes a place a good analog.</p>
      <h2>Every site against every target</h2>
      <p>Each number is the share of Earth’s land that scores higher than the analog site for that Mars target, with ice and snow left in.
      Lower is better. Green is the top 10%, amber the top 25%.</p>
      ${v.presets.map((p) => `<h3>${esc(p.label)}</h3>${matrix(v, p.id)}`).join('')}
      <h2>Other checks</h2>
      <ul class="checks-list">${[v.self_match, v.stability, ...v.reader_checks].map(check).join('')}</ul>
      <h2>How to read this</h2>
      <ul>${v.notes.map((n) => `<li>${esc(n)}</li>`).join('')}</ul>
      <p class="caveat">Generated ${esc(v.generated)} by <code>pipeline/validate.py</code>, which re-runs both versions.</p>`;
  })
  .catch((e: Error) => {
    doc.innerHTML = `<h1>Validation</h1><p>${esc(e.message)}. Run <code>make data</code> to build the results.</p>`;
  });
