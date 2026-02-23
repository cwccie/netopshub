/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        noh: {
          bg: "#0f172a",
          surface: "#1e293b",
          border: "#334155",
          primary: "#3b82f6",
          secondary: "#8b5cf6",
          accent: "#06b6d4",
          success: "#22c55e",
          warning: "#eab308",
          danger: "#ef4444",
          text: "#f1f5f9",
          muted: "#94a3b8",
        },
      },
    },
  },
  plugins: [],
};
