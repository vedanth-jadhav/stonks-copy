import { f as fallback, c as ensure_array_like, a as attr, k as stringify, e as escape_html, d as attr_class, b as bind_props, i as store_get, u as unsubscribe_stores } from "../../chunks/index2.js";
import "@sveltejs/kit/internal";
import "../../chunks/exports.js";
import "../../chunks/utils.js";
import "clsx";
import "@sveltejs/kit/internal/server";
import "../../chunks/root.js";
import "../../chunks/state.svelte.js";
import { P as Panel } from "../../chunks/Panel.js";
import { f as formatDateTime } from "../../chunks/format.js";
import { c as controlRoom } from "../../chunks/control-room.js";
import { Z as Zap } from "../../chunks/zap.js";
import { S as Shield_check } from "../../chunks/shield-check.js";
import { A as Activity } from "../../chunks/activity.js";
import { L as Layers } from "../../chunks/layers.js";
import { C as Clock } from "../../chunks/clock.js";
function SystemBoard($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let map = $$props["map"];
    let selectedNodeId = fallback($$props["selectedNodeId"], "");
    let onSelect = $$props["onSelect"];
    let lines = [];
    function updateLines() {
      return;
    }
    function primaryMetric(node) {
      return node.metric ? `${node.metric.label}: ${node.metric.value}` : "NO DATA";
    }
    if (map) setTimeout(updateLines, 0);
    $$renderer2.push(`<div class="system-board-container svelte-bxrxfz"><svg class="flow-lines svelte-bxrxfz"><defs class="svelte-bxrxfz"><linearGradient id="line-grad" x1="0%" y1="0%" x2="100%" y2="0%" class="svelte-bxrxfz"><stop offset="0%" stop-color="var(--emerald)" stop-opacity="0.2" class="svelte-bxrxfz"></stop><stop offset="50%" stop-color="var(--emerald)" stop-opacity="0.6" class="svelte-bxrxfz"></stop><stop offset="100%" stop-color="var(--emerald)" stop-opacity="0.2" class="svelte-bxrxfz"></stop></linearGradient></defs><!--[-->`);
    const each_array = ensure_array_like(lines);
    for (let $$index = 0, $$length = each_array.length; $$index < $$length; $$index++) {
      let line = each_array[$$index];
      $$renderer2.push(`<path${attr("d", `M ${stringify(line.x1)} ${stringify(line.y1)} C ${stringify((line.x1 + line.x2) / 2)} ${stringify(line.y1)}, ${stringify((line.x1 + line.x2) / 2)} ${stringify(line.y2)}, ${stringify(line.x2)} ${stringify(line.y2)}`)} stroke="url(#line-grad)" stroke-width="2" fill="none" class="pulse-path svelte-bxrxfz"></path><circle r="3" fill="var(--emerald)" class="data-particle svelte-bxrxfz"><animateMotion dur="3s" repeatCount="indefinite"${attr("path", `M ${stringify(line.x1)} ${stringify(line.y1)} C ${stringify((line.x1 + line.x2) / 2)} ${stringify(line.y1)}, ${stringify((line.x1 + line.x2) / 2)} ${stringify(line.y2)}, ${stringify(line.x2)} ${stringify(line.y2)}`)} class="svelte-bxrxfz"></animateMotion></circle>`);
    }
    $$renderer2.push(`<!--]--></svg> <div class="system-board-track svelte-bxrxfz"><!--[-->`);
    const each_array_1 = ensure_array_like(map.stages);
    for (let $$index_2 = 0, $$length = each_array_1.length; $$index_2 < $$length; $$index_2++) {
      let stage = each_array_1[$$index_2];
      const nodes = map.nodes.filter((n) => n.stage === stage.id);
      $$renderer2.push(`<section class="flow-stage svelte-bxrxfz"><div class="stage-header svelte-bxrxfz"><span class="mono text-emerald opacity-50 text-[10px] tracking-tighter svelte-bxrxfz">${escape_html(stage.id.toUpperCase())}</span> <h3 class="text-xs font-bold tracking-widest uppercase opacity-80 svelte-bxrxfz">${escape_html(stage.caption)}</h3></div> <div class="node-stack svelte-bxrxfz"><!--[-->`);
      const each_array_2 = ensure_array_like(nodes);
      for (let $$index_1 = 0, $$length2 = each_array_2.length; $$index_1 < $$length2; $$index_1++) {
        let node = each_array_2[$$index_1];
        $$renderer2.push(`<button${attr_class("node-card svelte-bxrxfz", void 0, {
          "selected": selectedNodeId === node.id,
          "border-emerald": node.status === "healthy",
          "border-amber": node.status === "warning",
          "border-crimson": node.status === "critical"
        })}><div class="flex justify-between items-start mb-2 svelte-bxrxfz"><span class="text-[10px] font-bold uppercase tracking-tighter opacity-60 svelte-bxrxfz">${escape_html(node.label)}</span> <div${attr_class("w-1.5 h-1.5 rounded-full svelte-bxrxfz", void 0, {
          "bg-emerald": node.status === "healthy",
          "bg-amber": node.status === "warning",
          "bg-crimson": node.status === "critical"
        })}></div></div> <div class="mono text-xs font-medium mb-1 truncate svelte-bxrxfz">${escape_html(primaryMetric(node))}</div> <div class="text-[9px] opacity-40 uppercase svelte-bxrxfz">${escape_html(formatDateTime(node.updated_at).split(" ")[1])}</div></button>`);
      }
      $$renderer2.push(`<!--]--></div></section>`);
    }
    $$renderer2.push(`<!--]--> <section class="flow-stage boss-stage svelte-bxrxfz"><div class="stage-header svelte-bxrxfz"><span class="mono text-amber opacity-50 text-[10px] tracking-tighter svelte-bxrxfz">TERMINAL</span> <h3 class="text-xs font-bold tracking-widest uppercase opacity-80 svelte-bxrxfz">BOSS CORE</h3></div> <div class="boss-radar-container svelte-bxrxfz"><button${attr_class("boss-radar svelte-bxrxfz", void 0, { "selected": selectedNodeId === "boss" })}><div class="radar-rings svelte-bxrxfz"><div class="ring svelte-bxrxfz"></div> <div class="ring svelte-bxrxfz"></div> <div class="ring svelte-bxrxfz"></div></div> <div class="radar-content svelte-bxrxfz"><div class="text-[10px] opacity-60 uppercase mb-1 svelte-bxrxfz">Decision</div> <div class="mono text-xl font-bold text-amber svelte-bxrxfz">${escape_html(map.boss.value)}</div></div></button> <button class="mt-4 text-[10px] font-bold uppercase tracking-widest text-amber hover:underline svelte-bxrxfz">Review Protocol →</button></div></section></div></div>`);
    bind_props($$props, { map, selectedNodeId, onSelect });
  });
}
function _page($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    var $$store_subs;
    let selectedNode;
    let selectedNodeId = "agent_06_macro";
    async function handleSelect(nodeId) {
      selectedNodeId = nodeId;
      if (nodeId !== "boss") {
        await controlRoom.selectAgent(nodeId);
      }
    }
    if (store_get($$store_subs ??= {}, "$controlRoom", controlRoom).systemMap && !store_get($$store_subs ??= {}, "$controlRoom", controlRoom).systemMap.nodes.some((node) => node.id === selectedNodeId) && selectedNodeId !== "boss") {
      selectedNodeId = store_get($$store_subs ??= {}, "$controlRoom", controlRoom).systemMap.nodes[0]?.id ?? "boss";
    }
    selectedNode = selectedNodeId === "boss" ? null : store_get($$store_subs ??= {}, "$controlRoom", controlRoom).systemMap?.nodes.find((node) => node.id === selectedNodeId) ?? null;
    if (!store_get($$store_subs ??= {}, "$controlRoom", controlRoom).systemMap || !store_get($$store_subs ??= {}, "$controlRoom", controlRoom).overview) {
      $$renderer2.push("<!--[0-->");
      $$renderer2.push(`<div class="flex flex-col items-center justify-center min-h-[60vh] gap-4">`);
      Zap($$renderer2, { size: 32, class: "text-emerald animate-pulse" });
      $$renderer2.push(`<!----> <div class="mono text-[10px] tracking-[0.2em] text-emerald opacity-50 uppercase svelte-1uha8ag">Synchronizing Neural Links...</div></div>`);
    } else {
      $$renderer2.push("<!--[-1-->");
      $$renderer2.push(`<div class="space-y-6 svelte-1uha8ag"><section class="flex justify-between items-end border-b border-subtle pb-6 svelte-1uha8ag"><div class="space-y-1 svelte-1uha8ag"><div class="flex items-center gap-2 text-emerald svelte-1uha8ag">`);
      Shield_check($$renderer2, { size: 14 });
      $$renderer2.push(`<!----> <span class="mono text-[10px] tracking-[0.2em] uppercase font-bold">Secure Command Environment</span></div> <h1 class="text-3xl font-bold tracking-tight svelte-1uha8ag">Tactical Operations <span class="text-emerald">HUD</span></h1> <p class="text-ink-secondary text-sm max-w-xl svelte-1uha8ag">Real-time pipeline monitoring and high-frequency signal arbitration.</p></div> <div class="flex gap-4"><div class="status-metric text-right"><span class="status-metric__label">SIGNAL NODES</span> <span class="status-metric__value mono text-emerald">${escape_html(store_get($$store_subs ??= {}, "$controlRoom", controlRoom).systemMap.memory_signal.nodes)}</span></div> <div class="status-metric text-right"><span class="status-metric__label">ACTIVE EDGES</span> <span class="status-metric__value mono text-emerald">${escape_html(store_get($$store_subs ??= {}, "$controlRoom", controlRoom).systemMap.memory_signal.edges)}</span></div> <div class="status-metric text-right"><span class="status-metric__label">MARKET STATE</span> <span class="status-metric__value mono text-amber">${escape_html(store_get($$store_subs ??= {}, "$controlRoom", controlRoom).overview.market.session_state)}</span></div></div></section> <div class="grid grid-cols-1 xl-grid-cols-split gap-6 items-start svelte-1uha8ag">`);
      Panel($$renderer2, {
        eyebrow: "EXECUTION TOPOLOGY",
        title: "Signal Flow Map",
        tone: "emerald",
        children: ($$renderer3) => {
          SystemBoard($$renderer3, {
            map: store_get($$store_subs ??= {}, "$controlRoom", controlRoom).systemMap,
            selectedNodeId,
            onSelect: handleSelect
          });
        },
        $$slots: { default: true }
      });
      $$renderer2.push(`<!----> `);
      Panel($$renderer2, {
        eyebrow: "NODE DIAGNOSTICS",
        title: selectedNodeId === "boss" ? "TERMINAL CORE" : selectedNode?.label ?? "SELECTION",
        tone: selectedNodeId === "boss" ? "amber" : "emerald",
        children: ($$renderer3) => {
          if (selectedNodeId === "boss") {
            $$renderer3.push("<!--[0-->");
            $$renderer3.push(`<div class="space-y-6 svelte-1uha8ag"><p class="text-xs text-ink-secondary leading-relaxed svelte-1uha8ag">Final portfolio arbitration and execution gate. All signals terminate here for final routing.</p> <div class="grid grid-cols-2 gap-4 border-y border-subtle py-4 svelte-1uha8ag"><div class="status-metric"><span class="status-metric__label">STATUS</span> <span class="status-metric__value text-emerald">${escape_html(store_get($$store_subs ??= {}, "$controlRoom", controlRoom).systemMap.boss.status)}</span></div> <div class="status-metric"><span class="status-metric__label">THROUGHPUT</span> <span class="status-metric__value mono">${escape_html(store_get($$store_subs ??= {}, "$controlRoom", controlRoom).systemMap.boss.value)}</span></div></div> <div class="space-y-3 svelte-1uha8ag"><span class="status-metric__label svelte-1uha8ag">LATEST DECISIONS</span> <div class="space-y-2 svelte-1uha8ag"><!--[-->`);
            const each_array = ensure_array_like(store_get($$store_subs ??= {}, "$controlRoom", controlRoom).overview.latest_decisions.slice(0, 4));
            for (let $$index = 0, $$length = each_array.length; $$index < $$length; $$index++) {
              let decision = each_array[$$index];
              $$renderer3.push(`<div class="p-3 bg-obsidian-700 border border-subtle flex justify-between items-center group hover:border-emerald transition-colors svelte-1uha8ag"><div class="flex flex-col"><span class="mono text-xs font-bold text-emerald">${escape_html(decision.ticker ?? "PORT")}</span> <span class="text-[9px] text-ink-dim uppercase">Origin: ${escape_html(decision.origin ?? "SYS")}</span></div> <div class="flex flex-col text-right"><span${attr_class("mono text-xs font-bold", void 0, {
                "text-emerald": decision.decision === "BUY",
                "text-crimson": decision.decision === "SELL"
              })}>${escape_html(decision.decision ?? "HOLD")}</span> <span class="text-[9px] text-ink-dim mono">C: ${escape_html(Number(decision.confidence ?? 0).toFixed(2))}</span></div></div>`);
            }
            $$renderer3.push(`<!--]--></div></div> <button class="w-full p-2 border border-amber text-amber mono text-[10px] uppercase tracking-widest hover:bg-amber-dim transition-colors svelte-1uha8ag">ACCESS COMMAND PROTOCOL</button></div>`);
          } else if (selectedNode && store_get($$store_subs ??= {}, "$controlRoom", controlRoom).selectedAgent?.agent_id === selectedNode.id) {
            $$renderer3.push("<!--[1-->");
            $$renderer3.push(`<div class="space-y-6 svelte-1uha8ag"><p class="text-xs text-ink-secondary leading-relaxed svelte-1uha8ag">${escape_html(selectedNode.summary)}</p> <div class="grid grid-cols-2 gap-4 border-y border-subtle py-4 svelte-1uha8ag"><div class="status-metric"><span class="status-metric__label">HEALTH</span> <span${attr_class("status-metric__value", void 0, {
              "text-emerald": selectedNode.status === "healthy",
              "text-amber": selectedNode.status === "warning",
              "text-crimson": selectedNode.status === "critical"
            })}>${escape_html(selectedNode.status.toUpperCase())}</span></div> <div class="status-metric"><span class="status-metric__label">SYNCED</span> <span class="status-metric__value mono text-[10px]">${escape_html(formatDateTime(selectedNode.updated_at).split(" ")[1])}</span></div></div> `);
            if (selectedNode.warnings.length) {
              $$renderer3.push("<!--[0-->");
              $$renderer3.push(`<div class="p-3 bg-crimson-dim border border-crimson/30 text-crimson text-[10px] leading-relaxed svelte-1uha8ag"><div class="flex items-center gap-2 mb-1 font-bold">`);
              Activity($$renderer3, { size: 10 });
              $$renderer3.push(`<!----> <span>WARNING DETECTED</span></div> <!--[-->`);
              const each_array_1 = ensure_array_like(selectedNode.warnings);
              for (let $$index_1 = 0, $$length = each_array_1.length; $$index_1 < $$length; $$index_1++) {
                let warning = each_array_1[$$index_1];
                $$renderer3.push(`<p>• ${escape_html(warning)}</p>`);
              }
              $$renderer3.push(`<!--]--></div>`);
            } else {
              $$renderer3.push("<!--[-1-->");
            }
            $$renderer3.push(`<!--]--> <div class="space-y-3 svelte-1uha8ag"><span class="status-metric__label svelte-1uha8ag">RECENT PULSES</span> <div class="space-y-2 svelte-1uha8ag"><!--[-->`);
            const each_array_2 = ensure_array_like(store_get($$store_subs ??= {}, "$controlRoom", controlRoom).selectedAgent.runs.slice(0, 3));
            for (let $$index_2 = 0, $$length = each_array_2.length; $$index_2 < $$length; $$index_2++) {
              let run = each_array_2[$$index_2];
              $$renderer3.push(`<div class="p-2 bg-obsidian-700 border border-subtle flex justify-between items-center svelte-1uha8ag"><span class="mono text-[10px]">${escape_html(run.status)}</span> <span class="mono text-[10px] opacity-40 svelte-1uha8ag">${escape_html(formatDateTime(String(run.finished_at ?? run.started_at ?? "")).split(" ")[1])}</span></div>`);
            }
            $$renderer3.push(`<!--]--></div></div> <div class="space-y-3 svelte-1uha8ag"><span class="status-metric__label svelte-1uha8ag">ACTIVE SIGNALS</span> <div class="grid grid-cols-2 gap-2 svelte-1uha8ag"><!--[-->`);
            const each_array_3 = ensure_array_like(store_get($$store_subs ??= {}, "$controlRoom", controlRoom).selectedAgent.signals.slice(0, 4));
            for (let $$index_3 = 0, $$length = each_array_3.length; $$index_3 < $$length; $$index_3++) {
              let signal = each_array_3[$$index_3];
              $$renderer3.push(`<div class="p-2 bg-obsidian-900 border border-subtle flex justify-between items-center"><span class="mono text-[10px] font-bold">${escape_html(signal.ticker)}</span> <span class="mono text-[10px] text-emerald">${escape_html(Number(signal.score ?? 0).toFixed(2))}</span></div>`);
            }
            $$renderer3.push(`<!--]--></div></div></div>`);
          } else {
            $$renderer3.push("<!--[-1-->");
            $$renderer3.push(`<div class="flex flex-col items-center justify-center py-20 text-ink-dim gap-2 svelte-1uha8ag">`);
            Layers($$renderer3, { size: 24, strokeWidth: 1 });
            $$renderer3.push(`<!----> <span class="mono text-[9px] uppercase tracking-widest">Awaiting Selection</span></div>`);
          }
          $$renderer3.push(`<!--]-->`);
        },
        $$slots: { default: true }
      });
      $$renderer2.push(`<!----></div> <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 svelte-1uha8ag">`);
      Panel($$renderer2, {
        eyebrow: "SYSTEM OUTPUTS",
        title: "Artifact Registry",
        children: ($$renderer3) => {
          $$renderer3.push(`<div class="grid grid-cols-2 sm:grid-cols-4 gap-4 svelte-1uha8ag"><!--[-->`);
          const each_array_4 = ensure_array_like(store_get($$store_subs ??= {}, "$controlRoom", controlRoom).systemMap.artifacts);
          for (let $$index_4 = 0, $$length = each_array_4.length; $$index_4 < $$length; $$index_4++) {
            let artifact = each_array_4[$$index_4];
            $$renderer3.push(`<button class="p-4 bg-obsidian-800 border border-subtle text-left group hover:border-emerald transition-all"><div class="status-metric mb-2"><span class="status-metric__label">${escape_html(artifact.label)}</span> <span class="status-metric__value mono text-lg group-hover:text-emerald">${escape_html(artifact.value)}</span></div> <p class="text-[9px] text-ink-dim uppercase leading-tight truncate svelte-1uha8ag">${escape_html(artifact.caption)}</p></button>`);
          }
          $$renderer3.push(`<!--]--></div>`);
        },
        $$slots: { default: true }
      });
      $$renderer2.push(`<!----> `);
      Panel($$renderer2, {
        eyebrow: "TEMPORAL SCHEDULER",
        title: "Next Cron Sequence",
        children: ($$renderer3) => {
          $$renderer3.push(`<div class="space-y-2 svelte-1uha8ag"><!--[-->`);
          const each_array_5 = ensure_array_like(store_get($$store_subs ??= {}, "$controlRoom", controlRoom).systemMap.schedule);
          for (let $$index_5 = 0, $$length = each_array_5.length; $$index_5 < $$length; $$index_5++) {
            let item = each_array_5[$$index_5];
            $$renderer3.push(`<div class="p-3 bg-obsidian-800 border border-subtle flex justify-between items-center hover:bg-obsidian-700 transition-colors svelte-1uha8ag"><div class="flex items-center gap-3">`);
            Clock($$renderer3, { size: 14, class: "text-emerald opacity-50" });
            $$renderer3.push(`<!----> <span class="mono text-xs font-medium uppercase">${escape_html(item.label)}</span></div> <div class="flex items-center gap-4"><span class="mono text-xs text-emerald">${escape_html(formatDateTime(item.value).split(" ")[1])}</span> <span class="text-[9px] px-2 py-0-5 border border-subtle rounded-full uppercase text-ink-dim svelte-1uha8ag">${escape_html(item.pending ? "PENDING" : "SCHEDULED")}</span></div></div>`);
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
