"use strict";

/* Выполняется до отрисовки страницы, чтобы тёмная тема не сменялась
   светлой вспышкой при загрузке. */
(function () {
  var theme = null;
  try {
    theme = localStorage.getItem("recoin-theme");
  } catch (e) {
    theme = null;
  }
  if (theme !== "dark" && theme !== "light") {
    theme = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches
      ? "dark"
      : "light";
  }
  document.documentElement.dataset.theme = theme;
})();
