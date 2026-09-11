"use strict";

/* Переключение языка интерфейса. Английские строки подставляются вместо
   русских по словарю: ключ – точный русский текст, который стоит в разметке
   или приходит из скриптов. Разметку размечать не нужно, поэтому перевод
   работает и для разделов, которые собираются на ходу. */

const LANG_KEY = "recoin-lang";

const DICT = {
  /* ---------- витрина ---------- */
  "ReCoin – сколько вы потратили на самом деле": "ReCoin – how much you really spent",
  "Войти": "Sign in",
  "Регистрация": "Sign up",
  "Приложение": "Open app",
  "Открыть приложение": "Open the app",
  "Банк показывает обороты.": "Your bank shows turnover.",
  "Мы показываем траты.": "We show spending.",
  "Разобрать свою выписку": "Analyse my statement",
  "Что делает ReCoin": "What ReCoin does",
  "Читает выписку": "Reads the statement",
  "PDF из банка превращается в разобранные операции.":
    "A bank PDF turns into itemised transactions.",
  "Дата, сумма, магазин и категория по каждой операции. Итоги сверяются с напечатанными в выписке. Если сумма не сошлась, приложение сообщит об этом.":
    "Date, amount, merchant and category for every transaction. Totals are checked against the ones printed in the statement, and any mismatch is reported.",
  "Отделяет траты от переводов": "Separates spending from transfers",
  "Перевод себе тратой не является.": "A transfer to yourself is not spending.",
  "Деньги на вкладе остаются вашими, возвращённый долг тратой не был, платёж по кредитке гасит долг. Три случая считаются по-разному, и в итоговую сумму попадает только потраченное.":
    "Money in a savings account stays yours, a repaid loan was never spending, and a credit card payment clears debt. All three are counted differently, so only real spending reaches the total.",
  "Задаёт вопросы и разбирает": "Asks questions and reviews",
  "Советы с расчётом экономии в рублях.": "Advice with savings calculated in roubles.",
  "Спрашивает то, чего нет в выписке: цели, намерения, обязательность трат. По ответам собирает разбор с оценкой экономии за год по каждому совету.":
    "It asks what the statement cannot show: goals, intentions, which costs are unavoidable. From your answers it builds a review with yearly savings for every suggestion.",
  "Разбирает банковскую выписку и показывает, сколько денег вы потратили на самом деле.":
    "Analyses a bank statement and shows how much money you really spent.",
  "Сервис": "Product",
  "Разобрать выписку": "Analyse a statement",
  "Разработка": "Development",
  "Исходный код": "Source code",
  "Сообщить об ошибке": "Report a problem",
  "Данные": "Data",
  "Разобранные выписки на диск не пишутся: они живут в памяти сервера и исчезают при перезапуске.":
    "Parsed statements are never written to disk: they live in server memory and disappear on restart.",
  "Все права защищены.": "All rights reserved.",
  "Приложение ещё разворачивается. Страница обновится, как только появится рабочий адрес.":
    "The app is still being deployed. This page will be updated once it has an address.",

  /* ---------- вход и регистрация ---------- */
  "Вход": "Sign in",
  "Продолжим с того места, где остановились.": "Let us pick up where you left off.",
  "Как к вам обращаться": "How should we address you",
  "Почта": "Email",
  "Код из письма": "Code from the email",
  "Пароль": "Password",
  "не менее 8 символов": "at least 8 characters",
  "хотя бы одна цифра": "at least one digit",
  "хотя бы одна заглавная буква": "at least one capital letter",
  "хотя бы один специальный знак": "at least one special character",
  "Повторите пароль": "Repeat the password",
  "Забыли пароль?": "Forgot your password?",
  "Ещё нет аккаунта?": "No account yet?",
  "Зарегистрироваться": "Create an account",
  "Уже регистрировались?": "Already registered?",
  "Имя": "Name",
  "шесть цифр": "six digits",
  "Тот же пароль ещё раз": "The same password again",
  "Создать аккаунт": "Create account",
  "Создаю…": "Creating…",
  "Проверяю…": "Checking…",
  "Восстановление пароля": "Password recovery",
  "Пришлём код на почту, указанную при регистрации.":
    "We will send a code to the email you registered with.",
  "Прислать код": "Send the code",
  "Отправляю…": "Sending…",
  "Вспомнили пароль?": "Remembered your password?",
  "Новый пароль": "New password",
  "Введите код из письма и придумайте новый пароль.":
    "Enter the code from the email and choose a new password.",
  "Сменить пароль": "Change password",
  "Меняю…": "Changing…",
  "Начать заново?": "Start over?",
  "Укажите адрес почты.": "Enter your email address.",
  "Код состоит из шести цифр.": "The code is six digits long.",
  "Пароль не отвечает требованиям ниже.": "The password does not meet the rules below.",
  "Пароли не совпадают.": "The passwords do not match.",
  "Не получилось. Попробуйте ещё раз.": "That did not work. Please try again.",
  "Почтовый сервер не настроен, поэтому код записан в журнал сервера.":
    "Email is not configured, so the code was written to the server log.",
  "Проверьте адрес почты – он выглядит неправильно.": "Check the email address – it looks wrong.",
  "Такая почта уже зарегистрирована. Войдите вместо регистрации.":
    "This email is already registered. Sign in instead.",
  "Неверная почта или пароль.": "Wrong email or password.",
  "Код не запрашивался. Начните восстановление заново.":
    "No code was requested. Start the recovery again.",
  "Срок действия кода истёк. Запросите новый.": "The code has expired. Request a new one.",
  "Слишком много попыток. Запросите новый код.": "Too many attempts. Request a new code.",
  "Неверный код. Попытки исчерпаны, запросите новый.":
    "Wrong code. No attempts left, request a new one.",
  "Учётная запись не найдена.": "Account not found.",
  "Нужно войти в аккаунт": "You need to sign in",
  "Если такая почта зарегистрирована, код отправлен на неё.":
    "If that email is registered, a code has been sent to it.",

  /* ---------- кабинет ---------- */
  "ReCoin – кабинет": "ReCoin – dashboard",
  "Выписки": "Statements",
  "Загрузите PDF из банка – разберём операции и посчитаем настоящие траты.":
    "Upload a bank PDF – we will itemise the transactions and count real spending.",
  "Счета": "Accounts",
  "Уточните назначение счетов – от этого зависят итоговые цифры.":
    "Tell us what these accounts are for – the totals depend on it.",
  "Траты": "Spending",
  "Куда уходили деньги за загруженный период.": "Where the money went over the uploaded period.",
  "Вопросы": "Questions",
  "Несколько вопросов, чтобы разбор был точнее.":
    "A few questions to make the review more accurate.",
  "Разбор": "Review",
  "Что получается, что мешает и что с этим делать.":
    "What works, what gets in the way and what to do about it.",
  "Профиль": "Profile",
  "Сведения об учётной записи.": "Account details.",
  "Оставить отзыв": "Send feedback",
  "Расскажите, что стоит улучшить, мы читаем всё.":
    "Tell us what to improve – we read everything.",
  "Расскажите, что показалось неудобным или чего не хватает":
    "Tell us what felt awkward or what is missing",
  "Изменить пароль": "Change password",
  "Выйти": "Sign out",
  "Перетащите выписку в PDF": "Drop a PDF statement here",
  "или нажмите, чтобы выбрать файл": "or click to choose a file",
  "Как получить выписку": "How to get a statement",
  "В приложении банка откройте счёт или карту.": "Open an account or card in your banking app.",
  "Выберите «Выписка» или «Справка о движении средств».":
    "Choose «Statement» or «Account activity report».",
  "Период – год, формат – PDF.": "Period – one year, format – PDF.",
  "За год видно подписки, сезонные траты и возвращённые долги. По месяцу многое просто не успевает проявиться.":
    "A year reveals subscriptions, seasonal costs and repaid debts. A single month simply does not show enough.",
  "Продолжить": "Continue",
  "Добавить ещё выписку": "Add another statement",
  "Ничего уточнять не нужно – в выписке не нашлось переводов на счета, которые заметно повлияли бы на итог.":
    "Nothing to clarify – the statement has no transfers that would noticeably change the total.",
  "Куда ещё уходят деньги": "Where else the money goes",
  "Заметная часть переводов идёт на счёт, по которому вы выписку не загружали. Уточните, чей он – от этого зависит точность расчёта.":
    "A noticeable share of transfers goes to an account you did not upload a statement for. Tell us whose it is – accuracy depends on it.",
  "Ваши счета": "Your accounts",
  "Показать разбор": "Show the review",
  "Назад": "Back",
  "Пропустить": "Skip",
  "Перейти к разбору": "Go to the review",
  "Изменить счета": "Edit accounts",
  "Вернуться к цифрам": "Back to the numbers",
  "Загрузить другую выписку": "Upload another statement",
  "Сменить картинку": "Change picture",
  "Убрать": "Remove",
  "png, jpg, webp или gif до 2 МБ": "png, jpg, webp or gif up to 2 MB",
  "Дата регистрации": "Registered on",
  "Что улучшить": "What to improve",
  "Пожелание, замечание или описание ошибки. Можно приложить снимок экрана.":
    "A suggestion, a remark or a bug report. You can attach a screenshot.",
  "Прикрепить картинку": "Attach a picture",
  "Отправить": "Send",
  "Ваш отзыв отправлен!": "Your feedback has been sent.",
  "Спасибо что помогаете нам стать лучше!": "Thank you for helping us improve.",
  "Написать ещё": "Write again",
  "Пришлём код на вашу почту.": "We will send a code to your email.",
  "Мой второй счёт": "My own account",
  "Счёт другого человека": "Someone else's account",
  "Разбор выписки": "Statement review",
  "Итог": "Total",
  "Читаю выписку…": "Reading the statement…",
  "Не удалось разобрать файл": "The file could not be parsed",
  "Выписка загружена": "Statement uploaded",
  "можно добавить ещё одну": "you can add another one",
  "Траты по месяцам": "Spending by month",
  "Доли категорий трат": "Category shares",
  "Регулярные списания": "Recurring charges",
  "Крупные покупки": "Large purchases",
  "повторяются с одинаковой суммой": "repeat with the same amount",
  "самые дорогие за период": "the most expensive of the period",
  "за период": "for the period",
  "в год": "per year",
  "из 100": "out of 100",
  "Из них покупки": "Of which purchases",
  "Покупок в месяц": "Purchases per month",
  "Отложено на вклады": "Moved to savings",
  "Долг вырос на": "Debt grew by",
  "Погашено долга": "Debt repaid",
  "Одолжено и не вернулось": "Lent and not returned",
  "без изменений": "no change",
  "Смотрю на ваши траты и собираю вопросы…": "Looking at your spending and preparing questions…",
  "Подвожу итог…": "Putting it all together…",
  "Как вы обращаетесь с деньгами": "How you handle money",
  "Что получается": "What works",
  "сильные стороны": "your strengths",
  "Что мешает": "What gets in the way",
  "на что стоит посмотреть": "worth a closer look",
  "Что сделать": "What to do",
  "Напишите, что хотите сообщить.": "Write what you would like to tell us.",
  "Слишком длинный текст, сократите его.": "The text is too long, please shorten it.",
  "Картинка не загружена": "No picture uploaded",
  "Картинка больше 2 МБ.": "The picture is larger than 2 MB.",
  "Картинка больше 5 МБ.": "The picture is larger than 5 MB.",
  "Подойдут png, jpg, webp и gif.": "png, jpg, webp and gif will do.",
  "Поддерживаются картинки png, jpg, webp и gif.": "Supported picture formats: png, jpg, webp, gif.",
  "Отзыв не удалось сохранить. Попробуйте позже.": "The feedback could not be saved. Try later.",
  "Сначала загрузите выписку": "Upload a statement first",
  "Не удалось разобрать файлы": "The files could not be parsed",
  "разбор не удался": "parsing failed",
  "Прочее": "Other",

  /* ---------- категории трат ---------- */
  "Продукты": "Groceries",
  "Кафе и рестораны": "Cafes and restaurants",
  "Транспорт": "Transport",
  "Жильё и ЖКУ": "Housing and utilities",
  "Развлечения": "Entertainment",
  "Ставки": "Betting",
  "Спортзал": "Gym",
  "Здоровье": "Health",
  "Одежда и красота": "Clothing and beauty",
  "Связь и интернет": "Phone and internet",
  "Подписки": "Subscriptions",
  "Образование": "Education",
  "Услуги": "Services",
  "Переводы": "Transfers",
  "Наличные": "Cash",

  /* ---------- подписи и кнопки ---------- */
  "Включить тёмную тему": "Switch to dark theme",
  "Включить светлую тему": "Switch to light theme",
  "Закрыть": "Close",
  "Отмена": "Cancel",
  "Сохранить": "Save",
};

