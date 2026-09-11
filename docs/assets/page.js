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
    article.querySelectorAll("p").forEach((line) => {
      line.style.transition = "none";
    });
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
  // При первых вызовах раскладки может ещё не быть, поэтому попытки
  // повторяются до появления ширины ряда.
  let attempts = 20;
  const ensureReserve = () => {
    reserveCardSpace();
    if (!cards.style.minHeight && attempts-- > 0) requestAnimationFrame(ensureReserve);
  };

  ensureReserve();
  window.addEventListener("load", ensureReserve);
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
