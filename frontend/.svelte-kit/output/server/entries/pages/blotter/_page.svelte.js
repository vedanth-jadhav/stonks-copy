import { i as store_get, e as escape_html, u as unsubscribe_stores, c as ensure_array_like } from "../../../chunks/index2.js";
import { L as LedgerTable } from "../../../chunks/LedgerTable.js";
import { P as Panel } from "../../../chunks/Panel.js";
import { c as controlRoom } from "../../../chunks/control-room.js";
import { f as formatDateTime, a as formatCurrency } from "../../../chunks/format.js";
import { Z as Zap } from "../../../chunks/zap.js";
import { C as Clipboard_list } from "../../../chunks/clipboard-list.js";
function _page($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    var $$store_subs;
    if (!store_get($$store_subs ??= {}, "$controlRoom", controlRoom).portfolio) {
      $$renderer2.push("<!--[0-->");
      $$renderer2.push(`<div class="flex flex-col items-center justify-center min-h-[60vh] gap-4 svelte-1lhqghf">`);
      Zap($$renderer2, { size: 32, class: "text-emerald animate-pulse" });
      $$renderer2.push(`<!----> <div class="mono text-[10px] tracking-[0.2em] text-emerald opacity-50 uppercase">Accessing Audit Vault...</div></div>`);
    } else {
      $$renderer2.push("<!--[-1-->");
      $$renderer2.push(`<div class="space-y-6 svelte-1lhqghf"><section class="flex justify-between items-end border-b border-subtle pb-6 svelte-1lhqghf"><div class="space-y-1 svelte-1lhqghf"><div class="flex items-center gap-2 text-emerald svelte-1lhqghf">`);
      Clipboard_list($$renderer2, { size: 14 });
      $$renderer2.push(`<!----> <span class="mono text-[10px] tracking-[0.2em] uppercase font-bold">Execution Ledger</span></div> <h1 class="text-3xl font-bold tracking-tight svelte-1lhqghf">System <span class="text-emerald">Blotter</span></h1> <p class="text-ink-secondary text-sm max-w-xl svelte-1lhqghf">Audit trails, decision sequences, and instruction validation.</p></div> <div class="flex gap-4"><div class="status-metric text-right"><span class="status-metric__label">DECISIONS</span> <span class="status-metric__value mono text-emerald">${escape_html(store_get($$store_subs ??= {}, "$controlRoom", controlRoom).portfolio.decisions.length)}</span></div> <div class="status-metric text-right"><span class="status-metric__label">ORDERS</span> <span class="status-metric__value mono text-emerald">${escape_html(store_get($$store_subs ??= {}, "$controlRoom", controlRoom).portfolio.orders.length)}</span></div> <div class="status-metric text-right"><span class="status-metric__label">FILLS</span> <span class="status-metric__value mono text-emerald">${escape_html(store_get($$store_subs ??= {}, "$controlRoom", controlRoom).portfolio.fills.length)}</span></div></div></section> <div class="grid grid-cols-1 md-grid-cols-3 gap-6 svelte-1lhqghf">`);
      Panel($$renderer2, {
        eyebrow: "COMMAND PROTOCOL",
        title: "Recent Decisions",
        tone: "emerald",
        children: ($$renderer3) => {
          $$renderer3.push(`<div class="space-y-3 svelte-1lhqghf"><!--[-->`);
          const each_array = ensure_array_like(store_get($$store_subs ??= {}, "$controlRoom", controlRoom).portfolio.decisions.slice(0, 5));
          for (let $$index = 0, $$length = each_array.length; $$index < $$length; $$index++) {
            let decision = each_array[$$index];
            $$renderer3.push(`<div class="p-3 bg-obsidian-700 border border-subtle flex justify-between items-start group hover:border-emerald transition-colors svelte-1lhqghf"><div class="flex flex-col"><span class="mono text-xs font-bold text-emerald">${escape_html(String(decision.ticker))}</span> <span class="text-[9px] text-ink-dim uppercase mt-1">${escape_html(formatDateTime(String(decision.created_at ?? "")).split(" ")[1])}</span></div> <div class="text-right"><span class="mono text-xs font-bold uppercase">${escape_html(String(decision.decision))}</span> <div class="text-[9px] text-ink-dim mono">CONF: ${escape_html(Number(decision.confidence ?? 0).toFixed(2))}</div></div></div>`);
          }
          $$renderer3.push(`<!--]--></div>`);
        },
        $$slots: { default: true }
      });
      $$renderer2.push(`<!----> `);
      Panel($$renderer2, {
        eyebrow: "INSTRUCTION FLOW",
        title: "Pending Orders",
        children: ($$renderer3) => {
          $$renderer3.push(`<div class="space-y-3 svelte-1lhqghf"><!--[-->`);
          const each_array_1 = ensure_array_like(store_get($$store_subs ??= {}, "$controlRoom", controlRoom).portfolio.orders.slice(0, 5));
          for (let $$index_1 = 0, $$length = each_array_1.length; $$index_1 < $$length; $$index_1++) {
            let order = each_array_1[$$index_1];
            $$renderer3.push(`<div class="p-3 bg-obsidian-700 border border-subtle flex justify-between items-start group hover:border-amber transition-colors svelte-1lhqghf"><div class="flex flex-col"><span class="mono text-xs font-bold text-amber">${escape_html(String(order.ticker))}</span> <span class="text-[9px] text-ink-dim uppercase mt-1">${escape_html(formatDateTime(String(order.created_at ?? "")).split(" ")[1])}</span></div> <div class="text-right"><span class="mono text-xs font-bold">${escape_html(String(order.shares ?? 0))} SH</span> <div class="text-[9px] text-ink-dim uppercase tracking-widest">${escape_html(String(order.decision))}</div></div></div>`);
          }
          $$renderer3.push(`<!--]--></div>`);
        },
        $$slots: { default: true }
      });
      $$renderer2.push(`<!----> `);
      Panel($$renderer2, {
        eyebrow: "EXECUTION LOG",
        title: "Matched Fills",
        children: ($$renderer3) => {
          $$renderer3.push(`<div class="space-y-3 svelte-1lhqghf"><!--[-->`);
          const each_array_2 = ensure_array_like(store_get($$store_subs ??= {}, "$controlRoom", controlRoom).portfolio.fills.slice(0, 5));
          for (let $$index_2 = 0, $$length = each_array_2.length; $$index_2 < $$length; $$index_2++) {
            let fill = each_array_2[$$index_2];
            $$renderer3.push(`<div class="p-3 bg-obsidian-700 border border-subtle flex justify-between items-start group hover:border-emerald transition-colors svelte-1lhqghf"><div class="flex flex-col"><span class="mono text-xs font-bold text-emerald">${escape_html(String(fill.ticker))}</span> <span class="text-[9px] text-ink-dim uppercase mt-1">${escape_html(String(fill.action))}</span></div> <div class="text-right"><span class="mono text-xs font-bold">${escape_html(formatCurrency(Number(fill.fill_price ?? 0)))}</span> <div class="text-[9px] text-ink-dim mono">CHRG: ${escape_html(formatCurrency(Number(fill.charges ?? 0)))}</div></div></div>`);
          }
          $$renderer3.push(`<!--]--></div>`);
        },
        $$slots: { default: true }
      });
      $$renderer2.push(`<!----></div> <div class="grid grid-cols-1 lg-grid-cols-blotter gap-6 items-start svelte-1lhqghf">`);
      Panel($$renderer2, {
        eyebrow: "AUDIT TABLE",
        title: "Chronological Fills",
        tone: "emerald",
        children: ($$renderer3) => {
          LedgerTable($$renderer3, {
            rows: store_get($$store_subs ??= {}, "$controlRoom", controlRoom).portfolio.fills,
            columns: [
              { key: "ticker", label: "TICKER", type: "mono" },
              { key: "action", label: "ACTION" },
              { key: "fill_price", label: "PRICE", type: "mono" },
              { key: "charges", label: "CHARGES", type: "mono" },
              { key: "execution_type", label: "TYPE" }
            ]
          });
        },
        $$slots: { default: true }
      });
      $$renderer2.push(`<!----> `);
      Panel($$renderer2, {
        eyebrow: "VALIDATION",
        title: "IC Diagnostics",
        children: ($$renderer3) => {
          $$renderer3.push(`<div class="space-y-4 svelte-1lhqghf"><p class="text-[10px] text-ink-dim uppercase tracking-widest leading-relaxed svelte-1lhqghf">Cross-validation of agent signals against realized outcomes.</p> <div class="grid grid-cols-1 gap-3 svelte-1lhqghf"><!--[-->`);
          const each_array_3 = ensure_array_like(store_get($$store_subs ??= {}, "$controlRoom", controlRoom).agents);
          for (let $$index_3 = 0, $$length = each_array_3.length; $$index_3 < $$length; $$index_3++) {
            let agent = each_array_3[$$index_3];
            $$renderer3.push(`<div class="p-3 bg-obsidian-900 border border-subtle group hover:border-emerald transition-colors"><div class="flex justify-between items-center mb-2 svelte-1lhqghf"><span class="mono text-[10px] font-bold text-emerald">${escape_html(agent.agent_id.replace("agent_", "").toUpperCase())}</span> <span class="text-[9px] text-ink-dim uppercase tracking-tighter">${escape_html(String(agent.latest_run?.status ?? "idle"))}</span></div> <div class="grid grid-cols-3 gap-2 svelte-1lhqghf"><div class="status-metric"><span class="status-metric__label">IC</span> <span class="status-metric__value mono text-xs">${escape_html(Number(agent.ic_snapshot.ic_value ?? 0).toFixed(3))}</span></div> <div class="status-metric"><span class="status-metric__label">WIN %</span> <span class="status-metric__value mono text-xs">${escape_html(agent.ic_snapshot.win_rate !== void 0 ? `${(Number(agent.ic_snapshot.win_rate) * 100).toFixed(0)}%` : "--")}</span></div> <div class="status-metric text-right"><span class="status-metric__label">SMPL</span> <span class="status-metric__value mono text-xs">${escape_html(String(agent.ic_snapshot.sample_size ?? 0))}</span></div></div></div>`);
          }
          $$renderer3.push(`<!--]--></div></div>`);
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