/* Строки с подставленными числами и датами переводятся по образцу. */
const MONTHS = {
  "января": "January", "февраля": "February", "марта": "March", "апреля": "April",
  "мая": "May", "июня": "June", "июля": "July", "августа": "August",
  "сентября": "September", "октября": "October", "ноября": "November", "декабря": "December",
};

const PATTERNS = [
  [/^(\d{1,2}) (января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря) (\d{4})$/,
    (m) => `${m[1]} ${MONTHS[m[2]]} ${m[3]}`],
  [/^(\d+) (операция|операции|операций)$/, (m) => `${m[1]} ${m[1] === "1" ? "transaction" : "transactions"}`],
  [/^(\d+) (категория|категории|категорий)$/, (m) => `${m[1]} ${m[1] === "1" ? "category" : "categories"}`],
  [/^· (\d+) (раз|раза)$/, (m) => `· ${m[1]} ${m[1] === "1" ? "time" : "times"}`],
  [/^Код отправлен на (.+?)\. Письмо приходит в течение минуты\.$/,
    (m) => `The code has been sent to ${m[1]}. It arrives within a minute.`],
  [/^Код отправлен на (.+?)\.$/, (m) => `The code has been sent to ${m[1]}.`],
  [/^Неверный код\. Осталось попыток: (\d+)\.$/, (m) => `Wrong code. Attempts left: ${m[1]}.`],
  [/^(\d+)% к прошлому месяцу$/, (m) => `${m[1]}% vs last month`],
  [/^\+(\d+)% к прошлому месяцу$/, (m) => `+${m[1]}% vs last month`],
  [/^(.+): файл больше 25 МБ$/, (m) => `${m[1]}: the file is larger than 25 MB`],
  [/^(.+): это не PDF$/, (m) => `${m[1]}: this is not a PDF`],
  [/^(.+): операции не найдены\. Возможно, это скан или выписка неподдерживаемого банка\.$/,
    (m) => `${m[1]}: no transactions found. It may be a scan or a statement from an unsupported bank.`],
];

