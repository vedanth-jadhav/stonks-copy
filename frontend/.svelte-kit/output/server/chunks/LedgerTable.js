import { f as fallback, c as ensure_array_like, e as escape_html, d as attr_class, a as attr, b as bind_props } from "./index2.js";
function LedgerTable($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let rows = fallback($$props["rows"], () => [], true);
    let columns = fallback($$props["columns"], () => [], true);
    $$renderer2.push(`<div class="ledger-container svelte-181u797"><table class="ledger-table svelte-181u797"><thead><tr><!--[-->`);
    const each_array = ensure_array_like(columns);
    for (let $$index = 0, $$length = each_array.length; $$index < $$length; $$index++) {
      let column = each_array[$$index];
      $$renderer2.push(`<th class="status-metric__label svelte-181u797">${escape_html(column.label)}</th>`);
    }
    $$renderer2.push(`<!--]--></tr></thead><tbody>`);
    if (rows.length) {
      $$renderer2.push("<!--[0-->");
      $$renderer2.push(`<!--[-->`);
      const each_array_1 = ensure_array_like(rows);
      for (let $$index_2 = 0, $$length = each_array_1.length; $$index_2 < $$length; $$index_2++) {
        let row = each_array_1[$$index_2];
        $$renderer2.push(`<tr class="ledger-row svelte-181u797"><!--[-->`);
        const each_array_2 = ensure_array_like(columns);
        for (let $$index_1 = 0, $$length2 = each_array_2.length; $$index_1 < $$length2; $$index_1++) {
          let column = each_array_2[$$index_1];
          $$renderer2.push(`<td${attr_class("svelte-181u797", void 0, { "mono": column.type === "mono" })}>${escape_html(String(row[column.key] ?? "--"))}</td>`);
        }
        $$renderer2.push(`<!--]--></tr>`);
      }
      $$renderer2.push(`<!--]-->`);
    } else {
      $$renderer2.push("<!--[-1-->");
      $$renderer2.push(`<tr><td${attr("colspan", columns.length)} class="empty-cell svelte-181u797">NO RECORDS IN BUFFER</td></tr>`);
    }
    $$renderer2.push(`<!--]--></tbody></table></div>`);
    bind_props($$props, { rows, columns });
  });
}
export {
  LedgerTable as L
};
