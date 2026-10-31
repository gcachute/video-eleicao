const NOMES = {
  2010: { 13: "Dilma", 45: "Serra" },
  2014: { 13: "Dilma", 45: "Aécio" },
  2018: { 17: "Bolsonaro", 13: "Haddad" },
  2022: { 13: "Lula", 22: "Bolsonaro" },
  2026: { 13: "Lula", 22: "Flávio" },
};
const ANOS = [2010, 2014, 2018, 2022, 2026];
const LARG = 520, ALT = 340;
const M = { t: 16, r: 14, b: 40, l: 40 };

const $ = (id) => document.getElementById(id);
const num = (v, c = 1) => v.toLocaleString("pt-BR", { minimumFractionDigits: c, maximumFractionDigits: c });
const inteiro = (v) => v.toLocaleString("pt-BR");
const cor = (nr) => `var(--${nr === 13 ? "vermelho" : "azul"})`;
const nome = (ano, nr) => NOMES[ano]?.[nr] ?? String(nr);
const rotuloTurno = (t) => `${t.ano} · ${t.turno}º turno`;
const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;");

let resumo = null, dados = null, video = null, progresso = 100, tocando = null;
const cache = new Map();
const pedidoAtual = { id: 0 };

async function json(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(url);
  return r.json();
}

async function turno(ano, t) {
  const k = `${ano}_${t}`;
  if (!cache.has(k)) cache.set(k, await json(`dados/turno_${k}.json`));
  return cache.get(k);
}

function montarFiltro() {
  $("filtro").innerHTML = ANOS.map((a) => `<div class="ano"><span>${a}</span>${[1, 2]
    .map((t) => `<button type="button" data-ano="${a}" data-turno="${t}" aria-pressed="false" aria-label="${a}, ${t}º turno">${t}º</button>`)
    .join("")}</div>`).join("");
  $("filtro").addEventListener("click", (e) => {
    const b = e.target.closest("button");
    if (b) escolher(+b.dataset.ano, +b.dataset.turno);
  });
}

async function escolher(ano, t) {
  const id = ++pedidoAtual.id;
  parar();
  const d = await turno(ano, t);
  if (id !== pedidoAtual.id) return;
  dados = d;
  document.querySelectorAll("#filtro button").forEach((b) =>
    b.setAttribute("aria-pressed", String(+b.dataset.ano === ano && +b.dataset.turno === t)));
  document.querySelectorAll(".mini").forEach((b) =>
    b.setAttribute("aria-pressed", String(+b.dataset.ano === ano && +b.dataset.turno === t)));
  document.querySelectorAll("#tabela-turnos tbody tr").forEach((r) =>
    r.setAttribute("aria-selected", String(+r.dataset.ano === ano && +r.dataset.turno === t)));
  try { history.replaceState(null, "", `#${ano}-${t}`); } catch (_) {}
  progresso = 100;
  $("progresso").value = 100;
  desenharTudo();
}

function desenharTudo() {
  aviso();
  tiles();
  legenda();
  graficos();
  tabelaCurva();
  prepararMapa();
  amostras();
  atualizarProgresso();
}

function aviso() {
  const d = dados;
  const textos = {
    real: `<b>Ordem de chegada real.</b> ${rotuloTurno(d)}: as urnas estão na ordem em que ${d.ano === 2018 ? "cada uma entrou pela primeira vez na totalização" : "cada boletim foi recebido"}.`,
    oficial: `<b>Parciais oficiais do TSE.</b> ${rotuloTurno(d)}: a curva da esquerda vem da tabela minuto a minuto do TSE. Ela traz votos, e não urnas, então o eixo é o percentual dos votos válidos. O mapa e as regiões usam a ordem estimada.`,
    estimada: `<b>Ordem de chegada estimada.</b> ${rotuloTurno(d)}: não há hora por urna nem tabela de parciais, então a ordem foi emprestada do mesmo turno de 2018. Não é o que apareceu na noite da eleição. Os losangos são registros da época.`,
  };
  $("aviso").innerHTML = textos[d.ordem];
  if (d.ano === 2026 && d.turno === 2 && video) {
    const n = video.video.filter((l) => !l.igual).length;
    $("aviso").innerHTML += ` Este é o turno do vídeo: <a href="#divergencias">${n} ${n === 1 ? "número diverge" : "números divergem"} dos dados do TSE</a>.`;
  }
  $("tit-chegada").textContent = { real: "Na ordem real de chegada", oficial: "Parciais oficiais do TSE", estimada: "Na ordem estimada de chegada" }[d.ordem];
}

