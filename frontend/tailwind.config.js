module.exports = {
  darkMode: "class",
  content: [
    "./pages/**/*.{js,ts,jsx,tsx}",
    "./components/**/*.{js,ts,jsx,tsx}",
    "./app/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Ferrari / race UI tokens
        raceBlack: {
          1: "#050507",
          2: "#09090B",
        },
        chrome: {
          1: "#0F0F14",
          2: "#27272A",
          3: "#3F3F46",
          4: "#E5E7EB",
        },
        ferrariRed: {
          DEFAULT: "#E10600",
          1: "#B10000",
          2: "#FF1B1B",
        },
        // Override default tailwind red scale to use official Ferrari Corsa red tones
        red: {
          50: "#FFF5F5",
          100: "#FED7D7",
          200: "#FEB2B2",
          300: "#FC8181",
          400: "#F56565",
          500: "#FF1B1B", // Ferrari Red Light
          600: "#E10600", // Ferrari Rosso Corsa (Default Red)
          700: "#B10000", // Ferrari Red Dark
          800: "#9B0000",
          900: "#7B0000",
          950: "#4A0000",
        },
        // Override default tailwind yellow scale to use Giallo Modena yellow tones
        yellow: {
          50: "#FEFCE8",
          100: "#FEF9C3",
          200: "#FEF08A",
          300: "#FDE047",
          400: "#FACC15",
          500: "#FFDC00", // Giallo Modena (Ferrari Yellow)
          600: "#EAB308",
          700: "#A16207",
          800: "#854D0E",
          900: "#713F12",
          950: "#422006",
        },
        // keep existing semantic keys for compatibility
        primary: "#E10600",
        secondary: "#000000",
        accent: "#FFFFFF",
      },
      boxShadow: {
        ferrariGlow: "0 0 24px rgba(225,6,0,0.35)",
        ferrariGlowStrong: "0 0 40px rgba(225,6,0,0.55)",
      },
    },
  },
  plugins: [],
};

