export const MAX_QUANTITY = 2147483647;
const currencyFormatter = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', minimumFractionDigits: 2, maximumFractionDigits: 2 });
const integerFormatter = new Intl.NumberFormat('en-IN');

// Intl accepts decimal strings directly; don't lose integer precision by
// converting PostgreSQL's exact monetary aggregates to Number first.
export const money = (value) => currencyFormatter.format(value ?? 0);
export const number = (value) => integerFormatter.format(Number(value || 0));
export const dateTime = (value) => new Intl.DateTimeFormat('en-IN', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Kolkata' }).format(new Date(value));
export const shortDate = (value) => new Intl.DateTimeFormat('en-IN', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Kolkata' }).format(new Date(value));

export function stockState(product) {
  if (product.quantity === 0) return { key: 'out', label: 'Out of stock' };
  if (product.quantity <= product.reorder_level) return { key: 'low', label: 'Low stock' };
  return { key: 'healthy', label: 'In stock' };
}

export function initials(name) {
  return name.trim().split(/\s+/).slice(0, 2).map((part) => part[0]).join('').toUpperCase() || 'P';
}

export function integerInput(value, minimum = 0) {
  if (!/^\d+$/.test(String(value))) return null;
  const parsed = Number(value);
  return Number.isSafeInteger(parsed) && parsed >= minimum && parsed <= MAX_QUANTITY ? parsed : null;
}

export function validateProduct(form) {
  const errors = {};
  if (!/^[A-Z0-9][A-Z0-9._-]{0,63}$/.test(form.sku.trim().toUpperCase())) errors.sku = 'Use letters, numbers, dots, hyphens, or underscores (up to 64 characters).';
  if (!form.name.trim()) errors.name = 'Enter a product name.';
  if (!form.category.trim()) errors.category = 'Enter a category.';
  if (!/^(?:0|[1-9]\d{0,9})(?:\.\d{1,2})?$/.test(String(form.unit_price))) errors.unit_price = 'Enter a nonnegative price with up to two decimal places.';
  if (integerInput(form.reorder_level) === null) errors.reorder_level = 'Enter a whole number between 0 and 2,147,483,647.';
  return errors;
}