function tiles() {
  const d = dados, a = d.a, b = d.b;
  const s = d.sorteios_ordem;
  const am = d.amostras.find((x) => x.n === 1000);
  const itens = [
    ["Resultado final", `${num(a.pct)}% a ${num(b.pct)}%`, `${nome(d.ano, a.nr)} e ${nome(d.ano, b.nr)}, votos válidos`],
    d.ordem !== "estimada"
      ? [`Trocas de liderança, ${d.ordem === "real" ? "ordem real" : "parciais oficiais"}`, String(d.viradas.length), d.viradas.length ? `às ${d.viradas.map((v) => v.hora).join(" e ")}` : `${inteiro(d.urnas)} urnas`]
      : ["Trocas de liderança, ordem real", "sem dado", `sem hora de chegada · ${inteiro(d.urnas)} urnas`],
    ["Trocas de liderança, ordem sorteada", num(s.viradas_media, 1), `média de ${inteiro(s.n)} sorteios · ${num(s.pct_sem_virada, 0)}% sem nenhuma`],
    ["Margem de erro com 1.000 urnas", `±${num(am.erro_95)} ponto`, `${num(am.pct_das_urnas, 2)}% das urnas · líder certo em ${num(am.acerta_lider, 0)}%`],
  ];
  $("tiles").innerHTML = itens.map(([t, v, n]) => `<div class="tile"><small>${t}</small><strong>${v}</strong><span>${n}</span></div>`).join("");
}

function legenda() {
  const d = dados;
  $("legenda").innerHTML = [d.a, d.b].map((c) =>
    `<span><i style="background:${cor(c.nr)}"></i>${nome(d.ano, c.nr)}</span>`).join("") +
    `<span><i class="faixa"></i>Faixa de 95% dos sorteios</span>` +
    (marcosDoTurno().some((m) => Object.keys(m.valores).length) ? `<span><i class="losango"></i>Registro da época</span>` : "");
}

function dominioY() {
  const d = dados, vals = [];
  const c = d.curva, f = d.sorteada.faixa;
  c.x.forEach((x, i) => { if (x >= 1) vals.push(c.a[i], c.b[i]); });
  f.x.forEach((x, i) => { if (x >= 1) vals.push(f.a_min[i], f.a_max[i], f.b_min[i], f.b_max[i]); });
  vals.push(d.a.pct, d.b.pct);
  let min = Math.min(...vals), max = Math.max(...vals);
  const meio = d.turno === 2 ? 50 : (min + max) / 2;
  const meia = Math.max(max - meio, meio - min, 3) + 0.5;
  const passo = meia > 12 ? 5 : 2;
  min = Math.floor((meio - meia) / passo) * passo;
  max = Math.ceil((meio + meia) / passo) * passo;
  return { min, max, passo };
}

const escalas = (y) => ({
  sx: (x) => M.l + (x / 100) * (LARG - M.l - M.r),
  sy: (v) => M.t + (1 - (v - y.min) / (y.max - y.min)) * (ALT - M.t - M.b),
});

function caminho(xs, ys, sx, sy, ate = 101) {
  let p = "";
  for (let i = 0; i < xs.length && xs[i] <= ate; i++) p += `${p ? "L" : "M"}${sx(xs[i]).toFixed(1)} ${sy(ys[i]).toFixed(1)}`;
  return p;
}

function marcosDoTurno() {
  return (video?.marcos ?? []).filter((m) => m.ano === dados.ano && m.turno === dados.turno);
}

function losangos(sx, sy, y) {
  let s = "";
  for (const m of marcosDoTurno()) {
    const x = m.x ?? m.urnas;
    if (x == null) continue;
    for (const [nr, v] of Object.entries(m.valores)) {
      if (v < y.min || v > y.max) continue;
      const px = sx(x), py = sy(v);
      s += `<rect x="${px - 4}" y="${py - 4}" width="8" height="8" transform="rotate(45 ${px} ${py})" fill="var(--superficie)" stroke="${cor(+nr)}" stroke-width="2"><title>${esc(m.fonte)}: ${nome(m.ano, +nr)} ${num(v, 2)}%</title></rect>`;
    }
  }
  return s;
}

