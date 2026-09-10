"use strict";

/* Адрес рабочего приложения. Замените на выданный хостингом после
   развёртывания – страница подставит его во все кнопки. */
const APP_URL = "";

const links = document.querySelectorAll("[data-app-link]");
if (APP_URL) {
  links.forEach((link) => {
    link.href = APP_URL;
    link.rel = "noopener";
  });
} else {
  links.forEach((link) => {
    link.removeAttribute("href");
    link.setAttribute("aria-disabled", "true");
  });
  const note = document.getElementById("soon");
  if (note) note.hidden = false;
}