const fromPatterns = (key) => {
  for (const [re, build] of PATTERNS) {
    const match = key.match(re);
    if (match) return build(match);
  }
  return null;
};

const lookup = (key) => DICT[key] || fromPatterns(key);

const ATTRS = ["placeholder", "title", "aria-label", "alt"];
const SKIP_TAGS = new Set(["SCRIPT", "STYLE", "CANVAS", "NOSCRIPT"]);

// Исходные русские строки хранятся, чтобы вернуть их при переключении назад.
const originalText = new WeakMap();
const originalAttr = new WeakMap();

const storedLang = () => {
  try {
    const saved = localStorage.getItem(LANG_KEY);
    return saved === "en" || saved === "ru" ? saved : null;
  } catch {
    return null;
  }
};

let current = storedLang() || "ru";

const translateTextNodes = (root, toEnglish) => {
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
    acceptNode: (node) =>
      node.parentElement && !SKIP_TAGS.has(node.parentElement.tagName)
        ? NodeFilter.FILTER_ACCEPT
        : NodeFilter.FILTER_REJECT,
  });

  const nodes = [];
  while (walker.nextNode()) nodes.push(walker.currentNode);

  for (const node of nodes) {
    if (toEnglish) {
      // В разметке длинные фразы разбиты переносами строк, поэтому пробелы
      // сводятся к одному – иначе ключ не совпал бы со словарём.
      const value = node.nodeValue;
      const key = value.trim().replace(/\s+/g, " ");
      const translated = key ? lookup(key) : null;
      if (!translated) continue;
      if (!originalText.has(node)) originalText.set(node, value);
      const lead = value.slice(0, value.length - value.trimStart().length);
      const tail = value.slice(value.trimEnd().length);
      node.nodeValue = lead + translated + tail;
    } else if (originalText.has(node)) {
      node.nodeValue = originalText.get(node);
      originalText.delete(node);
    }
  }
};

