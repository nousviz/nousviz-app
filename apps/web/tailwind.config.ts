import type { Config } from "tailwindcss";

export default {
  darkMode: ["class"],
  // B151.1 (v0.9.4.1): scan plugin widget source so any Tailwind utility
  // class strings used by plugin-shipped widgets get included in the
  // host's CSS build. Note: this only matters if the operator rebuilds
  // the host frontend after installing/updating a plugin (e.g. via
  // setup.sh). Plugins that ship pre-bundled JS without rebuilding the
  // host bundle are limited to utilities the host already uses.
  // Plugin authors: stick to commonly-used utilities to maximise
  // compatibility with already-built host bundles.
  content: [
    "./index.html",
    "./src/**/*.{ts,tsx}",
    "../../plugins/installed/*/widget/**/*.{js,jsx,ts,tsx}",
    "../../plugins/utilities/*/widget/**/*.{js,jsx,ts,tsx}",
    "../../plugins/official/*/widget/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    container: {
      center: true,
      padding: "2rem",
      screens: { "2xl": "1400px" },
    },
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
        sidebar: {
          DEFAULT: "hsl(var(--sidebar-background))",
          foreground: "hsl(var(--sidebar-foreground))",
          primary: "hsl(var(--sidebar-primary))",
          "primary-foreground": "hsl(var(--sidebar-primary-foreground))",
          accent: "hsl(var(--sidebar-accent))",
          "accent-foreground": "hsl(var(--sidebar-accent-foreground))",
          border: "hsl(var(--sidebar-border))",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      fontSize: {
        'page-title':     ['32px', { lineHeight: '1.2', fontWeight: '600' }],
        'section-header': ['20px', { lineHeight: '1.3', fontWeight: '600' }],
        'card-title':     ['16px', { lineHeight: '1.4', fontWeight: '600' }],
        'body':           ['14px', { lineHeight: '1.5' }],
        'meta':           ['12px', { lineHeight: '1.4' }],
      },
      maxWidth: {
        'content': '1280px',
      },
      keyframes: {
        "accordion-down": {
          from: { height: "0" },
          to: { height: "var(--radix-accordion-content-height)" },
        },
        "accordion-up": {
          from: { height: "var(--radix-accordion-content-height)" },
          to: { height: "0" },
        },
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
      },
    },
  },
  plugins: [require("tailwindcss-animate"), require("@tailwindcss/typography")],
} satisfies Config;