function moldura(y, sx, sy, id, eixo = "urnas apuradas") {
  let s = `<defs><clipPath id="clip-${id}"><rect x="${M.l}" y="${M.t}" width="${LARG - M.l - M.r}" height="${ALT - M.t - M.b}"/></clipPath></defs>`;
  for (let v = y.min; v <= y.max + 1e-6; v += y.passo) {
    s += `<line class="grade" x1="${M.l}" x2="${LARG - M.r}" y1="${sy(v)}" y2="${sy(v)}"/><text x="${M.l - 8}" y="${sy(v) + 4}" text-anchor="end">${v}%</text>`;
  }
  for (const x of [0, 25, 50, 75, 100]) s += `<text x="${sx(x)}" y="${ALT - M.b + 18}" text-anchor="${x === 0 ? "start" : x === 100 ? "end" : "middle"}">${x}%</text>`;
  s += `<line class="eixo" x1="${M.l}" x2="${LARG - M.r}" y1="${ALT - M.b}" y2="${ALT - M.b}"/>`;
  s += `<text x="${(M.l + LARG - M.r) / 2}" y="${ALT - 4}" text-anchor="middle">${eixo}</text>`;
  return s;
}

function faixa(xs, lo, hi, sx, sy, nr) {
  let p = "";
  xs.forEach((x, i) => { p += `${p ? "L" : "M"}${sx(x).toFixed(1)} ${sy(hi[i]).toFixed(1)}`; });
  for (let i = xs.length - 1; i >= 0; i--) p += `L${sx(xs[i]).toFixed(1)} ${sy(lo[i]).toFixed(1)}`;
  return `<path d="${p}Z" fill="${cor(nr)}" opacity=".14"/>`;
}

function graficos() {
  const d = dados, y = dominioY();
  const { sx, sy } = escalas(y);
  for (const [id, c, comFaixa] of [["g-chegada", d.curva, false], ["g-sorteada", d.sorteada.exemplo, true]]) {
    let s = `<svg viewBox="0 0 ${LARG} ${ALT}" role="img" aria-label="Linhas de ${nome(d.ano, d.a.nr)} e ${nome(d.ano, d.b.nr)} ao longo da apuração">`;
    s += moldura(y, sx, sy, id, !comFaixa && d.ordem === "oficial" ? "votos válidos apurados" : "urnas apuradas");
    s += `<g clip-path="url(#clip-${id})">`;
    if (comFaixa) {
      const f = d.sorteada.faixa;
      s += faixa(f.x, f.a_min, f.a_max, sx, sy, d.a.nr) + faixa(f.x, f.b_min, f.b_max, sx, sy, d.b.nr);
    }
    for (const [k, nr] of [["a", d.a.nr], ["b", d.b.nr]]) {
      s += `<path d="${caminho(c.x, c[k], sx, sy)}" fill="none" stroke="${cor(nr)}" stroke-width="2" opacity=".22"/>`;
      s += `<path class="ativa" data-k="${k}" fill="none" stroke="${cor(nr)}" stroke-width="2" stroke-linejoin="round"/>`;
    }
    s += `</g>`;
    if (!comFaixa) {
      for (const v of d.ordem !== "estimada" ? d.viradas.slice(0, 8) : []) {
        const i = c.x.findIndex((x) => x >= v.pct);
        if (i < 0) continue;
        const px = sx(v.pct), py = sy(c.a[i]);
        s += `<circle cx="${px}" cy="${py}" r="5" fill="var(--superficie)" stroke="var(--texto)" stroke-width="2"/>`;
        if (d.viradas.length <= 4) s += `<text class="forte" x="${px}" y="${py - 11}" text-anchor="middle">${v.hora ?? num(v.pct, 0) + "%"}</text>`;
      }
    }
    if (!comFaixa) s += `<g class="losangos">${losangos(sx, sy, y)}</g>`;
    for (const [k, nr] of [["a", d.a.nr], ["b", d.b.nr]]) {
      s += `<circle class="ponta" data-k="${k}" r="5" fill="${cor(nr)}" stroke="var(--superficie)" stroke-width="2"/>`;
      s += `<text class="forte rotulo" data-k="${k}" text-anchor="end"></text>`;
    }
    s += `<line class="mira" stroke="var(--eixo)" y1="${M.t}" y2="${ALT - M.b}" visibility="hidden"/></svg>`;
    const el = $(id);
    el.innerHTML = s;
    el._curva = c;
    el._esc = { sx, sy };
    ligarDica(el);
  }
  atualizarLinhas();
}

function indice(xs, alvo) {
  let lo = 0, hi = xs.length - 1;
  while (lo < hi) {
    const m = (lo + hi + 1) >> 1;
    if (xs[m] <= alvo) lo = m; else hi = m - 1;
  }
  return lo;
}

