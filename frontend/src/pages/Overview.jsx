import { Activity, ArrowDownLeft, ArrowRight, ArrowUpRight, CheckCircle2, IndianRupee, Layers, Package, Plus, ShieldCheck, TriangleAlert } from 'lucide-react';
import { money, number, shortDate } from '../lib/format.js';
import { Button, EmptyState, ErrorNotice, LoadingState, ProductAvatar, ProductTable } from '../components/UI.jsx';

export function ActivityList({ movements, onHistory, openingProductId, compact = false }) {
  return <div className={`activity-list ${compact ? 'activity-compact' : ''}`}>{movements.map((movement) => <div className="activity-item" key={movement.id}>
    <span className={`activity-symbol symbol-${movement.movement_type.toLowerCase()}`}>{movement.movement_type === 'IN' ? <ArrowDownLeft size={18} /> : <ArrowUpRight size={18} />}</span>
    <div className="activity-description"><strong>{movement.product_name}</strong><p><span className={movement.movement_type === 'IN' ? 'positive' : ''}>{movement.movement_type === 'IN' ? 'Received' : 'Issued'} {number(movement.quantity)} {movement.quantity === 1 ? 'unit' : 'units'}</span>{!compact && <span className="activity-sku"> · {movement.product_sku}</span>}</p>{!compact && movement.note && <p className="activity-note">{movement.note}</p>}</div>
    <div className="activity-trailing"><time dateTime={movement.created_at}>{shortDate(movement.created_at)}</time>{!compact && <Button className="button-small" onClick={() => onHistory(movement)} busy={openingProductId === movement.product_id}>View history</Button>}</div>
  </div>)}</div>;
}

export default function Overview({ dashboard, snapshot, onRetry, onAction, onAdd, onNavigate }) {
  const data = dashboard.data;
  if (!data) return <><ErrorNotice error={dashboard.error} onRetry={onRetry} title="We couldn’t load your overview" />{dashboard.loading && <LoadingState />}</>;
  const healthyCount = data.total_products - data.low_stock_count;
  const healthyPercent = data.total_products ? Math.round(healthyCount / data.total_products * 100) : null;
  const cards = [
    { title: 'Total products', value: number(data.total_products), caption: 'In your product catalog', icon: Package, color: 'sage' },
    { title: 'Units on hand', value: number(data.total_units), caption: 'Across your inventory', icon: Layers, color: 'blue' },
    { title: 'Inventory value', value: money(data.inventory_value), caption: 'At current unit prices', icon: IndianRupee, color: 'sand' },
    { title: 'Low-stock products', value: number(data.low_stock_count), caption: 'At or below reorder level', icon: TriangleAlert, color: 'orange' },
  ];
  return <>
    <ErrorNotice error={dashboard.error} onRetry={onRetry} title="Your overview may be out of date" />
    <section className="stats-grid" aria-label="Inventory summary">{cards.map(({ title, value, caption, icon: Icon, color }) => <article className="stat-card" key={title}><div className="stat-card-top"><span>{title}</span><span className={`stat-icon tint-${color}`}><Icon size={18} strokeWidth={1.8} /></span></div><strong className={`stat-value ${title === 'Inventory value' ? 'stat-money' : ''}`}>{value}</strong><p>{caption}</p></article>)}</section>
    <div className="overview-grid">
      <section className="panel snapshot-panel"><header className="panel-header"><div><h2>Product snapshot <span className="count-chip">{number(data.total_products)}</span></h2><p>A quick look at what’s on your shelves.</p></div><button className="text-button" onClick={() => onNavigate('products')}>View all products <ArrowRight size={15} /></button></header>
        <ErrorNotice error={snapshot.error} onRetry={onRetry} />
        {snapshot.loading && !snapshot.data ? <LoadingState /> : snapshot.data?.items.length ? <ProductTable products={snapshot.data.items} loading={snapshot.loading} compact onAction={onAction} /> : !snapshot.error && <EmptyState title="Your shelves start here" description="Add your first product, then receive its opening stock." compact><Button variant="primary" icon={Plus} onClick={onAdd}>Add first product</Button></EmptyState>}
        {snapshot.data?.items.length > 0 && <div className="panel-bottom"><span><ShieldCheck size={14} />Every stock movement is recorded.</span><button className="text-button" onClick={() => onNavigate('activity')}>View activity <ArrowRight size={14} /></button></div>}
      </section>
      <section className="panel health-panel"><header className="panel-header"><div><h2>Stock health</h2><p>Keep your essentials covered.</p></div><ShieldCheck size={19} className="muted" /></header><div className="stock-health-body"><div className="health-ring" style={{ '--healthy': `${healthyPercent ?? 0}%` }} role="img" aria-label={healthyPercent === null ? 'No inventory yet' : `${healthyPercent}% of products are above their reorder level`}><div><strong>{healthyPercent === null ? '—' : `${healthyPercent}%`}</strong><span>healthy stock</span></div></div><div className="health-legend"><div><span><i className="legend-dot dot-green" />Above reorder level</span><strong>{number(healthyCount)}</strong></div><div><span><i className="legend-dot dot-orange" />Needs attention</span><strong>{number(data.low_stock_count)}</strong></div></div></div><div className={`health-note ${data.low_stock_count ? 'health-note-warning' : ''}`}>{data.low_stock_count ? <TriangleAlert size={17} /> : <CheckCircle2 size={17} />}<p>{data.total_products === 0 ? 'Your stock health will appear as you add products.' : data.low_stock_count ? `${number(data.low_stock_count)} ${data.low_stock_count === 1 ? 'product is' : 'products are'} ready for a restock.` : 'Looking good. Your products are above their reorder levels.'}</p></div></section>
      <section className="panel attention-panel"><header className="panel-header"><div><h2>Needs attention <span className="count-chip count-warning">{number(data.low_stock_count)}</span></h2><p>Products at or below their reorder level.</p></div>{data.low_stock_count > 0 && <button className="text-button" onClick={() => onNavigate('products', 'low')}>View all <ArrowRight size={15} /></button>}</header>
        {data.low_stock_products.length ? <div className="attention-list">{data.low_stock_products.slice(0, 5).map((product) => <div className="attention-item" key={product.id}><ProductAvatar product={product} small /><div><strong>{product.name}</strong><span>{number(product.quantity)} left · Reorder at {number(product.reorder_level)}</span></div><button className="restock-button" aria-label={`Restock ${product.name}`} onClick={() => onAction('receive', product)}><Plus size={15} />Restock</button></div>)}</div> : <EmptyState icon={CheckCircle2} title={data.total_products ? 'All stocked up' : 'No alerts yet'} description={data.total_products ? 'Nothing needs restocking right now. We’ll keep an eye on it.' : 'Low-stock products will show up here as your catalog grows.'} compact />}
      </section>
      <section className="panel recent-panel"><header className="panel-header"><div><h2>Recent activity</h2><p>The latest ins and outs.</p></div><button className="text-button" onClick={() => onNavigate('activity')}>View all <ArrowRight size={15} /></button></header>{data.recent_movements.length ? <ActivityList movements={data.recent_movements.slice(0, 4)} compact /> : <EmptyState icon={Activity} title="A fresh start" description="Your first stock movement will appear here." compact />}</section>
    </div>
  </>;
}
