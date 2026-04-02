"use client";

import { createContext, useContext } from "react";

/* Dark-only design. ThemeProvider is kept for compatibility but does nothing. */
interface ThemeContextValue {
  theme: "dark";
  toggleTheme: () => void;
}

const ThemeContext = createContext<ThemeContextValue>({
  theme: "dark",
  toggleTheme: () => {},
});

export function useTheme() {
  return useContext(ThemeContext);
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  return (
    <ThemeContext.Provider value={{ theme: "dark", toggleTheme: () => {} }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function ThemeScript() {
  return null;
}