function atualizarLinhas() {
  for (const id of ["g-chegada", "g-sorteada"]) {
    const el = $(id), c = el._curva, { sx, sy } = el._esc;
    if (!c) continue;
    const i = indice(c.x, progresso);
    const ordem = c.a[i] >= c.b[i] ? ["a", "b"] : ["b", "a"];
    for (const k of ["a", "b"]) {
      el.querySelector(`.ativa[data-k="${k}"]`).setAttribute("d", caminho(c.x, c[k], sx, sy, progresso));
      const px = sx(c.x[i]), py = Math.max(M.t, Math.min(ALT - M.b, sy(c[k][i])));
      const pt = el.querySelector(`.ponta[data-k="${k}"]`);
      pt.setAttribute("cx", px);
      pt.setAttribute("cy", py);
      const t = el.querySelector(`.rotulo[data-k="${k}"]`);
      const naEsquerda = px > 150;
      t.setAttribute("text-anchor", naEsquerda ? "end" : "start");
      t.setAttribute("x", px + (naEsquerda ? -10 : 10));
      t.setAttribute("y", py + (k === ordem[0] ? -9 : 17));
      t.textContent = `${nome(dados.ano, dados[k].nr)} ${num(c[k][i])}%`;
    }
  }
}

function ligarDica(el) {
  const svg = el.querySelector("svg"), mira = el.querySelector(".mira");
  const mover = (e) => {
    const r = svg.getBoundingClientRect();
    const fx = ((e.clientX - r.left) / r.width) * LARG;
    const x = Math.max(0, Math.min(100, ((fx - M.l) / (LARG - M.l - M.r)) * 100));
    const c = el._curva, i = indice(c.x, x);
    const px = el._esc.sx(c.x[i]);
    mira.setAttribute("x1", px); mira.setAttribute("x2", px); mira.setAttribute("visibility", "visible");
    const d = dados;
    const hora = c.hora ? ` · ${c.hora[i]}` : "";
    const base = el.id === "g-chegada" && d.ordem === "oficial" ? "dos votos válidos" : "das urnas";
    mostrarDica(e, `<b>${num(c.x[i])}% ${base}${hora}</b>` +
      `<i style="background:${cor(d.a.nr)}"></i>${nome(d.ano, d.a.nr)} ${num(c.a[i], 2)}%<br>` +
      `<i style="background:${cor(d.b.nr)}"></i>${nome(d.ano, d.b.nr)} ${num(c.b[i], 2)}%`);
  };
  svg.addEventListener("pointermove", mover);
  svg.addEventListener("pointerleave", () => { mira.setAttribute("visibility", "hidden"); esconderDica(); });
}

function mostrarDica(e, html) {
  const d = $("dica");
  d.innerHTML = html;
  d.hidden = false;
  const w = d.offsetWidth;
  d.style.left = `${Math.min(innerWidth - w - 8, e.clientX + 14)}px`;
  d.style.top = `${Math.max(8, e.clientY - d.offsetHeight - 10)}px`;
}
const esconderDica = () => { $("dica").hidden = true; };

function tabelaCurva() {
  const d = dados, c = d.curva, s = d.sorteada.exemplo;
  const linhas = [];
  for (const alvo of [1, 5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 95, 100]) {
    const i = indice(c.x, alvo), j = indice(s.x, alvo);
    linhas.push(`<tr><td class="n">${alvo}%</td>${c.hora ? `<td class="n">${c.hora[i]}</td>` : ""}<td class="n">${num(c.a[i], 2)}%</td><td class="n">${num(c.b[i], 2)}%</td><td class="n">${num(s.a[j], 2)}%</td><td class="n">${num(s.b[j], 2)}%</td></tr>`);
  }
  const A = nome(d.ano, d.a.nr), B = nome(d.ano, d.b.nr);
  $("tabela-curva").innerHTML = `<div class="rolagem"><table><thead><tr><th class="n">Urnas</th>${c.hora ? `<th class="n">Hora</th>` : ""}<th class="n">${A}, chegada</th><th class="n">${B}, chegada</th><th class="n">${A}, sorteio</th><th class="n">${B}, sorteio</th></tr></thead><tbody>${linhas.join("")}</tbody></table></div>`;
}

