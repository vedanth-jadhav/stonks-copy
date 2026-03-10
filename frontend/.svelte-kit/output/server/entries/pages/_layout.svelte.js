import { s as spread_props, f as fallback, a as attr, e as escape_html, b as bind_props, c as ensure_array_like, d as attr_class, g as slot, h as head, i as store_get, u as unsubscribe_stores } from "../../chunks/index2.js";
import { Z as Zap } from "../../chunks/zap.js";
import { S as Shield_check } from "../../chunks/shield-check.js";
import { I as Icon } from "../../chunks/Icon.js";
import { p as page } from "../../chunks/index3.js";
import "@sveltejs/kit/internal";
import "../../chunks/exports.js";
import "../../chunks/utils.js";
import "@sveltejs/kit/internal/server";
import "../../chunks/root.js";
import "../../chunks/state.svelte.js";
import { f as formatDateTime } from "../../chunks/format.js";
import { B as Bot } from "../../chunks/bot.js";
import { A as Activity } from "../../chunks/activity.js";
import { P as Power } from "../../chunks/power.js";
import { G as Gauge } from "../../chunks/gauge.js";
import { C as Clipboard_list } from "../../chunks/clipboard-list.js";
import { M as Memory_stick } from "../../chunks/memory-stick.js";
import { S as Settings_2 } from "../../chunks/settings-2.js";
import { F as File_text } from "../../chunks/file-text.js";
import { c as controlRoom } from "../../chunks/control-room.js";
function Bell($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let { $$slots, $$events, ...props } = $$props;
    const iconNode = [
      ["path", { "d": "M10.268 21a2 2 0 0 0 3.464 0" }],
      [
        "path",
        {
          "d": "M3.262 15.326A1 1 0 0 0 4 17h16a1 1 0 0 0 .74-1.673C19.41 13.956 18 12.499 18 8A6 6 0 0 0 6 8c0 4.499-1.411 5.956-2.738 7.326"
        }
      ]
    ];
    Icon($$renderer2, spread_props([
      { name: "bell" },
      /**
       * @component @name Bell
       * @description Lucide SVG icon component, renders SVG Element with children.
       *
       * @preview ![img](data:image/svg+xml;base64,PHN2ZyAgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIgogIHdpZHRoPSIyNCIKICBoZWlnaHQ9IjI0IgogIHZpZXdCb3g9IjAgMCAyNCAyNCIKICBmaWxsPSJub25lIgogIHN0cm9rZT0iIzAwMCIgc3R5bGU9ImJhY2tncm91bmQtY29sb3I6ICNmZmY7IGJvcmRlci1yYWRpdXM6IDJweCIKICBzdHJva2Utd2lkdGg9IjIiCiAgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIgogIHN0cm9rZS1saW5lam9pbj0icm91bmQiCj4KICA8cGF0aCBkPSJNMTAuMjY4IDIxYTIgMiAwIDAgMCAzLjQ2NCAwIiAvPgogIDxwYXRoIGQ9Ik0zLjI2MiAxNS4zMjZBMSAxIDAgMCAwIDQgMTdoMTZhMSAxIDAgMCAwIC43NC0xLjY3M0MxOS40MSAxMy45NTYgMTggMTIuNDk5IDE4IDhBNiA2IDAgMCAwIDYgOGMwIDQuNDk5LTEuNDExIDUuOTU2LTIuNzM4IDcuMzI2IiAvPgo8L3N2Zz4K) - https://lucide.dev/icons/bell
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
function Briefcase_business($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let { $$slots, $$events, ...props } = $$props;
    const iconNode = [
      ["path", { "d": "M12 12h.01" }],
      ["path", { "d": "M16 6V4a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2" }],
      ["path", { "d": "M22 13a18.15 18.15 0 0 1-20 0" }],
      [
        "rect",
        { "width": "20", "height": "14", "x": "2", "y": "6", "rx": "2" }
      ]
    ];
    Icon($$renderer2, spread_props([
      { name: "briefcase-business" },
      /**
       * @component @name BriefcaseBusiness
       * @description Lucide SVG icon component, renders SVG Element with children.
       *
       * @preview ![img](data:image/svg+xml;base64,PHN2ZyAgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIgogIHdpZHRoPSIyNCIKICBoZWlnaHQ9IjI0IgogIHZpZXdCb3g9IjAgMCAyNCAyNCIKICBmaWxsPSJub25lIgogIHN0cm9rZT0iIzAwMCIgc3R5bGU9ImJhY2tncm91bmQtY29sb3I6ICNmZmY7IGJvcmRlci1yYWRpdXM6IDJweCIKICBzdHJva2Utd2lkdGg9IjIiCiAgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIgogIHN0cm9rZS1saW5lam9pbj0icm91bmQiCj4KICA8cGF0aCBkPSJNMTIgMTJoLjAxIiAvPgogIDxwYXRoIGQ9Ik0xNiA2VjRhMiAyIDAgMCAwLTItMmgtNGEyIDIgMCAwIDAtMiAydjIiIC8+CiAgPHBhdGggZD0iTTIyIDEzYTE4LjE1IDE4LjE1IDAgMCAxLTIwIDAiIC8+CiAgPHJlY3Qgd2lkdGg9IjIwIiBoZWlnaHQ9IjE0IiB4PSIyIiB5PSI2IiByeD0iMiIgLz4KPC9zdmc+Cg==) - https://lucide.dev/icons/briefcase-business
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
function Folder_kanban($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let { $$slots, $$events, ...props } = $$props;
    const iconNode = [
      [
        "path",
        {
          "d": "M4 20h16a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.93a2 2 0 0 1-1.66-.9l-.82-1.2A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13c0 1.1.9 2 2 2Z"
        }
      ],
      ["path", { "d": "M8 10v4" }],
      ["path", { "d": "M12 10v2" }],
      ["path", { "d": "M16 10v6" }]
    ];
    Icon($$renderer2, spread_props([
      { name: "folder-kanban" },
      /**
       * @component @name FolderKanban
       * @description Lucide SVG icon component, renders SVG Element with children.
       *
       * @preview ![img](data:image/svg+xml;base64,PHN2ZyAgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIgogIHdpZHRoPSIyNCIKICBoZWlnaHQ9IjI0IgogIHZpZXdCb3g9IjAgMCAyNCAyNCIKICBmaWxsPSJub25lIgogIHN0cm9rZT0iIzAwMCIgc3R5bGU9ImJhY2tncm91bmQtY29sb3I6ICNmZmY7IGJvcmRlci1yYWRpdXM6IDJweCIKICBzdHJva2Utd2lkdGg9IjIiCiAgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIgogIHN0cm9rZS1saW5lam9pbj0icm91bmQiCj4KICA8cGF0aCBkPSJNNCAyMGgxNmEyIDIgMCAwIDAgMi0yVjhhMiAyIDAgMCAwLTItMmgtNy45M2EyIDIgMCAwIDEtMS42Ni0uOWwtLjgyLTEuMkEyIDIgMCAwIDAgNy45MyAzSDRhMiAyIDAgMCAwLTIgMnYxM2MwIDEuMS45IDIgMiAyWiIgLz4KICA8cGF0aCBkPSJNOCAxMHY0IiAvPgogIDxwYXRoIGQ9Ik0xMiAxMHYyIiAvPgogIDxwYXRoIGQ9Ik0xNiAxMHY2IiAvPgo8L3N2Zz4K) - https://lucide.dev/icons/folder-kanban
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
function Layout_grid($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let { $$slots, $$events, ...props } = $$props;
    const iconNode = [
      [
        "rect",
        { "width": "7", "height": "7", "x": "3", "y": "3", "rx": "1" }
      ],
      [
        "rect",
        { "width": "7", "height": "7", "x": "14", "y": "3", "rx": "1" }
      ],
      [
        "rect",
        { "width": "7", "height": "7", "x": "14", "y": "14", "rx": "1" }
      ],
      [
        "rect",
        { "width": "7", "height": "7", "x": "3", "y": "14", "rx": "1" }
      ]
    ];
    Icon($$renderer2, spread_props([
      { name: "layout-grid" },
      /**
       * @component @name LayoutGrid
       * @description Lucide SVG icon component, renders SVG Element with children.
       *
       * @preview ![img](data:image/svg+xml;base64,PHN2ZyAgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIgogIHdpZHRoPSIyNCIKICBoZWlnaHQ9IjI0IgogIHZpZXdCb3g9IjAgMCAyNCAyNCIKICBmaWxsPSJub25lIgogIHN0cm9rZT0iIzAwMCIgc3R5bGU9ImJhY2tncm91bmQtY29sb3I6ICNmZmY7IGJvcmRlci1yYWRpdXM6IDJweCIKICBzdHJva2Utd2lkdGg9IjIiCiAgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIgogIHN0cm9rZS1saW5lam9pbj0icm91bmQiCj4KICA8cmVjdCB3aWR0aD0iNyIgaGVpZ2h0PSI3IiB4PSIzIiB5PSIzIiByeD0iMSIgLz4KICA8cmVjdCB3aWR0aD0iNyIgaGVpZ2h0PSI3IiB4PSIxNCIgeT0iMyIgcng9IjEiIC8+CiAgPHJlY3Qgd2lkdGg9IjciIGhlaWdodD0iNyIgeD0iMTQiIHk9IjE0IiByeD0iMSIgLz4KICA8cmVjdCB3aWR0aD0iNyIgaGVpZ2h0PSI3IiB4PSIzIiB5PSIxNCIgcng9IjEiIC8+Cjwvc3ZnPgo=) - https://lucide.dev/icons/layout-grid
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
function Lock($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let { $$slots, $$events, ...props } = $$props;
    const iconNode = [
      [
        "rect",
        {
          "width": "18",
          "height": "11",
          "x": "3",
          "y": "11",
          "rx": "2",
          "ry": "2"
        }
      ],
      ["path", { "d": "M7 11V7a5 5 0 0 1 10 0v4" }]
    ];
    Icon($$renderer2, spread_props([
      { name: "lock" },
      /**
       * @component @name Lock
       * @description Lucide SVG icon component, renders SVG Element with children.
       *
       * @preview ![img](data:image/svg+xml;base64,PHN2ZyAgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIgogIHdpZHRoPSIyNCIKICBoZWlnaHQ9IjI0IgogIHZpZXdCb3g9IjAgMCAyNCAyNCIKICBmaWxsPSJub25lIgogIHN0cm9rZT0iIzAwMCIgc3R5bGU9ImJhY2tncm91bmQtY29sb3I6ICNmZmY7IGJvcmRlci1yYWRpdXM6IDJweCIKICBzdHJva2Utd2lkdGg9IjIiCiAgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIgogIHN0cm9rZS1saW5lam9pbj0icm91bmQiCj4KICA8cmVjdCB3aWR0aD0iMTgiIGhlaWdodD0iMTEiIHg9IjMiIHk9IjExIiByeD0iMiIgcnk9IjIiIC8+CiAgPHBhdGggZD0iTTcgMTFWN2E1IDUgMCAwIDEgMTAgMHY0IiAvPgo8L3N2Zz4K) - https://lucide.dev/icons/lock
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
function LoginGate($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let error = fallback($$props["error"], "");
    let busy = fallback($$props["busy"], false);
    let onSubmit = $$props["onSubmit"];
    let password = "quant";
    $$renderer2.push(`<div class="hud-scanline"></div> <div class="hud-vignette"></div> <div class="login-gate svelte-9u7n1y"><div class="absolute top-10 left-10 flex items-center gap-2 text-emerald opacity-50 svelte-9u7n1y">`);
    Zap($$renderer2, { size: 14 });
    $$renderer2.push(`<!----> <span class="mono text-[10px] tracking-[0.2em] uppercase font-bold svelte-9u7n1y">Uplink: Protected</span></div> <form class="login-card panel svelte-9u7n1y"><div class="space-y-6 relative z-10 svelte-9u7n1y"><div class="flex justify-center svelte-9u7n1y"><div class="w-12 h-12 rounded-full border border-emerald flex items-center justify-center text-emerald animate-pulse bg-emerald-dim svelte-9u7n1y">`);
    Shield_check($$renderer2, { size: 24 });
    $$renderer2.push(`<!----></div></div> <div class="text-center space-y-2 svelte-9u7n1y"><div class="mono text-[10px] tracking-[0.3em] text-emerald uppercase font-bold svelte-9u7n1y">Terminal Authorization</div> <h1 class="text-2xl font-bold tracking-tight svelte-9u7n1y">Access Control Room</h1> <p class="text-ink-secondary text-xs max-w-[280px] mx-auto leading-relaxed svelte-9u7n1y">Proprietary trading surface. Unauthorized access is strictly prohibited.</p></div> <div class="space-y-4 svelte-9u7n1y"><div class="space-y-2 svelte-9u7n1y"><label class="status-metric__label svelte-9u7n1y" for="password">OPERATOR KEY</label> <div class="relative svelte-9u7n1y"><input id="password"${attr("value", password)} class="w-full bg-obsidian-900 border border-subtle p-3 pl-10 mono text-sm text-emerald focus:border-emerald outline-none transition-all" type="password" placeholder="••••••••"/> `);
    Lock($$renderer2, {
      size: 14,
      class: "absolute left-3 top-1/2 -translate-y-1/2 text-ink-dim"
    });
    $$renderer2.push(`<!----></div></div> <button class="w-full py-3 bg-emerald text-obsidian-900 mono text-xs font-bold uppercase tracking-[0.2em] hover:bg-emerald-glow transition-all disabled:opacity-50 svelte-9u7n1y" type="submit"${attr("disabled", busy, true)}>${escape_html(busy ? "AUTHORIZING..." : "INITIATE UPLINK")}</button></div> `);
    if (error) {
      $$renderer2.push("<!--[0-->");
      $$renderer2.push(`<div class="p-3 bg-crimson-dim border border-crimson/30 text-crimson text-[10px] text-center mono uppercase tracking-widest svelte-9u7n1y">${escape_html(error)}</div>`);
    } else {
      $$renderer2.push("<!--[-1-->");
    }
    $$renderer2.push(`<!--]--></div> <div class="absolute inset-0 pointer-events-none opacity-20 svelte-9u7n1y"><div class="absolute top-0 left-0 w-20 h-px bg-emerald svelte-9u7n1y"></div> <div class="absolute top-0 left-0 h-20 w-px bg-emerald svelte-9u7n1y"></div> <div class="absolute bottom-0 right-0 w-20 h-px bg-emerald svelte-9u7n1y"></div> <div class="absolute bottom-0 right-0 h-20 w-px bg-emerald svelte-9u7n1y"></div></div></form> <div class="absolute bottom-10 mono text-[8px] text-ink-dim uppercase tracking-[0.4em] svelte-9u7n1y">Secure Desk // NSE Execution Node 042</div></div>`);
    bind_props($$props, { error, busy, onSubmit });
  });
}
function Shell($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let connected = fallback($$props["connected"], false);
    let overview = fallback($$props["overview"], null);
    let metrics = fallback($$props["metrics"], () => [], true);
    let alerts = fallback($$props["alerts"], () => [], true);
    let onLogout = $$props["onLogout"];
    const nav = [
      { label: "System Map", href: "/", icon: Layout_grid },
      { label: "Command", href: "/command", icon: Gauge },
      {
        label: "Portfolio",
        href: "/portfolio",
        icon: Briefcase_business
      },
      { label: "Blotter", href: "/blotter", icon: Clipboard_list },
      { label: "Memory", href: "/memory", icon: Memory_stick },
      { label: "Config", href: "/config", icon: Settings_2 },
      { label: "Gemini OAuth", href: "/gemini-oauth", icon: Bot },
      { label: "Logs", href: "/logs", icon: Folder_kanban },
      { label: "Reports", href: "/reports", icon: File_text }
    ];
    $$renderer2.push(`<div class="hud-scanline"></div> <div class="hud-vignette"></div> <div class="app-shell"><aside class="rail"><div class="rail__brand">`);
    Bot($$renderer2, { size: 24, class: "text-emerald" });
    $$renderer2.push(`<!----></div> <nav class="flex flex-col gap-4 svelte-w96i92"><!--[-->`);
    const each_array = ensure_array_like(nav);
    for (let $$index = 0, $$length = each_array.length; $$index < $$length; $$index++) {
      let item = each_array[$$index];
      $$renderer2.push(`<button${attr_class("rail__link", void 0, { "active": page.url.pathname === item.href })}${attr("title", item.label)}>`);
      if (item.icon) {
        $$renderer2.push("<!--[-->");
        item.icon($$renderer2, { size: 20 });
        $$renderer2.push("<!--]-->");
      } else {
        $$renderer2.push("<!--[!-->");
        $$renderer2.push("<!--]-->");
      }
      $$renderer2.push(`</button>`);
    }
    $$renderer2.push(`<!--]--></nav> <div class="mt-auto flex flex-col gap-4 svelte-w96i92"><button${attr_class("rail__link", void 0, { "text-emerald": connected, "text-crimson": !connected })}${attr("title", connected ? "Uplink Active" : "Uplink Severed")}>`);
    Activity($$renderer2, { size: 20 });
    $$renderer2.push(`<!----></button> <button class="rail__link text-crimson hover:bg-crimson-dim" title="Terminate Session">`);
    Power($$renderer2, { size: 20 });
    $$renderer2.push(`<!----></button></div></aside> <div class="workspace"><header class="command-band"><div class="flex items-center gap-6 svelte-w96i92"><div class="status-metric"><span class="status-metric__label">MARKET STATE</span> <span${attr_class("status-metric__value", void 0, {
      "text-emerald": overview?.market.is_market_day,
      "text-amber": !overview?.market.is_market_day
    })}>${escape_html(overview?.market.is_market_day ? "TRADING" : "HALTED")}</span></div> <div class="status-metric"><span class="status-metric__label">LATENCY</span> <span class="status-metric__value mono">24ms</span></div></div> <div class="status-strip hidden md:flex svelte-w96i92"><!--[-->`);
    const each_array_1 = ensure_array_like(metrics);
    for (let $$index_1 = 0, $$length = each_array_1.length; $$index_1 < $$length; $$index_1++) {
      let metric = each_array_1[$$index_1];
      $$renderer2.push(`<div class="status-metric"><span class="status-metric__label">${escape_html(metric.label)}</span> <span${attr_class("status-metric__value mono", void 0, {
        "text-emerald": metric.tone === "positive",
        "text-crimson": metric.tone === "negative",
        "text-amber": metric.tone === "warning"
      })}>${escape_html(metric.value)}</span></div>`);
    }
    $$renderer2.push(`<!--]--></div> <div class="flex items-center gap-4 svelte-w96i92"><div class="status-metric text-right svelte-w96i92"><span class="status-metric__label">SYSTEM TIME</span> <span class="status-metric__value mono">${escape_html(overview ? formatDateTime(overview.market.timestamp_utc).split(" ")[1] : "--:--:--")}</span></div> <button${attr_class("rail__link relative svelte-w96i92", void 0, { "text-amber": alerts.length > 0 })}>`);
    Bell($$renderer2, { size: 20 });
    $$renderer2.push(`<!----> `);
    if (alerts.length > 0) {
      $$renderer2.push("<!--[0-->");
      $$renderer2.push(`<span class="absolute -top-1 -right-1 w-2 h-2 bg-amber rounded-full animate-pulse svelte-w96i92"></span>`);
    } else {
      $$renderer2.push("<!--[-1-->");
    }
    $$renderer2.push(`<!--]--></button></div></header> <main class="main-stage"><!--[-->`);
    slot($$renderer2, $$props, "default", {});
    $$renderer2.push(`<!--]--></main></div> `);
    {
      $$renderer2.push("<!--[-1-->");
    }
    $$renderer2.push(`<!--]--></div>`);
    bind_props($$props, { connected, overview, metrics, alerts, onLogout });
  });
}
function _layout($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    var $$store_subs;
    head("12qhfyh", $$renderer2, ($$renderer3) => {
      $$renderer3.title(($$renderer4) => {
        $$renderer4.push(`<title>Quant Control Room // HUD</title>`);
      });
    });
    if (store_get($$store_subs ??= {}, "$controlRoom", controlRoom).booting && !store_get($$store_subs ??= {}, "$controlRoom", controlRoom).authenticated) {
      $$renderer2.push("<!--[0-->");
      $$renderer2.push(`<div class="flex flex-col items-center justify-center min-h-screen bg-obsidian-900 gap-4">`);
      Zap($$renderer2, { size: 32, class: "text-emerald animate-pulse" });
      $$renderer2.push(`<!----> <div class="mono text-[10px] tracking-[0.4em] text-emerald opacity-50 uppercase">Securing Local Execution Node...</div></div>`);
    } else if (!store_get($$store_subs ??= {}, "$controlRoom", controlRoom).authenticated) {
      $$renderer2.push("<!--[1-->");
      LoginGate($$renderer2, {
        error: store_get($$store_subs ??= {}, "$controlRoom", controlRoom).error,
        busy: store_get($$store_subs ??= {}, "$controlRoom", controlRoom).booting,
        onSubmit: (password) => controlRoom.login(password)
      });
    } else {
      $$renderer2.push("<!--[-1-->");
      Shell($$renderer2, {
        connected: store_get($$store_subs ??= {}, "$controlRoom", controlRoom).connected,
        overview: store_get($$store_subs ??= {}, "$controlRoom", controlRoom).overview,
        metrics: store_get($$store_subs ??= {}, "$controlRoom", controlRoom).systemMap?.top_metrics ?? [],
        alerts: store_get($$store_subs ??= {}, "$controlRoom", controlRoom).systemMap?.alerts ?? [],
        onLogout: () => controlRoom.logout(),
        children: ($$renderer3) => {
          $$renderer3.push(`<!--[-->`);
          slot($$renderer3, $$props, "default", {});
          $$renderer3.push(`<!--]-->`);
        },
        $$slots: { default: true }
      });
    }
    $$renderer2.push(`<!--]-->`);
    if ($$store_subs) unsubscribe_stores($$store_subs);
  });
}
export {
  _layout as default
};
