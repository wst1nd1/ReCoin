"use strict";

/* Знак на фоне подвала: золотая подсветка следует за курсором.
   Скрипт передаёт положение указателя в стили, остальное делает маска. */

const word = document.getElementById("footer-word");

if (word) {
  word.addEventListener("mousemove", (event) => {
    const box = word.getBoundingClientRect();
    if (!box.width || !box.height) return;
    word.style.setProperty("--mx", `${((event.clientX - box.left) / box.width) * 100}%`);
    word.style.setProperty("--my", `${((event.clientY - box.top) / box.height) * 100}%`);
  });
}

/* Год в строке об авторских правах. */
const year = document.getElementById("footer-year");
if (year) year.textContent = String(new Date().getFullYear());
