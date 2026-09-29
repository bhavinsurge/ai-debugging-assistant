/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        ink: "#0f1c1a",
        moss: "#1f4d45",
        signal: "#c45c26",
        mist: "#e8f0ee",
        paper: "#f7faf8",
        line: "#c5d4cf",
      },
      fontFamily: {
        display: ["var(--font-display)", "Georgia", "serif"],
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
      keyframes: {
        rise: {
          "0%": { opacity: "0", transform: "translateY(12px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        pulseBar: {
          "0%, 100%": { transform: "scaleX(0.35)", opacity: "0.55" },
          "50%": { transform: "scaleX(1)", opacity: "1" },
        },
      },
      animation: {
        rise: "rise 0.6s ease-out both",
        "pulse-bar": "pulseBar 1.8s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};
