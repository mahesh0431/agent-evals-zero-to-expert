// Interactive widgets. Place <div data-widget="NAME"></div> anywhere in a module.
// Widgets: passk, ci, variance, compare, compound, judgefix, wer, elo
(function () {
  const $ = (h) => { const t = document.createElement("template"); t.innerHTML = h.trim(); return t.content.firstChild; };
  const fmt = (x, d = 1) => (x * 100).toFixed(d) + "%";
  const clamp = (x, a, b) => Math.max(a, Math.min(b, x));

  // --- tiny SVG line chart -------------------------------------------------
  function chart(svg, { series, xmin, xmax, ymin = 0, ymax = 1, xlabel = "", ylabel = "", xticks = [], yticks = [0, .25, .5, .75, 1], yfmt = v => Math.round(v * 100) + "%", markers = [] }) {
    const W = 640, H = 260, L = 52, R = 16, T = 14, B = 40;
    const X = x => L + (x - xmin) / (xmax - xmin) * (W - L - R);
    const Y = y => T + (1 - (y - ymin) / (ymax - ymin)) * (H - T - B);
    let s = `<line x1="${L}" y1="${H - B}" x2="${W - R}" y2="${H - B}" style="stroke:var(--line)"/>`;
    yticks.forEach(v => s += `<line x1="${L}" x2="${W - R}" y1="${Y(v)}" y2="${Y(v)}" style="stroke:var(--line);stroke-dasharray:3 4"/><text x="${L - 6}" y="${Y(v) + 4}" text-anchor="end" style="fill:var(--muted)">${yfmt(v)}</text>`);
    xticks.forEach(v => s += `<text x="${X(v)}" y="${H - B + 16}" text-anchor="middle" style="fill:var(--muted)">${v}</text>`);
    s += `<text x="${(L + W - R) / 2}" y="${H - 6}" text-anchor="middle" style="fill:var(--muted)">${xlabel}</text>`;
    s += `<text x="14" y="${(T + H - B) / 2}" text-anchor="middle" transform="rotate(-90 14 ${(T + H - B) / 2})" style="fill:var(--muted)">${ylabel}</text>`;
    markers.forEach(m => s += `<line x1="${X(m.x)}" x2="${X(m.x)}" y1="${T}" y2="${H - B}" style="stroke:var(--${m.color || "muted"});stroke-dasharray:4 3"/>`);
    series.forEach(se => {
      const d = se.pts.map((p, i) => `${i ? "L" : "M"}${X(p[0]).toFixed(1)},${Y(clamp(p[1], ymin, ymax)).toFixed(1)}`).join("");
      s += `<path d="${d}" style="fill:none;stroke:var(--${se.color});stroke-width:2.6"/>`;
      if (se.dots) se.pts.forEach(p => s += `<circle cx="${X(p[0])}" cy="${Y(p[1])}" r="3.5" style="fill:var(--${se.color})"/>`);
      if (se.label) { const p = se.pts[se.pts.length - 1]; s += `<text x="${X(p[0]) - 4}" y="${Y(p[1]) - 8}" text-anchor="end" style="fill:var(--${se.color});font-weight:700">${se.label}</text>`; }
    });
    svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
    svg.innerHTML = s;
  }
  const slider = (id, label, min, max, step, val) =>
    `<label>${label} <b data-out="${id}"></b><input type="range" data-in="${id}" min="${min}" max="${max}" step="${step}" value="${val}"></label>`;
  const stat = (id, label) => `<div class="stat"><small>${label}</small><span data-stat="${id}">–</span></div>`;
  function wire(el, update) {
    const get = () => Object.fromEntries([...el.querySelectorAll("[data-in]")].map(i => [i.dataset.in, i.type === "range" ? +i.value : i.value]));
    const run = () => update(get(), (k, v) => { const o = el.querySelector(`[data-out="${k}"]`); if (o) o.textContent = v; }, (k, v) => { const o = el.querySelector(`[data-stat="${k}"]`); if (o) o.textContent = v; });
    el.querySelectorAll("[data-in]").forEach(i => i.addEventListener("input", run));
    run();
    return run;
  }
  const binom = (n, k) => { if (k < 0 || k > n) return 0; let r = 1; for (let i = 1; i <= k; i++) r = r * (n - k + i) / i; return r; };
  const z = 1.959964;
  const wilson = (p, n) => { const d = 1 + z * z / n, c = (p + z * z / (2 * n)) / d, h = z * Math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d; return [c - h, c + h]; };
  function randn() { let u = 0, v = 0; while (!u) u = Math.random(); while (!v) v = Math.random(); return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v); }

  const W = {
    passk(el) {
      el.innerHTML = `<h4>pass@k vs pass^k</h4><div class="wdesc">An agent solves a task with per-trial probability p. pass@k asks "did at least one of k tries work?". pass^k asks "did all k tries work?". Drag p and watch them split.</div>
      <div class="controls">${slider("p", "Per-trial success p", 0.05, 0.99, 0.01, 0.7)}${slider("k", "Highlight k", 1, 10, 1, 5)}</div><svg></svg>
      <div class="readout">${stat("a", "pass@k = 1-(1-p)^k")}${stat("b", "pass^k = p^k")}${stat("c", "gap")}</div>
      <div class="note">Idealised curves assuming independent trials. Real agents' trials are correlated (the same task tends to fail the same way), so measured pass^k usually decays more slowly than p^k, and pass@k rises more slowly than 1-(1-p)^k.</div>`;
      wire(el, (v, out, st) => {
        out("p", v.p.toFixed(2)); out("k", v.k);
        const ks = [...Array(10)].map((_, i) => i + 1);
        chart(el.querySelector("svg"), { xmin: 1, xmax: 10, xticks: ks, xlabel: "k (number of trials)", ylabel: "probability",
          series: [{ color: "good", label: "pass@k", dots: 1, pts: ks.map(k => [k, 1 - Math.pow(1 - v.p, k)]) },
                   { color: "bad", label: "pass^k", dots: 1, pts: ks.map(k => [k, Math.pow(v.p, k)]) }], markers: [{ x: v.k, color: "accent" }] });
        const a = 1 - Math.pow(1 - v.p, v.k), b = Math.pow(v.p, v.k);
        st("a", fmt(a)); st("b", fmt(b)); st("c", ((a - b) * 100).toFixed(1) + " pts");
      });
    },

    ci(el) {
      el.innerHTML = `<h4>How big is my error bar?</h4><div class="wdesc">Your eval has n samples and scores an accuracy. The 95% Wilson interval shows the range the true accuracy plausibly lies in. Notice how slowly it shrinks: 4× the samples only halves the width.</div>
      <div class="controls">${slider("n", "Number of samples n", 10, 3000, 10, 200)}${slider("acc", "Observed accuracy", 0.01, 0.99, 0.01, 0.72)}</div><svg></svg>
      <div class="readout">${stat("lo", "lower bound")}${stat("hi", "upper bound")}${stat("w", "± half-width")}</div>`;
      wire(el, (v, out, st) => {
        out("n", v.n); out("acc", fmt(v.acc, 0));
        const [lo, hi] = wilson(v.acc, v.n);
        const ns = [10, 20, 50, 100, 200, 400, 800, 1600, 3000];
        const lx = n => Math.log10(n);
        chart(el.querySelector("svg"), { xmin: 1, xmax: lx(3000), xlabel: "samples n (log scale)", ylabel: "accuracy", xticks: [],
          series: [{ color: "accent", pts: ns.map(n => [lx(n), wilson(v.acc, n)[1]]) }, { color: "accent", pts: ns.map(n => [lx(n), wilson(v.acc, n)[0]]) },
                   { color: "good", pts: [[1, v.acc], [lx(3000), v.acc]] }], markers: [{ x: lx(v.n), color: "warn" }] });
        const svg = el.querySelector("svg");
        ns.forEach(n => { const x = 52 + (lx(n) - 1) / (lx(3000) - 1) * 572; svg.insertAdjacentHTML("beforeend", `<text x="${x}" y="236" text-anchor="middle" style="fill:var(--muted)">${n}</text>`); });
        st("lo", fmt(lo)); st("hi", fmt(hi)); st("w", "±" + ((hi - lo) / 2 * 100).toFixed(1) + " pts");
      });
    },

    variance(el) {
      el.innerHTML = `<h4>Re-run the same eval 40 times</h4><div class="wdesc">The system's true success rate is fixed. Each "run" draws n fresh attempts. The histogram shows the scores you would see. Anything inside the spread is noise, not progress.</div>
      <div class="controls">${slider("p", "True success rate", 0.05, 0.95, 0.01, 0.65)}${slider("n", "Samples per run", 10, 1000, 10, 100)}</div>
      <button class="run">Run 40 evals</button><svg></svg><div class="readout">${stat("min", "lowest run")}${stat("max", "highest run")}${stat("sd", "std. dev.")}</div>`;
      const draw = (v, out, st) => {
        out("p", fmt(v.p, 0)); out("n", v.n);
        const runs = [...Array(40)].map(() => { let c = 0; for (let i = 0; i < v.n; i++) c += Math.random() < v.p; return c / v.n; });
        const bins = 30, lo = 0, hi = 1, cnt = Array(bins).fill(0);
        runs.forEach(r => cnt[Math.min(bins - 1, Math.floor((r - lo) / (hi - lo) * bins))]++);
        const Wd = 640, H = 220, L = 30, B = 34, bw = (Wd - L - 10) / bins, mx = Math.max(...cnt, 1);
        let s = `<line x1="${L}" y1="${H - B}" x2="${Wd - 10}" y2="${H - B}" style="stroke:var(--line)"/>`;
        cnt.forEach((c, i) => { const h = c / mx * (H - B - 16); s += `<rect x="${L + i * bw + 1}" y="${H - B - h}" width="${bw - 2}" height="${h}" rx="2" style="fill:var(--accent);opacity:.85"/>`; });
        [0, .25, .5, .75, 1].forEach(t => s += `<text x="${L + t * (Wd - L - 10)}" y="${H - B + 16}" text-anchor="${t === 1 ? "end" : t === 0 ? "start" : "middle"}" style="fill:var(--muted)">${t * 100}%</text>`);
        const px = L + v.p * (Wd - L - 10);
        s += `<line x1="${px}" x2="${px}" y1="8" y2="${H - B}" style="stroke:var(--good);stroke-width:2;stroke-dasharray:4 3"/><text x="${px + 4}" y="18" style="fill:var(--good);font-weight:700">true rate</text>`;
        s += `<text x="${(Wd) / 2}" y="${H - 4}" text-anchor="middle" style="fill:var(--muted)">observed score of each run</text>`;
        const svg = el.querySelector("svg"); svg.setAttribute("viewBox", `0 0 ${Wd} ${H}`); svg.innerHTML = s;
        const m = runs.reduce((a, b) => a + b) / runs.length, sd = Math.sqrt(runs.reduce((a, b) => a + (b - m) ** 2, 0) / (runs.length - 1));
        st("min", fmt(Math.min(...runs))); st("max", fmt(Math.max(...runs))); st("sd", (sd * 100).toFixed(1) + " pts");
      };
      const run = wire(el, draw);
      el.querySelector("button.run").onclick = run;
    },

    compare(el) {
      el.innerHTML = `<h4>Is model B really better than model A?</h4><div class="wdesc">Two systems run on the same n questions. "Discordant" questions are ones exactly one of them gets right, and only those carry information about the difference. This uses the paired test from Anthropic's "Adding error bars to evals".</div>
      <div class="controls">${slider("n", "Questions n", 50, 3000, 50, 500)}${slider("a", "Model A accuracy", 0.3, 0.95, 0.005, 0.70)}${slider("d", "B minus A (points)", -10, 10, 0.5, 3)}${slider("r", "Share of questions where they disagree", 0.05, 0.6, 0.01, 0.2)}</div>
      <div class="readout">${stat("diff", "difference")}${stat("ci", "95% CI of difference")}${stat("v", "verdict")}</div>
      <div class="note">SE of a paired difference = sqrt(Var(sᵢᴮ − sᵢᴬ) / n). With binary scores, that variance comes from the disagreement rate: questions both models get right or both get wrong add nothing. That's why paired comparisons need far fewer samples than comparing two independent scores.</div>`;
      wire(el, (v, out, st) => {
        out("n", v.n); out("a", fmt(v.a, 1)); out("d", (v.d > 0 ? "+" : "") + v.d); out("r", fmt(v.r, 0));
        const dd = v.d / 100, r = Math.max(v.r, Math.abs(dd) + 0.001);
        const varD = r - dd * dd; const se = Math.sqrt(varD / v.n);
        const lo = dd - z * se, hi = dd + z * se;
        st("diff", (dd * 100 > 0 ? "+" : "") + (dd * 100).toFixed(1) + " pts");
        st("ci", `[${(lo * 100).toFixed(1)}, ${(hi * 100).toFixed(1)}]`);
        st("v", lo > 0 ? "B better ✓" : hi < 0 ? "A better ✓" : "can't tell");
      });
    },

    compound(el) {
      el.innerHTML = `<h4>Errors compound over long tasks</h4><div class="wdesc">If each step of an agent's task succeeds independently with probability p, the whole task succeeds with p^steps. Small per-step reliability gains matter enormously for long tasks.</div>
      <div class="controls">${slider("p", "Per-step success p", 0.8, 0.999, 0.001, 0.97)}${slider("s", "Steps in the task", 1, 200, 1, 30)}</div><svg></svg>
      <div class="readout">${stat("t", "task success")}${stat("h", "steps until 50% success")}</div>`;
      wire(el, (v, out, st) => {
        out("p", fmt(v.p, 1)); out("s", v.s);
        const xs = [...Array(41)].map((_, i) => i * 5);
        chart(el.querySelector("svg"), { xmin: 0, xmax: 200, xticks: [0, 50, 100, 150, 200], xlabel: "number of steps", ylabel: "task success",
          series: [{ color: "accent", pts: xs.map(x => [x, Math.pow(v.p, x)]) }, { color: "muted", pts: xs.map(x => [x, Math.pow(0.99, x)]), label: "p=99%" }], markers: [{ x: v.s, color: "warn" }] });
        st("t", fmt(Math.pow(v.p, v.s))); st("h", (Math.log(0.5) / Math.log(v.p)).toFixed(0));
      });
    },

    judgefix(el) {
      el.innerHTML = `<h4>Correct a pass rate for judge error</h4><div class="wdesc">Your LLM judge says 80% of outputs pass, but the judge itself makes mistakes. If you measured its true positive rate (TPR) and true negative rate (TNR) against human labels, you can estimate the real pass rate: θ = (p_obs + TNR − 1) / (TPR + TNR − 1).</div>
      <div class="controls">${slider("p", "Judge's observed pass rate", 0.01, 0.99, 0.01, 0.80)}${slider("tpr", "Judge TPR (catches real passes)", 0.5, 1, 0.01, 0.92)}${slider("tnr", "Judge TNR (catches real fails)", 0.5, 1, 0.01, 0.75)}</div>
      <div class="readout">${stat("t", "estimated true pass rate")}${stat("b", "judge bias")}</div>
      <div class="note">A lenient judge (low TNR) inflates your score. This is the Rogan–Gladen prevalence correction from epidemiology; use bootstrap resampling of both the eval set and the judge-validation set to put an error bar on it (Module 13).</div>`;
      wire(el, (v, out, st) => {
        out("p", fmt(v.p, 0)); out("tpr", fmt(v.tpr, 0)); out("tnr", fmt(v.tnr, 0));
        const den = v.tpr + v.tnr - 1; const t = den > 0.02 ? clamp((v.p + v.tnr - 1) / den, 0, 1) : NaN;
        st("t", isNaN(t) ? "judge ≈ random" : fmt(t)); st("b", isNaN(t) ? "–" : ((v.p - t) * 100 > 0 ? "+" : "") + ((v.p - t) * 100).toFixed(1) + " pts");
      });
    },

    wer(el) {
      el.innerHTML = `<h4>Word error rate, live</h4><div class="wdesc">WER = (substitutions + deletions + insertions) / words in the reference. Edit the ASR hypothesis and watch the alignment.</div>
      <div class="controls"><label>Reference (what was said)<input type="text" data-in="ref" value="I want to cancel order four five six today"></label>
      <label>Hypothesis (what ASR heard)<input type="text" data-in="hyp" value="I want to cancel the order for five six"></label></div>
      <div class="align" style="font-family:var(--mono);font-size:14px;line-height:2;overflow-x:auto"></div>
      <div class="readout">${stat("s", "substitutions")}${stat("d", "deletions")}${stat("i", "insertions")}${stat("w", "WER")}</div>
      <div class="note">Notice "four" → "for": one substitution that changes an order number. WER treats every word equally; for agents, errors on entities (numbers, names) matter far more, so voice evals also track entity accuracy (Module 09).</div>`;
      wire(el, (v, out, st) => {
        const norm = s => s.toLowerCase().replace(/[^\w\s']/g, "").split(/\s+/).filter(Boolean);
        const r = norm(v.ref), h = norm(v.hyp), n = r.length, m = h.length;
        const D = [...Array(n + 1)].map((_, i) => [...Array(m + 1)].map((_, j) => i === 0 ? j : j === 0 ? i : 0));
        for (let i = 1; i <= n; i++) for (let j = 1; j <= m; j++) D[i][j] = Math.min(D[i - 1][j] + 1, D[i][j - 1] + 1, D[i - 1][j - 1] + (r[i - 1] === h[j - 1] ? 0 : 1));
        let i = n, j = m, ops = []; let S = 0, Dl = 0, I = 0;
        while (i > 0 || j > 0) {
          if (i > 0 && j > 0 && D[i][j] === D[i - 1][j - 1] + (r[i - 1] === h[j - 1] ? 0 : 1)) { ops.unshift(r[i - 1] === h[j - 1] ? ["ok", r[i - 1]] : ["sub", r[i - 1], h[j - 1]]); if (r[i - 1] !== h[j - 1]) S++; i--; j--; }
          else if (i > 0 && D[i][j] === D[i - 1][j] + 1) { ops.unshift(["del", r[i - 1]]); Dl++; i--; }
          else { ops.unshift(["ins", h[j - 1]]); I++; j--; }
        }
        const chip = (t, c, tip) => `<span title="${tip}" style="padding:2px 6px;margin:2px;border-radius:5px;background:var(--${c}-soft, var(--surface-2));color:var(--${c === "muted" ? "text" : c})">${t}</span>`;
        el.querySelector(".align").innerHTML = ops.map(o => o[0] === "ok" ? chip(o[1], "muted", "match") : o[0] === "sub" ? chip(`${o[1]}→${o[2]}`, "warn", "substitution") : o[0] === "del" ? chip(`<s>${o[1]}</s>`, "bad", "deletion") : chip(`+${o[1]}`, "violet", "insertion")).join(" ");
        st("s", S); st("d", Dl); st("i", I); st("w", n ? fmt((S + Dl + I) / n) : "–");
      });
    },

    elo(el) {
      el.innerHTML = `<h4>Arena ratings in one picture</h4><div class="wdesc">Pairwise-preference leaderboards (like Arena) fit a Bradley–Terry model: the chance A beats B depends only on the rating gap. P(A wins) = 1 / (1 + 10^(−(Rᴬ − Rᴮ)/400)).</div>
      <div class="controls">${slider("g", "Rating gap Rᴬ − Rᴮ", -400, 400, 5, 50)}</div><svg></svg><div class="readout">${stat("p", "P(A preferred)")}</div>
      <div class="note">A 50-point gap is only about a 57/43 preference split. Small gaps between top models are often inside the confidence intervals the leaderboard reports.</div>`;
      wire(el, (v, out, st) => {
        out("g", (v.g > 0 ? "+" : "") + v.g);
        const f = g => 1 / (1 + Math.pow(10, -g / 400));
        const xs = [...Array(33)].map((_, i) => -400 + i * 25);
        chart(el.querySelector("svg"), { xmin: -400, xmax: 400, xticks: [-400, -200, 0, 200, 400], xlabel: "rating gap", ylabel: "P(A wins)", series: [{ color: "violet", pts: xs.map(x => [x, f(x)]) }], markers: [{ x: v.g, color: "accent" }] });
        st("p", fmt(f(v.g)));
      });
    },
  };

  document.querySelectorAll("[data-widget]").forEach(el => {
    const fn = W[el.dataset.widget];
    if (!fn) return;
    el.classList.add("widget");
    try { fn(el); } catch (e) { el.innerHTML = "<p class='note'>This interactive widget failed to load.</p>"; console.error(e); }
  });
})();
