/**
 * 将下钻表中的 code（6 位或已带后缀）规范为 K 线 API 用 symbol。
 */
export function toAshareKlineSymbol(code: string): string {
  const raw = (code || '').trim().toUpperCase();
  if (!raw) return '';
  const base = raw.split('.', 1)[0].replace(/\D/g, '');
  if (base.length < 5) return raw;
  const six = base.length >= 8 ? base.slice(0, 8) : base.slice(0, 6);
  if (six.length === 8) return `${six}.BJ`;
  if (six.startsWith('6')) return `${six}.SH`;
  return `${six}.SZ`;
}

export function eastMoneyIndividualUrl(symbol: string): string {
  const s = toAshareKlineSymbol(symbol);
  const code = s.split('.', 1)[0];
  if (!code) return 'https://www.eastmoney.com/';
  if (s.endsWith('.SH')) return `https://quote.eastmoney.com/sh${code}.html`;
  if (s.endsWith('.BJ')) return `https://quote.eastmoney.com/bj${code}.html`;
  return `https://quote.eastmoney.com/sz${code}.html`;
}
