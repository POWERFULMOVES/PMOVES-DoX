export interface DoXTheme {
  edition: string;
  brandName: string;
  brandNameShort: string;
  logoPath: string;
  logoCollapsedPath: string;
  faviconPath: string;
  metaTitle: string;
  metaDescription: string;
  glowColors: { top: string; bottom: string };
  gradientFrom: string;
  gradientTo: string;
  cssOverridePath?: string;
}
