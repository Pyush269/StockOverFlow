import { cloneElement, useCallback, useState } from 'react';
import { AlertTriangle, ArrowDownLeft, ArrowRight, ArrowUpRight, Check, History, Package, Plus, Search, ShieldCheck, Trash2 } from 'lucide-react';
import { api } from '../services/api.js';
import { dateTime, integerInput, MAX_QUANTITY, number, validateProduct } from '../lib/format.js';
import { useDebounced, useResource } from '../hooks/useResource.js';
import { Button, EmptyState, ErrorNotice, LoadingState, Modal, Pagination, ProductAvatar, StockBadge } from './UI.jsx';

function Field({ id, label, error, hint, children, className = '' }) {
  return <div className={`field ${className}`}><label htmlFor={id}>{label}</label>{cloneElement(children, { id, 'aria-invalid': Boolean(error), 'aria-describedby': error ? `${id}-error` : hint ? `${id}-hint` : undefined })}{error ? <p className="field-error" id={`${id}-error`}>{error}</p> : hint && <p className="field-hint" id={`${id}-hint`}>{hint}</p>}</div>;
}

export function ProductDialog({ product, categories, onClose, onSuccess }) {
  const [form, setForm] = useState({ sku: product?.sku || '', name: product?.name || '', category: product?.category || '', unit_price: product?.unit_price || '0.00', reorder_level: String(product?.reorder_level ?? 5), description: product?.description || '' });
  const [errors, setErrors] = useState({});
  const [error, setError] = useState(null);
  const [pending, setPending] = useState(false);
  const update = (name) => (event) => { setForm((previous) => ({ ...previous, [name]: event.target.value })); setErrors((previous) => ({ ...previous, [name]: undefined })); };

  async function submit(event) {
    event.preventDefault();
    if (pending) return;
    const issues = validateProduct(form);
    setErrors(issues);
    if (Object.keys(issues).length) return;
    setError(null); setPending(true);
    const payload = { ...form, sku: form.sku.trim().toUpperCase(), name: form.name.trim(), category: form.category.trim(), description: form.description.trim(), reorder_level: Number(form.reorder_level) };
    try {
      const saved = product ? await api.updateProduct(product.id, payload) : await api.createProduct(payload);
      onSuccess(saved, product ? 'Product details updated.' : 'Product added. You can now receive its opening stock.');
    } catch (failure) {
      setError(failure);
      const fields = Object.fromEntries((failure.details || []).map((detail) => [detail.field.split('.').at(-1), detail.message]));
      if (failure.code === 'duplicate_sku') fields.sku = 'This SKU is already in your catalog. Choose a unique SKU.';
      setErrors(fields);
    } finally { setPending(false); }
  }

  return <Modal title={product ? 'Edit product' : 'Add a product'} subtitle={product ? 'Update the details in your catalog.' : 'Give your next product a place in your inventory.'} onClose={onClose} busy={pending}
    footer={<><Button onClick={onClose} disabled={pending}>Cancel</Button><Button variant="primary" icon={product ? Check : Plus} type="submit" form="product-form" busy={pending}>{pending ? 'Saving product…' : product ? 'Save changes' : 'Add product'}</Button></>}>
    <ErrorNotice error={error} title="We couldn’t save this product" />
    <form id="product-form" onSubmit={submit}><fieldset disabled={pending} className="form-grid">
      <Field id="product-name" label="Product name" error={errors.name} className="full-width"><input autoFocus value={form.name} onChange={update('name')} maxLength={200} placeholder="e.g. USB-C Hub" required /></Field>
      <Field id="product-sku" label="SKU" error={errors.sku} hint="A unique identifier for this product."><input value={form.sku} onChange={update('sku')} maxLength={64} placeholder="e.g. HUB-001" required autoCapitalize="characters" spellCheck="false" /></Field>
      <Field id="product-category" label="Category" error={errors.category}><input value={form.category} onChange={update('category')} list="category-suggestions" maxLength={80} placeholder="e.g. Electronics" required /></Field>
      <datalist id="category-suggestions">{categories.map((category) => <option key={category} value={category} />)}</datalist>
      <Field id="product-price" label="Unit price (₹)" error={errors.unit_price}><input type="text" inputMode="decimal" value={form.unit_price} onChange={update('unit_price')} placeholder="0.00" required /></Field>
      <Field id="product-reorder" label="Reorder level" error={errors.reorder_level} hint="We’ll flag stock at or below this level."><input type="number" min="0" max={MAX_QUANTITY} step="1" value={form.reorder_level} onChange={update('reorder_level')} required /></Field>
      <Field id="product-description" label="Description (optional)" error={errors.description} className="full-width"><textarea rows={3} value={form.description} onChange={update('description')} maxLength={5000} placeholder="Add a few details about this product…" /></Field>
    </fieldset></form>
    {!product && <div className="info-note"><Package size={17} /><span>New products start with zero stock. Use <strong>Receive stock</strong> to record the opening quantity.</span></div>}
  </Modal>;
}

