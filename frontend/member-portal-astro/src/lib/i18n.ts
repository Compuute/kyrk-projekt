export type BilingualText = { sv: string; am: string };

export function t(obj: BilingualText | undefined | null, lang: string): string {
  if (!obj || typeof obj !== 'object') return '';
  if (typeof (obj as any)[lang] === 'string') return (obj as any)[lang];
  if (typeof obj.sv === 'string') return obj.sv;
  return '';
}

export function detectLanguage(): 'sv' | 'am' {
  if (typeof navigator === 'undefined') return 'sv';
  const navLang = (navigator.language || 'sv').toLowerCase();
  if (navLang.startsWith('am')) return 'am';
  return 'sv';
}
