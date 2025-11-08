export function getApiBase(): string {
  if (typeof window !== 'undefined') {
    const v = localStorage.getItem('lms_api_base');
    if (v && v.trim()) return v.trim();
  }
  return process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8484';
}

export function setApiBase(v: string) {
  if (typeof window !== 'undefined') {
    localStorage.setItem('lms_api_base', v);
  }
}

export function getAuthorDefault(): string {
  if (typeof window !== 'undefined') {
    return localStorage.getItem('lms_analyst_author') || '';
  }
  return '';
}

export function setAuthorDefault(v: string) {
  if (typeof window !== 'undefined') {
    localStorage.setItem('lms_analyst_author', v);
  }
}

export function getVlmEnabled(): boolean {
  if (typeof window !== 'undefined') {
    const v = localStorage.getItem('lms_vlm_enabled');
    if (v === 'true') return true;
    if (v === 'false') return false;
  }
  return true;
}

export function setVlmEnabled(v: boolean) {
  if (typeof window !== 'undefined') {
    localStorage.setItem('lms_vlm_enabled', v ? 'true' : 'false');
  }
}

export function getUseOllama(): boolean {
  if (typeof window !== 'undefined') {
    return localStorage.getItem('lms_use_ollama') === 'true';
  }
  return false;
}

export function setUseOllama(v: boolean) {
  if (typeof window !== 'undefined') {
    localStorage.setItem('lms_use_ollama', v ? 'true' : 'false');
  }
}

export function getOfflineHint(): boolean {
  if (typeof window !== 'undefined') {
    return localStorage.getItem('lms_offline') === 'true';
  }
  return false;
}

export function setOfflineHint(v: boolean) {
  if (typeof window !== 'undefined') {
    localStorage.setItem('lms_offline', v ? 'true' : 'false');
  }
}

// HRM settings
export function getHRMEnabled(): boolean {
  if (typeof window !== 'undefined') {
    return localStorage.getItem('lms_hrm_enabled') === 'true';
  }
  return false;
}

export function setHRMEnabled(v: boolean) {
  if (typeof window !== 'undefined') {
    localStorage.setItem('lms_hrm_enabled', v ? 'true' : 'false');
  }
}

export function getHRMMmax(): number {
  if (typeof window !== 'undefined') {
    const v = localStorage.getItem('lms_hrm_mmax');
    const n = v ? parseInt(v, 10) : NaN;
    return Number.isFinite(n) && n > 0 ? n : 6;
  }
  return 6;
}

export function setHRMMmax(n: number) {
  if (typeof window !== 'undefined') {
    localStorage.setItem('lms_hrm_mmax', String(n));
  }
}

export function getHRMMmin(): number {
  if (typeof window !== 'undefined') {
    const v = localStorage.getItem('lms_hrm_mmin');
    const n = v ? parseInt(v, 10) : NaN;
    return Number.isFinite(n) && n > 0 ? n : 2;
  }
  return 2;
}

export function setHRMMmin(n: number) {
  if (typeof window !== 'undefined') {
    localStorage.setItem('lms_hrm_mmin', String(n));
  }
}
