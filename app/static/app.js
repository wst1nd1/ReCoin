"use strict";

// Значки разделов. Кнопка в боковой панели показывает тот, что соответствует
// открытому разделу.
const ICONS = {
  upload: '<svg viewBox="0 0 24 24"><path d="M6 3h8l4 4v14a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1z"/><path d="M14 3v5h4"/></svg>',
  accounts: '<svg viewBox="0 0 24 24"><rect x="3" y="6" width="18" height="13" rx="2"/><path d="M3 10h18M7 15h4"/></svg>',
  dash: '<svg viewBox="0 0 24 24"><path d="M4 19V9M10 19V5M16 19v-7M22 19H2"/></svg>',
  questions: '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="M9.5 9.5a2.6 2.6 0 1 1 3.3 2.5c-.6.2-.8.7-.8 1.3v.4"/><circle cx="12" cy="17" r=".6" fill="currentColor"/></svg>',
  report: '<svg viewBox="0 0 24 24"><path d="M12 3a9 9 0 1 0 9 9h-9V3z"/></svg>',
  profile: '<svg viewBox="0 0 24 24"><circle cx="12" cy="8" r="4"/><path d="M5 20a7 7 0 0 1 14 0"/></svg>',
  feedback: '<svg viewBox="0 0 24 24"><path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H19v15H6.5A2.5 2.5 0 0 0 4 20.5z"/><path d="M4 20.5A2.5 2.5 0 0 1 6.5 18H19v3H6.5A2.5 2.5 0 0 1 4 20.5z"/><path d="M8 7.5h7M8 11h5"/></svg>',
};

const STEPS = [
  { id: "s-upload", slug: "vypiski", icon: "upload", group: 0, title: "Выписки",
    sub: "Загрузите PDF из банка – разберём операции и посчитаем настоящие траты." },
  { id: "s-accounts", slug: "scheta", icon: "accounts", group: 0, title: "Счета",
    sub: "Уточните назначение счетов – от этого зависят итоговые цифры." },
  { id: "s-dash", slug: "traty", icon: "dash", group: 0, title: "Траты",
    sub: "Куда уходили деньги за загруженный период." },
  { id: "s-questions", slug: "voprosy", icon: "questions", group: 1, title: "Вопросы",
    sub: "Несколько вопросов, чтобы разбор был точнее." },
  { id: "s-report", slug: "razbor", icon: "report", group: 1, title: "Разбор",
    sub: "Что получается, что мешает и что с этим делать." },
  { id: "s-profile", slug: "profil", icon: "profile", group: 2, title: "Профиль",
    sub: "Сведения об учётной записи." },
  { id: "s-feedback", slug: "otzyv", icon: "feedback", group: 3, title: "Оставить отзыв",
    sub: "Расскажите, что стоит улучшить, мы читаем всё." },
];

// Группы разделов. Каждой соответствует одна кнопка боковой панели.
const GROUPS = [
  { first: 0, label: "Разбор выписки" },
  { first: 3, label: "Итог" },
];

// Золотая гамма ведущая, остальные оттенки подобраны так, чтобы соседние
// сегменты кольца различались.
const CAT_COLORS = {
  "Продукты": "#d9a336",
  "Кафе и рестораны": "#a86e18",
  "Транспорт": "#edd08a",
  "Жильё и ЖКУ": "#2f7fa8",
  "Развлечения": "#c9873f",
  "Ставки": "#d9584a",
  "Спортзал": "#12a06a",
  "Здоровье": "#7a9e3f",
  "Одежда и красота": "#d98b7a",
  "Связь и интернет": "#8c8a7f",
  "Подписки": "#b8944a",
  "Образование": "#4a9d6b",
  "Услуги": "#a8a396",
  "Переводы": "#d2cec4",
  "Наличные": "#bdb8ab",
  // «Прочее» часто самая крупная статья, поэтому цвет заметный, а не почти белый.
  "Прочее": "#8a8578",
};

// Цвет для категорий, которых нет в списке выше.
const FALLBACK_COLOR = "#8fa0bb";

const state = {
  step: 0,
  reached: 0,
  data: null,
  questions: [],
  answers: {},
  qIndex: 0,
  accountOwner: {},
};

const $ = (id) => document.getElementById(id);

function money(value) {
  return new Intl.NumberFormat("ru-RU").format(Math.round(value)) + " ₽";
}

function catColor(name) {
  return CAT_COLORS[name] || FALLBACK_COLOR;
}

function plural(n, one, few, many) {
  const mod10 = n % 10, mod100 = n % 100;
  if (mod10 === 1 && mod100 !== 11) return one;
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 10 || mod100 >= 20)) return few;
  return many;
}

// Изменение к предыдущему месяцу: рост трат тревожен, снижение – хорошо.
function deltaMark(delta) {
  if (delta === null || delta === undefined) return "";
  const rounded = Math.round(delta);
  if (Math.abs(rounded) < 3) return `<span>без изменений</span>`;
  const color = rounded > 0 ? "var(--red)" : "var(--green)";
  return `<span style="color:${color}">${rounded > 0 ? "+" : ""}${rounded}% к прошлому месяцу</span>`;
}

/* ---------- навигация ---------- */

// Последний открытый раздел каждой группы. Кнопка возвращает туда, где
// пользователь остановился, а не в начало группы. Третья группа – отзыв,
// её кнопка стоит отдельно внизу панели.
const lastInGroup = [0, 3, 5, 6];
const PROFILE_STEP = 5;
const FEEDBACK_STEP = 6;
// Разделы вне ленты разбора: попадать в них можно всегда, и они не
// открывают шаги, до которых пользователь ещё не дошёл.
const SIDE_STEPS = new Set([PROFILE_STEP, FEEDBACK_STEP]);

