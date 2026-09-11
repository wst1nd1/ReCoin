"use strict";

/* Раскрывающиеся карточки: в ряду они одинаковые, по нажатию одна занимает
   больше места и показывает полный текст, повторное нажатие возвращает ряд. */
const cards = document.getElementById("cards");

if (cards) {
  const articles = [...cards.querySelectorAll("article")];

  const toggle = (article) => {
    const wasOpen = article.classList.contains("open");
    articles.forEach((a) => {
      a.classList.remove("open");
      a.setAttribute("aria-expanded", "false");
    });
    if (!wasOpen) {
      article.classList.add("open");
      article.setAttribute("aria-expanded", "true");
    }
  };

  articles.forEach((article) => {
    article.addEventListener("click", () => toggle(article));
    article.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        toggle(article);
      }
    });
  });
}

/* Место под самую большую раскрытую карточку резервируется заранее:
   тогда при раскрытии и закрытии страница не меняет длину, а подвал
   остаётся на месте. Замер идёт на копии ряда, спрятанной за пределами
   экрана, поэтому на самой странице ничего не мелькает. */
const reserveCardSpace = () => {
  if (!cards) return;

  const width = cards.getBoundingClientRect().width;
  // До расчёта раскладки ширины ещё нет, замер в этот момент бессмысленен.
  if (!width) return;

  const probe = cards.cloneNode(true);
  probe.removeAttribute("id");
  probe.style.position = "absolute";
  probe.style.left = "-10000px";
  probe.style.top = "0";
  probe.style.width = `${width}px`;
  probe.style.minHeight = "0";
  probe.style.visibility = "hidden";

  const copies = [...probe.querySelectorAll("article")];
  copies.forEach((article) => {
    article.style.transition = "none";
    const full = article.querySelector(".full");
    if (full) full.style.transition = "none";
  });

  cards.parentNode.appendChild(probe);

  // Ряд меряется столько раз, сколько карточек: раскрыта каждый раз одна.
  // В строку это даёт высоту самой большой карточки, в столбик – сумму.
  let tallest = 0;
  copies.forEach((article) => {
    copies.forEach((other) => other.classList.remove("open"));
    article.classList.add("open");
    tallest = Math.max(tallest, probe.offsetHeight);
  });

  probe.remove();

  if (tallest > 0) cards.style.minHeight = `${Math.ceil(tallest)}px`;
};

if (cards) {
  reserveCardSpace();
  window.addEventListener("load", reserveCardSpace);
  window.addEventListener("resize", reserveCardSpace);
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(reserveCardSpace);
}

/* Появление секций при прокрутке. */
const revealables = document.querySelectorAll(".reveal");
if (revealables.length) {
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("seen");
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.12, rootMargin: "0px 0px -40px 0px" }
  );
  revealables.forEach((el) => observer.observe(el));
}

/* ---------- вход, регистрация и восстановление ---------- */

const modal = document.getElementById("auth-modal");
const form = document.getElementById("auth-form");
const errorBox = document.getElementById("auth-error");
const noteBox = document.getElementById("auth-note");
const submitBtn = document.getElementById("auth-submit");
const rulesList = document.getElementById("password-rules");

const fields = {
  name: document.getElementById("name-field"),
  email: document.getElementById("email-field"),
  code: document.getElementById("code-field"),
  password: document.getElementById("password-field"),
  repeat: document.getElementById("repeat-field"),
};

// Режимы формы. Поля, тексты и адрес запроса задаются здесь, чтобы
// переключение не расползалось по коду.
const MODES = {
  login: {
    title: "Вход",
    sub: "Продолжим с того места, где остановились.",
    submit: "Войти",
    pending: "Проверяю…",
    url: "/api/auth/login",
    show: ["email", "password"],
    passwordLabel: "Пароль",
    autocomplete: "current-password",
    rules: false,
    forgot: true,
    switchText: "Ещё нет аккаунта?",
    switchAction: "Зарегистрироваться",
    switchTo: "register",
  },
  register: {
    title: "Регистрация",
    sub: "",
    submit: "Создать аккаунт",
    pending: "Создаю…",
    url: "/api/auth/register",
    show: ["name", "email", "password", "repeat"],
    passwordLabel: "Пароль",
    autocomplete: "new-password",
    rules: true,
    forgot: false,
    switchText: "Уже регистрировались?",
    switchAction: "Войти",
    switchTo: "login",
  },
  resetRequest: {
    title: "Восстановление пароля",
    sub: "Пришлём код на почту, указанную при регистрации.",
    submit: "Прислать код",
    pending: "Отправляю…",
    url: "/api/auth/reset/request",
    show: ["email"],
    rules: false,
    forgot: false,
    switchText: "Вспомнили пароль?",
    switchAction: "Войти",
    switchTo: "login",
  },
  resetConfirm: {
    title: "Новый пароль",
    sub: "Введите код из письма и придумайте новый пароль.",
    submit: "Сменить пароль",
    pending: "Меняю…",
    url: "/api/auth/reset/confirm",
    show: ["code", "password", "repeat"],
    passwordLabel: "Новый пароль",
    autocomplete: "new-password",
    rules: true,
    forgot: false,
    switchText: "Начать заново?",
    switchAction: "Войти",
    switchTo: "login",
  },
};

