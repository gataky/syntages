// Recipe pages: servings scaler, ticking off ingredients and steps, keeping the
// screen awake. The markup comes from hooks/recipes.py; amounts that scale are
// <span class="q" data-qty data-to data-unit>, followed by <span class="u"> when
// they have a unit. Material's instant navigation swaps pages without a reload,
// so setup runs for every page through document$.

const PLURAL = { cup: "cups", can: "cans", box: "boxes", clove: "cloves" };
const METRIC = new Set(["g", "kg", "ml", "dl", "l"]);
const BIGGER = { g: "kg", ml: "l" }; // 1000 g shows as 1 kg
const GLYPHS = [[0, ""], [1 / 8, "⅛"], [1 / 4, "¼"], [1 / 3, "⅓"], [1 / 2, "½"], [2 / 3, "⅔"], [3 / 4, "¾"], [1, ""]];
const SCALES = [[0.5, "½×"], [1, "1×"], [2, "2×"], [3, "3×"]];

// Same rounding as format_number() in hooks/recipes.py: decimals for metric
// units and large numbers, kitchen fractions for the rest.
function fmt(value, unit) {
  if (METRIC.has(unit) || value >= 10) {
    return String(value < 10 ? Math.round(value * 10) / 10 : Math.round(value));
  }
  let whole = Math.floor(value);
  const part = value - whole;
  const [frac, glyph] = GLYPHS.reduce((a, b) => (Math.abs(b[0] - part) < Math.abs(a[0] - part) ? b : a));
  if (Math.abs(frac - part) > 0.04) return String(Math.round(value * 100) / 100);
  if (frac === 1) whole += 1;
  return (whole || "") + glyph || "0";
}

function load(key) {
  try {
    return JSON.parse(localStorage.getItem(key)) || {};
  } catch {
    return {};
  }
}

function save(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {}
}

// Screen wake lock. The browser drops it when the tab is hidden, so it is
// requested again on return while still wanted.
const wake = { lock: null, wanted: false, button: null };

async function setWake(on) {
  wake.wanted = on;
  if (on && !wake.lock && document.visibilityState === "visible") {
    try {
      wake.lock = await navigator.wakeLock.request("screen");
      wake.lock.addEventListener("release", () => {
        wake.lock = null;
        showWake();
      });
    } catch {}
  } else if (!on && wake.lock) {
    await wake.lock.release();
  }
  showWake();
}

function showWake() {
  if (wake.button?.isConnected) wake.button.setAttribute("aria-pressed", String(!!wake.lock));
}

document.addEventListener("visibilitychange", () => {
  if (wake.wanted && document.visibilityState === "visible") setWake(true);
});

function setup() {
  const tools = document.querySelector(".recipe-tools");
  if (!tools) {
    setWake(false);
    return;
  }
  const article = tools.closest("article");
  const key = "recipe:" + location.pathname;
  const state = { scale: 1, checked: [], done: [], ...load(key) };

  const boxes = [...article.querySelectorAll(".recipe-ingredients input[type=checkbox]")];
  const steps = [...article.querySelectorAll(".recipe-step")];
  const quantities = [...article.querySelectorAll(".q")];
  for (const q of quantities) {
    q.dataset.orig = q.textContent;
    const u = q.nextElementSibling?.matches(".u") && q.nextElementSibling;
    if (u) u.dataset.orig = u.textContent;
  }

  const scaler = document.createElement("div");
  scaler.className = "recipe-scale";
  scaler.setAttribute("role", "group");
  scaler.setAttribute("aria-label", "Scale the recipe");
  for (const [value, label] of SCALES) {
    const b = document.createElement("button");
    b.type = "button";
    b.textContent = label;
    b.dataset.scale = value;
    b.addEventListener("click", () => {
      state.scale = value;
      render();
    });
    scaler.append(b);
  }

  const reset = document.createElement("button");
  reset.type = "button";
  reset.className = "recipe-reset";
  reset.textContent = "Reset";
  reset.addEventListener("click", () => {
    Object.assign(state, { scale: 1, checked: [], done: [] });
    render();
  });

  // Nothing to scale when no ingredient has an amount (fried chicken).
  tools.replaceChildren(...(quantities.length ? [scaler] : []));
  if ("wakeLock" in navigator) {
    wake.button = document.createElement("button");
    wake.button.type = "button";
    wake.button.className = "recipe-wake";
    wake.button.textContent = "Keep screen on";
    wake.button.addEventListener("click", () => {
      const on = !wake.lock;
      save("recipe:wake", on);
      setWake(on);
    });
    tools.append(wake.button);
    setWake(load("recipe:wake") === true);
  }
  tools.append(reset);

  boxes.forEach((box) =>
    box.addEventListener("change", () => {
      state.checked = boxes.flatMap((b, j) => (b.checked ? [j] : []));
      render();
    }),
  );
  steps.forEach((step) =>
    step.querySelector(".step-num").addEventListener("click", () => {
      step.classList.toggle("done");
      state.done = steps.flatMap((s, j) => (s.classList.contains("done") ? [j] : []));
      render();
    }),
  );

  function render() {
    for (const b of scaler.children) b.setAttribute("aria-pressed", String(+b.dataset.scale === state.scale));
    for (const q of quantities) {
      const u = q.nextElementSibling?.matches(".u") && q.nextElementSibling;
      const unit = q.dataset.unit;
      if (state.scale === 1) {
        q.textContent = q.dataset.orig;
        if (u) u.textContent = u.dataset.orig;
        continue;
      }
      let qty = q.dataset.qty * state.scale;
      let to = q.dataset.to && q.dataset.to * state.scale;
      let shown = unit;
      if (BIGGER[unit] && qty >= 1000) {
        [qty, to, shown] = [qty / 1000, to && to / 1000, BIGGER[unit]];
      }
      q.textContent = fmt(qty, shown) + (to ? "–" + fmt(to, shown) : "");
      if (u) u.textContent = PLURAL[unit] && (to || qty) > 1 ? PLURAL[unit] : shown;
    }
    boxes.forEach((b, i) => (b.checked = state.checked.includes(i)));
    steps.forEach((s, i) => {
      s.classList.toggle("done", state.done.includes(i));
      s.querySelector(".step-num").setAttribute("aria-pressed", String(state.done.includes(i)));
    });
    reset.hidden = state.scale === 1 && !state.checked.length && !state.done.length;
    save(key, state);
  }

  render();
}

document$.subscribe(setup);