function renderRail() {
  const current = STEPS[state.step];

  $("rail-nav").innerHTML = GROUPS.map((group, index) => {
    const inGroup = current.group === index;
    // На кнопке значок открытого раздела, если группа активна,
    // иначе значок того раздела, где пользователь был в ней последний раз.
    const step = STEPS[inGroup ? state.step : lastInGroup[index]];
    const locked = group.first > state.reached;
    return `
      <button class="rail-btn${inGroup ? " active" : ""}" data-group="${index}"
              title="${inGroup ? step.title : group.label}"
              aria-label="${inGroup ? step.title : group.label}"
              ${locked ? "disabled" : ""}>${ICONS[step.icon]}</button>`;
  }).join("");

  $("rail-nav").querySelectorAll("[data-group]").forEach((btn) => {
    btn.onclick = () => {
      const index = Number(btn.dataset.group);
      if (GROUPS[index].first > state.reached) return;
      go(lastInGroup[index]);
    };
  });

  $("feedback-btn").classList.toggle("active", state.step === FEEDBACK_STEP);
}

function go(index, push = true) {
  state.step = index;
  // Отзыв доступен всегда и не считается пройденным шагом разбора,
  // иначе он открыл бы разделы, до которых пользователь ещё не дошёл.
  if (!SIDE_STEPS.has(index)) {
    state.reached = Math.max(state.reached, index);
  }
  lastInGroup[STEPS[index].group] = index;

  document.querySelectorAll(".screen").forEach((el) => el.classList.remove("on"));
  $(STEPS[index].id).classList.add("on");

  $("page-title").textContent = STEPS[index].title;
  $("page-sub").textContent = STEPS[index].sub;

  renderRail();
  paintFooterLinks();

  // Каждый переход попадает в историю браузера, поэтому разделы внутри
  // группы листаются его стрелками «назад» и «вперёд».
  if (push) {
    history.pushState({ step: index }, "", `#${STEPS[index].slug}`);
  }

  window.scrollTo({ top: 0, behavior: "smooth" });
}

window.addEventListener("popstate", (event) => {
  const step = event.state && typeof event.state.step === "number" ? event.state.step : 0;
  if (SIDE_STEPS.has(step) || step <= state.reached) go(step, false);
});

$("feedback-btn").onclick = () => go(FEEDBACK_STEP);

// Ссылки подвала ведут в разделы кабинета. Недоступные пока разделы
// показываются приглушённо и не срабатывают.
document.querySelectorAll("[data-go]").forEach((link) => {
  link.addEventListener("click", (event) => {
    event.preventDefault();
    const index = Number(link.dataset.go);
    if (!SIDE_STEPS.has(index) && index > state.reached) return;
    go(index);
  });
});

function paintFooterLinks() {
  document.querySelectorAll("[data-go]").forEach((link) => {
    const index = Number(link.dataset.go);
    const locked = !SIDE_STEPS.has(index) && index > state.reached;
    link.classList.toggle("locked", locked);
  });
}

/* ---------- меню профиля ---------- */

const userBtn = $("user-btn");
const userMenu = $("user-menu");

function closeUserMenu() {
  userMenu.hidden = true;
  userBtn.setAttribute("aria-expanded", "false");
}

userBtn.onclick = (e) => {
  e.stopPropagation();
  const open = userMenu.hidden;
  userMenu.hidden = !open;
  userBtn.setAttribute("aria-expanded", String(open));
};

document.addEventListener("click", () => { if (!userMenu.hidden) closeUserMenu(); });
document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeUserMenu(); });

$("logout").onclick = async () => {
  await fetch("/api/auth/logout", { method: "POST" });
  location.href = "/";
};

/* ---------- загрузка ---------- */

const drop = $("drop");
const fileInput = $("file");

["dragenter", "dragover"].forEach((ev) =>
  drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.add("hot"); })
);
["dragleave", "drop"].forEach((ev) =>
  drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.remove("hot"); })
);
drop.addEventListener("drop", (e) => {
  if (e.dataTransfer.files.length) upload(e.dataTransfer.files);
});
fileInput.addEventListener("change", () => {
  if (fileInput.files.length) upload(fileInput.files);
});
$("add-more").onclick = () => fileInput.click();

async function upload(files) {
  const form = new FormData();
  for (const f of files) form.append("files", f);

  drop.classList.add("busy");
  $("drop-title").textContent = "Читаю выписку…";
  $("drop-sub").textContent = files.length > 1 ? `${files.length} файла` : files[0].name;
  $("upload-error").innerHTML = "";

  try {
    const res = await fetch("/api/upload", { method: "POST", body: form });
    const body = await res.json();
    if (res.status === 401) { location.href = "/"; return; }
    if (!res.ok) throw new Error(body.detail || "Не удалось разобрать файл");

    state.data = body;
    renderFiles(body);
    renderAccounts(body);
    $("upload-actions").hidden = false;
    $("drop-title").textContent = "Выписка загружена";
    $("drop-sub").textContent = "можно добавить ещё одну";
  } catch (err) {
    $("upload-error").innerHTML = `<div class="err">${err.message}</div>`;
    $("drop-title").textContent = "Перетащите выписку в PDF";
    $("drop-sub").textContent = "или нажмите, чтобы выбрать файл";
  } finally {
    drop.classList.remove("busy");
    fileInput.value = "";
  }
}

function renderFiles(data) {
  const rows = data.statements.map((s) => `
    <div class="file">
      <span class="ok">✓</span>
      <div>
        <b>${s.source}</b>
        <div class="muted">${s.bank}${s.period ? ", " + s.period : ""}</div>
      </div>
      <span class="meta">${s.parsed} ${plural(s.parsed, "операция", "операции", "операций")}</span>
    </div>`).join("");

  const notes = (data.notes || []).map((n) => `<p class="muted">${n}</p>`).join("");
  const problems = (data.problems || []).length
    ? `<div class="err">${data.problems.join("<br>")}</div>` : "";

  $("files").innerHTML = rows + notes + problems;
}

