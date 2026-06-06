export type ThemeId = "harbor" | "harbor-deep" | "harbor-moon" | "harbor-chart";

export const siteConfig = {
  defaultTheme: "harbor" satisfies ThemeId,
  showThemeSelector: true,
} as const;
