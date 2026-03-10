import { f as fallback, d as attr_class, e as escape_html, g as slot, b as bind_props } from "./index2.js";
/* empty css                                    */
function Panel($$renderer, $$props) {
  let eyebrow = fallback($$props["eyebrow"], "");
  let title = fallback($$props["title"], "");
  let compact = fallback($$props["compact"], false);
  let tone = fallback(
    $$props["tone"],
    ""
    // "emerald", "amber", "crimson"
  );
  $$renderer.push(`<section${attr_class("panel svelte-hxsa5u", void 0, {
    "panel--compact": compact,
    "border-emerald": tone === "emerald",
    "border-amber": tone === "amber",
    "border-crimson": tone === "crimson"
  })}>`);
  if (eyebrow || title) {
    $$renderer.push("<!--[0-->");
    $$renderer.push(`<header class="panel__head svelte-hxsa5u"><div class="status-metric">`);
    if (eyebrow) {
      $$renderer.push("<!--[0-->");
      $$renderer.push(`<span class="status-metric__label">${escape_html(eyebrow)}</span>`);
    } else {
      $$renderer.push("<!--[-1-->");
    }
    $$renderer.push(`<!--]--> `);
    if (title) {
      $$renderer.push("<!--[0-->");
      $$renderer.push(`<h2 class="status-metric__value">${escape_html(title)}</h2>`);
    } else {
      $$renderer.push("<!--[-1-->");
    }
    $$renderer.push(`<!--]--></div> <!--[-->`);
    slot($$renderer, $$props, "head", {});
    $$renderer.push(`<!--]--></header>`);
  } else {
    $$renderer.push("<!--[-1-->");
  }
  $$renderer.push(`<!--]--> <div class="panel__content svelte-hxsa5u"><!--[-->`);
  slot($$renderer, $$props, "default", {});
  $$renderer.push(`<!--]--></div> <div class="hud-decor-tl svelte-hxsa5u"></div> <div class="hud-decor-br svelte-hxsa5u"></div></section>`);
  bind_props($$props, { eyebrow, title, compact, tone });
}
export {
  Panel as P
};