/* Mapa */
let pontos = [];
function prepararMapa() {
  const cv = $("mapa"), r = cv.parentElement.getBoundingClientRect();
  const dpr = devicePixelRatio || 1;
  cv.width = r.width * dpr;
  cv.height = r.height * dpr;
  const lon0 = -74.2, lon1 = -34.6, lat0 = 5.4, lat1 = -33.9;
  const cosLat = Math.cos((14 * Math.PI) / 180);
  const escala = Math.min(r.width / ((lon1 - lon0) * cosLat), r.height / (lat0 - lat1));
  const ox = (r.width - (lon1 - lon0) * cosLat * escala) / 2;
  const oy = (r.height - (lat0 - lat1) * escala) / 2;
  const est = getComputedStyle(document.documentElement);
  const cores = {
    13: est.getPropertyValue("--vermelho").trim(),
    outro: est.getPropertyValue("--azul").trim(),
    apagado: est.getPropertyValue("--apagado").trim(),
  };
  const fator = r.width / 520;
  pontos = dados.municipios.map(([la, lo, a, b, pos, nm]) => ({
    x: ox + (lo - lon0) * cosLat * escala,
    y: oy + (lat0 - la) * escala,
    raio: Math.max(1, Math.min(11, Math.sqrt(a + b) / 62)) * fator,
    pos, nm, a, b,
    cor: (a >= b ? dados.a.nr : dados.b.nr) === 13 ? cores[13] : cores.outro,
  })).sort((p, q) => q.raio - p.raio);
  cv._cores = cores;
  cv._dpr = dpr;
  cv._w = r.width;
  cv._h = r.height;
  desenharMapa();
}

function desenharMapa() {
  const cv = $("mapa"), g = cv.getContext("2d");
  g.setTransform(cv._dpr, 0, 0, cv._dpr, 0, 0);
  g.clearRect(0, 0, cv._w, cv._h);
  for (const p of pontos) {
    const aceso = p.pos <= progresso;
    g.globalAlpha = aceso ? 0.72 : 0.55;
    g.fillStyle = aceso ? p.cor : cv._cores.apagado;
    g.beginPath();
    g.arc(p.x, p.y, aceso ? p.raio : 1, 0, 6.2832);
    g.fill();
  }
  g.globalAlpha = 1;
}

function ligarMapa() {
  const cv = $("mapa");
  cv.addEventListener("pointermove", (e) => {
    const r = cv.getBoundingClientRect();
    const x = e.clientX - r.left, y = e.clientY - r.top;
    let melhor = null, dist = 24 * 24;
    for (const p of pontos) {
      const d = (p.x - x) ** 2 + (p.y - y) ** 2;
      if (d < dist) { dist = d; melhor = p; }
    }
    if (!melhor) return esconderDica();
    const t = melhor.a + melhor.b || 1, d = dados;
    mostrarDica(e, `<b>${esc(melhor.nm)}</b>${nome(d.ano, d.a.nr)} ${inteiro(melhor.a)} (${num(melhor.a / t * 100)}%)<br>${nome(d.ano, d.b.nr)} ${inteiro(melhor.b)} (${num(melhor.b / t * 100)}%)<br>Acende em ${num(melhor.pos)}% das urnas`);
  });
  cv.addEventListener("pointerleave", esconderDica);
}

function regioes() {
  const d = dados, i = Math.round(progresso);
  $("regioes").innerHTML = d.regioes.map((r) => `<div class="regiao"><span>${r.nome}</span><div class="trilho"><div class="barra" style="width:${r.apurado[i]}%"></div></div><output>${num(r.apurado[i], 0)}%</output><div class="regiao-nota">${nome(d.ano, d.a.nr)} ${num(r.a)}% · ${nome(d.ano, d.b.nr)} ${num(r.b)}%</div></div>`).join("");
}

function atualizarProgresso() {
  atualizarLinhas();
  desenharMapa();
  regioes();
  const c = dados.curva, i = indice(c.x, progresso);
  $("progresso-txt").textContent = `${num(progresso)}% ${dados.ordem === "oficial" ? "dos votos" : "das urnas"}${c.hora ? ` · ${c.hora[i]}` : ""}`;
}

function parar() {
  if (tocando) cancelAnimationFrame(tocando);
  tocando = null;
  $("tocar").textContent = "▶";
  $("tocar").setAttribute("aria-label", "Reproduzir a apuração");
}

function tocar() {
  if (tocando) return parar();
  if (progresso >= 100) progresso = 0;
  const inicio = performance.now(), de = progresso, dur = 16000 * (1 - de / 100);
  $("tocar").textContent = "❚❚";
  $("tocar").setAttribute("aria-label", "Pausar");
  const passo = (t) => {
    const f = Math.min(1, (t - inicio) / dur);
    progresso = de + (100 - de) * f;
    $("progresso").value = progresso;
    atualizarProgresso();
    if (f < 1) tocando = requestAnimationFrame(passo); else parar();
  };
  tocando = requestAnimationFrame(passo);
}