/* ---------- счета ---------- */

function accountCard(a) {
  return `
    <div class="acc">
      <div class="who">
        <b>${a.title}</b>
        <div class="flow">
          пришло <em>${money(a.incoming)}</em> · ушло <em>${money(a.outgoing)}</em> ·
          ${a.netto < 0 ? "не вернулось" : "сверх ушедшего"} <em>${money(Math.abs(a.netto))}</em>
        </div>
      </div>
      <select data-key="${a.key}" class="acc-type">
        <option value="unknown"${a.type === "unknown" ? " selected" : ""}>Выберите назначение</option>
        <option value="savings"${a.type === "savings" ? " selected" : ""}>Накопительный счёт или вклад</option>
        <option value="credit"${a.type === "credit" ? " selected" : ""}>Кредитная карта</option>
        <option value="neutral"${a.type === "neutral" ? " selected" : ""}>Другая моя карта</option>
      </select>
    </div>`;
}

// Счёт, который мы не опознали: спрашиваем «чей он», а не что за тип –
// тип станет ясен только после загрузки его выписки.
function pendingCard(p) {
  const picked = state.accountOwner[p.key];
  const btn = (value, label) =>
    `<button class="choice-btn${picked === value ? " picked" : ""}"
       data-key="${p.key}" data-choice="${value}">${label}</button>`;
  return `
    <div class="acc">
      <div class="who">
        <b>${p.title}</b>
        <div class="flow">пришло <em>${money(p.incoming)}</em> · ушло <em>${money(p.outgoing)}</em></div>
      </div>
      <div class="choice-buttons">
        ${btn("self", "Мой второй счёт")}
        ${btn("other", "Счёт другого человека")}
      </div>
    </div>`;
}

function awaitingCard(a) {
  return `
    <div class="acc awaiting">
      <div class="who">
        <b>${a.title}</b>
        <div class="flow">пришло <em>${money(a.incoming)}</em> · ушло <em>${money(a.outgoing)}</em> – ждём выписку по этому счёту</div>
      </div>
      <button class="btn ghost" data-goto-upload>Загрузить выписку</button>
    </div>`;
}

function renderAccounts(data) {
  const accounts = data.accounts || [];
  const pending = data.pending_accounts || [];
  const awaiting = data.awaiting_statements || [];

  $("accounts-title").hidden = !accounts.length;
  $("accounts-list").innerHTML = accounts.map(accountCard).join("");

  $("pending-title").hidden = !pending.length;
  $("pending-hint").hidden = !pending.length;
  $("pending-list").innerHTML = pending.map(pendingCard).join("");

  $("awaiting-list").innerHTML = awaiting.map(awaitingCard).join("");
  $("awaiting-list").querySelectorAll("[data-goto-upload]").forEach((btn) => {
    btn.onclick = () => go(0);
  });

  $("pending-list").querySelectorAll(".choice-btn").forEach((btn) => {
    btn.onclick = () => {
      state.accountOwner[btn.dataset.key] = btn.dataset.choice;
      renderAccounts(data);
    };
  });

  $("accounts-empty").hidden = accounts.length + pending.length + awaiting.length > 0;
}

async function saveAccounts() {
  const account_types = {};
  document.querySelectorAll(".acc-type").forEach((el) => {
    if (el.value !== "unknown") account_types[el.dataset.key] = el.value;
  });

  const res = await fetch("/api/accounts", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ account_types, account_owner: state.accountOwner }),
  });
  if (res.status === 401) { location.href = "/"; return state.data; }
  state.data = await res.json();
  return state.data;
}

/* ---------- графика ---------- */

const CHART = { w: 660, h: 168, padL: 12, padR: 12, padT: 26, padB: 28 };

// Гладкая кривая по опорным точкам (Catmull-Rom, переведённый в кубические кривые).
function smoothPath(points, tension = 0.32) {
  if (points.length < 2) return "";
  let path = `M ${points[0][0].toFixed(1)} ${points[0][1].toFixed(1)}`;
  for (let i = 0; i < points.length - 1; i++) {
    const p0 = points[i - 1] || points[i];
    const p1 = points[i];
    const p2 = points[i + 1];
    const p3 = points[i + 2] || p2;
    const c1x = p1[0] + (p2[0] - p0[0]) * tension;
    const c1y = p1[1] + (p2[1] - p0[1]) * tension;
    const c2x = p2[0] - (p3[0] - p1[0]) * tension;
    const c2y = p2[1] - (p3[1] - p1[1]) * tension;
    path += ` C ${c1x.toFixed(1)} ${c1y.toFixed(1)}, ${c2x.toFixed(1)} ${c2y.toFixed(1)}, ${p2[0].toFixed(1)} ${p2[1].toFixed(1)}`;
  }
  return path;
}

function chartGeometry(months) {
  const { w, h, padL, padR, padT, padB } = CHART;
  const values = months.map((m) => m.amount);
  const max = Math.max(...values, 1);
  const min = Math.min(...values, 0);
  const span = max - min || 1;

  const x = (i) => padL + (i * (w - padL - padR)) / Math.max(1, months.length - 1);
  const y = (v) => padT + (1 - (v - min) / span) * (h - padT - padB);
  return { x, y, max, min, points: months.map((m, i) => [x(i), y(m.amount)]) };
}

