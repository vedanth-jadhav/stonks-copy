import { writable } from 'svelte/store';

export type Theme = 'dark' | 'light';

const STORAGE_KEY = 'stonks-theme';

function createThemeStore() {
  const persisted =
    typeof localStorage !== 'undefined'
      ? (localStorage.getItem(STORAGE_KEY) as Theme | null)
      : null;

  const initial: Theme = persisted === 'light' ? 'light' : 'dark';
  const store = writable<Theme>(initial);

  function applyTheme(t: Theme) {
    document.documentElement.setAttribute('data-theme', t);
    localStorage.setItem(STORAGE_KEY, t);
  }

  function toggle() {
    store.update((current) => {
      const next: Theme = current === 'dark' ? 'light' : 'dark';
      applyTheme(next);
      return next;
    });
  }

  function init() {
    store.subscribe(applyTheme);
  }

  return { subscribe: store.subscribe, toggle, init };
}

export const theme = createThemeStore();
