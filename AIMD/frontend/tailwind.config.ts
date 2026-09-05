import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{js,ts,jsx,tsx,mdx}", "./components/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        ink: "#090d12",
        panel: "#10161e",
        line: "#25313d",
        signal: "#56d6c8",
        amber: "#f5b75c",
        alert: "#ed7569",
      },
      boxShadow: {
        halo: "0 0 0 1px rgba(86, 214, 200, 0.12), 0 20px 80px rgba(0, 0, 0, 0.28)",
      },
    },
  },
  plugins: [],
};

export default config;
