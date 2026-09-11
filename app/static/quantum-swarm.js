"use strict";

/* Компонент фонового узора на React. Библиотеки подключаются как модули
   с внешней сети, сборка проекту не нужна. Разметка описана шаблонами htm –
   это тот же синтаксис, что и JSX, только без предварительной компиляции. */

import React, { useEffect, useRef, useState, useCallback } from "https://esm.sh/react@18.3.1";
import { createRoot } from "https://esm.sh/react-dom@18.3.1/client";
import htm from "https://esm.sh/htm@3.1.1";
import clsx from "https://esm.sh/clsx@2.1.1";
import { twMerge } from "https://esm.sh/tailwind-merge@2.5.4";
import { Play, Pause, Zap } from "https://esm.sh/lucide-react@0.468.0?deps=react@18.3.1";

const html = htm.bind(React.createElement);
const cn = (...inputs) => twMerge(clsx(inputs));

/* Цвета узора берутся из темы страницы. */
function readPalette() {
  const style = getComputedStyle(document.documentElement);
  const dark = document.documentElement.dataset.theme === "dark";
  const hex = (style.getPropertyValue(dark ? "--accent" : "--accent-text").trim() || "#d9a336").replace("#", "");
  const full = hex.length === 3 ? hex.split("").map((c) => c + c).join("") : hex;
  const num = parseInt(full, 16);
  return {
    rgb: `${(num >> 16) & 255}, ${(num >> 8) & 255}, ${num & 255}`,
    dot: dark ? 0.6 : 0.55,
    line: dark ? 0.26 : 0.34,
  };
}