// Линия трат по месяцам: заливка, средний уровень, точка и подсказка под курсором.
function spark(months) {
  if (!months.length) return "";
  const { w, h, padL, padR, padB } = CHART;
  const { x, y, points } = chartGeometry(months);
  const avg = months.reduce((s, m) => s + m.amount, 0) / months.length;

  const line = smoothPath(points);
  const area = `${line} L ${x(months.length - 1).toFixed(1)} ${h - padB} L ${padL} ${h - padB} Z`;

  const guides = months.map((_, i) =>
    `<line class="guide" x1="${x(i).toFixed(1)}" y1="${CHART.padT - 8}" x2="${x(i).toFixed(1)}" y2="${h - padB}"/>`
  ).join("");

  // Подписи только по краям и в середине, иначе на годовом периоде каша.
  const marks = new Set([0, Math.floor((months.length - 1) / 2), months.length - 1]);
  const labels = months.map((m, i) =>
    marks.has(i)
      ? `<text x="${x(i).toFixed(1)}" y="${h - 8}" text-anchor="${i === 0 ? "start" : i === months.length - 1 ? "end" : "middle"}">${m.label.replace(/ \d{4}$/, "")}</text>`
      : ""
  ).join("");

  return `
    <div class="chart-holder" id="chart-holder">
      <svg class="spark" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none"
           role="img" aria-label="Траты по месяцам" id="spark">
        <defs>
          <linearGradient id="areaFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#d9a336" stop-opacity="0.3"/>
            <stop offset="55%" stop-color="#d9a336" stop-opacity="0.12"/>
            <stop offset="100%" stop-color="#d9a336" stop-opacity="0.02"/>
          </linearGradient>
        </defs>
        ${guides}
        <path class="band draw" d="${area}"/>
        <line class="avg" x1="${padL}" y1="${y(avg).toFixed(1)}" x2="${w - padR}" y2="${y(avg).toFixed(1)}"/>
        <path class="line draw" id="spark-line" d="${line}"/>
        <g id="spark-cursor"></g>
        ${labels}
      </svg>
      <div class="chart-tip" id="chart-tip" hidden></div>
    </div>`;
}

// Наведение на график: ближайшая точка подсвечивается, подсказка идёт следом.
function bindChart(months) {
  const svg = $("spark");
  const holder = $("chart-holder");
  const tip = $("chart-tip");
  const cursor = $("spark-cursor");
  if (!svg || !months.length) return;

  const { x, y } = chartGeometry(months);
  const { w, h } = CHART;

  // Линия рисуется от начала к концу при появлении блока.
  const path = $("spark-line");
  if (path) path.style.setProperty("--len", Math.ceil(path.getTotalLength()));

  const show = (index) => {
    const px = x(index);
    const py = y(months[index].amount);
    cursor.innerHTML = `
      <circle class="halo" cx="${px.toFixed(1)}" cy="${py.toFixed(1)}" r="13"/>
      <circle class="hot-dot" cx="${px.toFixed(1)}" cy="${py.toFixed(1)}" r="6"/>`;
    tip.hidden = false;
    tip.style.left = `${(px / w) * 100}%`;
    tip.style.top = `${(py / h) * 100}%`;
    tip.innerHTML = `${money(months[index].amount)}<small>${months[index].label}</small>`;
  };

  const nearest = (clientX) => {
    const rect = svg.getBoundingClientRect();
    const local = ((clientX - rect.left) / rect.width) * w;
    let best = 0;
    let bestDist = Infinity;
    months.forEach((_, i) => {
      const dist = Math.abs(x(i) - local);
      if (dist < bestDist) { bestDist = dist; best = i; }
    });
    return best;
  };

  holder.addEventListener("mousemove", (e) => show(nearest(e.clientX)));
  holder.addEventListener("touchstart", (e) => show(nearest(e.touches[0].clientX)), { passive: true });
  holder.addEventListener("touchmove", (e) => show(nearest(e.touches[0].clientX)), { passive: true });
  holder.addEventListener("mouseleave", () => {
    tip.hidden = true;
    cursor.innerHTML = "";
  });

  show(months.length - 1);
}

// Кольцо категорий: сегменты появляются по очереди, наведение подсвечивает долю.
function donut(categories) {
  const size = 196, stroke = 26, r = (size - stroke) / 2, c = 2 * Math.PI * r;
  const total = categories.reduce((s, x) => s + x.amount, 0) || 1;
  let offset = 0;

  const arcs = categories.map((cat, i) => {
    const len = (cat.amount / total) * c;
    const seg = `<circle class="donut-seg" data-index="${i}"
      cx="${size / 2}" cy="${size / 2}" r="${r}" fill="none"
      stroke="${catColor(cat.name)}" stroke-width="${stroke}" stroke-linecap="round"
      stroke-dasharray="0 ${c}" stroke-dashoffset="${-offset}"
      transform="rotate(-90 ${size / 2} ${size / 2})"
      style="transition: stroke-dasharray 0.8s cubic-bezier(0.25,0.8,0.3,1) ${(i * 0.06).toFixed(2)}s, filter 0.2s, opacity 0.2s"
      data-len="${Math.max(len - 3, 0).toFixed(2)} ${(c - len + 3).toFixed(2)}"></circle>`;
    offset += len;
    return seg;
  }).join("");

  return `
    <div class="donut-holder" id="donut-holder">
      <svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}"
           role="img" aria-label="Доли категорий трат" id="donut">
        <circle class="donut-track" cx="${size / 2}" cy="${size / 2}" r="${r}" fill="none"
                stroke-width="${stroke}"/>
        ${arcs}
      </svg>
      <div class="donut-center" id="donut-center">
        <div class="val num">${money(total)}</div>
        <div class="pct">за период</div>
      </div>
    </div>`;
}