/* Amostras */
function margemDoVideo(n) {
  if (dados.ano !== 2026 || dados.turno !== 2 || !video) return "";
  const l = video.video.find((x) => x.item === `Margem de erro com ${inteiro(n)} urnas`);
  return l && !l.igual ? `<small class="diverge">no vídeo: ${esc(l.video)}</small>` : "";
}

function amostras() {
  const d = dados, nr = d.a.nr, A = nome(d.ano, nr);
  $("sub-amostra").textContent = `Cada ponto é um sorteio de urnas, e mostra o percentual de ${A} nesse sorteio. A linha marca o resultado final, ${num(d.a.pct)}%.`;
  const todos = d.amostras[0].pontos;
  const lo = Math.floor(Math.min(...todos) / 5) * 5, hi = Math.ceil(Math.max(...todos) / 5) * 5;
  const L = 600, sx = (v) => 8 + ((v - lo) / (hi - lo)) * (L - 16);
  const linhas = d.amostras.map((a) => {
    const cx = a.pontos.map((v, i) => {
      const j = ((i * 2654435761) >>> 0) % 1000 / 1000;
      return `<circle cx="${sx(v).toFixed(1)}" cy="${(10 + j * 52).toFixed(1)}" r="2.5"/>`;
    }).join("");
    return `<div class="amostra"><div><b>${inteiro(a.n)} urnas</b><small>${num(a.pct_das_urnas, a.pct_das_urnas < 0.1 ? 3 : 2)}% do total</small></div>` +
      `<svg viewBox="0 0 ${L} 72" preserveAspectRatio="none" role="img" aria-label="${a.pontos.length} sorteios de ${a.n} urnas"><line x1="${sx(d.a.pct)}" x2="${sx(d.a.pct)}" y1="0" y2="72" stroke="var(--texto)" stroke-width="1"/><g fill="${cor(nr)}" opacity=".5">${cx}</g></svg>` +
      `<div class="num"><b>±${num(a.erro_95)} ponto${a.erro_95 >= 2 ? "s" : ""}</b><small>líder certo em ${num(a.acerta_lider, 1)}%</small>${margemDoVideo(a.n)}</div></div>`;
  }).join("");
  let marcas = "";
  for (let v = lo; v <= hi; v += hi - lo > 40 ? 10 : 5) marcas += `<text x="${sx(v)}" y="16" text-anchor="middle">${v}%</text>`;
  $("amostras").innerHTML = linhas + `<div class="amostra"><div></div><svg class="eixo-amostra" viewBox="0 0 ${L} 24" style="height:24px" aria-hidden="true">${marcas}</svg><div></div></div>`;
}

/* Comparação entre turnos */
function multiplos() {
  const L = 200, H = 110;
  const todos = resumo.turnos.flatMap((t) => t.mini.x.map((x, i) => (x >= 1 ? Math.abs(t.mini.a[i] - t.mini.b[i]) : 0)));
  const lim = Math.ceil(Math.max(...todos) / 5) * 5;
  $("multiplos").innerHTML = resumo.turnos.map((t) => {
    const sx = (x) => 2 + (x / 100) * (L - 4), sy = (v) => H / 2 - (v / lim) * (H / 2 - 4);
    const dif = t.mini.a.map((v, i) => v - t.mini.b[i]);
    return `<button class="mini" type="button" data-ano="${t.ano}" data-turno="${t.turno}" aria-pressed="false" aria-label="${rotuloTurno(t)}"><b>${t.ano}, ${t.turno}º</b><small>ordem ${t.ordem}</small>` +
      `<svg viewBox="0 0 ${L} ${H}" aria-hidden="true"><line class="eixo" x1="0" x2="${L}" y1="${H / 2}" y2="${H / 2}"/><path d="${caminho(t.mini.x, dif, sx, (v) => sy(Math.max(-lim, Math.min(lim, v))))}" fill="none" stroke="var(--texto-2)" stroke-width="2"/></svg></button>`;
  }).join("");
  $("multiplos").addEventListener("click", (e) => {
    const b = e.target.closest(".mini");
    if (b) escolher(+b.dataset.ano, +b.dataset.turno);
  });
}

