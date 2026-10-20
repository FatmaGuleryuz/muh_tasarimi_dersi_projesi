/** Renkler ve ölçüler: Stitch "Executive Forest & Sand" tasarım sistemi (DESIGN.md). */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        canvas: "#F6F3EC",
        surface: "#FFFFFF",
        forest: { DEFAULT: "#1E3A28", dark: "#152A1D" },
        sage: "#2E5A3D",
        amber: "#C77D2E",
        brick: "#BA3C2A",
        ink: { DEFAULT: "#1A1A1A", 2: "#555555", 3: "#777777" },
        line: "#E5E1D8",
        "row-line": "#E2E8F0",
        "row-hover": "#FBF9F5",
      },
      fontFamily: { sans: ['"Plus Jakarta Sans"', "system-ui", "sans-serif"] },
      borderRadius: { DEFAULT: "4px", lg: "8px" },
      boxShadow: { none: "none" }, // tasarım sistemi: gölge yok, sadece 1px kenarlık
    },
  },
  plugins: [],
};