export function ProductPickerDialog({ onClose, onPick }) {
  const [search, setSearch] = useState('');
  const query = useDebounced(search);
  const [revision, setRevision] = useState(0);
  const loader = useCallback((signal) => api.products({ q: query.trim(), limit: 8 }, signal), [query]);
  const result = useResource(loader, revision);
  return <Modal title="Record a stock movement" subtitle="Choose the product you want to receive or issue." onClose={onClose} className="picker-modal">
    <div className="search-field picker-search"><Search size={18} /><input autoFocus aria-label="Find a product" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search by product name or SKU…" maxLength={100} /></div>
    <ErrorNotice error={result.error} onRetry={() => setRevision((value) => value + 1)} />
    {result.loading ? <LoadingState text="Finding products…" /> : result.data?.items.length ? <div className="picker-list">{result.data.items.map((product) => <button className="picker-product" key={product.id} onClick={() => onPick(product)}><ProductAvatar product={product} /><span><strong>{product.name}</strong><small>{product.sku} · {number(product.quantity)} on hand</small></span><ArrowRight size={18} /></button>)}{result.data.total > 8 && <p className="picker-hint">Search by name or SKU to find more products.</p>}</div> : !result.error && <EmptyState compact title="No products found" description={search ? 'Try a different name or SKU.' : 'Add a product to your catalog before recording stock.'} />}
  </Modal>;
}

export function MovementDialog({ product, intent = 'IN', onClose, onSuccess }) {
  const [type, setType] = useState(intent);
  const [quantity, setQuantity] = useState('');
  const [note, setNote] = useState('');
  const [error, setError] = useState(null);
  const [pending, setPending] = useState(false);
  const [revision, setRevision] = useState(0);
  const loader = useCallback((signal) => api.product(product.id, signal), [product.id]);
  const latest = useResource(loader, revision);
  const current = latest.data || product;
  const units = integerInput(quantity, 1);
  const projected = units === null ? current.quantity : current.quantity + (type === 'IN' ? units : -units);
  const notEnough = units !== null && projected < 0;
  const tooMany = units !== null && projected > MAX_QUANTITY;

  async function submit(event) {
    event.preventDefault();
    if (pending || units === null || notEnough || tooMany || latest.loading || latest.error) return;
    setPending(true); setError(null);
    try {
      const result = await api.createMovement(product.id, { movement_type: type, quantity: units, note: note.trim() });
      onSuccess(result.product, `${number(units)} ${units === 1 ? 'unit' : 'units'} ${type === 'IN' ? 'received into' : 'issued from'} ${result.product.name}.`);
    } catch (failure) { setError(failure); setRevision((value) => value + 1); }
    finally { setPending(false); }
  }

  return <Modal title="Record stock movement" subtitle="Keep your inventory and its history in step." onClose={onClose} busy={pending}
    footer={<><Button onClick={onClose} disabled={pending}>Cancel</Button><Button type="submit" form="movement-form" variant="primary" icon={type === 'IN' ? ArrowDownLeft : ArrowUpRight} busy={pending} disabled={units === null || notEnough || tooMany || latest.loading || Boolean(latest.error)}>{pending ? 'Saving movement…' : type === 'IN' ? 'Confirm receipt' : 'Confirm issue'}</Button></>}>
    <div className="selected-product"><ProductAvatar product={current} /><div><strong>{current.name}</strong><span>{current.sku}</span></div><StockBadge product={current} /></div>
    <ErrorNotice error={latest.error} onRetry={() => setRevision((value) => value + 1)} title="Couldn’t check current stock" />
    <ErrorNotice error={error} title="Movement wasn’t saved" />
    <form id="movement-form" onSubmit={submit}><fieldset disabled={pending}>
      <div className="movement-toggle" role="group" aria-label="Movement type"><button type="button" className={type === 'IN' ? 'selected' : ''} aria-pressed={type === 'IN'} onClick={() => { setType('IN'); setError(null); }}><ArrowDownLeft size={17} />Receive stock</button><button type="button" className={type === 'OUT' ? 'selected' : ''} aria-pressed={type === 'OUT'} onClick={() => { setType('OUT'); setError(null); }}><ArrowUpRight size={17} />Issue stock</button></div>
      <Field id="movement-quantity" label="Quantity" hint="Enter a positive whole number."><input autoFocus type="number" min="1" max={MAX_QUANTITY} step="1" value={quantity} onChange={(event) => setQuantity(event.target.value)} placeholder="e.g. 10" required /></Field>
      <div className={`quantity-preview ${notEnough || tooMany ? 'quantity-invalid' : ''}`}><div><span>Current stock</span><strong>{number(current.quantity)} <small>units</small></strong></div><ArrowRight size={20} /><div><span>After this movement</span><strong>{number(projected)} <small>units</small></strong></div></div>
      {notEnough && <p className="stock-warning" role="alert"><AlertTriangle size={16} />Only {number(current.quantity)} units are available. Enter {number(current.quantity)} or fewer.</p>}
      {tooMany && <p className="stock-warning" role="alert">This receipt exceeds the supported stock limit.</p>}
      <Field id="movement-note" label="Note (optional)"><textarea rows={3} value={note} onChange={(event) => setNote(event.target.value)} placeholder={type === 'IN' ? 'e.g. Delivery received from supplier' : 'e.g. Customer order #1042'} maxLength={500} /></Field>
    </fieldset></form>
    <div className="info-note"><ShieldCheck size={17} /><span>Every movement is saved to your ledger. Stock history stays read-only.</span></div>
  </Modal>;
}