const translateAttributes = (root, toEnglish) => {
  const elements = root.nodeType === 1 ? [root, ...root.querySelectorAll("*")] : [...root.querySelectorAll("*")];

  for (const el of elements) {
    for (const attr of ATTRS) {
      if (!el.hasAttribute || !el.hasAttribute(attr)) continue;
      const value = el.getAttribute(attr).trim();

      if (toEnglish) {
        const translatedAttr = lookup(value);
        if (!translatedAttr) continue;
        let saved = originalAttr.get(el) || {};
        if (!(attr in saved)) {
          saved[attr] = el.getAttribute(attr);
          originalAttr.set(el, saved);
        }
        el.setAttribute(attr, translatedAttr);
      } else {
        const saved = originalAttr.get(el);
        if (saved && attr in saved) {
          el.setAttribute(attr, saved[attr]);
          delete saved[attr];
        }
      }
    }
  }
};

const translate = (root, toEnglish) => {
  translateTextNodes(root, toEnglish);
  translateAttributes(root, toEnglish);
};

const updateButtons = () => {
  document.querySelectorAll(".lang-toggle").forEach((btn) => {
    btn.textContent = current === "en" ? "EN" : "RU";
    btn.setAttribute(
      "aria-label",
      current === "en" ? "Switch to Russian" : "Переключить на английский"
    );
    btn.setAttribute("title", btn.getAttribute("aria-label"));
  });
};

