import { useCallback, useEffect, useRef, useState } from 'react';
import { Activity as ActivityIcon, ArrowDownLeft, ArrowRight, Box, CalendarDays, ChevronRight, LayoutDashboard, Menu, Package, Plus, RefreshCw, Search, X } from 'lucide-react';
import { api } from './services/api.js';
import { number } from './lib/format.js';
import { useDebounced, useResource } from './hooks/useResource.js';
import { Button, ErrorNotice, Toast } from './components/UI.jsx';
import { DeleteDialog, HistoryDialog, MovementDialog, ProductDialog, ProductPickerDialog } from './components/InventoryDialogs.jsx';
import Overview from './pages/Overview.jsx';
import Products from './pages/Products.jsx';
import Activity from './pages/Activity.jsx';

const navigation = [
  { key: 'overview', label: 'Overview', icon: LayoutDashboard },
  { key: 'products', label: 'Products', icon: Package },
  { key: 'activity', label: 'Stock activity', icon: ActivityIcon },
];
const pageDetails = {
  overview: { title: 'Inventory overview', description: 'A little clarity for everything you keep in stock.' },
  products: { title: 'Your products', description: 'Manage your catalog, track quantities, and keep things moving.' },
  activity: { title: 'Stock activity', description: 'Every receipt. Every issue. Always accounted for.' },
};
const currentView = () => navigation.some((item) => item.key === location.hash.slice(2)) ? location.hash.slice(2) : 'overview';

