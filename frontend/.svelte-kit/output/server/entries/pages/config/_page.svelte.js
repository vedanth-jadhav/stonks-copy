import { s as spread_props, i as store_get, c as ensure_array_like, e as escape_html, d as attr_class, u as unsubscribe_stores, a as attr } from "../../../chunks/index2.js";
import { P as Panel } from "../../../chunks/Panel.js";
import { c as controlRoom } from "../../../chunks/control-room.js";
import { f as formatDateTime } from "../../../chunks/format.js";
import { Z as Zap } from "../../../chunks/zap.js";
import { S as Settings_2 } from "../../../chunks/settings-2.js";
import { C as Clock } from "../../../chunks/clock.js";
import { I as Icon } from "../../../chunks/Icon.js";
import { S as Search } from "../../../chunks/search.js";
function File_code($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let { $$slots, $$events, ...props } = $$props;
    const iconNode = [
      ["path", { "d": "M10 12.5 8 15l2 2.5" }],
      ["path", { "d": "m14 12.5 2 2.5-2 2.5" }],
      ["path", { "d": "M14 2v4a2 2 0 0 0 2 2h4" }],
      [
        "path",
        {
          "d": "M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7z"
        }
      ]
    ];
    Icon($$renderer2, spread_props([
      { name: "file-code" },
      /**
       * @component @name FileCode
       * @description Lucide SVG icon component, renders SVG Element with children.
       *
       * @preview ![img](data:image/svg+xml;base64,PHN2ZyAgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIgogIHdpZHRoPSIyNCIKICBoZWlnaHQ9IjI0IgogIHZpZXdCb3g9IjAgMCAyNCAyNCIKICBmaWxsPSJub25lIgogIHN0cm9rZT0iIzAwMCIgc3R5bGU9ImJhY2tncm91bmQtY29sb3I6ICNmZmY7IGJvcmRlci1yYWRpdXM6IDJweCIKICBzdHJva2Utd2lkdGg9IjIiCiAgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIgogIHN0cm9rZS1saW5lam9pbj0icm91bmQiCj4KICA8cGF0aCBkPSJNMTAgMTIuNSA4IDE1bDIgMi41IiAvPgogIDxwYXRoIGQ9Im0xNCAxMi41IDIgMi41LTIgMi41IiAvPgogIDxwYXRoIGQ9Ik0xNCAydjRhMiAyIDAgMCAwIDIgMmg0IiAvPgogIDxwYXRoIGQ9Ik0xNSAySDZhMiAyIDAgMCAwLTIgMnYxNmEyIDIgMCAwIDAgMiAyaDEyYTIgMiAwIDAgMCAyLTJWN3oiIC8+Cjwvc3ZnPgo=) - https://lucide.dev/icons/file-code
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
function Hard_drive($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let { $$slots, $$events, ...props } = $$props;
    const iconNode = [
      ["line", { "x1": "22", "x2": "2", "y1": "12", "y2": "12" }],
      [
        "path",
        {
          "d": "M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"
        }
      ],
      ["line", { "x1": "6", "x2": "6.01", "y1": "16", "y2": "16" }],
      [
        "line",
        { "x1": "10", "x2": "10.01", "y1": "16", "y2": "16" }
      ]
    ];
    Icon($$renderer2, spread_props([
      { name: "hard-drive" },
      /**
       * @component @name HardDrive
       * @description Lucide SVG icon component, renders SVG Element with children.
       *
       * @preview ![img](data:image/svg+xml;base64,PHN2ZyAgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIgogIHdpZHRoPSIyNCIKICBoZWlnaHQ9IjI0IgogIHZpZXdCb3g9IjAgMCAyNCAyNCIKICBmaWxsPSJub25lIgogIHN0cm9rZT0iIzAwMCIgc3R5bGU9ImJhY2tncm91bmQtY29sb3I6ICNmZmY7IGJvcmRlci1yYWRpdXM6IDJweCIKICBzdHJva2Utd2lkdGg9IjIiCiAgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIgogIHN0cm9rZS1saW5lam9pbj0icm91bmQiCj4KICA8bGluZSB4MT0iMjIiIHgyPSIyIiB5MT0iMTIiIHkyPSIxMiIgLz4KICA8cGF0aCBkPSJNNS40NSA1LjExIDIgMTJ2NmEyIDIgMCAwIDAgMiAyaDE2YTIgMiAwIDAgMCAyLTJ2LTZsLTMuNDUtNi44OUEyIDIgMCAwIDAgMTYuNzYgNEg3LjI0YTIgMiAwIDAgMC0xLjc5IDEuMTF6IiAvPgogIDxsaW5lIHgxPSI2IiB4Mj0iNi4wMSIgeTE9IjE2IiB5Mj0iMTYiIC8+CiAgPGxpbmUgeDE9IjEwIiB4Mj0iMTAuMDEiIHkxPSIxNiIgeTI9IjE2IiAvPgo8L3N2Zz4K) - https://lucide.dev/icons/hard-drive
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
function Message_square($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let { $$slots, $$events, ...props } = $$props;
    const iconNode = [
      [
        "path",
        {
          "d": "M22 17a2 2 0 0 1-2 2H6.828a2 2 0 0 0-1.414.586l-2.202 2.202A.71.71 0 0 1 2 21.286V5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2z"
        }
      ]
    ];
    Icon($$renderer2, spread_props([
      { name: "message-square" },
      /**
       * @component @name MessageSquare
       * @description Lucide SVG icon component, renders SVG Element with children.
       *
       * @preview ![img](data:image/svg+xml;base64,PHN2ZyAgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIgogIHdpZHRoPSIyNCIKICBoZWlnaHQ9IjI0IgogIHZpZXdCb3g9IjAgMCAyNCAyNCIKICBmaWxsPSJub25lIgogIHN0cm9rZT0iIzAwMCIgc3R5bGU9ImJhY2tncm91bmQtY29sb3I6ICNmZmY7IGJvcmRlci1yYWRpdXM6IDJweCIKICBzdHJva2Utd2lkdGg9IjIiCiAgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIgogIHN0cm9rZS1saW5lam9pbj0icm91bmQiCj4KICA8cGF0aCBkPSJNMjIgMTdhMiAyIDAgMCAxLTIgMkg2LjgyOGEyIDIgMCAwIDAtMS40MTQuNTg2bC0yLjIwMiAyLjIwMkEuNzEuNzEgMCAwIDEgMiAyMS4yODZWNWEyIDIgMCAwIDEgMi0yaDE2YTIgMiAwIDAgMSAyIDJ6IiAvPgo8L3N2Zz4K) - https://lucide.dev/icons/message-square
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
    let filteredFiles, marketSettings;
    let files = [];
    let selected = null;
    let searchQuery = "";
    filteredFiles = files.filter((f) => f.relative_path.toLowerCase().includes(searchQuery.toLowerCase()));
    marketSettings = store_get($$store_subs ??= {}, "$controlRoom", controlRoom).config?.settings.market ?? {};
    if (!store_get($$store_subs ??= {}, "$controlRoom", controlRoom).config || !store_get($$store_subs ??= {}, "$controlRoom", controlRoom).overview) {
      $$renderer2.push("<!--[0-->");
      $$renderer2.push(`<div class="flex flex-col items-center justify-center min-h-[60vh] gap-4 svelte-1gp6n77">`);
      Zap($$renderer2, { size: 32, class: "text-emerald animate-pulse" });
      $$renderer2.push(`<!----> <div class="mono text-[10px] tracking-[0.2em] text-emerald opacity-50 uppercase">Accessing Configuration Matrix...</div></div>`);
    } else {
      $$renderer2.push("<!--[-1-->");
      $$renderer2.push(`<div class="space-y-6 svelte-1gp6n77"><section class="flex justify-between items-end border-b border-subtle pb-6 svelte-1gp6n77"><div class="space-y-1 svelte-1gp6n77"><div class="flex items-center gap-2 text-emerald svelte-1gp6n77">`);
      Settings_2($$renderer2, { size: 14 });
      $$renderer2.push(`<!----> <span class="mono text-[10px] tracking-[0.2em] uppercase font-bold">System Configuration</span></div> <h1 class="text-3xl font-bold tracking-tight svelte-1gp6n77">Desk <span class="text-emerald">Controls</span></h1> <p class="text-ink-secondary text-sm max-w-xl svelte-1gp6n77">Environment parameters, provider health, and static artifacts.</p></div> <div class="flex gap-4"><!--[-->`);
      const each_array = ensure_array_like(Object.entries(store_get($$store_subs ??= {}, "$controlRoom", controlRoom).overview.provider_health));
      for (let $$index = 0, $$length = each_array.length; $$index < $$length; $$index++) {
        let [name, data] = each_array[$$index];
        const payload = data;
        $$renderer2.push(`<div class="status-metric text-right"><span class="status-metric__label uppercase">${escape_html(name)}</span> <span${attr_class("status-metric__value mono text-xs uppercase", void 0, {
          "text-emerald": payload.status === "READY" || payload.status === "OK",
          "text-amber": payload.status !== "READY" && payload.status !== "OK"
        })}>${escape_html(payload.status ?? "UNKNOWN")}</span></div>`);
      }
      $$renderer2.push(`<!--]--></div></section> <div class="grid grid-cols-1 md:grid-cols-3 gap-6 svelte-1gp6n77">`);
      Panel($$renderer2, {
        eyebrow: "RUNTIME",
        title: "Execution Gates",
        tone: "emerald",
        children: ($$renderer3) => {
          $$renderer3.push(`<div class="space-y-4 svelte-1gp6n77"><div class="grid grid-cols-1 gap-3 svelte-1gp6n77"><div class="flex justify-between items-center p-3 bg-obsidian-900 border border-subtle svelte-1gp6n77"><span class="status-metric__label">AUTONOMY</span> <span${attr_class("mono text-xs font-bold", void 0, {
            "text-amber": store_get($$store_subs ??= {}, "$controlRoom", controlRoom).config.runtime_state.autonomy_paused
          })}>${escape_html(store_get($$store_subs ??= {}, "$controlRoom", controlRoom).config.runtime_state.autonomy_paused ? "PAUSED" : "ACTIVE")}</span></div> <div class="flex justify-between items-center p-3 bg-obsidian-900 border border-subtle svelte-1gp6n77"><span class="status-metric__label">ENTRIES</span> <span${attr_class("mono text-xs font-bold", void 0, {
            "text-crimson": store_get($$store_subs ??= {}, "$controlRoom", controlRoom).config.runtime_state.entries_blocked
          })}>${escape_html(store_get($$store_subs ??= {}, "$controlRoom", controlRoom).config.runtime_state.entries_blocked ? "BLOCKED" : "OPEN")}</span></div> <div class="flex justify-between items-center p-3 bg-obsidian-900 border border-subtle svelte-1gp6n77"><span class="status-metric__label">EXITS ONLY</span> <span${attr_class("mono text-xs font-bold", void 0, {
            "text-amber": store_get($$store_subs ??= {}, "$controlRoom", controlRoom).config.runtime_state.exits_only
          })}>${escape_html(store_get($$store_subs ??= {}, "$controlRoom", controlRoom).config.runtime_state.exits_only ? "YES" : "NO")}</span></div></div> <div class="flex items-center gap-2 opacity-40 svelte-1gp6n77">`);
          Clock($$renderer3, { size: 10 });
          $$renderer3.push(`<!----> <span class="text-[9px] uppercase mono">UPDATED: ${escape_html(formatDateTime(store_get($$store_subs ??= {}, "$controlRoom", controlRoom).config.runtime_state.updated_at).split(" ")[1])}</span></div></div>`);
        },
        $$slots: { default: true }
      });
      $$renderer2.push(`<!----> `);
      Panel($$renderer2, {
        eyebrow: "THRESHOLDS",
        title: "Risk Parameters",
        tone: "amber",
        children: ($$renderer3) => {
          $$renderer3.push(`<div class="grid grid-cols-1 gap-3 svelte-1gp6n77"><div class="flex justify-between items-center p-3 bg-obsidian-900 border border-subtle svelte-1gp6n77"><span class="status-metric__label">CONVICTION</span> <span class="mono text-xs font-bold text-amber">${escape_html(String(marketSettings.conviction_threshold ?? "--"))}</span></div> <div class="flex justify-between items-center p-3 bg-obsidian-900 border border-subtle svelte-1gp6n77"><span class="status-metric__label">MAX POS %</span> <span class="mono text-xs font-bold">${escape_html(String(marketSettings.max_single_position_pct ?? "--"))}%</span></div> <div class="flex justify-between items-center p-3 bg-obsidian-900 border border-subtle svelte-1gp6n77"><span class="status-metric__label">MAX SECT %</span> <span class="mono text-xs font-bold">${escape_html(String(marketSettings.max_sector_exposure_pct ?? "--"))}%</span></div> <div class="flex justify-between items-center p-3 bg-obsidian-900 border border-subtle svelte-1gp6n77"><span class="status-metric__label">MIN CASH %</span> <span class="mono text-xs font-bold">${escape_html(String(marketSettings.min_cash_pct ?? "--"))}%</span></div></div>`);
        },
        $$slots: { default: true }
      });
      $$renderer2.push(`<!----> `);
      Panel($$renderer2, {
        eyebrow: "COMMUNICATIONS",
        title: "Active Desk Notes",
        children: ($$renderer3) => {
          $$renderer3.push(`<div class="space-y-3 svelte-1gp6n77">`);
          if (store_get($$store_subs ??= {}, "$controlRoom", controlRoom).config.active_messages.length) {
            $$renderer3.push("<!--[0-->");
            $$renderer3.push(`<!--[-->`);
            const each_array_1 = ensure_array_like(store_get($$store_subs ??= {}, "$controlRoom", controlRoom).config.active_messages.slice(0, 4));
            for (let $$index_1 = 0, $$length = each_array_1.length; $$index_1 < $$length; $$index_1++) {
              let message = each_array_1[$$index_1];
              $$renderer3.push(`<div class="p-3 bg-obsidian-700 border border-subtle space-y-2 group hover:border-emerald transition-colors svelte-1gp6n77"><div class="flex justify-between items-center svelte-1gp6n77"><span class="mono text-[10px] font-bold text-emerald">${escape_html(String(message.scope).toUpperCase())}</span> <span class="text-[9px] text-ink-dim uppercase">${escape_html(String(message.status))}</span></div> <p class="text-xs text-ink-secondary leading-relaxed svelte-1gp6n77">${escape_html(String(message.raw_text))}</p></div>`);
            }
            $$renderer3.push(`<!--]-->`);
          } else {
            $$renderer3.push("<!--[-1-->");
            $$renderer3.push(`<div class="flex flex-col items-center justify-center py-12 text-ink-dim gap-2 border border-dashed border-subtle svelte-1gp6n77">`);
            Message_square($$renderer3, { size: 20, strokeWidth: 1 });
            $$renderer3.push(`<!----> <span class="mono text-[9px] uppercase tracking-widest">No Active Directives</span></div>`);
          }
          $$renderer3.push(`<!--]--></div>`);
        },
        $$slots: { default: true }
      });
      $$renderer2.push(`<!----></div> <div class="grid grid-cols-1 lg:grid-cols-[320px,1fr] gap-6 items-start svelte-1gp6n77">`);
      Panel($$renderer2, {
        eyebrow: "ARTIFACTS",
        title: "Static Files",
        tone: "emerald",
        children: ($$renderer3) => {
          $$renderer3.push(`<div class="space-y-4 svelte-1gp6n77"><div class="relative svelte-1gp6n77"><input type="text"${attr("value", searchQuery)} placeholder="Filter artifacts..." class="w-full bg-obsidian-900 border border-subtle p-2 pl-8 mono text-[10px] uppercase outline-none focus:border-emerald transition-colors"/> `);
          Search($$renderer3, {
            size: 12,
            class: "absolute left-2.5 top-1/2 -translate-y-1/2 text-ink-dim"
          });
          $$renderer3.push(`<!----></div> <div class="space-y-1 max-h-[500px] overflow-y-auto pr-2 custom-scrollbar svelte-1gp6n77"><!--[-->`);
          const each_array_2 = ensure_array_like(filteredFiles);
          for (let $$index_2 = 0, $$length = each_array_2.length; $$index_2 < $$length; $$index_2++) {
            let file = each_array_2[$$index_2];
            $$renderer3.push(`<button${attr_class("w-full p-3 bg-obsidian-700 border border-subtle text-left group transition-all svelte-1gp6n77", void 0, {
              "border-emerald": selected?.relative_path === file.relative_path,
              "bg-emerald-dim": selected?.relative_path === file.relative_path
            })}${attr("disabled", !file.exists, true)}><div class="flex items-center gap-3 svelte-1gp6n77">`);
            File_code($$renderer3, {
              size: 14,
              class: selected?.relative_path === file.relative_path ? "text-emerald" : "text-ink-dim"
            });
            $$renderer3.push(`<!----> <div class="flex flex-col min-w-0"><span${attr_class("mono text-[10px] font-bold truncate svelte-1gp6n77", void 0, {
              "text-emerald": selected?.relative_path === file.relative_path
            })}>${escape_html(file.relative_path.split("/").pop())}</span> <span${attr_class("text-[8px] text-ink-dim uppercase tracking-tighter", void 0, { "text-emerald": file.exists, "text-crimson": !file.exists })}>${escape_html(file.exists ? "NODE_ACTIVE" : "NODE_MISSING")}</span></div></div> `);
            if (file.modified_at) {
              $$renderer3.push("<!--[0-->");
              $$renderer3.push(`<div class="mt-2 text-right opacity-40"><span class="mono text-[9px]">${escape_html(formatDateTime(file.modified_at).split(" ")[1])}</span></div>`);
            } else {
              $$renderer3.push("<!--[-1-->");
            }
            $$renderer3.push(`<!--]--></button>`);
          }
          $$renderer3.push(`<!--]--></div></div>`);
        },
        $$slots: { default: true }
      });
      $$renderer2.push(`<!----> `);
      Panel($$renderer2, {
        eyebrow: "MATRIX PREVIEW",
        title: "Buffer View",
        tone: "",
        children: ($$renderer3) => {
          {
            $$renderer3.push("<!--[-1-->");
            $$renderer3.push(`<div class="flex flex-col items-center justify-center py-40 text-ink-dim gap-4 border border-dashed border-subtle svelte-1gp6n77">`);
            Hard_drive($$renderer3, { size: 32, strokeWidth: 1 });
            $$renderer3.push(`<!----> <span class="mono text-[10px] uppercase tracking-[0.3em]">Select Configuration Node</span></div>`);
          }
          $$renderer3.push(`<!--]-->`);
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