let originalTitle = document.title;

const applyLanguage = (lang) => {
  current = lang;
  document.documentElement.lang = lang;
  translate(document.body, lang === "en");

  // Заголовок вкладки лежит вне тела страницы, его переводим отдельно.
  const titleKey = originalTitle.trim();
  const translatedTitle = lookup(titleKey);
  document.title = lang === "en" && translatedTitle ? translatedTitle : originalTitle;

  updateButtons();
};

const rememberLanguage = (lang) => {
  try {
    localStorage.setItem(LANG_KEY, lang);
  } catch {
    /* Приватный режим браузера запрещает запись – выбор живёт до перезагрузки. */
  }
  // Куку читает сервер: на её основе выбирается язык разбора и писем.
  document.cookie = `${LANG_KEY}=${lang}; path=/; max-age=31536000; samesite=lax`;
};

const setLanguage = (lang) => {
  applyLanguage(lang);
  rememberLanguage(lang);
};

/* Разделы кабинета собираются на ходу, поэтому новые узлы переводятся сразу. */
const observer = new MutationObserver((records) => {
  if (current !== "en") return;
  for (const record of records) {
    if (record.type === "attributes") {
      // Подписи кнопок меняются скриптами, поэтому переводятся ещё раз.
      translateAttributes(record.target, true);
      continue;
    }
    for (const node of record.addedNodes) {
      if (node.nodeType === 1) translate(node, true);
      else if (node.nodeType === 3 && node.parentElement) translateTextNodes(node.parentElement, true);
    }
  }
});

document.querySelectorAll(".lang-toggle").forEach((btn) => {
  btn.type = "button";
  btn.addEventListener("click", () => setLanguage(current === "en" ? "ru" : "en"));
});

applyLanguage(current);
rememberLanguage(current);
observer.observe(document.body, {
  childList: true,
  subtree: true,
  attributes: true,
  attributeFilter: ATTRS,
});
