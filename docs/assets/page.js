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