export function QuantumSwarm({ particleCount, chrome = true, tagline = "SWARM", headline = "" }) {
  const containerRef = useRef(null);
  const canvasRef = useRef(null);
  const particlesRef = useRef([]);
  const paletteRef = useRef(readPalette());
  const dimensionsRef = useRef({ width: 0, height: 0, cx: 0, cy: 0 });
  const pointerRef = useRef({ x: -2000, y: -2000, isDown: false, radius: 150, shockwaves: [] });

  const [isRunning, setIsRunning] = useState(true);

  /* Точки раскладываются по золотому углу – получается ровная спираль. */
  const buildSwarm = useCallback(() => {
    const { width, height, cx, cy } = dimensionsRef.current;
    if (!width || !height) return;

    const count = particleCount || (width < 620 ? 90 : width < 1000 ? 160 : 240);
    const golden = Math.PI * 2 * ((1 + Math.sqrt(5)) / 2);
    const maxRadius = Math.max(width, height) * 0.55;
    const particles = [];

    for (let i = 0; i < count; i++) {
      const distance = Math.pow(i / (count - 1 || 1), 0.6) * maxRadius;
      const angle = i * golden;
      particles.push({
        x: cx + Math.cos(angle) * distance,
        y: cy + Math.sin(angle) * distance,
        vx: 0,
        vy: 0,
        baseX: 0,
        baseY: 0,
        angle,
        distance,
        size: Math.random() * 1.4 + 0.5,
        excitation: 0,
        // Собственные фазы и размах блуждания: без них движение выглядит
        // слишком правильным.
        phaseX: Math.random() * Math.PI * 2,
        phaseY: Math.random() * Math.PI * 2,
        speedX: 0.6 + Math.random() * 1.6,
        speedY: 0.6 + Math.random() * 1.6,
        wander: 8 + Math.random() * 26,
      });
    }

    particlesRef.current = particles;
  }, [particleCount]);

  /* Размер холста следует за размером секции. */
  useEffect(() => {
    const container = containerRef.current;
    const canvas = canvasRef.current;
    if (!container || !canvas) return;

    const ctx = canvas.getContext("2d");

    const apply = (rect) => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const previous = dimensionsRef.current;

      const widthChanged = Math.abs(rect.width - previous.width) > 2;

      dimensionsRef.current = {
        width: rect.width,
        height: rect.height,
        // При смене одной высоты центр остаётся на месте, иначе узор
        // сползал бы каждый раз, когда страница становится длиннее.
        cx: widthChanged || !previous.width ? rect.width / 2 : previous.cx,
        cy: widthChanged || !previous.height ? rect.height / 2 : previous.cy,
      };

      canvas.width = Math.round(rect.width * dpr);
      canvas.height = Math.round(rect.height * dpr);
      canvas.style.width = `${rect.width}px`;
      canvas.style.height = `${rect.height}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

      // Заново точки расставляются только при смене ширины. Высота меняется
      // каждый раз, когда на странице что-то раскрывается, и пересборка
      // приводила бы к рывку.
      if (widthChanged || particlesRef.current.length === 0) buildSwarm();
    };

    // Первый расчёт сразу: сообщения наблюдателя приходят только вместе
    // с отрисовкой, а её может не быть до появления страницы на экране.
    // Пока размеры нулевые, попытки повторяются.
    let attempts = 8;
    const ensure = () => {
      apply(container.getBoundingClientRect());
      if (attempts-- > 0) setTimeout(ensure, 150);
    };
    ensure();
    window.addEventListener("load", ensure);

    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) apply(entry.contentRect);
    });

    observer.observe(container);

    // Запасной пересчёт: сообщения наблюдателя приходят вместе с отрисовкой,
    // а размеры слоя может поменять и внешний скрипт.
    const onResize = () => apply(container.getBoundingClientRect());
    window.addEventListener("resize", onResize);
    window.addEventListener("swarm:layout", onResize);

    return () => {
      observer.disconnect();
      window.removeEventListener("resize", onResize);
      window.removeEventListener("swarm:layout", onResize);
      window.removeEventListener("load", ensure);
      attempts = 0;
    };
  }, [buildSwarm]);

  /* Смена темы меняет цвета узора. */
  useEffect(() => {
    const observer = new MutationObserver(() => {
      paletteRef.current = readPalette();
    });
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    return () => observer.disconnect();
  }, []);

  /* Расчёт движения и отрисовка. */
  useEffect(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;

    const ctx = canvas.getContext("2d");
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let visible = true;
    let animId = 0;
    let time = 0;

    const io = new IntersectionObserver((entries) => {
      visible = entries[0].isIntersecting;
    });
    io.observe(container);

    const loop = () => {
      animId = requestAnimationFrame(loop);
      if (!isRunning || !visible || document.hidden) return;

      const { width, height, cx, cy } = dimensionsRef.current;
      const particles = particlesRef.current;
      const pointer = pointerRef.current;
      const palette = paletteRef.current;

      if (!reduced) time += 0.002;
      ctx.clearRect(0, 0, width, height);

      // Ударные волны от нажатий расходятся кольцами и затухают.
      for (let s = pointer.shockwaves.length - 1; s >= 0; s--) {
        const wave = pointer.shockwaves[s];
        wave.radius += 15;
        wave.strength *= 0.92;
        if (wave.radius > wave.maxRadius || wave.strength < 0.01) pointer.shockwaves.splice(s, 1);
      }

      for (const p of particles) {
        // Спираль поворачивается целиком, ближние точки – чуть быстрее.
        const angle = p.angle + time * (1 + 100 / (p.distance + 100));
        p.baseX = cx + Math.cos(angle) * p.distance + Math.sin(time * 9 * p.speedX + p.phaseX) * p.wander;
        p.baseY = cy + Math.sin(angle) * p.distance + Math.cos(time * 9 * p.speedY + p.phaseY) * p.wander;

        p.vx += (p.baseX - p.x) * 0.02;
        p.vy += (p.baseY - p.y) * 0.02;

        const dx = p.x - pointer.x;
        const dy = p.y - pointer.y;
        const dist = Math.hypot(dx, dy);
        if (dist < pointer.radius && dist > 0) {
          const force = (pointer.radius - dist) / pointer.radius;
          const direction = pointer.isDown ? -0.5 : 1.5;
          p.vx += (dx / dist) * force * direction;
          p.vy += (dy / dist) * force * direction;
          p.excitation = Math.max(p.excitation, force);
        }

        for (const wave of pointer.shockwaves) {
          const wx = p.x - wave.x;
          const wy = p.y - wave.y;
          const distWave = Math.hypot(wx, wy) || 1;
          const ring = Math.abs(distWave - wave.radius);
          if (ring < 30) {
            const impulse = (1 - ring / 30) * wave.strength * 15;
            p.vx += (wx / distWave) * impulse;
            p.vy += (wy / distWave) * impulse;
            p.excitation = 1;
          }
        }

        // Редкие случайные толчки сбивают правильность орбит.
        if (!reduced && Math.random() < 0.02) {
          p.vx += (Math.random() - 0.5) * 0.7;
          p.vy += (Math.random() - 0.5) * 0.7;
        }

        p.vx *= 0.88;
        p.vy *= 0.88;
        p.x += p.vx;
        p.y += p.vy;
        p.excitation *= 0.95;
      }

      // Связи между соседями по спирали образуют сетку.
      ctx.lineWidth = 0.6;
      for (let i = 0; i < particles.length; i++) {
        const a = particles[i];
        const limit = Math.min(particles.length, i + 15);
        for (let j = i + 1; j < limit; j++) {
          const b = particles[j];
          const dx = a.x - b.x;
          const dy = a.y - b.y;
          const distSq = dx * dx + dy * dy;
          if (distSq > 14400) continue;
          const opacity = 1 - Math.sqrt(distSq) / 120;
          const excited = Math.max(a.excitation, b.excitation);
          ctx.strokeStyle = `rgba(${palette.rgb}, ${Math.min(0.7, opacity * palette.line + excited * 0.5)})`;
          ctx.beginPath();
          ctx.moveTo(a.x, a.y);
          ctx.lineTo(b.x, b.y);
          ctx.stroke();
        }
      }

      for (const p of particles) {
        const radius = p.size + p.excitation * 2.5;
        if (p.excitation > 0.3) {
          ctx.fillStyle = `rgba(${palette.rgb}, ${p.excitation * 0.25})`;
          ctx.beginPath();
          ctx.arc(p.x, p.y, radius * 3, 0, Math.PI * 2);
          ctx.fill();
        }
        ctx.fillStyle = `rgba(${palette.rgb}, ${palette.dot})`;
        ctx.beginPath();
        ctx.arc(p.x, p.y, radius, 0, Math.PI * 2);
        ctx.fill();
      }
    };

    animId = requestAnimationFrame(loop);
    return () => {
      cancelAnimationFrame(animId);
      io.disconnect();
    };
  }, [isRunning]);

  const pointFrom = (event) => {
    const rect = containerRef.current.getBoundingClientRect();
    return { x: event.clientX - rect.left, y: event.clientY - rect.top };
  };

  const handleMove = (event) => {
    const point = pointFrom(event);
    pointerRef.current.x = point.x;
    pointerRef.current.y = point.y;
  };

  const handleDown = (event) => {
    const point = pointFrom(event);
    pointerRef.current.isDown = true;
    pointerRef.current.shockwaves.push({ x: point.x, y: point.y, radius: 10, maxRadius: 220, strength: 0.8 });
  };

  const handleUp = () => {
    pointerRef.current.isDown = false;
  };

  const handleLeave = () => {
    pointerRef.current.x = -2000;
    pointerRef.current.y = -2000;
    pointerRef.current.isDown = false;
  };

  const pulse = () => {
    const { cx, cy, width, height } = dimensionsRef.current;
    pointerRef.current.shockwaves.push({
      x: cx,
      y: cy,
      radius: 10,
      maxRadius: Math.max(width, height) * 0.8,
      strength: 1.5,
    });
  };

  const buttonClass =
    "flex items-center gap-1.5 rounded-lg border border-black/10 bg-white/60 px-2.5 py-1.5 " +
    "text-[10px] backdrop-blur-md transition-colors hover:bg-white/80 " +
    "dark:border-white/10 dark:bg-white/5 dark:hover:bg-white/10";

  return html`
    <div
      ref=${containerRef}
      onMouseMove=${handleMove}
      onMouseDown=${handleDown}
      onMouseUp=${handleUp}
      onMouseLeave=${handleLeave}
      class=${cn("absolute inset-0 select-none overflow-hidden")}
    >
      <canvas ref=${canvasRef} class="absolute inset-0 block h-full w-full" />

      ${chrome &&
      html`
        <div class="pointer-events-none relative z-10 flex h-full w-full flex-col justify-between p-5">
          <header class="pointer-events-auto flex w-full items-center justify-between font-mono text-[11px]">
            <span class="font-semibold uppercase tracking-wider">${tagline}</span>
            <span class="flex items-center gap-2">
              <button type="button" class=${buttonClass} onClick=${pulse}>
                <${Zap} size=${12} /> ИМПУЛЬС
              </button>
              <button type="button" class=${buttonClass} onClick=${() => setIsRunning((v) => !v)}>
                <${isRunning ? Pause : Play} size=${12} /> ${isRunning ? "ПАУЗА" : "ПУСК"}
              </button>
            </span>
          </header>
          <main class="flex flex-col items-center justify-center text-center">
            <h2 class="font-mono text-5xl font-black uppercase tracking-tighter">${headline}</h2>
          </main>
          <div class="h-8 w-full" />
        </div>
      `}
    </div>
  `;
}

const mount = document.getElementById("swarm-root");

if (mount) {
  /* На витрине слой тянется от раздела о возможностях до конца страницы,
     поэтому его границы пересчитываются при изменении разметки. В кабинете
     слой занимает весь экран, и считать ничего не нужно. */
  const start = document.getElementById("how");
  const fixed = mount.classList.contains("swarm-fixed");

  const layout = () => {
    if (!start || fixed) return;
    const top = start.getBoundingClientRect().top + window.scrollY;
    mount.style.top = `${top}px`;
    mount.style.height = `${Math.max(0, document.documentElement.scrollHeight - top)}px`;
    window.dispatchEvent(new Event("swarm:layout"));
  };

  layout();
  // Высота страницы меняется по мере загрузки стилей и картинок.
  window.addEventListener("load", layout);
  new ResizeObserver(layout).observe(document.body);
  window.addEventListener("resize", layout);

  createRoot(mount).render(html`<${QuantumSwarm} chrome=${false} />`);

  // Компонент появляется в разметке не мгновенно, поэтому размеры слоя
  // сообщаются ему ещё раз после первой отрисовки.
  setTimeout(layout, 0);
  setTimeout(layout, 600);
}

export default QuantumSwarm;