let mode = "login";
let resetEmail = "";

/* Требования к паролю. Те же правила проверяет сервер, здесь они нужны,
   чтобы человек видел несоответствие сразу, а не после отправки. */
const CHECKS = {
  length: (value) => value.length >= 8,
  digit: (value) => /\d/.test(value),
  upper: (value) => /[A-ZА-ЯЁ]/.test(value),
  special: (value) => /[^A-Za-zА-Яа-яЁё0-9\s]/.test(value),
};

function paintRules() {
  const value = form.password.value;
  let allGood = true;
  rulesList.querySelectorAll("li").forEach((item) => {
    const ok = CHECKS[item.dataset.rule](value);
    item.classList.toggle("ok", ok);
    if (!ok) allGood = false;
  });
  return allGood;
}

form.password.addEventListener("input", () => {
  if (MODES[mode].rules) paintRules();
});

function setMode(next) {
  mode = next;
  const config = MODES[mode];

  document.getElementById("auth-title").textContent = config.title;
  // Пустое пояснение скрывается целиком, иначе под заголовком остаётся пробел.
  const sub = document.getElementById("auth-sub");
  sub.textContent = config.sub;
  sub.hidden = !config.sub;
  document.getElementById("switch-text").textContent = config.switchText;
  document.getElementById("auth-switch").textContent = config.switchAction;
  submitBtn.textContent = config.submit;

  Object.entries(fields).forEach(([key, element]) => {
    element.hidden = !config.show.includes(key);
  });

  rulesList.hidden = !config.rules;
  document.getElementById("forgot-line").hidden = !config.forgot;

  if (config.passwordLabel) {
    document.getElementById("password-label").textContent = config.passwordLabel;
    form.password.setAttribute("autocomplete", config.autocomplete);
  }

  errorBox.hidden = true;
  noteBox.hidden = true;
  if (config.rules) paintRules();
}

function openModal(next) {
  setMode(next);
  modal.hidden = false;
  setTimeout(() => {
    const first = form.querySelector(".field:not([hidden]) input");
    if (first) first.focus();
  }, 60);
}

function closeModal() {
  modal.hidden = true;
  form.reset();
  errorBox.hidden = true;
  noteBox.hidden = true;
}

document.querySelectorAll("[data-open-auth]").forEach((el) => {
  el.onclick = () => openModal(el.dataset.openAuth);
});

document.getElementById("auth-close").onclick = closeModal;
document.getElementById("auth-switch").onclick = () => setMode(MODES[mode].switchTo);
document.getElementById("auth-forgot").onclick = () => setMode("resetRequest");

modal.addEventListener("click", (e) => {
  if (e.target === modal) closeModal();
});

document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && !modal.hidden) closeModal();
});

function collect() {
  const config = MODES[mode];
  const payload = {};
  if (config.show.includes("email")) payload.email = form.email.value.trim();
  if (config.show.includes("name")) payload.name = form.name.value.trim();
  if (config.show.includes("code")) payload.code = form.code.value.trim();
  if (config.show.includes("password")) payload.password = form.password.value;
  if (config.show.includes("repeat")) payload.password_repeat = form.password_repeat.value;
  // На смене пароля адрес не показывается, он остался с предыдущего шага.
  if (mode === "resetConfirm") payload.email = resetEmail;
  return payload;
}

function localProblem() {
  const config = MODES[mode];
  if (config.show.includes("email") && !form.email.value.trim()) {
    return "Укажите адрес почты.";
  }
  if (config.show.includes("code") && form.code.value.trim().length !== 6) {
    return "Код состоит из шести цифр.";
  }
  if (config.rules && !paintRules()) {
    return "Пароль не отвечает требованиям ниже.";
  }
  if (config.show.includes("repeat") && form.password.value !== form.password_repeat.value) {
    return "Пароли не совпадают.";
  }
  return null;
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  errorBox.hidden = true;
  noteBox.hidden = true;

  const problem = localProblem();
  if (problem) {
    errorBox.textContent = problem;
    errorBox.hidden = false;
    return;
  }

  const config = MODES[mode];
  submitBtn.disabled = true;
  const original = submitBtn.textContent;
  submitBtn.textContent = config.pending;

  try {
    const res = await fetch(config.url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(collect()),
    });
    const body = await res.json();
    if (!res.ok) throw new Error(body.detail || "Не получилось. Попробуйте ещё раз.");

    if (mode === "resetRequest") {
      resetEmail = form.email.value.trim();
      setMode("resetConfirm");
      noteBox.textContent = body.mail_configured
        ? `Код отправлен на ${resetEmail}. Письмо приходит в течение минуты.`
        : "Почтовый сервер не настроен, поэтому код записан в журнал сервера.";
      noteBox.hidden = false;
      submitBtn.disabled = false;
      submitBtn.textContent = MODES[mode].submit;
      setTimeout(() => form.code.focus(), 60);
      return;
    }

    location.href = "/app";
  } catch (err) {
    errorBox.textContent = err.message;
    errorBox.hidden = false;
    submitBtn.disabled = false;
    submitBtn.textContent = original;
  }
});

setMode("login");
