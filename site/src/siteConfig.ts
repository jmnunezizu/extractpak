export type ThemeId = "harbor" | "harbor-deep" | "harbor-moon" | "harbor-chart";

export const siteConfig = {
  defaultTheme: "harbor" satisfies ThemeId,
  showThemeSelector: false,
  googleAnalyticsMeasurementId: import.meta.env.VITE_GA_MEASUREMENT_ID ?? "",
} as const;
