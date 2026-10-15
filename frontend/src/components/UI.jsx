import { useEffect, useId, useRef } from 'react';
import { AlertTriangle, ArrowDownLeft, ArrowRight, ArrowUpRight, CheckCircle2, ChevronLeft, ChevronRight, History, LoaderCircle, Package, Pencil, RefreshCw, Trash2, X } from 'lucide-react';
import { initials, money, number, stockState } from '../lib/format.js';

export function Button({ children, icon: Icon, variant = 'secondary', busy = false, className = '', type = 'button', ...props }) {
  return <button type={type} className={`button button-${variant} ${className}`} {...props} disabled={props.disabled || busy}>
    {busy ? <LoaderCircle size={16} className="spin" aria-hidden="true" /> : Icon && <Icon size={16} aria-hidden="true" />}{children}
  </button>;
}

export function StockBadge({ product }) {
  const state = stockState(product);
  return <span className={`stock-badge stock-${state.key}`}><span className="status-dot" />{state.label}</span>;
}

export function ProductAvatar({ product, small = false }) {
  const palette = ['sage', 'sand', 'blue', 'rose'][product.id % 4];
  return <span aria-hidden="true" className={`product-avatar avatar-${palette} ${small ? 'avatar-small' : ''}`}>{initials(product.name)}</span>;
}

export function EmptyState({ title, description, children, icon: Icon = Package, compact = false }) {
  return <div className={`empty-state ${compact ? 'empty-compact' : ''}`}><span className="empty-icon"><Icon size={25} strokeWidth={1.5} /></span><h3>{title}</h3><p>{description}</p>{children}</div>;
}

export function ErrorNotice({ error, onRetry, title = 'Something needs another try' }) {
  if (!error) return null;
  return <div className="error-notice" role="alert"><AlertTriangle size={19} aria-hidden="true" /><div><strong>{title}</strong><p>{error.message || String(error)}</p></div>{onRetry && <Button icon={RefreshCw} onClick={onRetry}>Try again</Button>}</div>;
}

export function Pagination({ page, limit, total, onPage, loading, noun = 'products' }) {
  if (!total) return null;
  const start = page * limit + 1;
  return <div className="pagination"><p>Showing <strong>{number(start)}–{number(Math.min((page + 1) * limit, total))}</strong> of <strong>{number(total)}</strong> {noun}</p><div><button className="pagination-button" aria-label={`Previous ${noun} page`} disabled={loading || page === 0} onClick={() => onPage(page - 1)}><ChevronLeft size={17} /></button><span className="page-current" aria-label={`Page ${page + 1}`}>{page + 1}</span><button className="pagination-button" aria-label={`Next ${noun} page`} disabled={loading || (page + 1) * limit >= total} onClick={() => onPage(page + 1)}><ChevronRight size={17} /></button></div></div>;
}

export function Modal({ title, subtitle, onClose, busy = false, children, footer, className = '' }) {
  const reference = useRef(null);
  const headingId = useId();
  useEffect(() => {
    const element = reference.current;
    element.showModal();
    return () => element.close();
  }, []);
  return <dialog ref={reference} className={`modal ${className}`} aria-labelledby={headingId}
    onCancel={(event) => { event.preventDefault(); if (!busy) onClose(); }}
    onClick={(event) => { if (event.target === event.currentTarget && !busy) { const rect = event.currentTarget.getBoundingClientRect(); if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) onClose(); } }}>
    <header className="modal-header"><div><h2 id={headingId}>{title}</h2>{subtitle && <p>{subtitle}</p>}</div><button className="icon-button" aria-label="Close dialog" onClick={onClose} disabled={busy}><X size={21} /></button></header>
    <div className="modal-body">{children}</div>{footer && <footer className="modal-footer">{footer}</footer>}
  </dialog>;
}

export function ProductTable({ products, loading, compact = false, onAction }) {
  return <div className={`table-scroll ${compact ? 'table-compact' : ''}`} aria-busy={loading}>
    <table className="product-table"><thead><tr><th scope="col">Product</th>{!compact && <th scope="col">Category</th>}<th scope="col" className="number-cell">On hand</th>{!compact && <><th scope="col" className="number-cell">Reorder at</th><th scope="col" className="number-cell">Unit price</th></>}<th scope="col">Status</th><th scope="col"><span className="sr-only">Actions</span></th></tr></thead>
      <tbody>{products.map((product) => <tr key={product.id}>
        <td className="product-cell"><ProductAvatar product={product} /><div><button className="product-name" onClick={() => onAction('history', product)}>{product.name}</button><span className="sku">{product.sku}</span></div></td>
        {!compact && <td data-label="Category"><span className="category-text">{product.category}</span></td>}
        <td data-label="On hand" className="number-cell"><strong className="quantity-value">{number(product.quantity)}</strong>{compact && <span className="quantity-unit"> units</span>}</td>
        {!compact && <><td data-label="Reorder at" className="number-cell muted">{number(product.reorder_level)}</td><td data-label="Unit price" className="number-cell price-cell">{money(product.unit_price)}</td></>}
        <td data-label="Status"><StockBadge product={product} /></td>
        <td className="actions-cell">{compact ? <button className="icon-button" aria-label={`View history for ${product.name}`} onClick={() => onAction('history', product)}><ArrowRight size={18} /></button> : <div className="row-actions">
          {[['receive', ArrowDownLeft, 'Receive stock for'], ['issue', ArrowUpRight, 'Issue stock for'], ['history', History, 'View history for'], ['edit', Pencil, 'Edit'], ['delete', Trash2, 'Delete']].map(([action, Icon, label]) => <button key={action} className={`icon-button action-${action}`} title={`${label} ${product.name}`} aria-label={`${label} ${product.name}`} onClick={() => onAction(action, product)}><Icon size={16} /></button>)}
        </div>}</td>
      </tr>)}</tbody>
    </table>
  </div>;
}

export function LoadingState({ text = 'Loading your inventory…' }) {
  return <div className="loading-state" role="status"><LoaderCircle className="spin" size={21} /><span>{text}</span></div>;
}

export function Toast({ message, onDismiss }) {
  useEffect(() => { const timer = setTimeout(onDismiss, 5500); return () => clearTimeout(timer); }, [message, onDismiss]);
  return <div className="toast" role="status"><CheckCircle2 size={20} /><span>{message}</span><button aria-label="Dismiss notification" onClick={onDismiss}><X size={16} /></button></div>;
}
