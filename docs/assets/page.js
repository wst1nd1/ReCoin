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
   тогда при раскрытии страница не меняет длину. Замер идёт на копии ряда,
   спрятанной за пределами экрана, чтобы на самой странице ничего не мелькало. */
const reserveCardSpace = () => {
  if (!cards) return;

  const probe = cards.cloneNode(true);
  probe.removeAttribute("id");
  probe.style.position = "absolute";
  probe.style.left = "-10000px";
  probe.style.top = "0";
  probe.style.width = `${cards.getBoundingClientRect().width}px`;
  probe.style.minHeight = "0";
  probe.style.visibility = "hidden";
  probe.querySelectorAll("article").forEach((article) => {
    article.classList.add("open");
    article.style.transition = "none";
    const full = article.querySelector(".full");
    if (full) full.style.transition = "none";
  });

  cards.parentNode.appendChild(probe);
  let tallest = 0;
  probe.querySelectorAll("article").forEach((article) => {
    tallest = Math.max(tallest, article.offsetHeight);
  });
  probe.remove();

  if (tallest > 0) cards.style.minHeight = `${Math.ceil(tallest)}px`;
};

if (cards) {
  reserveCardSpace();
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