function tabelaTurnos() {
  const cab = ["Turno", "Ordem", "Resultado", "Urnas", "Trocas, ordem de chegada", "Trocas, ordem sorteada", "Maior distância do final, chegada", "Maior distância do final, sorteio", "Erro com 1.000 urnas"];
  const linhas = resumo.turnos.map((t) => {
    const a = t.amostras.find((x) => x.n === 1000);
    return `<tr class="clicavel" data-ano="${t.ano}" data-turno="${t.turno}" aria-selected="false"><td>${t.ano}, ${t.turno}º</td><td><span class="selo">${t.ordem}</span></td>` +
      `<td>${nome(t.ano, t.a.nr)} ${num(t.a.pct)} · ${nome(t.ano, t.b.nr)} ${num(t.b.pct)}</td><td class="n">${inteiro(t.urnas)}</td>` +
      `<td class="n">${t.ordem !== "estimada" ? t.viradas.length : "–"}</td><td class="n">${num(t.sorteios_ordem.viradas_media, 2)}</td><td class="n">${t.ordem !== "estimada" ? num(t.distancia_max) : "–"}</td><td class="n">${num(t.distancia_max_sorteada)}</td><td class="n">±${num(a.erro_95)}</td></tr>`;
  }).join("");
  $("tabela-turnos").innerHTML = `<thead><tr>${cab.map((c, i) => `<th class="${i > 2 ? "n" : ""}">${c}</th>`).join("")}</tr></thead><tbody>${linhas}</tbody>`;
  $("tabela-turnos").addEventListener("click", (e) => {
    const r = e.target.closest("tr.clicavel");
    if (r) escolher(+r.dataset.ano, +r.dataset.turno);
  });
}

function tabelaConferencia() {
  if (!video) return;
  const diferentes = video.video.filter((l) => !l.igual), iguais = video.video.filter((l) => l.igual);
  $("sub-divergencias").textContent = `Dos ${video.video.length} números do vídeo comparados, ${diferentes.length} ficam diferentes dos dados do TSE na mesma precisão em que o vídeo os mostra, e ${iguais.length} são iguais.`;
  $("tabela-divergencias").innerHTML = `<thead><tr><th>Item, 2º turno de 2026</th><th class="n">Vídeo</th><th class="n">Dados do TSE</th><th>Diferença</th></tr></thead><tbody>${diferentes.map((l) =>
    `<tr><td>${esc(l.item)}</td><td class="n">${esc(l.video)}</td><td class="n">${esc(l.calculado)}</td><td>${esc(l.diferenca)}</td></tr>`).join("")}</tbody>`;
  $("resumo-iguais").textContent = `Ver os ${iguais.length} itens iguais ao vídeo`;
  $("tabela-video").innerHTML = `<thead><tr><th>Item, 2º turno de 2026</th><th class="n">Vídeo</th><th class="n">Dados do TSE</th></tr></thead><tbody>${iguais.map((l) =>
    `<tr><td>${esc(l.item)}</td><td class="n">${esc(l.video)}</td><td class="n">${esc(l.calculado)}</td></tr>`).join("")}</tbody>`;
  $("tabela-oficial").innerHTML = `<thead><tr><th>Turno</th><th>Candidato</th><th class="n">Soma das urnas</th><th class="n">Total oficial TSE</th><th class="n">Diferença</th></tr></thead><tbody>${video.oficial.map((l) =>
    `<tr><td>${l.ano}, ${l.turno}º</td><td>${esc(nome(l.ano, l.nr))}</td><td class="n">${inteiro(l.urnas)}</td><td class="n">${inteiro(l.oficial)}</td><td class="n">${inteiro(l.urnas - l.oficial)}</td></tr>`).join("")}</tbody>`;
}

