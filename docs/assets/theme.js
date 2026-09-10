"use strict";

/* Светлая и тёмная темы. Выбор хранится в браузере, при первом заходе
   берётся системная настройка. Тема применяется на элементе <html>,
   поэтому переключение меняет цвета сразу на всей странице. */

const THEME_KEY = "recoin-theme";

const systemTheme = () =>
  window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";

const storedTheme = () => {
  try {
    const saved = localStorage.getItem(THEME_KEY);
    return saved === "dark" || saved === "light" ? saved : null;
  } catch {
    return null;
  }
};

const currentTheme = () => document.documentElement.dataset.theme || storedTheme() || systemTheme();

const SUN = `<svg class="tt-sun" viewBox="0 0 24 24" fill="none" stroke="currentColor"
  stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="4"/>
  <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>`;

const MOON = `<svg class="tt-moon" viewBox="0 0 24 24" fill="none" stroke="currentColor"
  stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
  <path d="M20 14.5A8.5 8.5 0 0 1 9.5 4a8.5 8.5 0 1 0 10.5 10.5z"/></svg>`;

const applyTheme = (theme) => {
  document.documentElement.dataset.theme = theme;
  document.querySelectorAll(".theme-toggle").forEach((btn) => {
    btn.setAttribute("aria-checked", theme === "dark" ? "true" : "false");
    btn.setAttribute("aria-label", theme === "dark" ? "Включить светлую тему" : "Включить тёмную тему");
  });
};

const setTheme = (theme) => {
  applyTheme(theme);
  try {
    localStorage.setItem(THEME_KEY, theme);
  } catch {
    /* Приватный режим браузера запрещает запись – тема останется до перезагрузки. */
  }
};

/* Наполняет кнопку разметкой: значки на треке, подвижная кнопка и вспышка. */
const buildToggle = (btn) => {
  btn.type = "button";
  btn.setAttribute("role", "switch");
  btn.innerHTML = `<span class="tt-thumb">${SUN}${MOON}</span>`;

  btn.addEventListener("click", () => {
    setTheme(currentTheme() === "dark" ? "light" : "dark");
    btn.classList.remove("flip");
    // Пауза в один кадр перезапускает поворот значка.
    requestAnimationFrame(() => btn.classList.add("flip"));
    setTimeout(() => btn.classList.remove("flip"), 400);
  });
};

document.querySelectorAll(".theme-toggle").forEach(buildToggle);
applyTheme(currentTheme());

/* Пока пользователь не выбрал тему сам, страница следует системной настройке. */
if (window.matchMedia) {
  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", (e) => {
    if (!storedTheme()) applyTheme(e.matches ? "dark" : "light");
  });
}
