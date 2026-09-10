"use strict";

/* Название в подвале: цветной контур проявляется в круге под курсором.
   Круг задан радиальным градиентом, который служит маской для текста. */

const word = document.getElementById("footer-word");
const wordMask = document.getElementById("footerWordMask");

if (word && wordMask) {
  const follow = (event) => {
    const box = word.getBoundingClientRect();
    if (!box.width || !box.height) return;
    // Координаты курсора переводятся в систему координат рисунка.
    wordMask.setAttribute("cx", ((event.clientX - box.left) / box.width) * 300);
    wordMask.setAttribute("cy", ((event.clientY - box.top) / box.height) * 100);
  };

  word.addEventListener("mousemove", follow);
  word.addEventListener("mouseleave", () => {
    wordMask.setAttribute("cx", 150);
    wordMask.setAttribute("cy", 50);
  });
}

/* Год в строке об авторских правах. */
const year = document.getElementById("footer-year");
if (year) year.textContent = String(new Date().getFullYear());
