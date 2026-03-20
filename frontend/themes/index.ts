import type { DoXTheme } from './types';
import { defaultTheme } from './default';
import { unfcuTheme } from './unfcu/theme';

const themes: Record<string, DoXTheme> = {
  default: defaultTheme,
  unfcu: unfcuTheme,
};

export function getTheme(): DoXTheme {
  const edition = process.env.NEXT_PUBLIC_DOX_EDITION || 'default';
  return themes[edition] || defaultTheme;
}

export type { DoXTheme };
export { defaultTheme, unfcuTheme };