export default function App() {
  const [view, setView] = useState(currentView);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('');
  const [stockFilter, setStockFilter] = useState('');
  const [page, setPage] = useState(0);
  const [revision, setRevision] = useState(0);
  const [modal, setModal] = useState(null);
  const [toast, setToast] = useState(null);
  const [actionError, setActionError] = useState(null);
  const [openingProductId, setOpeningProductId] = useState(null);
  const searchRef = useRef(null);
  const query = useDebounced(search);
  const dashboardLoader = useCallback((signal) => api.dashboard(signal), []);
  const snapshotLoader = useCallback((signal) => api.products({ limit: 5 }, signal), []);
  const categoriesLoader = useCallback((signal) => api.categories(signal), []);
  const catalogLoader = useCallback((signal) => api.products({ q: query.trim(), category, stock_status: stockFilter, limit: 10, offset: page * 10 }, signal), [query, category, stockFilter, page]);
  const dashboard = useResource(dashboardLoader, revision);
  const snapshot = useResource(snapshotLoader, revision);
  const categories = useResource(categoriesLoader, revision);
  const catalog = useResource(catalogLoader, revision);
  const refresh = useCallback(() => setRevision((value) => value + 1), []);
  const closeModal = useCallback(() => setModal(null), []);
  const dismissToast = useCallback(() => setToast(null), []);

  useEffect(() => { const update = () => { setView(currentView()); setSidebarOpen(false); }; addEventListener('hashchange', update); return () => removeEventListener('hashchange', update); }, []);
  useEffect(() => { document.title = `${pageDetails[view].title} · StockFlow`; }, [view]);
  useEffect(() => { if (catalog.data && !catalog.loading && page > 0 && page * 10 >= catalog.data.total) setPage(Math.max(0, Math.ceil(catalog.data.total / 10) - 1)); }, [catalog.data, catalog.loading, page]);
  useEffect(() => { if (!sidebarOpen) return; const close = (event) => { if (event.key === 'Escape') setSidebarOpen(false); }; addEventListener('keydown', close); return () => removeEventListener('keydown', close); }, [sidebarOpen]);

  const navigate = useCallback((next, status) => {
    if (status !== undefined) { setSearch(''); setCategory(''); setStockFilter(status); setPage(0); }
    setView(next); setSidebarOpen(false); location.hash = `/${next}`;
  }, []);

  function action(type, product) {
    setActionError(null);
    if (type === 'receive' || type === 'issue') setModal({ type: 'movement', product, intent: type === 'receive' ? 'IN' : 'OUT' });
    else setModal({ type, product });
  }

  function saved(product, message) {
    setModal(null); setToast({ id: Date.now(), message }); refresh();
  }

  async function historyForMovement(movement) {
    if (openingProductId !== null) return;
    setOpeningProductId(movement.product_id); setActionError(null);
    try { action('history', await api.product(movement.product_id)); }
    catch (error) { setActionError({ error, movement }); }
    finally { setOpeningProductId(null); }
  }

  const showAdd = () => setModal({ type: 'edit', product: null });
  const showPicker = () => setModal({ type: 'picker' });
  const clearFilters = () => { setSearch(''); setCategory(''); setStockFilter(''); setPage(0); };
  const connected = Boolean(dashboard.data && !dashboard.error);
  const isRefreshing = dashboard.loading || catalog.loading;

  return <>
    <a className="skip-link" href="#main-content" onClick={(event) => { event.preventDefault(); const main = document.getElementById('main-content'); main.setAttribute('tabindex', '-1'); main.focus(); }}>Skip to content</a>
    {sidebarOpen && <button className="sidebar-backdrop" aria-label="Close navigation" onClick={() => setSidebarOpen(false)} />}
    <aside className={`sidebar ${sidebarOpen ? 'sidebar-open' : ''}`} id="workspace-navigation">
      <a className="brand" href="#/overview" onClick={() => setSidebarOpen(false)}><span className="brand-mark"><Box size={25} strokeWidth={1.6} /></span><span>Stock<span className="brand-light">Flow</span><small>INVENTORY, IN ORDER.</small></span></a>
      <div className="workspace-label">WORKSPACE</div>
      <nav aria-label="Main navigation">{navigation.map(({ key, label, icon: Icon }) => <a key={key} className={`nav-item ${view === key ? 'nav-active' : ''}`} href={`#/${key}`} aria-current={view === key ? 'page' : undefined} onClick={() => setSidebarOpen(false)}><Icon size={19} strokeWidth={1.7} /><span>{label}</span>{key === 'products' && dashboard.data && <span className="nav-count">{number(dashboard.data.total_products)}</span>}</a>)}</nav>
      <div className="sidebar-bottom"><div className="sidebar-note"><span className="note-mark"><Package size={22} strokeWidth={1.5} /></span><h3>A place for every product.</h3><p>Keep stock moving and the details in order.</p><button onClick={showPicker}>Record a movement <ArrowRight size={14} /></button></div><div className="workspace-footer"><span className="workspace-avatar">SF</span><div><strong>StockFlow workspace</strong><span>Inventory management</span></div><span className="workspace-online" title={connected ? 'Inventory connected' : 'Checking inventory connection'} /></div></div>
    </aside>
    <div className="app-shell"><header className="topbar"><div className="topbar-left"><button className="icon-button mobile-menu" aria-label="Open navigation" aria-expanded={sidebarOpen} aria-controls="workspace-navigation" onClick={() => setSidebarOpen(true)}><Menu size={21} /></button><span className="breadcrumb-root">Workspace</span><ChevronRight size={14} className="muted" /><span className="breadcrumb-current">{navigation.find((item) => item.key === view).label}</span></div><div className="topbar-right"><button className="topbar-search" aria-label="Find a product" onClick={() => { navigate('products'); setTimeout(() => searchRef.current?.focus(), 0); }}><Search size={17} /><span>Find a product</span></button><span className={`connection-pill ${connected ? '' : 'connection-pending'}`}><span className="status-dot" />{connected ? 'Inventory connected' : dashboard.error ? 'Connection unavailable' : 'Connecting'}</span></div></header>
      <main className="main-content" id="main-content"><div className="page-eyebrow"><span><span className="eyebrow-line" />YOUR INVENTORY WORKSPACE</span><span className="today"><CalendarDays size={14} />{new Intl.DateTimeFormat('en-IN', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'Asia/Kolkata' }).format(new Date())}</span></div><div className="page-heading"><div><h1>{pageDetails[view].title}</h1><p>{pageDetails[view].description}</p></div><div className="page-actions"><button className="icon-button refresh-button" aria-label="Refresh inventory" title="Refresh inventory" onClick={refresh} disabled={isRefreshing}><RefreshCw size={17} className={isRefreshing ? 'spin' : ''} /></button><Button icon={ArrowDownLeft} onClick={showPicker}>Record movement</Button><Button variant="primary" icon={Plus} onClick={showAdd}>Add product</Button></div></div>
        <ErrorNotice error={actionError?.error} title="We couldn’t open this product" onRetry={() => historyForMovement(actionError.movement)} />
        {view === 'overview' && <Overview dashboard={dashboard} snapshot={snapshot} onRetry={refresh} onAction={action} onAdd={showAdd} onNavigate={navigate} />}
        {view === 'products' && <Products result={catalog} categories={categories.data || []} categoriesError={categories.error} search={search} onSearch={(value) => { setSearch(value); setPage(0); }} category={category} onCategory={(value) => { setCategory(value); setPage(0); }} stockFilter={stockFilter} onStockFilter={(value) => { setStockFilter(value); setPage(0); }} page={page} onPage={setPage} onClear={clearFilters} onRetry={refresh} onAdd={showAdd} onAction={action} searchRef={searchRef} />}
        {view === 'activity' && <Activity dashboard={dashboard} onRetry={refresh} onRecord={showPicker} onNavigate={navigate} onHistory={historyForMovement} openingProductId={openingProductId} />}
        <footer className="page-footer"><span>StockFlow <span>·</span> A clearer view of your inventory.</span><span>Amounts in INR <span>·</span> Times in IST</span></footer>
      </main>
    </div>
    {modal?.type === 'edit' && <ProductDialog product={modal.product} categories={categories.data || []} onClose={closeModal} onSuccess={saved} />}
    {modal?.type === 'picker' && <ProductPickerDialog onClose={closeModal} onPick={(product) => setModal({ type: 'movement', product, intent: 'IN' })} />}
    {modal?.type === 'movement' && <MovementDialog product={modal.product} intent={modal.intent} onClose={closeModal} onSuccess={saved} />}
    {modal?.type === 'history' && <HistoryDialog product={modal.product} onClose={closeModal} />}
    {modal?.type === 'delete' && <DeleteDialog product={modal.product} onClose={closeModal} onSuccess={saved} />}
    {toast && <Toast key={toast.id} message={toast.message} onDismiss={dismissToast} />}
  </>;
}
