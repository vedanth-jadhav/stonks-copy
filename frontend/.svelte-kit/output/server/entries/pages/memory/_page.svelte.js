import { s as spread_props, i as store_get, e as escape_html, u as unsubscribe_stores, a as attr, c as ensure_array_like } from "../../../chunks/index2.js";
import { P as Panel } from "../../../chunks/Panel.js";
import { c as controlRoom } from "../../../chunks/control-room.js";
import { Z as Zap } from "../../../chunks/zap.js";
import { M as Memory_stick } from "../../../chunks/memory-stick.js";
import { S as Search } from "../../../chunks/search.js";
import { L as Layers } from "../../../chunks/layers.js";
import { I as Icon } from "../../../chunks/Icon.js";
function Database($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let { $$slots, $$events, ...props } = $$props;
    const iconNode = [
      ["ellipse", { "cx": "12", "cy": "5", "rx": "9", "ry": "3" }],
      ["path", { "d": "M3 5V19A9 3 0 0 0 21 19V5" }],
      ["path", { "d": "M3 12A9 3 0 0 0 21 12" }]
    ];
    Icon($$renderer2, spread_props([
      { name: "database" },
      /**
       * @component @name Database
       * @description Lucide SVG icon component, renders SVG Element with children.
       *
       * @preview ![img](data:image/svg+xml;base64,PHN2ZyAgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIgogIHdpZHRoPSIyNCIKICBoZWlnaHQ9IjI0IgogIHZpZXdCb3g9IjAgMCAyNCAyNCIKICBmaWxsPSJub25lIgogIHN0cm9rZT0iIzAwMCIgc3R5bGU9ImJhY2tncm91bmQtY29sb3I6ICNmZmY7IGJvcmRlci1yYWRpdXM6IDJweCIKICBzdHJva2Utd2lkdGg9IjIiCiAgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIgogIHN0cm9rZS1saW5lam9pbj0icm91bmQiCj4KICA8ZWxsaXBzZSBjeD0iMTIiIGN5PSI1IiByeD0iOSIgcnk9IjMiIC8+CiAgPHBhdGggZD0iTTMgNVYxOUE5IDMgMCAwIDAgMjEgMTlWNSIgLz4KICA8cGF0aCBkPSJNMyAxMkE5IDMgMCAwIDAgMjEgMTIiIC8+Cjwvc3ZnPgo=) - https://lucide.dev/icons/database
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
    let query = "caution regime";
    let results = [];
    let searching = false;
    if (!store_get($$store_subs ??= {}, "$controlRoom", controlRoom).memory) {
      $$renderer2.push("<!--[0-->");
      $$renderer2.push(`<div class="flex flex-col items-center justify-center min-h-[60vh] gap-4 svelte-1czmmpc">`);
      Zap($$renderer2, { size: 32, class: "text-emerald animate-pulse" });
      $$renderer2.push(`<!----> <div class="mono text-[10px] tracking-[0.2em] text-emerald opacity-50 uppercase">Loading Memory Graph...</div></div>`);
    } else {
      $$renderer2.push("<!--[-1-->");
      $$renderer2.push(`<div class="space-y-6 svelte-1czmmpc"><section class="flex justify-between items-end border-b border-subtle pb-6 svelte-1czmmpc"><div class="space-y-1 svelte-1czmmpc"><div class="flex items-center gap-2 text-emerald svelte-1czmmpc">`);
      Memory_stick($$renderer2, { size: 14 });
      $$renderer2.push(`<!----> <span class="mono text-[10px] tracking-[0.2em] uppercase font-bold">Neural Retrieval Desk</span></div> <h1 class="text-3xl font-bold tracking-tight svelte-1czmmpc">System <span class="text-emerald">Memory</span></h1> <p class="text-ink-secondary text-sm max-w-xl svelte-1czmmpc">Semantic search across the knowledge graph and historical episode retrieval.</p></div> <div class="flex gap-4 svelte-1czmmpc"><div class="status-metric text-right"><span class="status-metric__label">GRAPH NODES</span> <span class="status-metric__value mono text-emerald">${escape_html(store_get($$store_subs ??= {}, "$controlRoom", controlRoom).memory?.nodes.length ?? 0)}</span></div> <div class="status-metric text-right"><span class="status-metric__label">EDGES</span> <span class="status-metric__value mono text-emerald">${escape_html(store_get($$store_subs ??= {}, "$controlRoom", controlRoom).memory?.edges.length ?? 0)}</span></div></div></section> `);
      Panel($$renderer2, {
        eyebrow: "SEMANTIC SEARCH",
        title: "Knowledge Retrieval",
        tone: "emerald",
        children: ($$renderer3) => {
          $$renderer3.push(`<form class="flex gap-4 svelte-1czmmpc"><div class="relative flex-1 svelte-1czmmpc"><input type="text"${attr("value", query)} placeholder="Search the neural graph (e.g., 'market regime shifts')" class="w-full bg-obsidian-900 border border-subtle p-3 pl-10 mono text-xs text-emerald outline-none focus:border-emerald transition-colors svelte-1czmmpc"/> `);
          Search($$renderer3, {
            size: 14,
            class: "absolute left-3 top-1/2 -translate-y-1/2 text-ink-dim"
          });
          $$renderer3.push(`<!----></div> <button type="submit"${attr("disabled", searching, true)} class="px-8 bg-emerald text-obsidian-900 mono text-xs font-bold uppercase tracking-widest hover:bg-emerald-glow transition-all svelte-1czmmpc">${escape_html("QUERY")}</button></form>`);
        },
        $$slots: { default: true }
      });
      $$renderer2.push(`<!----> <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start svelte-1czmmpc">`);
      Panel($$renderer2, {
        eyebrow: "SEARCH RESULTS",
        title: "Relevant Episodes",
        children: ($$renderer3) => {
          $$renderer3.push(`<div class="space-y-3 svelte-1czmmpc">`);
          if (results.length) {
            $$renderer3.push("<!--[0-->");
            $$renderer3.push(`<!--[-->`);
            const each_array = ensure_array_like(results);
            for (let $$index = 0, $$length = each_array.length; $$index < $$length; $$index++) {
              let result = each_array[$$index];
              $$renderer3.push(`<div class="p-4 bg-obsidian-700 border border-subtle space-y-3 group hover:border-emerald transition-colors svelte-1czmmpc"><div class="flex justify-between items-center svelte-1czmmpc"><span class="mono text-[10px] font-bold text-emerald">${escape_html(String(result.ref_id).toUpperCase())}</span> <span class="text-[9px] text-ink-dim uppercase tracking-widest">${escape_html(String(result.node_type))}</span></div> <p class="text-xs text-ink-secondary leading-relaxed svelte-1czmmpc">${escape_html(String(result.content))}</p></div>`);
            }
            $$renderer3.push(`<!--]-->`);
          } else {
            $$renderer3.push("<!--[-1-->");
            $$renderer3.push(`<div class="flex flex-col items-center justify-center py-20 text-ink-dim gap-4 border border-dashed border-subtle svelte-1czmmpc">`);
            Layers($$renderer3, { size: 24, strokeWidth: 1 });
            $$renderer3.push(`<!----> <span class="mono text-[9px] uppercase tracking-widest">Execute query to retrieve data</span></div>`);
          }
          $$renderer3.push(`<!--]--></div>`);
        },
        $$slots: { default: true }
      });
      $$renderer2.push(`<!----> `);
      Panel($$renderer2, {
        eyebrow: "GRAPH TAPE",
        title: "Recent Node Entries",
        children: ($$renderer3) => {
          $$renderer3.push(`<div class="space-y-3 svelte-1czmmpc"><!--[-->`);
          const each_array_1 = ensure_array_like((store_get($$store_subs ??= {}, "$controlRoom", controlRoom).memory?.nodes ?? []).slice(0, 8));
          for (let $$index_1 = 0, $$length = each_array_1.length; $$index_1 < $$length; $$index_1++) {
            let node = each_array_1[$$index_1];
            $$renderer3.push(`<div class="p-3 bg-obsidian-800 border border-subtle flex gap-4 group hover:border-emerald transition-colors svelte-1czmmpc"><div class="flex-shrink-0 mt-1">`);
            Database($$renderer3, { size: 14, class: "text-ink-dim group-hover:text-emerald" });
            $$renderer3.push(`<!----></div> <div class="flex flex-col min-w-0 svelte-1czmmpc"><div class="flex justify-between items-center mb-1 svelte-1czmmpc"><span class="mono text-[10px] font-bold text-emerald">${escape_html(String(node.ref_id).toUpperCase())}</span> <span class="text-[8px] text-ink-dim uppercase">${escape_html(String(node.node_type))}</span></div> <p class="text-[11px] text-ink-secondary leading-normal truncate svelte-1czmmpc">${escape_html(String(node.content))}</p></div></div>`);
          }
          $$renderer3.push(`<!--]--> `);
          if (!store_get($$store_subs ??= {}, "$controlRoom", controlRoom).memory?.nodes.length) {
            $$renderer3.push("<!--[0-->");
            $$renderer3.push(`<div class="text-center py-20 text-ink-dim mono text-[10px] uppercase tracking-widest svelte-1czmmpc">No entries in buffer</div>`);
          } else {
            $$renderer3.push("<!--[-1-->");
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
