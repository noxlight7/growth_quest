export const toOptionalInt = (value) => {
  if (value === '' || value === null || value === undefined) return null;
  const parsed = Number(value);
  return Number.isNaN(parsed) ? null : parsed;
};

export const toInt = (value, fallback = 0) => {
  const parsed = Number(value);
  return Number.isNaN(parsed) ? fallback : parsed;
};

export const serializeTags = (value) =>
  value
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean);

export const formatTags = (tags) => (tags && tags.length ? tags.join(', ') : '');

export const sortByTitle = (items, locale) =>
  [...items].sort((a, b) => (a.title || '').localeCompare(b.title || '', locale));
