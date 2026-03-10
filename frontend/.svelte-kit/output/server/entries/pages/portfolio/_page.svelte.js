import { s as spread_props, i as store_get, e as escape_html, d as attr_class, u as unsubscribe_stores, c as ensure_array_like, a as attr } from "../../../chunks/index2.js";
import { L as LedgerTable } from "../../../chunks/LedgerTable.js";
import { P as Panel } from "../../../chunks/Panel.js";
import { S as Sparkline } from "../../../chunks/Sparkline.js";
import { c as controlRoom } from "../../../chunks/control-room.js";
import { a as formatCurrency, b as formatSignedPercent, c as formatPercent, d as formatDate } from "../../../chunks/format.js";
import { Z as Zap } from "../../../chunks/zap.js";
import { I as Icon } from "../../../chunks/Icon.js";
import { P as Power } from "../../../chunks/power.js";
function Chart_pie($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let { $$slots, $$events, ...props } = $$props;
    const iconNode = [
      [
        "path",
        {
          "d": "M21 12c.552 0 1.005-.449.95-.998a10 10 0 0 0-8.953-8.951c-.55-.055-.998.398-.998.95v8a1 1 0 0 0 1 1z"
        }
      ],
      ["path", { "d": "M21.21 15.89A10 10 0 1 1 8 2.83" }]
    ];
    Icon($$renderer2, spread_props([
      { name: "chart-pie" },
      /**
       * @component @name ChartPie
       * @description Lucide SVG icon component, renders SVG Element with children.
       *
       * @preview ![img](data:image/svg+xml;base64,PHN2ZyAgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIgogIHdpZHRoPSIyNCIKICBoZWlnaHQ9IjI0IgogIHZpZXdCb3g9IjAgMCAyNCAyNCIKICBmaWxsPSJub25lIgogIHN0cm9rZT0iIzAwMCIgc3R5bGU9ImJhY2tncm91bmQtY29sb3I6ICNmZmY7IGJvcmRlci1yYWRpdXM6IDJweCIKICBzdHJva2Utd2lkdGg9IjIiCiAgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIgogIHN0cm9rZS1saW5lam9pbj0icm91bmQiCj4KICA8cGF0aCBkPSJNMjEgMTJjLjU1MiAwIDEuMDA1LS40NDkuOTUtLjk5OGExMCAxMCAwIDAgMC04Ljk1My04Ljk1MWMtLjU1LS4wNTUtLjk5OC4zOTgtLjk5OC45NXY4YTEgMSAwIDAgMCAxIDF6IiAvPgogIDxwYXRoIGQ9Ik0yMS4yMSAxNS44OUExMCAxMCAwIDEgMSA4IDIuODMiIC8+Cjwvc3ZnPgo=) - https://lucide.dev/icons/chart-pie
       * @see https://lucide.dev/guide/packages/lucide-svelte - Documentation
       *
       * @param {Object} props - Lucide icons props and any valid SVG attribute
       * @returns {FunctionalComponent} Svelte component
       *
       */
      props,
      {
        iconNode,
        children: ($$renderer3) => {
          props.children?.($$renderer3);
          $$renderer3.push(`<!---->`);
        },
        $$slots: { default: true }
      }
    ]));
  });
}
function Trending_up($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let { $$slots, $$events, ...props } = $$props;
    const iconNode = [
      ["path", { "d": "M16 7h6v6" }],
      ["path", { "d": "m22 7-8.5 8.5-5-5L2 17" }]
    ];
    Icon($$renderer2, spread_props([
      { name: "trending-up" },
      /**
       * @component @name TrendingUp
       * @description Lucide SVG icon component, renders SVG Element with children.
       *
       * @preview ![img](data:image/svg+xml;base64,PHN2ZyAgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIgogIHdpZHRoPSIyNCIKICBoZWlnaHQ9IjI0IgogIHZpZXdCb3g9IjAgMCAyNCAyNCIKICBmaWxsPSJub25lIgogIHN0cm9rZT0iIzAwMCIgc3R5bGU9ImJhY2tncm91bmQtY29sb3I6ICNmZmY7IGJvcmRlci1yYWRpdXM6IDJweCIKICBzdHJva2Utd2lkdGg9IjIiCiAgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIgogIHN0cm9rZS1saW5lam9pbj0icm91bmQiCj4KICA8cGF0aCBkPSJNMTYgN2g2djYiIC8+CiAgPHBhdGggZD0ibTIyIDctOC41IDguNS01LTVMMiAxNyIgLz4KPC9zdmc+Cg==) - https://lucide.dev/icons/trending-up
       * @see https://lucide.dev/guide/packages/lucide-svelte - Documentation
       *
       * @param {Object} props - Lucide icons props and any valid SVG attribute
       * @returns {FunctionalComponent} Svelte component
       *
       */
      props,
      {
        iconNode,
        children: ($$renderer3) => {
          props.children?.($$renderer3);
          $$renderer3.push(`<!---->`);
        },
        $$slots: { default: true }
      }
    ]));
  });
}
function _page($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    var $$store_subs;
    let busyTicker = "";
    if (!store_get($$store_subs ??= {}, "$controlRoom", controlRoom).portfolio) {
      $$renderer2.push("<!--[0-->");
      $$renderer2.push(`<div class="flex flex-col items-center justify-center min-h-[60vh] gap-4 svelte-1uo84gz">`);
      Zap($$renderer2, { size: 32, class: "text-emerald animate-pulse" });
      $$renderer2.push(`<!----> <div class="mono text-[10px] tracking-[0.2em] text-emerald opacity-50 uppercase">Loading Capital Structures...</div></div>`);
    } else {
      $$renderer2.push("<!--[-1-->");
      $$renderer2.push(`<div class="space-y-6 svelte-1uo84gz"><section class="flex justify-between items-end border-b border-subtle pb-6 svelte-1uo84gz"><div class="space-y-1 svelte-1uo84gz"><div class="flex items-center gap-2 text-emerald svelte-1uo84gz">`);
      Trending_up($$renderer2, { size: 14 });
      $$renderer2.push(`<!----> <span class="mono text-[10px] tracking-[0.2em] uppercase font-bold">Capital Allocation Wall</span></div> <h1 class="text-3xl font-bold tracking-tight svelte-1uo84gz">Portfolio <span class="text-emerald">Dynamics</span></h1> <p class="text-ink-secondary text-sm max-w-xl svelte-1uo84gz">Asset exposure, equity curves, and direct execution overrides.</p></div> <div class="w-64 h-16 opacity-80 svelte-1uo84gz">`);
      Sparkline($$renderer2, {
        values: store_get($$store_subs ??= {}, "$controlRoom", controlRoom).portfolio.marks.map((row) => row.portfolio_value).reverse()
      });
      $$renderer2.push(`<!----></div></section> <div class="grid grid-cols-2 md-grid-cols-3 lg-grid-cols-5 gap-4 svelte-1uo84gz"><div class="p-4 bg-obsidian-800 border border-subtle"><div class="status-metric"><span class="status-metric__label">NAV</span> <span class="status-metric__value mono text-xl">${escape_html(formatCurrency(store_get($$store_subs ??= {}, "$controlRoom", controlRoom).portfolio.snapshot.portfolio_value))}</span></div></div> <div class="p-4 bg-obsidian-800 border border-subtle"><div class="status-metric"><span class="status-metric__label">LIQUID CASH</span> <span class="status-metric__value mono text-xl">${escape_html(formatCurrency(store_get($$store_subs ??= {}, "$controlRoom", controlRoom).portfolio.snapshot.cash_balance))}</span></div></div> <div class="p-4 bg-obsidian-800 border border-subtle"><div class="status-metric"><span class="status-metric__label">EXPOSURE</span> <span class="status-metric__value mono text-xl">${escape_html(formatCurrency(store_get($$store_subs ??= {}, "$controlRoom", controlRoom).portfolio.snapshot.total_market_value))}</span></div></div> <div class="p-4 bg-obsidian-800 border border-subtle"><div class="status-metric"><span class="status-metric__label">UNREALIZED</span> <span${attr_class("status-metric__value mono text-xl", void 0, {
        "text-emerald": store_get($$store_subs ??= {}, "$controlRoom", controlRoom).portfolio.snapshot.total_unrealized_pnl >= 0,
        "text-crimson": store_get($$store_subs ??= {}, "$controlRoom", controlRoom).portfolio.snapshot.total_unrealized_pnl < 0
      })}>${escape_html(formatCurrency(store_get($$store_subs ??= {}, "$controlRoom", controlRoom).portfolio.snapshot.total_unrealized_pnl))}</span></div></div> <div class="p-4 bg-obsidian-800 border border-subtle"><div class="status-metric"><span class="status-metric__label">REALIZED</span> <span${attr_class("status-metric__value mono text-xl", void 0, {
        "text-emerald": store_get($$store_subs ??= {}, "$controlRoom", controlRoom).portfolio.snapshot.total_realized_pnl >= 0,
        "text-crimson": store_get($$store_subs ??= {}, "$controlRoom", controlRoom).portfolio.snapshot.total_realized_pnl < 0
      })}>${escape_html(formatCurrency(store_get($$store_subs ??= {}, "$controlRoom", controlRoom).portfolio.snapshot.total_realized_pnl))}</span></div></div></div> `);
      Panel($$renderer2, {
        eyebrow: "INVENTORY",
        title: "Live Holdings",
        tone: "emerald",
        children: ($$renderer3) => {
          {
            $$renderer3.push("<!--[-1-->");
          }
          $$renderer3.push(`<!--]--> <div class="grid grid-cols-1 md-grid-cols-2 lg-grid-cols-3 xl-grid-cols-4 gap-4 svelte-1uo84gz">`);
          if (store_get($$store_subs ??= {}, "$controlRoom", controlRoom).portfolio.positions.length) {
            $$renderer3.push("<!--[0-->");
            $$renderer3.push(`<!--[-->`);
            const each_array = ensure_array_like(store_get($$store_subs ??= {}, "$controlRoom", controlRoom).portfolio.positions);
            for (let $$index = 0, $$length = each_array.length; $$index < $$length; $$index++) {
              let position = each_array[$$index];
              $$renderer3.push(`<div class="p-4 bg-obsidian-700 border border-subtle space-y-4 hover:border-emerald transition-colors relative group svelte-1uo84gz"><div class="flex justify-between items-start svelte-1uo84gz"><div class="flex flex-col"><span class="mono text-lg font-bold text-emerald">${escape_html(position.ticker)}</span> <span class="text-[9px] text-ink-dim uppercase tracking-widest">${escape_html(position.position_type)} Position</span></div> <button class="p-2 border border-subtle text-ink-dim hover:text-crimson hover:border-crimson transition-all"${attr("disabled", busyTicker !== "", true)} title="FORCE TERMINATION">`);
              Power($$renderer3, {
                size: 14,
                class: busyTicker === position.ticker ? "animate-spin" : ""
              });
              $$renderer3.push(`<!----></button></div> <div class="grid grid-cols-2 gap-4 border-y border-subtle/50 py-3 svelte-1uo84gz"><div class="status-metric"><span class="status-metric__label">QUANTITY</span> <span class="status-metric__value mono text-sm">${escape_html(position.shares)}</span></div> <div class="status-metric text-right"><span class="status-metric__label">AVG PRICE</span> <span class="status-metric__value mono text-sm">${escape_html(formatCurrency(position.avg_entry_price))}</span></div></div> <div class="status-metric svelte-1uo84gz"><span class="status-metric__label">TOTAL EXPOSURE</span> <span class="status-metric__value mono text-sm">${escape_html(formatCurrency(position.total_cost))}</span></div></div>`);
            }
            $$renderer3.push(`<!--]-->`);
          } else {
            $$renderer3.push("<!--[-1-->");
            $$renderer3.push(`<div class="col-span-full py-12 flex flex-col items-center justify-center text-ink-dim gap-2 border border-dashed border-subtle svelte-1uo84gz">`);
            Chart_pie($$renderer3, { size: 24, strokeWidth: 1 });
            $$renderer3.push(`<!----> <span class="mono text-[10px] uppercase tracking-[0.2em]">Zero Inventory Detected</span></div>`);
          }
          $$renderer3.push(`<!--]--></div>`);
        },
        $$slots: { default: true }
      });
      $$renderer2.push(`<!----> <div class="grid grid-cols-1 lg-grid-cols-split gap-6 svelte-1uo84gz">`);
      Panel($$renderer2, {
        eyebrow: "TEMPORAL SNAPSHOT",
        title: "Current Regime",
        tone: "amber",
        children: ($$renderer3) => {
          if (store_get($$store_subs ??= {}, "$controlRoom", controlRoom).portfolio.marks[0]) {
            $$renderer3.push("<!--[0-->");
            const mark = store_get($$store_subs ??= {}, "$controlRoom", controlRoom).portfolio.marks[0];
            $$renderer3.push(`<div class="space-y-4 svelte-1uo84gz"><div class="p-4 bg-obsidian-900 border border-amber/20 svelte-1uo84gz"><div class="status-metric"><span class="status-metric__label">ACTIVE REGIME</span> <span class="status-metric__value text-amber text-xl tracking-tight uppercase svelte-1uo84gz">${escape_html(String(mark.details.regime ?? "EQUILIBRIUM"))}</span></div></div> <div class="grid grid-cols-2 gap-4 border-b border-subtle pb-4 svelte-1uo84gz"><div class="status-metric"><span class="status-metric__label">ALPHA G.V.</span> <span${attr_class("status-metric__value mono", void 0, {
              "text-emerald": Number(mark.alpha_pct ?? 0) >= 0,
              "text-crimson": Number(mark.alpha_pct ?? 0) < 0
            })}>${escape_html(formatSignedPercent(mark.alpha_pct ?? 0))}</span></div> <div class="status-metric text-right"><span class="status-metric__label">BENCHMARK</span> <span class="status-metric__value mono">${escape_html(formatPercent(mark.benchmark_return_pct ?? 0))}</span></div></div> <div class="space-y-3 svelte-1uo84gz"><div class="flex justify-between items-center svelte-1uo84gz"><span class="status-metric__label">REALIZED (24H)</span> <span${attr_class("mono text-sm", void 0, {
              "text-emerald": Number(mark.realized_pnl_today ?? 0) >= 0,
              "text-crimson": Number(mark.realized_pnl_today ?? 0) < 0
            })}>${escape_html(formatCurrency(mark.realized_pnl_today ?? 0))}</span></div> <div class="flex justify-between items-center svelte-1uo84gz"><span class="status-metric__label">AGGREGATE REALIZED</span> <span class="mono text-sm">${escape_html(formatCurrency(mark.total_realized_pnl ?? 0))}</span></div> <div class="flex justify-between items-center svelte-1uo84gz"><span class="status-metric__label">DATA STAMP</span> <span class="mono text-[10px] text-ink-dim uppercase">${escape_html(formatDate(mark.mark_date))}</span></div></div></div>`);
          } else {
            $$renderer3.push("<!--[-1-->");
            $$renderer3.push(`<div class="py-20 text-center text-ink-dim mono text-[10px] uppercase tracking-widest svelte-1uo84gz">Awaiting First Mark</div>`);
          }
          $$renderer3.push(`<!--]-->`);
        },
        $$slots: { default: true }
      });
      $$renderer2.push(`<!----> `);
      Panel($$renderer2, {
        eyebrow: "AUDIT TRAIL",
        title: "Marked Intervals",
        children: ($$renderer3) => {
          LedgerTable($$renderer3, {
            rows: store_get($$store_subs ??= {}, "$controlRoom", controlRoom).portfolio.marks,
            columns: [
              { key: "mark_date", label: "DATE" },
              { key: "portfolio_value", label: "NAV", type: "mono" },
              {
                key: "realized_pnl_today",
                label: "REALIZED (24H)",
                type: "mono"
              },
              { key: "unrealized_pnl", label: "UNREALIZED", type: "mono" },
              { key: "alpha_pct", label: "ALPHA %", type: "mono" }
            ]
          });
        },
        $$slots: { default: true }
      });
      $$renderer2.push(`<!----></div></div>`);
    }
    $$renderer2.push(`<!--]-->`);
    if ($$store_subs) unsubscribe_stores($$store_subs);
  });
}
export {
  _page as default
};