function bindDonut(categories) {
  const svg = $("donut");
  const center = $("donut-center");
  if (!svg) return;

  const segments = [...svg.querySelectorAll(".donut-seg")];
  const total = categories.reduce((s, x) => s + x.amount, 0) || 1;

  // Запуск отрисовки после вставки в документ.
  requestAnimationFrame(() => {
    segments.forEach((seg) => { seg.setAttribute("stroke-dasharray", seg.dataset.len); });
  });

  const reset = () => {
    segments.forEach((s) => { s.classList.remove("dim"); s.style.filter = "none"; });
    document.querySelectorAll(".legend-row").forEach((r) => r.classList.remove("hot"));
    center.innerHTML = `<div class="val num">${money(total)}</div><div class="pct">за период</div>`;
  };

  const highlight = (index) => {
    const cat = categories[index];
    if (!cat) return;
    segments.forEach((s, i) => {
      s.classList.toggle("dim", i !== index);
      s.style.filter = i === index ? `drop-shadow(0 0 6px ${catColor(cat.name)})` : "none";
    });
    document.querySelectorAll(".legend-row").forEach((r, i) => r.classList.toggle("hot", i === index));
    center.innerHTML = `
      <div class="cap">${cat.name}</div>
      <div class="val num">${money(cat.amount)}</div>
      <div class="pct num">${cat.share}%</div>`;
  };

  segments.forEach((seg, i) => {
    seg.addEventListener("mouseenter", () => highlight(i));
  });
  svg.addEventListener("mouseleave", reset);

  document.querySelectorAll(".legend-row").forEach((row, i) => {
    row.addEventListener("mouseenter", () => highlight(i));
    row.addEventListener("mouseleave", reset);
  });
}

/* ---------- дашборд ---------- */

function renderDash(d) {
  const t = d.totals;
  const saved = t.gross_expense - t.net_expense;
  const months = d.months_detail || [];
  const monthMax = Math.max(...months.map((m) => m.amount), 1);

  const extras = [
    `<div><span>Из них покупки</span><b class="num">${money(t.living_expense)}</b></div>`,
    `<div><span>Покупок в месяц</span><b class="num">${money(t.per_month)}</b></div>`,
  ];
  if (t.saved_to_savings > 0) extras.push(`<div><span>Отложено на вклады</span><b class="num" style="color:var(--green)">${money(t.saved_to_savings)}</b></div>`);
  if (t.debt_increased > 0) extras.push(`<div><span>Долг вырос на</span><b class="num" style="color:var(--red)">${money(t.debt_increased)}</b></div>`);
  if (t.debt_repaid > 0) extras.push(`<div><span>Погашено долга</span><b class="num">${money(t.debt_repaid)}</b></div>`);
  if (t.lent_not_returned > 0) extras.push(`<div><span>Одолжено и не вернулось</span><b class="num">${money(t.lent_not_returned)}</b></div>`);

  // Пока загружена одна выписка, часть картины скрыта – предлагаем догрузить.
  const promo = d.statements.length === 1 ? `
    <div class="promo">
      <h3>Видно не всё</h3>
      <p>Покупки, оплаченные с других карт, в эту выписку не попадают. Добавьте выписки
         по остальным счетам – переводы между ними схлопнутся сами.</p>
      <div class="promo-actions">
        <button class="btn" onclick="go(0)">Добавить выписку</button>
        <button class="btn quiet" id="single-card">У меня одна карта</button>
      </div>
      <p class="promo-answer" id="single-card-answer" hidden>Тогда картина полная,
         добавлять нечего. Если позже появится вторая карта или накопительный счёт,
         загрузите выписку по нему, и переводы между счетами перестанут выглядеть тратами.</p>
    </div>` : "";

  $("dash").innerHTML = `
    <div class="verdict">
      <div>
        <p class="lead">Банк насчитал расходов</p>
        <div class="struck num">${money(t.gross_expense)}</div>
        <div class="real num">${money(t.net_expense)}<small>потрачено на самом деле</small></div>
        <p class="why">Разница ${money(saved)} – это переводы между вашими счетами,
           возвращённые долги и деньги, отложенные на вклады. Тратами они не являются.</p>
      </div>
      <aside>${extras.join("")}</aside>
    </div>

    <div class="grid three" style="margin-bottom:14px">
      <div class="card stat"><b class="num">${money(t.average_check)}</b><span>средний чек</span></div>
      <div class="card stat"><b class="num">${t.operations}</b><span>операций разобрано</span></div>
      <div class="card stat sand explain" id="optional-card" tabindex="0" role="button" aria-expanded="false">
        <b class="num">${t.optional_share}%</b>
        <span>необязательные траты</span>
        <div class="explain-body"><span>Сюда попадают кафе и доставка, развлечения,
          ставки, подписки, одежда и красота. Это статьи, которые сокращаются без
          ущерба для нужного. Продукты, транспорт, жильё, здоровье и связь
          в расчёт не входят.</span></div>
      </div>
    </div>

    <div class="grid two">
      <div class="card">
        <h3>Траты по месяцам</h3>
        <p class="sub">${money(t.per_month)} в среднем · пунктир – средний уровень</p>
        ${spark(months)}
      </div>

      <div class="card">
        <h3>Куда уходят деньги</h3>
        <p class="sub">${d.categories.length} ${plural(d.categories.length, "категория", "категории", "категорий")} трат</p>
        <div class="donut-wrap">
          ${donut(d.categories.slice(0, 8))}
          <div class="legend">
            ${d.categories.slice(0, 8).map((c, i) => `
              <div class="legend-row" style="animation-delay:${(i * 0.05).toFixed(2)}s">
                <i style="background:${catColor(c.name)}"></i>
                <span class="nm">${c.name}</span>
                <span class="amt num">${money(c.amount)}</span>
                <span class="pct num">${c.share}%</span>
              </div>`).join("")}
          </div>
        </div>
      </div>
    </div>

    <div class="grid two" style="margin-top:14px">
      <div class="card">
        <h3>Где вы оставляете больше всего</h3>
        <p class="sub">по сумме за период</p>
        <div class="rows">
          ${d.merchants.slice(0, 8).map((m) => `
            <div class="row">
              <div class="t"><b>${m.name}</b><span>${m.category} · ${m.count} ${plural(m.count, "раз", "раза", "раз")}</span></div>
              <div class="v num">${money(m.amount)}</div>
            </div>`).join("")}
        </div>
      </div>

      <div>
        <div class="card">
          <h3>${d.regulars.length ? "Регулярные списания" : "Крупные покупки"}</h3>
          <p class="sub">${d.regulars.length ? "повторяются с одинаковой суммой" : "самые дорогие за период"}</p>
          <div class="rows">
            ${(d.regulars.length ? d.regulars : d.biggest).slice(0, 6).map((r) => `
              <div class="row">
                <div class="t"><b>${r.name}</b><span>${r.category}${r.count ? ` · ${r.count} ${plural(r.count, "раз", "раза", "раз")}` : ` · ${r.date}`}</span></div>
                <div class="v num">${money(r.per_year || r.amount)}${r.per_year ? "<span>в год</span>" : ""}</div>
              </div>`).join("")}
          </div>
        </div>
        ${promo ? `<div style="margin-top:14px">${promo}</div>` : ""}
      </div>
    </div>

    <div class="card" style="margin-top:14px">
      <h3>Каждый месяц</h3>
      <p class="sub">сколько потрачено и на что уходило больше всего</p>
      <div class="rows months">
        ${months.map((m, i) => `
          <div class="row month-row">
            <div class="t"><b>${m.label}</b><span>${m.count} ${plural(m.count, "операция", "операции", "операций")} · чаще всего ${m.top_category.toLowerCase()}</span></div>
            <div class="mbar-cell">
              <div class="mbar"><i data-width="${Math.max(2, (m.amount / monthMax) * 100).toFixed(1)}"
                   style="transition-delay:${(i * 0.045).toFixed(2)}s"></i></div>
            </div>
            <div class="v num">${money(m.amount)}${deltaMark(m.delta)}</div>
          </div>`).join("")}
      </div>
    </div>`;

  // Пояснение к необязательным тратам раскрывается по нажатию.
  const optional = $("optional-card");
  if (optional) {
    const toggle = () => {
      const open = optional.classList.toggle("open");
      optional.setAttribute("aria-expanded", String(open));
    };
    optional.onclick = toggle;
    optional.onkeydown = (e) => {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); toggle(); }
    };
  }

  const singleCard = $("single-card");
  if (singleCard) {
    singleCard.onclick = () => {
      $("single-card-answer").hidden = false;
      singleCard.disabled = true;
    };
  }

  // Оживляем то, что нельзя описать одной разметкой: график, кольцо и полосы.
  bindChart(months);
  bindDonut(d.categories.slice(0, 8));
  requestAnimationFrame(() => {
    document.querySelectorAll(".mbar i[data-width]").forEach((bar) => {
      bar.style.width = `${bar.dataset.width}%`;
    });
  });
}

