# Prompt 2: React frontend verification

Verified on 15 October 2026 (IST).

## Completed experience

- React/Vite inventory workspace with Overview, Products, and Stock activity views.
- Live dashboard totals, inventory value, stock-health distribution, low-stock queue, product snapshot, and recent movements.
- Catalog search by name/SKU, category selection, stock-level selection, pagination, and useful empty states.
- Create/edit forms with product validation, unique-SKU feedback, inline server errors, pending states, and retained input on failure.
- Receipt/issue dialogs that fetch current quantities, preview the result, prevent obvious overselling, and recover from stale-stock conflicts without losing the quantity or note.
- Read-only paginated product history; workspace activity lists the latest ten movements with access to each product's full ledger.
- Explicit delete confirmation/cancellation, successful deletion of unused products, and clear errors for ledger-protected products.
- Keyboard-accessible native dialogs, focus handling, skip navigation, mobile sidebar, and narrow-screen product cards.
- Success notifications, refresh/retry actions, cancellation of stale reads, and no fake inventory or growth figures.
- Locally bundled DM Sans/Manrope font assets, included OFL licenses, consistent INR display and IST timestamps.

The frontend uses relative `/api` requests. Local Vite proxies to the working FastAPI service on port 8000. Backend support added for case-insensitive category choices across the whole catalog and paginated `healthy`/`low`/`out` stock filters.

## Checks passed

| Check | Result |
|---|---|
| Backend PostgreSQL suite | **49 passed**, one existing upstream TestClient warning |
| Frontend API/validation/formatting tests | **11 passed** |
| Frontend production build | Passed |
| Chromium browser workflows | **8 passed** |
| Desktop and mobile screenshot review | Reviewed; mobile checked at 390×844 |

Outputs: [backend test log](BACKEND_PHASE2_RESULTS.txt), [frontend test/build/browser log](FRONTEND_TEST_RESULTS.txt).

Browser workflows cover:

1. Create/edit a product, receive 10, issue 3, prevent issuing 8, and inspect two real ledger entries plus refreshed dashboard totals.
2. Duplicate SKU and simulated temporary API failure: preserve form values, then retry successfully.
3. Cancel deletion, delete an unused test fixture, and reject deletion of a fixture with movement history.
4. Category choices across catalog pages, next-page navigation, stock-status filtering, and no-match search states.
5. Simulated concurrent operator: stock changes after the dialog opens; the server rejects the stale request, inputs remain, and available quantity refreshes.
6. Product picker, new movement, recent activity, and a product ledger spanning multiple pages.
7. Mobile navigation, catalog cards, dialogs, and no document-level horizontal overflow at 390px.
8. Retry a failed product-history fetch and use the skip link without changing the active view.

The unit tests also check exact formatting of large monetary strings without converting them through JavaScript Number.

## Isolation and evidence

The interactive browser connector exposed no browser in this session. Instead, the project was tested in a dedicated headless Chromium process using Playwright, with the official browser downloaded into the ignored `.playwright-browsers` directory. This does not automate or alter the user's browser profile.

Browser QA uses a disposable PostgreSQL database on 5433, API on 8001, and Vite on 5174. Synthetic test products exist only in that disposable environment. The helper stops its own QA processes and removes its database after the run. It does not alter the development inventory served by ports 5432/8000/5173.

Development screenshots are read-only captures of the actual development app:

- [Desktop overview](screenshots/frontend-overview.png)
- [Product catalog](screenshots/frontend-products.png)
- [Mobile overview](screenshots/frontend-mobile.png)

Files ending in `-qa.png` show isolated test fixtures rather than the user's development inventory.

## Run it

The current implementation session leaves the local API and frontend running. Open [StockFlow](http://127.0.0.1:5173).

To restart manually, from `stockflow/`, use separate PowerShell terminals:

```powershell
& .\scripts\start-backend.ps1
```

```powershell
& .\scripts\start-frontend.ps1
```

Repeat all frontend checks with `& .\scripts\test-frontend.ps1`. Add `-InstallBrowser` on a fresh checkout to download the official isolated Chromium binary. Install `npm.cmd ci` in frontend and the backend development environment first.

## Limits and next stage

Desktop Chromium and one narrow-screen Chromium viewport were exercised; Safari/Firefox, assistive technology, and a full accessibility audit were not verified. The current frontend runs through Vite, not a production Nginx container. A production build does not establish container security or cloud deployment readiness.

Next: **Prompt 3**, implementing non-root application images, multi-stage frontend build, correct Nginx routing, migration/startup ordering, and the complete persistent Docker Compose application stack.

References: [React effects](https://react.dev/reference/react/useEffect), [Vite proxy](https://vite.dev/config/server-options.html), [Playwright configuration](https://playwright.dev/docs/test-configuration), [Fontsource variable fonts](https://fontsource.org/docs/getting-started/variable).
