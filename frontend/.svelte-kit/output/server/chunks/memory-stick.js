import { s as spread_props } from "./index2.js";
import { I as Icon } from "./Icon.js";
function Memory_stick($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let { $$slots, $$events, ...props } = $$props;
    const iconNode = [
      ["path", { "d": "M6 19v-3" }],
      ["path", { "d": "M10 19v-3" }],
      ["path", { "d": "M14 19v-3" }],
      ["path", { "d": "M18 19v-3" }],
      ["path", { "d": "M8 11V9" }],
      ["path", { "d": "M16 11V9" }],
      ["path", { "d": "M12 11V9" }],
      ["path", { "d": "M2 15h20" }],
      [
        "path",
        {
          "d": "M2 7a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v1.1a2 2 0 0 0 0 3.837V17a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2v-5.1a2 2 0 0 0 0-3.837Z"
        }
      ]
    ];
    Icon($$renderer2, spread_props([
      { name: "memory-stick" },
      /**
       * @component @name MemoryStick
       * @description Lucide SVG icon component, renders SVG Element with children.
       *
       * @preview ![img](data:image/svg+xml;base64,PHN2ZyAgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIgogIHdpZHRoPSIyNCIKICBoZWlnaHQ9IjI0IgogIHZpZXdCb3g9IjAgMCAyNCAyNCIKICBmaWxsPSJub25lIgogIHN0cm9rZT0iIzAwMCIgc3R5bGU9ImJhY2tncm91bmQtY29sb3I6ICNmZmY7IGJvcmRlci1yYWRpdXM6IDJweCIKICBzdHJva2Utd2lkdGg9IjIiCiAgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIgogIHN0cm9rZS1saW5lam9pbj0icm91bmQiCj4KICA8cGF0aCBkPSJNNiAxOXYtMyIgLz4KICA8cGF0aCBkPSJNMTAgMTl2LTMiIC8+CiAgPHBhdGggZD0iTTE0IDE5di0zIiAvPgogIDxwYXRoIGQ9Ik0xOCAxOXYtMyIgLz4KICA8cGF0aCBkPSJNOCAxMVY5IiAvPgogIDxwYXRoIGQ9Ik0xNiAxMVY5IiAvPgogIDxwYXRoIGQ9Ik0xMiAxMVY5IiAvPgogIDxwYXRoIGQ9Ik0yIDE1aDIwIiAvPgogIDxwYXRoIGQ9Ik0yIDdhMiAyIDAgMCAxIDItMmgxNmEyIDIgMCAwIDEgMiAydjEuMWEyIDIgMCAwIDAgMCAzLjgzN1YxN2EyIDIgMCAwIDEtMiAySDRhMiAyIDAgMCAxLTItMnYtNS4xYTIgMiAwIDAgMCAwLTMuODM3WiIgLz4KPC9zdmc+Cg==) - https://lucide.dev/icons/memory-stick
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
export {
  Memory_stick as M
};