function teste() {
  const L = LARG, H = 260, m = { t: 12, r: 14, b: 34, l: 40 };
  $("teste").innerHTML = resumo.teste_emprestimo.map((t) => {
    const vals = [];
    t.real.x.forEach((x, i) => { if (x >= 1) vals.push(t.real.a[i], t.estimada.a[i]); });
    const lo = Math.floor(Math.min(...vals) - 0.5), hi = Math.ceil(Math.max(...vals) + 0.5);
    const passo = hi - lo > 12 ? 4 : hi - lo > 8 ? 2 : 1;
    const sx = (x) => m.l + (x / 100) * (L - m.l - m.r), sy = (v) => m.t + (1 - (v - lo) / (hi - lo)) * (H - m.t - m.b);
    let g = "";
    for (let v = lo; v <= hi; v += passo) g += `<line class="grade" x1="${m.l}" x2="${L - m.r}" y1="${sy(v)}" y2="${sy(v)}"/><text x="${m.l - 8}" y="${sy(v) + 4}" text-anchor="end">${v}%</text>`;
    for (const x of [0, 25, 50, 75, 100]) g += `<text x="${sx(x)}" y="${H - m.b + 18}" text-anchor="middle">${x}%</text>`;
    const real = t.ano === 2014 ? "Tabela oficial do TSE" : "Ordem real";
    return `<figure><figcaption>${t.ano}, ${t.turno}º turno: percentual de ${nome(t.ano, t.nr)}</figcaption><div class="legenda"><span><i style="background:var(--texto)"></i>${real}</span><span><i style="background:var(--azul)"></i>Ordem emprestada de 2018</span></div>` +
      `<div class="grafico"><svg viewBox="0 0 ${L} ${H}" role="img" aria-label="Curva verdadeira e curva estimada, ${t.ano}, ${t.turno}º turno"><defs><clipPath id="clip-t${t.ano}"><rect x="${m.l}" y="${m.t}" width="${L - m.l - m.r}" height="${H - m.t - m.b}"/></clipPath></defs>${g}` +
      `<g clip-path="url(#clip-t${t.ano})"><path d="${caminho(t.real.x, t.real.a, sx, sy)}" fill="none" stroke="var(--texto)" stroke-width="2"/><path d="${caminho(t.estimada.x, t.estimada.a, sx, sy)}" fill="none" stroke="var(--azul)" stroke-width="2"/></g></svg></div>` +
      `<p class="sub">Eixo: votos válidos já apurados. Diferença média entre as curvas: ${num(t.erro_medio, 2)} ponto${t.erro_medio >= 2 ? "s" : ""}; maior diferença: ${num(t.erro_max, 2)} pontos. Trocas de liderança: ${t.viradas_real.length ? t.viradas_real.map((v) => num(v) + "%").join(", ") : "nenhuma"} na curva verdadeira; ${t.viradas_estimada.length ? t.viradas_estimada.map((v) => num(v) + "%").join(", ") : "nenhuma"} na estimada.</p></figure>`;
  }).join("");
}

function tabelaMarcos() {
  if (!video?.marcos) return;
  const fmtValores = (ano, v) => Object.entries(v).map(([nr, p]) => `${nome(ano, +nr)} ${num(p, 2)}%`).join(" · ");
  const tipoHora = (m) => !m.hora ? "sem hora" : m.tipo === "publicacao" ? `${m.hora} (publicação)` : m.hora;
  const linhas = video.marcos.map((m) => {
    const noPonto = Object.entries(m.valores).map(([nr]) => `${nome(m.ano, +nr)} ${num(m.curva[nr], 2)}%`).join(" · ");
    const pontoHora = m.hora_curva ? ` · ${m.hora_curva}` : "";
    const pontoX = m.x != null ? `${num(m.x)}%${pontoHora}` : "";
    return `<tr><td>${m.ano}, ${m.turno}º<br><span class="selo">${m.ordem}</span></td><td>${tipoHora(m)}</td><td class="n">${m.urnas != null ? num(m.urnas, m.urnas % 1 ? 2 : 0) + "%" : "–"}</td>` +
      `<td>${fmtValores(m.ano, m.valores) || "–"}${m.nota ? `<small>${esc(m.nota)}</small>` : ""}</td><td>${noPonto || "–"}<small>${pontoX}</small></td>` +
      `<td><a class="fonte${m.oficial ? " oficial" : ""}" href="${esc(m.url)}" target="_blank" rel="noopener">${esc(m.fonte)}</a><small>${esc(m.data)}</small></td></tr>`;
  }).join("");
  $("tabela-marcos").innerHTML = `<thead><tr><th>Turno</th><th>Hora registrada</th><th class="n">Urnas registradas</th><th>Número registrado</th><th>Esta tela no mesmo ponto</th><th>Fonte</th></tr></thead><tbody>${linhas}</tbody>`;
}

async function iniciar() {
  montarFiltro();
  try {
    resumo = await json("dados/resumo.json");
  } catch (_) {
    $("aviso").textContent = "Os dados ainda estão sendo calculados. Atualize a página daqui a pouco.";
    return;
  }
  try { video = await json("dados/conferencia.json"); } catch (_) { video = null; }
  multiplos();
  tabelaTurnos();
  tabelaConferencia();
  tabelaMarcos();
  teste();
  ligarMapa();
  $("tocar").addEventListener("click", tocar);
  $("progresso").addEventListener("input", (e) => {
    parar();
    progresso = +e.target.value;
    atualizarProgresso();
  });
  addEventListener("resize", () => { if (dados) prepararMapa(); });
  const m = location.hash.match(/^#(\d{4})-([12])$/);
  await escolher(m ? +m[1] : 2026, m ? +m[2] : 2);
}

iniciar();
