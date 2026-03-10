import { f as fallback, a as attr, b as bind_props, k as stringify } from "./index2.js";
function Sparkline($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let points, fillPoints;
    let values = fallback($$props["values"], () => [], true);
    let tone = fallback($$props["tone"], "emerald");
    points = (() => {
      if (!values.length) return "";
      const min = Math.min(...values);
      const max = Math.max(...values);
      const span = Math.max(max - min, 1e-4);
      return values.map((value, index) => {
        const x = values.length === 1 ? 0 : index / (values.length - 1) * 100;
        const y = 40 - (value - min) / span * 40;
        return `${x},${y}`;
      }).join(" ");
    })();
    fillPoints = points ? `0,40 ${points} 100,40` : "";
    $$renderer2.push(`<div class="sparkline-wrapper svelte-18qpfvr"><svg class="sparkline svelte-18qpfvr" viewBox="0 0 100 40" preserveAspectRatio="none" aria-hidden="true"><defs><linearGradient${attr("id", `spark-grad-${stringify(tone)}`)} x1="0%" y1="0%" x2="0%" y2="100%"><stop offset="0%"${attr("stop-color", `var(--${stringify(tone)})`)} stop-opacity="0.2"></stop><stop offset="100%"${attr("stop-color", `var(--${stringify(tone)})`)} stop-opacity="0"></stop></linearGradient></defs>`);
    if (fillPoints) {
      $$renderer2.push("<!--[0-->");
      $$renderer2.push(`<polyline${attr("points", fillPoints)}${attr("fill", `url(#spark-grad-${stringify(tone)})`)} stroke="none"></polyline>`);
    } else {
      $$renderer2.push("<!--[-1-->");
    }
    $$renderer2.push(`<!--]--><polyline${attr("points", points)} fill="none"${attr("stroke", `var(--${stringify(tone)})`)} stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="spark-path svelte-18qpfvr"></polyline></svg></div>`);
    bind_props($$props, { values, tone });
  });
}
export {
  Sparkline as S
};
