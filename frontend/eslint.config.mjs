// eslint-config-next >=16 eksportuje flat config natywnie (eslint 9).
import nextCoreWebVitals from "eslint-config-next/core-web-vitals";

const config = [
  ...nextCoreWebVitals,
  {
    rules: {
      // Trzy istniejące miejsca (dashboard/monitoring/settings) używają wzorca
      // "ustaw stan po zmianie wyboru" sprzed tej reguły. Nowy kod ma jej
      // unikać (patrz react.dev/learn/you-might-not-need-an-effect);
      // istniejące sprzątamy przy najbliższej pracy nad tymi ekranami.
      "react-hooks/set-state-in-effect": "warn",
    },
  },
  { ignores: [".next/**", "node_modules/**"] },
];

export default config;
