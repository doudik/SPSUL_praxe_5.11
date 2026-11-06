const BRAND_ALIASES = {
  vw: 'volkswagen',
};

function normalizeString(val) {
  if (val === null || val === undefined) return null;
  const s = String(val).trim().toLowerCase().replace(/\s+/g, ' ');
  return s === '' || s === 'null' ? null : s;
}

function normalizeBrand(val) {
  const s = normalizeString(val);
  if (s === null) return null;
  return BRAND_ALIASES[s] ?? s;
}

function normalizeModel(val) {
  const s = normalizeString(val);
  if (s === null) return null;
  // odstraní generační označení na konci (Golf VII -> Golf, Passat B7 -> Passat)
  return s.replace(/\s+(mk\s?\d+|b\d+|i{1,3}|iv|vi{0,3}|ix|x)$/i, '').trim();
}

function normalizeNumber(val) {
  if (val === null || val === undefined) return null;
  if (typeof val === 'number') return val;

  const s = String(val).trim().toLowerCase();
  if (s === '' || s === 'null') return null;

  // "220k" / "15 tisic" / "15 tisíc" -> násobit 1000
  const isThousand = /(tisic|tisíc|\btis\b|k)\s*$/.test(s);
  const digits = s.replace(/[^\d]/g, '');
  if (digits === '') return null;

  let n = parseInt(digits, 10);
  if (isThousand && n < 1000) n *= 1000;
  return n;
}

export function compareCase(expected, actual) {
  if (actual === null || typeof actual !== 'object') {
    return { validJson: false, fields: {}, fullMatch: false };
  }

  const fields = {
    znacka: normalizeBrand(expected.znacka) === normalizeBrand(actual.znacka),
    model: normalizeModel(expected.model) === normalizeModel(actual.model),
    rok: normalizeNumber(expected.rok) === normalizeNumber(actual.rok),
    najezd_km: normalizeNumber(expected.najezd_km) === normalizeNumber(actual.najezd_km),
    cena: normalizeNumber(expected.cena) === normalizeNumber(actual.cena),
  };

  const fullMatch = Object.values(fields).every(Boolean);
  return { validJson: true, fields, fullMatch };
}
