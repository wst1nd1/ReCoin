"use strict";

/* Фон секции «Что делает ReCoin»: точки расставлены по спирали, медленно
   вращаются и соединяются линиями с ближайшими соседями. Курсор
   расталкивает точки рядом с собой. Рисуется на canvas поверх фона страницы. */

const canvas = document.getElementById("swarm");
const section = canvas && canvas.closest("section");

if (canvas && section && !window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
  const ctx = canvas.getContext("2d");
  const pointer = { x: -9999, y: -9999, radius: 130 };
  let points = [];
  let width = 0;
  let height = 0;
  let dpr = 1;
  let time = 0;
  let frame = 0;
  let visible = true;
  let colors = { dot: "rgba(217, 163, 54, 0.55)", line: "217, 163, 54" };

  /* Цвета берутся из темы: на странице они заданы переменными. */
  const readColors = () => {
    const style = getComputedStyle(document.documentElement);
    const dark = document.documentElement.dataset.theme === "dark";
    // На светлом фоне золотой бледнеет, поэтому берётся его тёмный оттенок.
    const accent = style.getPropertyValue(dark ? "--accent" : "--accent-text").trim() || "#d9a336";
    const rgb = hexToRgb(accent);
    colors = {
      dot: `rgba(${rgb}, ${dark ? 0.6 : 0.55})`,
      line: rgb,
      lineAlpha: dark ? 0.26 : 0.34,
    };
  };

  function hexToRgb(hex) {
    const value = hex.replace("#", "");
    const full = value.length === 3 ? value.split("").map((c) => c + c).join("") : value;
    const num = parseInt(full, 16);
    return `${(num >> 16) & 255}, ${(num >> 8) & 255}, ${num & 255}`;
  }

  /* Точки раскладываются по золотому углу – получается ровная спираль. */
  const build = () => {
    const count = width < 620 ? 80 : width < 1000 ? 140 : 200;
    const golden = Math.PI * (3 - Math.sqrt(5));
    const maxRadius = Math.max(width, height) * 0.62;
    points = [];

    for (let i = 0; i < count; i++) {
      const distance = Math.pow(i / (count - 1 || 1), 0.62) * maxRadius;
      const angle = i * golden;
      points.push({
        x: width / 2 + Math.cos(angle) * distance,
        y: height / 2 + Math.sin(angle) * distance,
        vx: 0,
        vy: 0,
        angle,
        distance,
        size: Math.random() * 1.3 + 0.6,
        excitation: 0,
      });
    }
  };

  const resize = () => {
    const rect = section.getBoundingClientRect();
    width = rect.width;
    height = rect.height;
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.round(width * dpr);
    canvas.height = Math.round(height * dpr);
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    build();
  };

  const step = () => {
    frame = requestAnimationFrame(step);
    if (!visible || document.hidden) return;

    time += 0.0016;
    ctx.clearRect(0, 0, width, height);

    const cx = width / 2;
    const cy = height / 2;

    for (const p of points) {
      // Вся спираль медленно поворачивается, ближние точки – чуть быстрее.
      const angle = p.angle + time * (1 + 120 / (p.distance + 120));
      const baseX = cx + Math.cos(angle) * p.distance;
      const baseY = cy + Math.sin(angle) * p.distance;

      p.vx += (baseX - p.x) * 0.02;
      p.vy += (baseY - p.y) * 0.02;

      const dx = p.x - pointer.x;
      const dy = p.y - pointer.y;
      const dist = Math.hypot(dx, dy);
      if (dist < pointer.radius && dist > 0) {
        const force = (pointer.radius - dist) / pointer.radius;
        p.vx += (dx / dist) * force * 1.4;
        p.vy += (dy / dist) * force * 1.4;
        p.excitation = Math.max(p.excitation, force);
      }

      p.vx *= 0.88;
      p.vy *= 0.88;
      p.x += p.vx;
      p.y += p.vy;
      p.excitation *= 0.95;
    }

    // Линии между соседями по спирали: короткие связи дают сетку.
    ctx.lineWidth = 0.6;
    for (let i = 0; i < points.length; i++) {
      const a = points[i];
      const limit = Math.min(points.length, i + 12);
      for (let j = i + 1; j < limit; j++) {
        const b = points[j];
        const dx = a.x - b.x;
        const dy = a.y - b.y;
        const distSq = dx * dx + dy * dy;
        if (distSq > 18000) continue;
        const dist = Math.sqrt(distSq);
        const near = 1 - dist / 134;
        const alpha = Math.min(0.6, near * colors.lineAlpha + Math.max(a.excitation, b.excitation) * 0.4);
        ctx.strokeStyle = `rgba(${colors.line}, ${alpha})`;
        ctx.beginPath();
        ctx.moveTo(a.x, a.y);
        ctx.lineTo(b.x, b.y);
        ctx.stroke();
      }
    }

    ctx.fillStyle = colors.dot;
    for (const p of points) {
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.size + p.excitation * 2, 0, Math.PI * 2);
      ctx.fill();
    }
  };

  section.addEventListener("mousemove", (event) => {
    const rect = section.getBoundingClientRect();
    pointer.x = event.clientX - rect.left;
    pointer.y = event.clientY - rect.top;
  });
  section.addEventListener("mouseleave", () => {
    pointer.x = -9999;
    pointer.y = -9999;
  });

  // Пока секция за пределами экрана, кадры не рисуются.
  if ("IntersectionObserver" in window) {
    new IntersectionObserver((entries) => {
      visible = entries[0].isIntersecting;
    }).observe(section);
  }

  new ResizeObserver(resize).observe(section);
  new MutationObserver(readColors).observe(document.documentElement, {
    attributes: true,
    attributeFilter: ["data-theme"],
  });

  readColors();
  resize();
  frame = requestAnimationFrame(step);
}
