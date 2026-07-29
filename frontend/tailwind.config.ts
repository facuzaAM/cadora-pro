import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./src/app/**/*.{ts,tsx}",
    "./src/components/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      backgroundImage: {
        "dot-pattern": "radial-gradient(circle, hsl(var(--primary) / 0.15) 1px, transparent 1px)",
        "dot-pattern-sm": "radial-gradient(circle, hsl(var(--primary) / 0.1) 1px, transparent 1px)",
        "grid-pattern": [
          "linear-gradient(to right, hsl(var(--border)) 1px, transparent 1px)",
          "linear-gradient(to bottom, hsl(var(--border)) 1px, transparent 1px)",
        ].join(","),
        "grid-pattern-subtle": [
          "linear-gradient(to right, hsl(var(--primary) / 0.04) 1px, transparent 1px)",
          "linear-gradient(to bottom, hsl(var(--primary) / 0.04) 1px, transparent 1px)",
        ].join(","),
      },
      animation: {
        "blob": "blob 8s ease-in-out infinite",
        "blob-delayed": "blob 8s ease-in-out 2s infinite",
        "blob-slow": "blob 12s ease-in-out 4s infinite",
      },
      keyframes: {
        blob: {
          "0%, 100%": { transform: "translate(0, 0) scale(1)" },
          "33%": { transform: "translate(30px, -50px) scale(1.05)" },
          "66%": { transform: "translate(-20px, 20px) scale(0.95)" },
        },
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};

export default config;
