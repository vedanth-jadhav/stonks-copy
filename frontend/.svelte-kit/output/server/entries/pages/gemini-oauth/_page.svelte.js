import { ag as ssr_context, s as spread_props, e as escape_html, a as attr, d as attr_class, c as ensure_array_like, ah as attr_style, k as stringify } from "../../../chunks/index2.js";
import "clsx";
import { P as Panel } from "../../../chunks/Panel.js";
import "../../../chunks/control-room.js";
import { f as formatDateTime } from "../../../chunks/format.js";
import { B as Bot } from "../../../chunks/bot.js";
import { I as Icon } from "../../../chunks/Icon.js";
function onDestroy(fn) {
  /** @type {SSRContext} */
  ssr_context.r.on_destroy(fn);
}
function Cpu($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let { $$slots, $$events, ...props } = $$props;
    const iconNode = [
      ["path", { "d": "M12 20v2" }],
      ["path", { "d": "M12 2v2" }],
      ["path", { "d": "M17 20v2" }],
      ["path", { "d": "M17 2v2" }],
      ["path", { "d": "M2 12h2" }],
      ["path", { "d": "M2 17h2" }],
      ["path", { "d": "M2 7h2" }],
      ["path", { "d": "M20 12h2" }],
      ["path", { "d": "M20 17h2" }],
      ["path", { "d": "M20 7h2" }],
      ["path", { "d": "M7 20v2" }],
      ["path", { "d": "M7 2v2" }],
      [
        "rect",
        { "x": "4", "y": "4", "width": "16", "height": "16", "rx": "2" }
      ],
      [
        "rect",
        { "x": "8", "y": "8", "width": "8", "height": "8", "rx": "1" }
      ]
    ];
    Icon($$renderer2, spread_props([
      { name: "cpu" },
      /**
       * @component @name Cpu
       * @description Lucide SVG icon component, renders SVG Element with children.
       *
       * @preview ![img](data:image/svg+xml;base64,PHN2ZyAgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIgogIHdpZHRoPSIyNCIKICBoZWlnaHQ9IjI0IgogIHZpZXdCb3g9IjAgMCAyNCAyNCIKICBmaWxsPSJub25lIgogIHN0cm9rZT0iIzAwMCIgc3R5bGU9ImJhY2tncm91bmQtY29sb3I6ICNmZmY7IGJvcmRlci1yYWRpdXM6IDJweCIKICBzdHJva2Utd2lkdGg9IjIiCiAgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIgogIHN0cm9rZS1saW5lam9pbj0icm91bmQiCj4KICA8cGF0aCBkPSJNMTIgMjB2MiIgLz4KICA8cGF0aCBkPSJNMTIgMnYyIiAvPgogIDxwYXRoIGQ9Ik0xNyAyMHYyIiAvPgogIDxwYXRoIGQ9Ik0xNyAydjIiIC8+CiAgPHBhdGggZD0iTTIgMTJoMiIgLz4KICA8cGF0aCBkPSJNMiAxN2gyIiAvPgogIDxwYXRoIGQ9Ik0yIDdoMiIgLz4KICA8cGF0aCBkPSJNMjAgMTJoMiIgLz4KICA8cGF0aCBkPSJNMjAgMTdoMiIgLz4KICA8cGF0aCBkPSJNMjAgN2gyIiAvPgogIDxwYXRoIGQ9Ik03IDIwdjIiIC8+CiAgPHBhdGggZD0iTTcgMnYyIiAvPgogIDxyZWN0IHg9IjQiIHk9IjQiIHdpZHRoPSIxNiIgaGVpZ2h0PSIxNiIgcng9IjIiIC8+CiAgPHJlY3QgeD0iOCIgeT0iOCIgd2lkdGg9IjgiIGhlaWdodD0iOCIgcng9IjEiIC8+Cjwvc3ZnPgo=) - https://lucide.dev/icons/cpu
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
function Refresh_ccw($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let { $$slots, $$events, ...props } = $$props;
    const iconNode = [
      [
        "path",
        { "d": "M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" }
      ],
      ["path", { "d": "M3 3v5h5" }],
      [
        "path",
        { "d": "M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16" }
      ],
      ["path", { "d": "M16 16h5v5" }]
    ];
    Icon($$renderer2, spread_props([
      { name: "refresh-ccw" },
      /**
       * @component @name RefreshCcw
       * @description Lucide SVG icon component, renders SVG Element with children.
       *
       * @preview ![img](data:image/svg+xml;base64,PHN2ZyAgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIgogIHdpZHRoPSIyNCIKICBoZWlnaHQ9IjI0IgogIHZpZXdCb3g9IjAgMCAyNCAyNCIKICBmaWxsPSJub25lIgogIHN0cm9rZT0iIzAwMCIgc3R5bGU9ImJhY2tncm91bmQtY29sb3I6ICNmZmY7IGJvcmRlci1yYWRpdXM6IDJweCIKICBzdHJva2Utd2lkdGg9IjIiCiAgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIgogIHN0cm9rZS1saW5lam9pbj0icm91bmQiCj4KICA8cGF0aCBkPSJNMjEgMTJhOSA5IDAgMCAwLTktOSA5Ljc1IDkuNzUgMCAwIDAtNi43NCAyLjc0TDMgOCIgLz4KICA8cGF0aCBkPSJNMyAzdjVoNSIgLz4KICA8cGF0aCBkPSJNMyAxMmE5IDkgMCAwIDAgOSA5IDkuNzUgOS43NSAwIDAgMCA2Ljc0LTIuNzRMMjEgMTYiIC8+CiAgPHBhdGggZD0iTTE2IDE2aDV2NSIgLz4KPC9zdmc+Cg==) - https://lucide.dev/icons/refresh-ccw
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
function Trash_2($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let { $$slots, $$events, ...props } = $$props;
    const iconNode = [
      ["path", { "d": "M10 11v6" }],
      ["path", { "d": "M14 11v6" }],
      ["path", { "d": "M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6" }],
      ["path", { "d": "M3 6h18" }],
      ["path", { "d": "M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" }]
    ];
    Icon($$renderer2, spread_props([
      { name: "trash-2" },
      /**
       * @component @name Trash2
       * @description Lucide SVG icon component, renders SVG Element with children.
       *
       * @preview ![img](data:image/svg+xml;base64,PHN2ZyAgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIgogIHdpZHRoPSIyNCIKICBoZWlnaHQ9IjI0IgogIHZpZXdCb3g9IjAgMCAyNCAyNCIKICBmaWxsPSJub25lIgogIHN0cm9rZT0iIzAwMCIgc3R5bGU9ImJhY2tncm91bmQtY29sb3I6ICNmZmY7IGJvcmRlci1yYWRpdXM6IDJweCIKICBzdHJva2Utd2lkdGg9IjIiCiAgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIgogIHN0cm9rZS1saW5lam9pbj0icm91bmQiCj4KICA8cGF0aCBkPSJNMTAgMTF2NiIgLz4KICA8cGF0aCBkPSJNMTQgMTF2NiIgLz4KICA8cGF0aCBkPSJNMTkgNnYxNGEyIDIgMCAwIDEtMiAySDdhMiAyIDAgMCAxLTItMlY2IiAvPgogIDxwYXRoIGQ9Ik0zIDZoMTgiIC8+CiAgPHBhdGggZD0iTTggNlY0YTIgMiAwIDAgMSAyLTJoNGEyIDIgMCAwIDEgMiAydjIiIC8+Cjwvc3ZnPgo=) - https://lucide.dev/icons/trash-2
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
function User_check($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let { $$slots, $$events, ...props } = $$props;
    const iconNode = [
      ["path", { "d": "m16 11 2 2 4-4" }],
      ["path", { "d": "M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" }],
      ["circle", { "cx": "9", "cy": "7", "r": "4" }]
    ];
    Icon($$renderer2, spread_props([
      { name: "user-check" },
      /**
       * @component @name UserCheck
       * @description Lucide SVG icon component, renders SVG Element with children.
       *
       * @preview ![img](data:image/svg+xml;base64,PHN2ZyAgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIgogIHdpZHRoPSIyNCIKICBoZWlnaHQ9IjI0IgogIHZpZXdCb3g9IjAgMCAyNCAyNCIKICBmaWxsPSJub25lIgogIHN0cm9rZT0iIzAwMCIgc3R5bGU9ImJhY2tncm91bmQtY29sb3I6ICNmZmY7IGJvcmRlci1yYWRpdXM6IDJweCIKICBzdHJva2Utd2lkdGg9IjIiCiAgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIgogIHN0cm9rZS1saW5lam9pbj0icm91bmQiCj4KICA8cGF0aCBkPSJtMTYgMTEgMiAyIDQtNCIgLz4KICA8cGF0aCBkPSJNMTYgMjF2LTJhNCA0IDAgMCAwLTQtNEg2YTQgNCAwIDAgMC00IDR2MiIgLz4KICA8Y2lyY2xlIGN4PSI5IiBjeT0iNyIgcj0iNCIgLz4KPC9zdmc+Cg==) - https://lucide.dev/icons/user-check
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
    let isCodeAssist;
    const statusCopy = {
      ready: "READY",
      warning: "WARNING",
      exhausted: "EXHAUSTED",
      unknown: "UNKNOWN",
      "auth-error": "AUTH_ERROR"
    };
    let accounts = [];
    let session = null;
    let binaryPath = "";
    let loginMode = "code_assist";
    let projectId = "";
    let savingSettings = false;
    let busyAccountId = "";
    function usageLabel(percent) {
      if (percent === null) return "Unknown";
      return `${Math.round(percent)}% REMAINING`;
    }
    onDestroy(() => {
    });
    isCodeAssist = loginMode === "code_assist";
    $$renderer2.push(`<div class="space-y-6 svelte-1tki7qa"><section class="flex justify-between items-end border-b border-subtle pb-6 svelte-1tki7qa"><div class="space-y-1 svelte-1tki7qa"><div class="flex items-center gap-2 text-emerald svelte-1tki7qa">`);
    Bot($$renderer2, { size: 14 });
    $$renderer2.push(`<!----> <span class="mono text-[10px] tracking-[0.2em] uppercase font-bold">Model Quota Orchestration</span></div> <h1 class="text-3xl font-bold tracking-tight svelte-1tki7qa">Gemini <span class="text-emerald">Pool</span></h1> <p class="text-ink-secondary text-sm max-w-xl svelte-1tki7qa">Multi-account OAuth management, CLIProxy readiness, and model headroom monitoring.</p></div> <div class="flex gap-4 svelte-1tki7qa"><div class="status-metric text-right"><span class="status-metric__label">TOTAL ACCOUNTS</span> <span class="status-metric__value mono text-emerald">${escape_html(accounts.length)}</span></div> <div class="status-metric text-right"><span class="status-metric__label">READY</span> <span class="status-metric__value mono text-emerald">${escape_html(accounts.filter((a) => a.status === "ready").length)}</span></div></div></section> <div class="grid grid-cols-1 lg:grid-cols-[400px,1fr] gap-6 items-start svelte-1tki7qa"><div class="space-y-6 svelte-1tki7qa">`);
    Panel($$renderer2, {
      eyebrow: "BINARY",
      title: "CLIProxy Launcher",
      tone: "emerald",
      children: ($$renderer3) => {
        $$renderer3.push(`<div class="space-y-6 svelte-1tki7qa"><div class="grid grid-cols-1 gap-2 svelte-1tki7qa"><div class="flex justify-between p-2 bg-obsidian-900 border border-subtle svelte-1tki7qa"><span class="status-metric__label">INSTALL</span> <span class="mono text-[10px] font-bold text-emerald">${escape_html("--")}</span></div> <div class="flex justify-between p-2 bg-obsidian-900 border border-subtle svelte-1tki7qa"><span class="status-metric__label">STATUS</span> <span class="mono text-[10px] font-bold text-emerald">${escape_html("--")}</span></div></div> <div class="space-y-2 svelte-1tki7qa"><label class="status-metric__label svelte-1tki7qa" for="cliproxy-binary">BINARY_PATH_OVERRIDE</label> <input id="cliproxy-binary" class="w-full bg-obsidian-900 border border-subtle p-2 mono text-[10px] text-emerald outline-none focus:border-emerald svelte-1tki7qa"${attr("value", binaryPath)}/></div> <div class="flex gap-2 svelte-1tki7qa"><button class="flex-1 py-2 bg-emerald text-obsidian-900 mono text-[10px] font-bold uppercase tracking-widest hover:bg-emerald-glow transition-all svelte-1tki7qa"${attr("disabled", savingSettings, true)}>${escape_html("UPDATE")}</button> <button class="flex-1 py-2 border border-subtle text-ink-dim mono text-[10px] font-bold uppercase tracking-widest hover:text-emerald hover:border-emerald transition-all svelte-1tki7qa"${attr("disabled", session?.status === "running", true)}>${escape_html("REINSTALL")}</button></div></div>`);
      },
      $$slots: { default: true }
    });
    $$renderer2.push(`<!----> `);
    Panel($$renderer2, {
      eyebrow: "OAUTH HANDOFF",
      title: "Live Session",
      tone: "amber",
      children: ($$renderer3) => {
        $$renderer3.push(`<div class="space-y-6 svelte-1tki7qa"><div class="flex items-center gap-3 p-3 bg-obsidian-900 border border-amber/30 svelte-1tki7qa"><div${attr_class("w-2 h-2 rounded-full animate-pulse svelte-1tki7qa", void 0, {
          "bg-amber": session?.status === "running",
          "bg-emerald": session?.status === "completed",
          "bg-ink-dim": !session
        })}></div> <span class="mono text-[10px] font-bold text-amber">${escape_html("IDLE")}</span></div> <p class="text-[10px] text-ink-secondary leading-relaxed uppercase tracking-tighter opacity-80 svelte-1tki7qa">${escape_html("Awaiting initiation of Gemini OAuth login sequence.")}</p> <div class="space-y-4 border-t border-subtle pt-4 svelte-1tki7qa"><div class="space-y-2 svelte-1tki7qa"><label class="status-metric__label svelte-1tki7qa" for="gemini-login-mode">AUTH_PROTOCOL</label> `);
        $$renderer3.select(
          {
            id: "gemini-login-mode",
            class: "w-full bg-obsidian-900 border border-subtle p-2 mono text-[10px] text-emerald outline-none focus:border-emerald",
            value: loginMode
          },
          ($$renderer4) => {
            $$renderer4.option({ value: "google_one" }, ($$renderer5) => {
              $$renderer5.push(`GOOGLE_ONE (CONSUMER)`);
            });
            $$renderer4.option({ value: "code_assist" }, ($$renderer5) => {
              $$renderer5.push(`CODE_ASSIST (CLOUD_PROJECT)`);
            });
          },
          "svelte-1tki7qa"
        );
        $$renderer3.push(`</div> `);
        if (isCodeAssist) {
          $$renderer3.push("<!--[0-->");
          $$renderer3.push(`<div class="space-y-2 svelte-1tki7qa"><label class="status-metric__label svelte-1tki7qa" for="gemini-project-id">GCP_PROJECT_ID</label> <input id="gemini-project-id" class="w-full bg-obsidian-900 border border-subtle p-2 mono text-[10px] text-emerald outline-none focus:border-emerald svelte-1tki7qa"${attr("value", projectId)} placeholder="e.g. keen-virtue-484413"/></div>`);
        } else {
          $$renderer3.push("<!--[-1-->");
        }
        $$renderer3.push(`<!--]--> <button class="w-full py-3 bg-amber-dim border border-amber text-amber mono text-[10px] font-bold uppercase tracking-widest hover:bg-amber/20 transition-all disabled:opacity-30 svelte-1tki7qa"${attr("disabled", true, true)}>${escape_html("ADD_ACCOUNT")}</button></div></div>`);
      },
      $$slots: { default: true }
    });
    $$renderer2.push(`<!----></div> `);
    Panel($$renderer2, {
      eyebrow: "ACCOUNT CLUSTER",
      title: "Gemini Quota Board",
      tone: "emerald",
      children: ($$renderer3) => {
        $$renderer3.push(`<div class="space-y-6 svelte-1tki7qa"><!--[-->`);
        const each_array = ensure_array_like(accounts);
        for (let $$index_1 = 0, $$length = each_array.length; $$index_1 < $$length; $$index_1++) {
          let account = each_array[$$index_1];
          $$renderer3.push(`<div class="p-6 bg-obsidian-800 border border-subtle relative group hover:border-emerald transition-all svelte-1tki7qa"><div class="flex justify-between items-start mb-6 svelte-1tki7qa"><div class="space-y-1 svelte-1tki7qa"><div class="flex items-center gap-2 svelte-1tki7qa">`);
          User_check($$renderer3, { size: 16, class: "text-emerald" });
          $$renderer3.push(`<!----> <span class="mono text-sm font-bold">${escape_html(account.email)}</span></div> <div class="mono text-[9px] text-ink-dim uppercase tracking-widest svelte-1tki7qa">${escape_html(account.project_id ? `PROJECT: ${account.project_id}` : "NO_PROJECT_LINK")}</div></div> <div class="flex flex-col text-right gap-1 svelte-1tki7qa"><span${attr_class("mono text-[10px] font-bold", void 0, {
            "text-emerald": account.status === "ready",
            "text-amber": account.status === "exhausted",
            "text-crimson": account.status === "auth-error"
          })}>${escape_html(statusCopy[account.status] ?? account.status)}</span> <span class="text-[9px] text-ink-dim uppercase mono">${escape_html(formatDateTime(account.modified_at).split(" ")[1])}</span></div></div> <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6 svelte-1tki7qa"><!--[-->`);
          const each_array_1 = ensure_array_like(account.usage.models);
          for (let $$index = 0, $$length2 = each_array_1.length; $$index < $$length2; $$index++) {
            let model = each_array_1[$$index];
            $$renderer3.push(`<div class="p-3 bg-obsidian-900 border border-subtle space-y-2 svelte-1tki7qa"><span class="status-metric__label text-[9px] truncate block svelte-1tki7qa">${escape_html(model.model_id)}</span> <div${attr_class("mono text-xs font-bold svelte-1tki7qa", void 0, {
              "text-emerald": model.available,
              "text-amber": !model.available
            })}>${escape_html(usageLabel(model.remaining_percent))}</div> <div class="h-1 bg-obsidian-700 w-full rounded-full overflow-hidden svelte-1tki7qa"><div class="h-full bg-emerald"${attr_style(`width: ${stringify(model.remaining_percent ?? 0)}%`)}></div></div></div>`);
          }
          $$renderer3.push(`<!--]--></div> `);
          if (account.usage.error) {
            $$renderer3.push("<!--[0-->");
            $$renderer3.push(`<div class="p-3 bg-crimson-dim border border-crimson/30 text-crimson text-[10px] mono uppercase tracking-widest mb-4 svelte-1tki7qa">${escape_html(account.usage.error)}</div>`);
          } else {
            $$renderer3.push("<!--[-1-->");
          }
          $$renderer3.push(`<!--]--> <div class="flex justify-end gap-3 pt-4 border-t border-subtle svelte-1tki7qa"><button class="flex items-center gap-2 px-4 py-2 border border-subtle text-ink-dim mono text-[10px] font-bold uppercase tracking-widest hover:text-emerald hover:border-emerald transition-all svelte-1tki7qa"${attr("disabled", busyAccountId === account.account_id, true)}>`);
          Refresh_ccw($$renderer3, {
            size: 12,
            class: busyAccountId === account.account_id ? "animate-spin" : ""
          });
          $$renderer3.push(`<!----> REFRESH_QUOTA</button> <button class="flex items-center gap-2 px-4 py-2 border border-subtle text-ink-dim mono text-[10px] font-bold uppercase tracking-widest hover:text-crimson hover:border-crimson transition-all svelte-1tki7qa"${attr("disabled", busyAccountId === account.account_id, true)}>`);
          Trash_2($$renderer3, { size: 12 });
          $$renderer3.push(`<!----> PURGE</button></div></div>`);
        }
        $$renderer3.push(`<!--]--> `);
        if (!accounts.length) {
          $$renderer3.push("<!--[0-->");
          $$renderer3.push(`<div class="flex flex-col items-center justify-center py-40 text-ink-dim gap-4 border border-dashed border-subtle svelte-1tki7qa">`);
          Cpu($$renderer3, { size: 32, strokeWidth: 1 });
          $$renderer3.push(`<!----> <span class="mono text-[10px] uppercase tracking-[0.3em]">No compute nodes in cluster</span></div>`);
        } else {
          $$renderer3.push("<!--[-1-->");
        }
        $$renderer3.push(`<!--]--></div>`);
      },
      $$slots: { default: true }
    });
    $$renderer2.push(`<!----></div> `);
    {
      $$renderer2.push("<!--[-1-->");
    }
    $$renderer2.push(`<!--]--></div>`);
  });
}
export {
  _page as default
};
