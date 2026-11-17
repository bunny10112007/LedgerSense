/**
 * Pure string-based Indian currency formatter and helpers.
 * Never uses parseFloat() or Number() to avoid floating point precision issues.
 */

export function formatINR(amountStr: string | null | undefined): string {
  if (!amountStr || typeof amountStr !== 'string') {
    return '₹0.00';
  }

  const trimmed = amountStr.trim();
  if (trimmed === '' || trimmed === 'null' || trimmed === 'undefined') {
    return '₹0.00';
  }

  let isNegative = false;
  let raw = trimmed;

  if (raw.startsWith('-')) {
    isNegative = true;
    raw = raw.slice(1).trim();
  } else if (raw.startsWith('+')) {
    raw = raw.slice(1).trim();
  }

  const parts = raw.split('.');
  let intPart = parts[0] || '0';
  let decPart = parts.length > 1 ? parts[1] : '00';

  // Normalize decPart to exactly 2 digits
  if (decPart.length === 0) {
    decPart = '00';
  } else if (decPart.length === 1) {
    decPart = decPart + '0';
  } else if (decPart.length > 2) {
    decPart = decPart.slice(0, 2);
  }

  // Remove leading zeros from integer part, but preserve single zero
  intPart = intPart.replace(/^0+(?=\d)/, '');
  if (!intPart) {
    intPart = '0';
  }

  // Indian number grouping:
  // Last 3 digits are grouped, then every 2 digits leftwards
  let formattedInt = '';
  if (intPart.length <= 3) {
    formattedInt = intPart;
  } else {
    const lastThree = intPart.slice(-3);
    const remaining = intPart.slice(0, -3);

    const pairs: string[] = [];
    let i = remaining.length;
    while (i > 0) {
      const start = Math.max(0, i - 2);
      pairs.unshift(remaining.slice(start, i));
      i -= 2;
    }
    formattedInt = pairs.join(',') + ',' + lastThree;
  }

  const result = `₹${formattedInt}.${decPart}`;
  return isNegative ? `-${result}` : result;
}

export function isZeroMoney(amountStr: string | null | undefined): boolean {
  if (!amountStr) return true;
  const cleaned = amountStr.replace(/[^0-9]/g, '');
  return cleaned === '' || /^0+$/.test(cleaned);
}
