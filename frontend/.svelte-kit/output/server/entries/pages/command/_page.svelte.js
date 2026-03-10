import { s as spread_props, i as store_get, u as unsubscribe_stores, e as escape_html, a as attr, c as ensure_array_like, d as attr_class } from "../../../chunks/index2.js";
import { P as Panel } from "../../../chunks/Panel.js";
import { S as Sparkline } from "../../../chunks/Sparkline.js";
import { c as controlRoom } from "../../../chunks/control-room.js";
import { f as formatDateTime, a as formatCurrency } from "../../../chunks/format.js";
import { Z as Zap } from "../../../chunks/zap.js";
import { G as Gauge } from "../../../chunks/gauge.js";
import { I as Icon } from "../../../chunks/Icon.js";
import { C as Clock } from "../../../chunks/clock.js";
import { A as Activity } from "../../../chunks/activity.js";
function Pause($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let { $$slots, $$events, ...props } = $$props;
    const iconNode = [
      [
        "rect",
        { "x": "14", "y": "3", "width": "5", "height": "18", "rx": "1" }
      ],
      [
        "rect",
        { "x": "5", "y": "3", "width": "5", "height": "18", "rx": "1" }
      ]
    ];
    Icon($$renderer2, spread_props([
      { name: "pause" },
      /**
       * @component @name Pause
       * @description Lucide SVG icon component, renders SVG Element with children.
       *
       * @preview ![img](data:image/svg+xml;base64,PHN2ZyAgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIgogIHdpZHRoPSIyNCIKICBoZWlnaHQ9IjI0IgogIHZpZXdCb3g9IjAgMCAyNCAyNCIKICBmaWxsPSJub25lIgogIHN0cm9rZT0iIzAwMCIgc3R5bGU9ImJhY2tncm91bmQtY29sb3I6ICNmZmY7IGJvcmRlci1yYWRpdXM6IDJweCIKICBzdHJva2Utd2lkdGg9IjIiCiAgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIgogIHN0cm9rZS1saW5lam9pbj0icm91bmQiCj4KICA8cmVjdCB4PSIxNCIgeT0iMyIgd2lkdGg9IjUiIGhlaWdodD0iMTgiIHJ4PSIxIiAvPgogIDxyZWN0IHg9IjUiIHk9IjMiIHdpZHRoPSI1IiBoZWlnaHQ9IjE4IiByeD0iMSIgLz4KPC9zdmc+Cg==) - https://lucide.dev/icons/pause
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
function Play($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let { $$slots, $$events, ...props } = $$props;
    const iconNode = [
      [
        "path",
        {
          "d": "M5 5a2 2 0 0 1 3.008-1.728l11.997 6.998a2 2 0 0 1 .003 3.458l-12 7A2 2 0 0 1 5 19z"
        }
      ]
    ];
    Icon($$renderer2, spread_props([
      { name: "play" },
      /**
       * @component @name Play
       * @description Lucide SVG icon component, renders SVG Element with children.
       *
       * @preview ![img](data:image/svg+xml;base64,PHN2ZyAgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIgogIHdpZHRoPSIyNCIKICBoZWlnaHQ9IjI0IgogIHZpZXdCb3g9IjAgMCAyNCAyNCIKICBmaWxsPSJub25lIgogIHN0cm9rZT0iIzAwMCIgc3R5bGU9ImJhY2tncm91bmQtY29sb3I6ICNmZmY7IGJvcmRlci1yYWRpdXM6IDJweCIKICBzdHJva2Utd2lkdGg9IjIiCiAgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIgogIHN0cm9rZS1saW5lam9pbj0icm91bmQiCj4KICA8cGF0aCBkPSJNNSA1YTIgMiAwIDAgMSAzLjAwOC0xLjcyOGwxMS45OTcgNi45OThhMiAyIDAgMCAxIC4wMDMgMy40NThsLTEyIDdBMiAyIDAgMCAxIDUgMTl6IiAvPgo8L3N2Zz4K) - https://lucide.dev/icons/play
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
function Send($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let { $$slots, $$events, ...props } = $$props;
    const iconNode = [
      [
        "path",
        {
          "d": "M14.536 21.686a.5.5 0 0 0 .937-.024l6.5-19a.496.496 0 0 0-.635-.635l-19 6.5a.5.5 0 0 0-.024.937l7.93 3.18a2 2 0 0 1 1.112 1.11z"
        }
      ],
      ["path", { "d": "m21.854 2.147-10.94 10.939" }]
    ];
    Icon($$renderer2, spread_props([
      { name: "send" },
      /**
       * @component @name Send
       * @description Lucide SVG icon component, renders SVG Element with children.
       *
       * @preview ![img](data:image/svg+xml;base64,PHN2ZyAgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIgogIHdpZHRoPSIyNCIKICBoZWlnaHQ9IjI0IgogIHZpZXdCb3g9IjAgMCAyNCAyNCIKICBmaWxsPSJub25lIgogIHN0cm9rZT0iIzAwMCIgc3R5bGU9ImJhY2tncm91bmQtY29sb3I6ICNmZmY7IGJvcmRlci1yYWRpdXM6IDJweCIKICBzdHJva2Utd2lkdGg9IjIiCiAgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIgogIHN0cm9rZS1saW5lam9pbj0icm91bmQiCj4KICA8cGF0aCBkPSJNMTQuNTM2IDIxLjY4NmEuNS41IDAgMCAwIC45MzctLjAyNGw2LjUtMTlhLjQ5Ni40OTYgMCAwIDAtLjYzNS0uNjM1bC0xOSA2LjVhLjUuNSAwIDAgMC0uMDI0LjkzN2w3LjkzIDMuMThhMiAyIDAgMCAxIDEuMTEyIDEuMTF6IiAvPgogIDxwYXRoIGQ9Im0yMS44NTQgMi4xNDctMTAuOTQgMTAuOTM5IiAvPgo8L3N2Zz4K) - https://lucide.dev/icons/send
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
    let sparkline;
    let message = "";
    let busyAction = "";
    const jobButtons = [
      {
        id: "morning-pipeline",
        label: "Morning Pipeline",
        detail: "09:30"
      },
      {
        id: "midday-pipeline",
        label: "Midday Pipeline",
        detail: "11:30"
      },
      {
        id: "afternoon-pipeline",
        label: "Afternoon Pipeline",
        detail: "13:00"
      },
      {
        id: "risk-final-pipeline",
        label: "Risk-Final Pipeline",
        detail: "14:30"
      },
      {
        id: "signal-backfill",
        label: "Signal Backfill",
        detail: "16:00"
      },
      {
        id: "weekly-report",
        label: "Weekly Report",
        detail: "Fri 16:30"
      },
      {
        id: "portfolio-history-repair",
        label: "Portfolio Repair",
        detail: "Manual"
      },
      { id: "holiday-sync", label: "Holiday Sync", detail: "08:16" },
      {
        id: "pairs-revalidation",
        label: "Pairs Revalidation",
        detail: "Sun 09:00"
      }
    ];
    sparkline = store_get($$store_subs ??= {}, "$controlRoom", controlRoom).portfolio?.marks.map((row) => row.portfolio_value).reverse() ?? [];
    if (!store_get($$store_subs ??= {}, "$controlRoom", controlRoom).overview || !store_get($$store_subs ??= {}, "$controlRoom", controlRoom).portfolio) {
      $$renderer2.push("<!--[0-->");
      $$renderer2.push(`<div class="flex flex-col items-center justify-center min-h-[60vh] gap-4 svelte-1x14rpa">`);
      Zap($$renderer2, { size: 32, class: "text-emerald animate-pulse" });
      $$renderer2.push(`<!----> <div class="mono text-[10px] tracking-[0.2em] text-emerald opacity-50 uppercase svelte-1x14rpa">Securing Command Uplink...</div></div>`);
    } else {
      $$renderer2.push("<!--[-1-->");
      $$renderer2.push(`<div class="space-y-6 svelte-1x14rpa"><section class="flex justify-between items-end border-b border-subtle pb-6 svelte-1x14rpa"><div class="space-y-1 svelte-1x14rpa"><div class="flex items-center gap-2 text-emerald svelte-1x14rpa">`);
      Gauge($$renderer2, { size: 14 });
      $$renderer2.push(`<!----> <span class="mono text-[10px] tracking-[0.2em] uppercase font-bold svelte-1x14rpa">Manual Override Surface</span></div> <h1 class="text-3xl font-bold tracking-tight svelte-1x14rpa">Operator <span class="text-emerald svelte-1x14rpa">Deck</span></h1> <p class="text-ink-secondary text-sm max-w-xl svelte-1x14rpa">Direct instruction injection, manual job triggering, and autonomy control.</p></div> <div class="w-64 h-16 opacity-80 svelte-1x14rpa">`);
      Sparkline($$renderer2, { values: sparkline });
      $$renderer2.push(`<!----></div></section> <div class="grid grid-cols-1 lg-grid-cols-command gap-6 items-start svelte-1x14rpa">`);
      Panel($$renderer2, {
        eyebrow: "INSTRUCTION INJECTION",
        title: "Direct Desk Note",
        tone: "emerald",
        children: ($$renderer3) => {
          $$renderer3.push(`<div class="space-y-4 svelte-1x14rpa"><textarea class="w-full h-32 bg-obsidian-900 border border-subtle p-4 mono text-xs text-emerald focus:border-emerald focus:ring-1 focus:ring-emerald outline-none resize-none svelte-1x14rpa" placeholder="[SYSTEM_CMD]: Enter override parameters (e.g., 'restrict INFY exposure')">`);
          const $$body = escape_html(message);
          if ($$body) {
            $$renderer3.push(`${$$body}`);
          }
          $$renderer3.push(`</textarea> <div class="flex justify-between items-center svelte-1x14rpa"><div class="flex gap-2 svelte-1x14rpa">`);
          if (store_get($$store_subs ??= {}, "$controlRoom", controlRoom).overview.runtime_state.autonomy_paused) {
            $$renderer3.push("<!--[0-->");
            $$renderer3.push(`<button class="flex items-center gap-2 px-4 py-2 bg-emerald-dim border border-emerald text-emerald mono text-[10px] font-bold uppercase tracking-widest hover:bg-emerald/20 transition-all svelte-1x14rpa"${attr("disabled", busyAction !== "", true)}>`);
            Play($$renderer3, { size: 12 });
            $$renderer3.push(`<!----> RESUME AUTONOMY</button>`);
          } else {
            $$renderer3.push("<!--[-1-->");
            $$renderer3.push(`<button class="flex items-center gap-2 px-4 py-2 bg-amber-dim border border-amber text-amber mono text-[10px] font-bold uppercase tracking-widest hover:bg-amber/20 transition-all svelte-1x14rpa"${attr("disabled", busyAction !== "", true)}>`);
            Pause($$renderer3, { size: 12 });
            $$renderer3.push(`<!----> HALT AUTONOMY</button>`);
          }
          $$renderer3.push(`<!--]--></div> <button class="flex items-center gap-2 px-6 py-2 bg-emerald text-obsidian-900 mono text-[10px] font-bold uppercase tracking-widest hover:bg-emerald-glow transition-all svelte-1x14rpa"${attr("disabled", !message.trim(), true)}>`);
          Send($$renderer3, { size: 12 });
          $$renderer3.push(`<!----> INJECT NOTE</button></div> `);
          {
            $$renderer3.push("<!--[-1-->");
          }
          $$renderer3.push(`<!--]--></div>`);
        },
        $$slots: { default: true }
      });
      $$renderer2.push(`<!----> `);
      Panel($$renderer2, {
        eyebrow: "JOB SEQUENCING",
        title: "Manual Triggers",
        children: ($$renderer3) => {
          $$renderer3.push(`<div class="grid grid-cols-2 gap-3 svelte-1x14rpa"><!--[-->`);
          const each_array = ensure_array_like(jobButtons);
          for (let $$index = 0, $$length = each_array.length; $$index < $$length; $$index++) {
            let job = each_array[$$index];
            $$renderer3.push(`<button class="p-3 bg-obsidian-700 border border-subtle text-left group hover:border-emerald transition-all svelte-1x14rpa"${attr("disabled", busyAction !== "", true)}><div class="flex flex-col svelte-1x14rpa"><span class="mono text-[10px] font-bold text-emerald group-hover:text-emerald-glow svelte-1x14rpa">${escape_html(job.label)}</span> <span class="text-[9px] text-ink-dim uppercase mt-1 tracking-tighter svelte-1x14rpa">${escape_html(job.detail)}</span></div> `);
            if (busyAction === job.id) {
              $$renderer3.push("<!--[0-->");
              $$renderer3.push(`<div class="mt-2 h-0.5 w-full bg-emerald/20 overflow-hidden svelte-1x14rpa"><div class="h-full bg-emerald animate-[shimmer_1s_infinite] svelte-1x14rpa"></div></div>`);
            } else {
              $$renderer3.push("<!--[-1-->");
            }
            $$renderer3.push(`<!--]--></button>`);
          }
          $$renderer3.push(`<!--]--></div>`);
        },
        $$slots: { default: true }
      });
      $$renderer2.push(`<!----></div> <div class="grid grid-cols-1 md-grid-cols-3 gap-6 svelte-1x14rpa">`);
      Panel($$renderer2, {
        eyebrow: "RUNTIME GATE",
        title: "Risk Sentinel",
        tone: "amber",
        children: ($$renderer3) => {
          $$renderer3.push(`<div class="space-y-4 svelte-1x14rpa"><div class="grid grid-cols-1 gap-3 svelte-1x14rpa"><div class="flex justify-between items-center p-3 bg-obsidian-900 border border-subtle svelte-1x14rpa"><span class="status-metric__label svelte-1x14rpa">AUTONOMY</span> <span${attr_class("mono text-xs font-bold svelte-1x14rpa", void 0, {
            "text-emerald": !store_get($$store_subs ??= {}, "$controlRoom", controlRoom).overview.runtime_state.autonomy_paused,
            "text-amber": store_get($$store_subs ??= {}, "$controlRoom", controlRoom).overview.runtime_state.autonomy_paused
          })}>${escape_html(store_get($$store_subs ??= {}, "$controlRoom", controlRoom).overview.runtime_state.autonomy_paused ? "PAUSED" : "ACTIVE")}</span></div> <div class="flex justify-between items-center p-3 bg-obsidian-900 border border-subtle svelte-1x14rpa"><span class="status-metric__label svelte-1x14rpa">ENTRIES</span> <span${attr_class("mono text-xs font-bold svelte-1x14rpa", void 0, {
            "text-emerald": !store_get($$store_subs ??= {}, "$controlRoom", controlRoom).overview.runtime_state.entries_blocked,
            "text-crimson": store_get($$store_subs ??= {}, "$controlRoom", controlRoom).overview.runtime_state.entries_blocked
          })}>${escape_html(store_get($$store_subs ??= {}, "$controlRoom", controlRoom).overview.runtime_state.entries_blocked ? "BLOCKED" : "ENABLED")}</span></div> <div class="flex justify-between items-center p-3 bg-obsidian-900 border border-subtle svelte-1x14rpa"><span class="status-metric__label svelte-1x14rpa">EXITS ONLY</span> <span${attr_class("mono text-xs font-bold svelte-1x14rpa", void 0, {
            "text-amber": store_get($$store_subs ??= {}, "$controlRoom", controlRoom).overview.runtime_state.exits_only
          })}>${escape_html(store_get($$store_subs ??= {}, "$controlRoom", controlRoom).overview.runtime_state.exits_only ? "YES" : "NO")}</span></div></div> <div class="flex items-center gap-2 opacity-40 svelte-1x14rpa">`);
          Clock($$renderer3, { size: 10 });
          $$renderer3.push(`<!----> <span class="text-[9px] uppercase mono svelte-1x14rpa">LAST SYNC: ${escape_html(formatDateTime(store_get($$store_subs ??= {}, "$controlRoom", controlRoom).overview.runtime_state.updated_at).split(" ")[1])}</span></div></div>`);
        },
        $$slots: { default: true }
      });
      $$renderer2.push(`<!----> `);
      Panel($$renderer2, {
        eyebrow: "CAPITAL STATE",
        title: "Equity Profile",
        children: ($$renderer3) => {
          $$renderer3.push(`<div class="space-y-4 svelte-1x14rpa"><div class="grid grid-cols-1 gap-3 svelte-1x14rpa"><div class="flex justify-between items-center p-3 bg-obsidian-900 border border-subtle svelte-1x14rpa"><span class="status-metric__label svelte-1x14rpa">NAV</span> <span class="mono text-xs font-bold text-emerald svelte-1x14rpa">${escape_html(formatCurrency(store_get($$store_subs ??= {}, "$controlRoom", controlRoom).overview.portfolio.portfolio_value))}</span></div> <div class="flex justify-between items-center p-3 bg-obsidian-900 border border-subtle svelte-1x14rpa"><span class="status-metric__label svelte-1x14rpa">DEPLOYED</span> <span class="mono text-xs font-bold svelte-1x14rpa">${escape_html(formatCurrency(store_get($$store_subs ??= {}, "$controlRoom", controlRoom).overview.portfolio.total_deployed))}</span></div> <div class="flex justify-between items-center p-3 bg-obsidian-900 border border-subtle svelte-1x14rpa"><span class="status-metric__label svelte-1x14rpa">OPEN NODES</span> <span class="mono text-xs font-bold svelte-1x14rpa">${escape_html(store_get($$store_subs ??= {}, "$controlRoom", controlRoom).overview.portfolio.open_positions)}</span></div></div> <div class="flex items-center gap-2 opacity-40 svelte-1x14rpa">`);
          Activity($$renderer3, { size: 10 });
          $$renderer3.push(`<!----> <span class="text-[9px] uppercase mono svelte-1x14rpa">EXPOSURE: ${escape_html(formatCurrency(store_get($$store_subs ??= {}, "$controlRoom", controlRoom).overview.portfolio.total_market_value))}</span></div></div>`);
        },
        $$slots: { default: true }
      });
      $$renderer2.push(`<!----> `);
      Panel($$renderer2, {
        eyebrow: "EXECUTION TAPE",
        title: "Recent Pulses",
        children: ($$renderer3) => {
          $$renderer3.push(`<div class="space-y-2 svelte-1x14rpa"><!--[-->`);
          const each_array_1 = ensure_array_like(store_get($$store_subs ??= {}, "$controlRoom", controlRoom).runs.slice(0, 5));
          for (let $$index_1 = 0, $$length = each_array_1.length; $$index_1 < $$length; $$index_1++) {
            let run = each_array_1[$$index_1];
            $$renderer3.push(`<div class="p-3 bg-obsidian-700 border border-subtle flex justify-between items-center group hover:border-emerald transition-colors svelte-1x14rpa"><div class="flex flex-col svelte-1x14rpa"><span class="mono text-[10px] font-bold truncate max-w-[120px] svelte-1x14rpa">${escape_html(String(run.name ?? run.job_name).toUpperCase())}</span> <span class="text-[8px] text-ink-dim uppercase mt-1 svelte-1x14rpa">${escape_html(formatDateTime(String(run.started_at ?? "")).split(" ")[1])}</span></div> <span${attr_class("mono text-[9px] px-2 py-0-5 border border-subtle rounded-full uppercase svelte-1x14rpa", void 0, {
              "text-emerald": run.status === "success",
              "text-amber": run.status === "running"
            })}>${escape_html(String(run.status ?? "IDLE"))}</span></div>`);
          }
          $$renderer3.push(`<!--]--></div>`);
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
