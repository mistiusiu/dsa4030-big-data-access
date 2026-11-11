/** Red Hat design language: Red Hat Display/Text/Mono, brand red on near-black,
 *  neutral grays, 3px radii, PatternFly-style status colours. */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        display: ['"Red Hat Display"', "system-ui", "sans-serif"],
        sans: ['"Red Hat Text"', "system-ui", "sans-serif"],
        mono: ['"Red Hat Mono"', "ui-monospace", "monospace"],
      },
      colors: {
        brand: { DEFAULT: "#ee0000", dark: "#be0000", darker: "#a60000", light: "#fce3e3" },
        ink: { DEFAULT: "#151515", 2: "#1f1f1f", 3: "#292929", 4: "#383838", 5: "#4d4d4d" },
        gray: {
          10: "#f2f2f2", 20: "#e0e0e0", 30: "#c7c7c7", 40: "#a3a3a3", 50: "#707070", 60: "#4d4d4d",
        },
        link: { DEFAULT: "#0066cc", dark: "#004d99", light: "#e0f0ff" },
        ok: { DEFAULT: "#3d7317", bg: "#e9f7df" },
        warn: { DEFAULT: "#795600", bg: "#fff4cc" },
        bad: { DEFAULT: "#a60000", bg: "#fce3e3" },
        teal: { DEFAULT: "#147878", bg: "#daf2f2" },
        purple: { DEFAULT: "#5e40be", bg: "#ece6ff" },
        orange: { DEFAULT: "#9e4a06", bg: "#ffe8cc" },
      },
      borderRadius: { DEFAULT: "3px", md: "6px" },
      boxShadow: { card: "0 1px 2px rgba(21,21,21,.08)", raised: "0 4px 12px rgba(21,21,21,.12)" },
    },
  },
  plugins: [],
};