export function HistoryDialog({ product, onClose }) {
  const [page, setPage] = useState(0);
  const [revision, setRevision] = useState(0);
  const loader = useCallback(async (signal) => {
    const [history, current] = await Promise.all([api.movements(product.id, { limit: 8, offset: page * 8 }, signal), api.product(product.id, signal)]);
    return { ...history, product: current };
  }, [product.id, page]);
  const result = useResource(loader, revision);
  const current = result.data?.product || product;
  return <Modal title="Stock history" subtitle="A clear record of what came in and what went out." onClose={onClose} className="history-modal" footer={<><span className="history-footer-note"><ShieldCheck size={15} />Read-only movement ledger</span><Button onClick={onClose}>Done</Button></>}>
    <div className="selected-product"><ProductAvatar product={current} /><div><strong>{current.name}</strong><span>{current.sku} · {number(current.quantity)} units on hand</span></div><StockBadge product={current} /></div>
    <ErrorNotice error={result.error} onRetry={() => setRevision((value) => value + 1)} />
    {result.loading && !result.data ? <LoadingState text="Loading stock history…" /> : result.data?.items.length ? <><div className="table-scroll"><table className="history-table"><thead><tr><th>Movement</th><th>Quantity</th><th>Note</th><th>Date · IST</th></tr></thead><tbody>{result.data.items.map((movement) => <tr key={movement.id}><td><span className={`movement-label movement-${movement.movement_type.toLowerCase()}`}>{movement.movement_type === 'IN' ? <ArrowDownLeft size={15} /> : <ArrowUpRight size={15} />}{movement.movement_type === 'IN' ? 'Received' : 'Issued'}</span></td><td><strong className={movement.movement_type === 'IN' ? 'positive' : 'muted'}>{movement.movement_type === 'IN' ? '+' : '−'}{number(movement.quantity)}</strong></td><td>{movement.note || <span className="muted">No note</span>}</td><td className="history-date">{dateTime(movement.created_at)}</td></tr>)}</tbody></table></div><Pagination page={page} limit={8} total={result.data.total} onPage={setPage} loading={result.loading} noun="movements" /></> : !result.error && <EmptyState icon={History} title="No movements yet" description="Receive the opening stock for this product to start its history." />}
  </Modal>;
}

export function DeleteDialog({ product, onClose, onSuccess }) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState(null);
  async function remove() {
    setPending(true); setError(null);
    try { await api.deleteProduct(product.id); onSuccess(product, `${product.name} was deleted from your catalog.`); }
    catch (failure) { setError(failure); }
    finally { setPending(false); }
  }
  return <Modal title="Delete this product?" subtitle="Check the product below before removing it." onClose={onClose} busy={pending} className="delete-modal" footer={<><Button onClick={onClose} disabled={pending}>Keep product</Button><Button variant="danger" icon={Trash2} onClick={remove} busy={pending}>{pending ? 'Deleting…' : 'Delete product'}</Button></>}>
    <div className="selected-product"><ProductAvatar product={product} /><div><strong>{product.name}</strong><span>{product.sku}</span></div></div><p className="delete-description">This removes the product from your catalog. Products with any stock movement history are protected and cannot be deleted.</p><ErrorNotice error={error} title="This product couldn’t be deleted" />
  </Modal>;
}
