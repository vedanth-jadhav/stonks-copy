<script lang="ts">
  export let rows: Array<Record<string, any>> = [];
  export let columns: Array<{ key: string; label: string; type?: 'mono' | 'text' }> = [];
</script>

<div class="ledger-container">
  <table class="ledger-table">
    <thead>
      <tr>
        {#each columns as column}
          <th class="status-metric__label">{column.label}</th>
        {/each}
      </tr>
    </thead>
    <tbody>
      {#if rows.length}
        {#each rows as row}
          <tr class="ledger-row">
            {#each columns as column}
              <td class:mono={column.type === 'mono'}>
                {String(row[column.key] ?? "--")}
              </td>
            {/each}
          </tr>
        {/each}
      {:else}
        <tr>
          <td colspan={columns.length} class="empty-cell">
            NO RECORDS IN BUFFER
          </td>
        </tr>
      {/if}
    </tbody>
  </table>
</div>

<style>
  .ledger-container {
    width: 100%;
    overflow-x: auto;
    border: 1px solid var(--border-subtle);
    background: var(--obsidian-800);
  }

  .ledger-table {
    width: 100%;
    border-collapse: collapse;
    text-align: left;
  }

  th {
    padding: 12px 16px;
    background: var(--obsidian-700);
    border-bottom: 1px solid var(--border-subtle);
    font-size: 10px;
    white-space: nowrap;
  }

  td {
    padding: 10px 16px;
    font-size: 13px;
    border-bottom: 1px solid var(--border-subtle);
    color: var(--ink-secondary);
  }

  .ledger-row {
    transition: background 0.1s ease;
  }

  .ledger-row:hover {
    background: var(--row-hover-bg);
    color: var(--ink-primary);
  }

  .ledger-row:hover td {
    color: var(--emerald);
  }

  .empty-cell {
    padding: 40px;
    text-align: center;
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    letter-spacing: 0.2em;
    color: var(--ink-dim);
  }

  .mono {
    font-family: 'JetBrains Mono', monospace;
    font-variant-numeric: tabular-nums;
  }
</style>
