

export const index = 0;
let component_cache;
export const component = async () => component_cache ??= (await import('../entries/pages/_layout.svelte.js')).default;
export const universal = {
  "ssr": false,
  "prerender": true
};
export const universal_id = "src/routes/+layout.ts";
export const imports = ["_app/immutable/nodes/0.DIGmKCEh.js","_app/immutable/chunks/Fl2vGg9w.js","_app/immutable/chunks/DlK7ccNx.js","_app/immutable/chunks/DZ-LGC5Q.js","_app/immutable/chunks/ft8FxlI5.js","_app/immutable/chunks/BC63ZyJW.js","_app/immutable/chunks/qJzJL3Y7.js","_app/immutable/chunks/Cl9sGg6z.js","_app/immutable/chunks/BkBxZKNh.js","_app/immutable/chunks/DxnzpLtJ.js","_app/immutable/chunks/CyHlRNtF.js","_app/immutable/chunks/W1VNjNpA.js","_app/immutable/chunks/BH5D8ekw.js","_app/immutable/chunks/CgOA-kfl.js","_app/immutable/chunks/CgJqDSRp.js","_app/immutable/chunks/DWt1Gy9C.js","_app/immutable/chunks/C1Z07YbU.js","_app/immutable/chunks/CnPjjAaE.js","_app/immutable/chunks/B1RHoipS.js","_app/immutable/chunks/DRS7IcY0.js","_app/immutable/chunks/6AYpV-1T.js","_app/immutable/chunks/CyZJEo9h.js"];
export const stylesheets = ["_app/immutable/assets/0.Tdv0RrQC.css"];
export const fonts = [];
