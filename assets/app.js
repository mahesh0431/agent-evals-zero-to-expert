// Agent Evals: Zero to Expert — shared navigation, theme, quizzes, copy buttons.
(function () {
  const PARTS = [
    { title: "Part I · Foundations", mods: [
      ["01", "what-are-evals", "What an eval is, and why it matters"],
      ["02", "anatomy-of-an-eval", "Anatomy of an eval"],
      ["03", "graders", "Graders: code, model, human"],
      ["04", "metrics-and-statistics", "Metrics and statistics"],
    ]},
    { title: "Part II · Agent evals, every modality", mods: [
      ["05", "agents-are-different", "Why agents are different"],
      ["06", "tool-use-and-conversation", "Tool use, RAG and conversational agents"],
      ["07", "coding-agents", "Coding agents"],
      ["08", "web-and-computer-use", "Web and computer-use agents"],
      ["09", "voice-agents", "Voice agents"],
      ["10", "vision-image-video", "Vision, image and video"],
      ["11", "multi-agent-long-horizon", "Multi-agent and long-horizon"],
    ]},
    { title: "Part III · Practice", mods: [
      ["12", "error-analysis", "Error analysis: building your own eval"],
      ["13", "llm-as-judge", "LLM-as-a-judge, in depth"],
      ["14", "tools-landscape", "The tools landscape"],
      ["15", "production-evals", "Evals in production and CI"],
    ]},
    { title: "Part IV · Expert", mods: [
      ["16", "how-labs-do-evals", "How the labs do evals"],
      ["17", "safety-evals", "Safety and dangerous-capability evals"],
      ["18", "benchmark-pitfalls", "Benchmark pitfalls"],
      ["19", "capstone", "Capstone: an agent eval end to end"],
      ["20", "expert-drill", "Expert drill, glossary and map"],
    ]},
    { title: "Part V · Evaluating the building blocks", mods: [
      ["21", "harness-evals", "Evaluating the agent harness"],
      ["22", "skills-evals", "Evaluating agent skills"],
      ["23", "memory-evals", "Evaluating agent memory"],
    ]},
  ];
  const ALL = PARTS.flatMap(p => p.mods);
  const inModules = location.pathname.includes("/modules/");
  const root = inModules ? "../" : "./";
  const current = (location.pathname.split("/").pop() || "index.html").replace(".html", "");
  const href = m => `${root}modules/${m[0]}-${m[1]}.html`;

  const store = {
    get(k) { try { return JSON.parse(localStorage.getItem(k)); } catch (e) { return null; } },
    set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} },
  };

  // theme
  const savedTheme = store.get("aez-theme");
  if (savedTheme) document.documentElement.dataset.theme = savedTheme;

  document.addEventListener("DOMContentLoaded", () => {
    const done = store.get("aez-done") || {};

    // top bar
    const bar = document.createElement("header");
    bar.className = "topbar";
    bar.innerHTML = `
      <button class="iconbtn navtoggle" aria-label="Toggle course menu">☰</button>
      <a class="brand" href="${root}index.html">Agent Evals <span>Zero → Expert</span></a>
      <div class="spacer"></div>
      <button class="iconbtn themebtn" aria-label="Switch light or dark theme" title="Light / dark">◐</button>
      <div class="progressbar"></div>`;
    document.body.prepend(bar);
    bar.querySelector(".navtoggle").onclick = () => document.body.classList.toggle("nav-open");
    bar.querySelector(".themebtn").onclick = () => {
      const cur = document.documentElement.dataset.theme || "light";
      const next = cur === "dark" ? "light" : "dark";
      document.documentElement.dataset.theme = next;
      store.set("aez-theme", next);
      if (document.querySelector(".hero3d canvas")) location.reload();
    };
    const pb = bar.querySelector(".progressbar");
    addEventListener("scroll", () => {
      const h = document.documentElement.scrollHeight - innerHeight;
      pb.style.width = (h > 0 ? (scrollY / h) * 100 : 0) + "%";
    }, { passive: true });

    // sidebar
    const side = document.querySelector(".sidebar");
    if (side) {
      side.innerHTML = `<a href="${root}index.html"${current === "index" ? ' class="active"' : ""}><span class="n">⌂</span>Course home</a><a href="${root}playground.html"${current === "playground" ? ' class="active"' : ""}><span class="n">▶</span>Eval Playground</a>` +
        PARTS.map(p => `<h4>${p.title}</h4>` + p.mods.map(m => {
          const id = `${m[0]}-${m[1]}`;
          const cls = [id === current ? "active" : "", done[id] ? "done" : ""].join(" ").trim();
          return `<a href="${href(m)}" class="${cls}"><span class="n">${m[0]}</span>${m[2]}</a>`;
        }).join("")).join("");
    }

    // pager + mark-complete
    const idx = ALL.findIndex(m => `${m[0]}-${m[1]}` === current);
    const content = document.querySelector(".content");
    if (idx >= 0 && content) {
      const prev = ALL[idx - 1], next = ALL[idx + 1];
      const pager = document.createElement("nav");
      pager.className = "pager";
      pager.innerHTML =
        (prev ? `<a href="${href(prev)}"><small>← Previous</small>${prev[0]} · ${prev[2]}</a>` : `<a href="${root}index.html"><small>← Back</small>Course home</a>`) +
        (next ? `<a class="next" href="${href(next)}"><small>Next →</small>${next[0]} · ${next[2]}</a>` : `<a class="next" href="${root}index.html"><small>Finished</small>Back to course home</a>`);
      content.appendChild(pager);
      pager.addEventListener("click", () => { done[current] = true; store.set("aez-done", done); });
    }

    // auto table of contents from h2
    const tocHost = document.querySelector("[data-toc]");
    if (tocHost) {
      const hs = [...document.querySelectorAll(".content h2")];
      hs.forEach((h, i) => { if (!h.id) h.id = "s" + (i + 1); });
      tocHost.innerHTML = `<b>In this module</b><ol>${hs.map(h => `<li><a href="#${h.id}">${h.textContent}</a></li>`).join("")}</ol>`;
      tocHost.className = "toc";
    }

    // copy buttons
    document.querySelectorAll("pre").forEach(pre => {
      const b = document.createElement("button");
      b.className = "iconbtn copy"; b.textContent = "Copy";
      b.onclick = () => {
        const txt = pre.querySelector("code")?.innerText ?? pre.innerText;
        navigator.clipboard?.writeText(txt).then(() => { b.textContent = "Copied"; setTimeout(() => b.textContent = "Copy", 1200); });
      };
      pre.appendChild(b);
    });

    // scroll reveal + animate arrows of the diagram on screen
    const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
    if ("IntersectionObserver" in window && !reduce) {
      const els = document.querySelectorAll(".content figure.diagram, .content .widget");
      const io = new IntersectionObserver(entries => entries.forEach(e => {
        if (e.target.matches("figure.diagram")) e.target.classList.toggle("in-view", e.intersectionRatio > 0.35);
      }), { threshold: [0, 0.35, 0.7] });
      els.forEach(el => io.observe(el));
    }

    // big outlined module number beside the title
    const h1 = document.querySelector(".content h1");
    if (idx >= 0 && h1) h1.insertAdjacentHTML("beforebegin", `<div class="modnum" aria-hidden="true">${ALL[idx][0]}</div>`);

    // syntax highlighting (vendored highlight.js)
    const codes = [...document.querySelectorAll("pre > code")];
    if (codes.length) {
      const hs = document.createElement("script");
      hs.src = root + "assets/vendor/highlight.min.js";
      hs.onload = () => codes.forEach(c => {
        const lang = (c.parentElement.dataset.lang || "").toLowerCase();
        const map = { jsonl: "json", sh: "bash", shell: "bash", yml: "yaml", py: "python" };
        const l = map[lang] || lang;
        if (!l || l === "text" || l === "csv" || !window.hljs.getLanguage(l)) return;
        try { c.innerHTML = window.hljs.highlight(c.textContent, { language: l, ignoreIllegals: true }).value; c.classList.add("hljs"); } catch (e) {}
      });
      document.body.appendChild(hs);
    }

    // click any diagram to view it full screen
    const lb = document.createElement("div");
    lb.className = "lightbox"; lb.hidden = true;
    lb.innerHTML = `<button class="iconbtn lbclose" aria-label="Close">✕</button><div class="lbinner diagram"></div><div class="lbcap"></div>`;
    document.body.appendChild(lb);
    const closeLb = () => { lb.hidden = true; lb.querySelector(".lbinner").innerHTML = ""; document.body.style.overflow = ""; };
    lb.addEventListener("click", e => { if (e.target === lb || e.target.classList.contains("lbclose")) closeLb(); });
    addEventListener("keydown", e => { if (e.key === "Escape" && !lb.hidden) closeLb(); });
    document.querySelectorAll(".content figure.diagram").forEach(fig => {
      const svg = fig.querySelector("svg"); if (!svg) return;
      const b = document.createElement("button");
      b.className = "iconbtn zoombtn"; b.textContent = "⤢ Enlarge"; b.setAttribute("aria-label", "Enlarge diagram");
      b.onclick = () => {
        const clone = svg.cloneNode(true);
        lb.querySelector(".lbinner").appendChild(clone);
        lb.querySelector(".lbcap").innerHTML = fig.querySelector("figcaption")?.innerHTML || "";
        lb.hidden = false; document.body.style.overflow = "hidden";
      };
      fig.appendChild(b);
    });

    // interactive widgets
    if (document.querySelector("[data-widget]")) {
      const s = document.createElement("script");
      s.src = root + "assets/widgets.js";
      document.body.appendChild(s);
    }

    // quizzes:<div class="q" data-answer="1"><p>Q</p><button class="opt">..</button>...<div class="why">..</div></div>
    document.querySelectorAll(".quiz .q").forEach(q => {
      const ans = +q.dataset.answer;
      q.querySelectorAll("button.opt").forEach((b, i) => {
        b.onclick = () => {
          if (q.classList.contains("answered")) return;
          q.classList.add("answered");
          b.classList.add(i === ans ? "right" : "wrong");
          q.querySelectorAll("button.opt")[ans].classList.add("right");
        };
      });
    });
  });
  window.AEZ = { PARTS, ALL };
})();
