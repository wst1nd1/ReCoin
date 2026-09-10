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

const modal = document.getElementById("auth-modal");
const form = document.getElementById("auth-form");
const errorBox = document.getElementById("auth-error");
const submitBtn = document.getElementById("auth-submit");
const nameField = document.getElementById("name-field");

let mode = "login";

const COPY = {
  login: {
    title: "Вход",
    sub: "Продолжим с того места, где остановились.",
    submit: "Войти",
    switchText: "Ещё нет аккаунта?",
    switchAction: "Зарегистрироваться",
    autocomplete: "current-password",
  },
  register: {
    title: "Регистрация",
    sub: "Аккаунт нужен, чтобы разборы не смешивались между людьми.",
    submit: "Создать аккаунт",
    switchText: "Уже регистрировались?",
    switchAction: "Войти",
    autocomplete: "new-password",
  },
};

function setMode(next) {
  mode = next;
  const copy = COPY[mode];
  document.getElementById("auth-title").textContent = copy.title;
  document.getElementById("auth-sub").textContent = copy.sub;
  document.getElementById("switch-text").textContent = copy.switchText;
  document.getElementById("auth-switch").textContent = copy.switchAction;
  submitBtn.textContent = copy.submit;
  nameField.hidden = mode !== "register";
  form.password.setAttribute("autocomplete", copy.autocomplete);
  errorBox.hidden = true;
}

function openModal(next) {
  setMode(next);
  modal.hidden = false;
  setTimeout(() => form.email.focus(), 60);
}

function closeModal() {
  modal.hidden = true;
  form.reset();
  errorBox.hidden = true;
}

document.querySelectorAll("[data-open-auth]").forEach((el) => {
  el.onclick = () => openModal(el.dataset.openAuth);
});

document.getElementById("auth-close").onclick = closeModal;
document.getElementById("auth-switch").onclick = () =>
  setMode(mode === "login" ? "register" : "login");

modal.addEventListener("click", (e) => {
  if (e.target === modal) closeModal();
});

document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && !modal.hidden) closeModal();
});

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  errorBox.hidden = true;
  submitBtn.disabled = true;
  const original = submitBtn.textContent;
  submitBtn.textContent = mode === "login" ? "Проверяю…" : "Создаю…";

  const payload = {
    email: form.email.value.trim(),
    password: form.password.value,
  };
  if (mode === "register") payload.name = form.name.value.trim();

  try {
    const res = await fetch(`/api/auth/${mode}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const body = await res.json();
    if (!res.ok) throw new Error(body.detail || "Не получилось. Попробуйте ещё раз.");
    location.href = "/app";
  } catch (err) {
    errorBox.textContent = err.message;
    errorBox.hidden = false;
    submitBtn.disabled = false;
    submitBtn.textContent = original;
  }
});
