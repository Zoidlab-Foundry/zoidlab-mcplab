/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#0b0d16", panel: "#141826", panel2: "#1b2133", line: "#2a3148",
        cy: "#a5b4fc", vi: "#818cf8", ind: "#6366f1", prism: "#818cf8",
        ink: "#e9ecf7", dim: "#97a1c4", faint: "#616c92",
        ok: "#22c55e", warn: "#f4b860", bad: "#ef4444",
      },
      boxShadow: {
        glow: "0 0 40px -10px rgba(129,140,248,0.40)",
      },
    },
  },
  plugins: [],
};