/* ---------- вопросы ---------- */

async function loadQuestions() {
  $("quiz").innerHTML = `<div class="loading"><span class="spinner"></span>Смотрю на ваши траты и собираю вопросы…</div>`;
  const res = await fetch("/api/questions", { method: "POST" });
  if (res.status === 401) { location.href = "/"; return; }
  const body = await res.json();
  state.questions = body.questions || [];
  state.qIndex = 0;
  renderQuestion();
}

function renderQuestion() {
  const q = state.questions[state.qIndex];
  if (!q) return submitAnswers();

  const picked = state.answers[q.id];
  $("quiz").innerHTML = `
    <p class="q-count">Вопрос ${state.qIndex + 1} из ${state.questions.length}</p>
    <h2 class="q-text">${q.text}</h2>
    <p class="q-hint">${q.hint || ""}</p>
    <div class="opts">
      ${(q.options || []).map((o) => `
        <button class="opt${picked === o ? " picked" : ""}" data-value="${o.replace(/"/g, "&quot;")}">${o}</button>`).join("")}
    </div>
    <textarea id="free" placeholder="Можно ответить своими словами">${picked && !(q.options || []).includes(picked) ? picked : ""}</textarea>
    <div class="actions">
      <button class="btn" id="q-next">${state.qIndex === state.questions.length - 1 ? "Получить разбор" : "Дальше"}</button>
      ${state.qIndex > 0 ? '<button class="btn ghost" id="q-back">Назад</button>' : ""}
      <button class="btn ghost" id="q-skip">Пропустить</button>
    </div>`;

  $("quiz").querySelectorAll(".opt").forEach((el) => {
    el.onclick = () => {
      state.answers[q.id] = el.dataset.value;
      $("quiz").querySelectorAll(".opt").forEach((o) => o.classList.remove("picked"));
      el.classList.add("picked");
      $("free").value = "";
    };
  });

  $("q-next").onclick = () => {
    const free = $("free").value.trim();
    if (free) state.answers[q.id] = free;
    next();
  };
  $("q-skip").onclick = next;
  if ($("q-back")) $("q-back").onclick = () => { state.qIndex--; renderQuestion(); };
}

function next() {
  state.qIndex++;
  if (state.qIndex >= state.questions.length) submitAnswers();
  else renderQuestion();
}

async function submitAnswers() {
  go(4);
  $("report").innerHTML = `<div class="card"><div class="loading"><span class="spinner"></span>Подвожу итог…</div></div>`;
  const res = await fetch("/api/report", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ answers: state.answers }),
  });
  if (res.status === 401) { location.href = "/"; return; }
  renderReport(await res.json());
}

/* ---------- отчёт ---------- */

function ring(score) {
  const size = 126, stroke = 11, r = (size - stroke) / 2, c = 2 * Math.PI * r;
  const filled = (score / 100) * c;
  const color = score >= 70 ? "#12a06a" : score >= 45 ? "#e8b04b" : "#d9584a";
  return `<svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}" role="img"
      aria-label="Оценка ${score} из 100">
    <circle class="ring-track" cx="${size / 2}" cy="${size / 2}" r="${r}" fill="none" stroke-width="${stroke}"/>
    <circle class="ring-fill" id="ring-fill" cx="${size / 2}" cy="${size / 2}" r="${r}" fill="none"
      stroke="${color}" stroke-width="${stroke}" stroke-linecap="round"
      stroke-dasharray="0 ${c}" data-fill="${filled.toFixed(2)} ${(c - filled).toFixed(2)}"
      transform="rotate(-90 ${size / 2} ${size / 2})"/>
    <text x="${size / 2}" y="${size / 2 + 3}" text-anchor="middle" font-size="30" font-weight="500" class="num ring-score">${score}</text>
    <text x="${size / 2}" y="${size / 2 + 21}" text-anchor="middle" font-size="11" class="ring-cap">из 100</text>
  </svg>`;
}

function renderReport(r) {
  const total = (r.advice || []).reduce((s, a) => s + (a.saving_per_year || 0), 0);
  $("report").innerHTML = `
    <div class="score-head">
      ${ring(r.score)}
      <div class="txt">
        <h2>Как вы обращаетесь с деньгами</h2>
        <p>${r.score_reason || ""}</p>
      </div>
    </div>

    <div class="lists">
      <div class="card">
        <h3>Что получается</h3>
        <p class="sub">сильные стороны</p>
        <ul class="good">${(r.strengths || []).map((s) => `<li>${s}</li>`).join("")}</ul>
      </div>
      <div class="card">
        <h3>Что мешает</h3>
        <p class="sub">на что стоит посмотреть</p>
        <ul class="bad">${(r.problems || []).map((s) => `<li>${s}</li>`).join("")}</ul>
      </div>
    </div>

    <div class="section-title">${total > 0 ? `Что сделать, чтобы сэкономить до ${money(total)} в год` : "Что сделать"}</div>
    ${(r.advice || []).map((a, i) => `
      <div class="tip" style="animation-delay:${(0.1 + i * 0.06).toFixed(2)}s">
        <div>
          <h4>${a.title}</h4>
          <p>${a.text}</p>
        </div>
        ${a.saving_per_year > 0 ? `<div class="save"><b class="num">${money(a.saving_per_year)}</b><span>в год</span></div>` : ""}
      </div>`).join("")}

    ${r.offline ? `<div class="card note" style="margin-top:14px">Разбор собран по правилам без обращения к модели –
      она сейчас недоступна. Цифры точные, формулировки проще обычного.</div>` : ""}`;

  // Кольцо оценки заполняется после вставки в документ.
  requestAnimationFrame(() => {
    const fill = $("ring-fill");
    if (fill) fill.setAttribute("stroke-dasharray", fill.dataset.fill);
  });
}

/* ---------- запуск ---------- */

$("go-accounts").onclick = () => go(1);
$("back-upload").onclick = () => go(0);
$("back-accounts").onclick = () => go(1);
$("back-dash").onclick = () => go(2);

$("go-dash").onclick = async () => {
  $("go-dash").disabled = true;
  $("go-dash").textContent = "Считаю…";
  try {
    const data = await saveAccounts();
    renderDash(data);
    go(2);
  } finally {
    $("go-dash").disabled = false;
    $("go-dash").textContent = "Показать разбор";
  }
};

$("go-questions").onclick = () => { go(3); loadQuestions(); };

$("start-over").onclick = async () => {
  await fetch("/api/reset", { method: "POST" });
  location.reload();
};

/* ---------- профиль ---------- */

// Картинка профиля показывается и в верхней панели, и в самом разделе.
function paintProfile(data) {
  $("profile-name").textContent = data.name;
  $("profile-email").textContent = data.email;
  $("profile-registered").textContent = data.registered || "неизвестна";

  const holder = $("profile-avatar");
  const topAvatar = document.querySelector(".user .avatar");

  if (data.avatar) {
    holder.innerHTML = `<img src="${data.avatar}" alt="">`;
    topAvatar.innerHTML = `<img src="${data.avatar}" alt="">`;
    $("avatar-remove").hidden = false;
  } else {
    holder.innerHTML = `<span>${data.initials}</span>`;
    topAvatar.textContent = data.initials;
    $("avatar-remove").hidden = true;
  }
}

async function loadProfile() {
  const res = await fetch("/api/profile");
  if (res.status === 401) { location.href = "/"; return; }
  paintProfile(await res.json());
}

$("open-profile").onclick = () => {
  closeUserMenu();
  go(PROFILE_STEP);
  loadProfile();
};

$("profile-password").onclick = () => $("change-password").click();

$("avatar-input").addEventListener("change", async () => {
  const file = $("avatar-input").files[0];
  if (!file) return;

  const errorBox = $("avatar-error");
  errorBox.innerHTML = "";

  const form = new FormData();
  form.append("image", file);

  try {
    const res = await fetch("/api/profile/avatar", { method: "POST", body: form });
    const body = await res.json();
    if (!res.ok) throw new Error(body.detail || "Не получилось загрузить.");
    paintProfile(body);
  } catch (err) {
    errorBox.innerHTML = `<div class="err">${err.message}</div>`;
  } finally {
    $("avatar-input").value = "";
  }
});

$("avatar-remove").onclick = async () => {
  const res = await fetch("/api/profile/avatar", { method: "DELETE" });
  if (res.ok) paintProfile(await res.json());
};

// Картинка нужна сразу: она стоит в верхней панели на каждом экране.
loadProfile();

/* ---------- отзыв ---------- */

const feedbackImage = $("feedback-image");

feedbackImage.addEventListener("change", () => {
  const file = feedbackImage.files[0];
  $("image-name").textContent = file ? file.name : "Прикрепить картинку";
  $("image-pick").classList.toggle("filled", Boolean(file));
});

$("feedback-send").onclick = async () => {
  const text = $("feedback-text").value.trim();
  const errorBox = $("feedback-error");
  errorBox.innerHTML = "";

  if (!text) {
    errorBox.innerHTML = `<div class="err">Напишите, что хотите сообщить.</div>`;
    return;
  }

  const form = new FormData();
  form.append("text", text);
  if (feedbackImage.files[0]) form.append("image", feedbackImage.files[0]);

  const button = $("feedback-send");
  button.disabled = true;
  button.textContent = "Отправляю…";

  try {
    const res = await fetch("/api/feedback", { method: "POST", body: form });
    if (res.status === 401) { location.href = "/"; return; }
    const body = await res.json();
    if (!res.ok) throw new Error(body.detail || "Не получилось отправить.");

    $("feedback-form").hidden = true;
    $("feedback-done").hidden = false;
  } catch (err) {
    errorBox.innerHTML = `<div class="err">${err.message}</div>`;
  } finally {
    button.disabled = false;
    button.textContent = "Отправить";
  }
};

$("feedback-again").onclick = () => {
  $("feedback-text").value = "";
  feedbackImage.value = "";
  $("image-name").textContent = "Прикрепить картинку";
  $("image-pick").classList.remove("filled");
  $("feedback-done").hidden = true;
  $("feedback-form").hidden = false;
};

/* ---------- смена пароля ---------- */

const passModal = $("pass-modal");
const passForm = $("pass-form");
const passError = $("pass-error");
const passNote = $("pass-note");
const passSubmit = $("pass-submit");

// Те же требования, что и при регистрации. Сервер проверяет их повторно.
const PASS_CHECKS = {
  length: (v) => v.length >= 8,
  digit: (v) => /\d/.test(v),
  upper: (v) => /[A-ZА-ЯЁ]/.test(v),
  special: (v) => /[^A-Za-zА-Яа-яЁё0-9\s]/.test(v),
};

let passStage = "request";

function paintPassRules() {
  const value = passForm.password.value;
  let allGood = true;
  $("pass-rules").querySelectorAll("li").forEach((item) => {
    const ok = PASS_CHECKS[item.dataset.rule](value);
    item.classList.toggle("ok", ok);
    if (!ok) allGood = false;
  });
  return allGood;
}

passForm.password.addEventListener("input", () => {
  if (passStage === "confirm") paintPassRules();
});

function setPassStage(stage) {
  passStage = stage;
  const confirming = stage === "confirm";

  $("pass-sub").textContent = confirming
    ? "Введите код из письма и придумайте новый пароль."
    : "Пришлём код на вашу почту.";
  $("pass-code-field").hidden = !confirming;
  $("pass-new-field").hidden = !confirming;
  $("pass-repeat-field").hidden = !confirming;
  $("pass-rules").hidden = !confirming;
  passSubmit.textContent = confirming ? "Сменить пароль" : "Прислать код";

  passError.hidden = true;
  if (confirming) paintPassRules();
}

$("change-password").onclick = () => {
  closeUserMenu();
  passForm.reset();
  passNote.hidden = true;
  setPassStage("request");
  passModal.hidden = false;
};

$("pass-close").onclick = () => { passModal.hidden = true; };
passModal.addEventListener("click", (e) => { if (e.target === passModal) passModal.hidden = true; });

passForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  passError.hidden = true;

  const email = document.querySelector(".user .who i").textContent.trim();
  passSubmit.disabled = true;

  try {
    if (passStage === "request") {
      passSubmit.textContent = "Отправляю…";
      const res = await fetch("/api/auth/reset/request", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
      const body = await res.json();
      if (!res.ok) throw new Error(body.detail || "Не получилось.");

      setPassStage("confirm");
      passNote.textContent = body.mail_configured
        ? `Код отправлен на ${email}.`
        : "Почтовый сервер не настроен, код записан в журнал сервера.";
      passNote.hidden = false;
      return;
    }

    if (passForm.code.value.trim().length !== 6) throw new Error("Код состоит из шести цифр.");
    if (!paintPassRules()) throw new Error("Пароль не отвечает требованиям ниже.");
    if (passForm.password.value !== passForm.password_repeat.value) {
      throw new Error("Пароли не совпадают.");
    }

    passSubmit.textContent = "Меняю…";
    const res = await fetch("/api/auth/reset/confirm", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email,
        code: passForm.code.value.trim(),
        password: passForm.password.value,
        password_repeat: passForm.password_repeat.value,
      }),
    });
    const body = await res.json();
    if (!res.ok) throw new Error(body.detail || "Не получилось.");

    passModal.hidden = true;
    // Смена пароля закрывает прежние входы, поэтому страница открывается заново.
    location.reload();
  } catch (err) {
    passError.textContent = err.message;
    passError.hidden = false;
  } finally {
    passSubmit.disabled = false;
    // Подпись берётся по текущему этапу: после перехода ко второму шагу
    // возврат к прежнему тексту сбил бы кнопку.
    passSubmit.textContent = passStage === "confirm" ? "Сменить пароль" : "Прислать код";
  }
});

// Первый раздел заменяет запись в истории, а не добавляет новую,
// иначе первое нажатие «назад» никуда не ведёт.
history.replaceState({ step: 0 }, "", "#" + STEPS[0].slug);
go(0, false);
