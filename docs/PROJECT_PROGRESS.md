# Project Progress

## Phase 3.1 Multi-Operator SKU Assignment

### Completed features
- Refactored SKU assignments from one-to-one to many-to-many.
- Added assignment roles: `owner`, `assistant`, `advertising`, `inventory`, `customer_service`.
- Preserved assignment history tracking for assign, reassign, and unassign actions.
- Updated assignment validation to prevent duplicate `sku_id + operator_id + role` records.
- Preserved existing operator/SKU CRUD flows and SKU owner/status refresh behavior.

### Database changes
- `sku_assignment` now uses `sku_id`, `operator_id`, `role`, and `assigned_at`.
- Added uniqueness on `sku_id + operator_id + role`.
- `assignment_history` now records `role` and `action` in addition to old/new operator fields.
- `sku_pool` keeps `status` and owner summary for compatibility with existing flows.

### Files created or updated
- Updated `src/wb_ops/db/models.py`.
- Updated `src/wb_ops/repositories/assignment_repository.py`.
- Updated `src/wb_ops/services/sku_assignment_service.py`.
- Updated `tests/test_sku_assignment_service.py`.
- Updated `docs/PROJECT_PROGRESS.md`.

### Known issues
- Existing local SQLite databases from the old one-to-one assignment schema need migration or recreation.
- Full test execution depends on SQLAlchemy being installed in the runtime environment.

### Next phase plan
- Implement Phase 4 metrics tables, repositories, services, and tests.

## Phase 4 Metrics System

### Completed features
- Added metrics model support for daily sales, revenue, orders, returns, inventory quantity, ad spend, CTR, and CPC.
- Implemented repository upsert/list operations for each metrics table.
- Implemented metrics service validation for existing SKUs and non-negative values.
- Added unit tests for daily, inventory, and advertising metrics workflows.

### Database changes
- Added `daily_metrics` with `sales`, `revenue`, `orders`, and `returns`.
- Added `inventory_metrics` with `inventory_quantity`.
- Added `advertising_metrics` with `ad_spend`, `ctr`, and `cpc`.
- Added uniqueness on `sku_id + date` for all metrics tables.

### Files created or updated
- Updated `src/wb_ops/db/models.py`.
- Created `src/wb_ops/repositories/metrics_repository.py`.
- Created `src/wb_ops/services/metrics_service.py`.
- Updated repository and service exports.
- Created `tests/test_metrics_service.py`.
- Updated `docs/PROJECT_PROGRESS.md`.

### Known issues
- No external WB metrics API ingestion is implemented yet; services accept normalized metric inputs.
- Existing local SQLite databases need migration or recreation to add the new tables.

### Next phase plan
- Implement Phase 5 Feishu integration framework with configuration placeholders and client abstractions.

## Phase 5 Feishu Framework

### Completed features
- Created Feishu integration package with configuration, client abstraction, and placeholder interfaces.
- Added placeholder interfaces for user sync, operator sync, notification sending, and report sending.
- Ensured Feishu credentials are not required for local development or tests.

### Database changes
- None in this phase.

### Files created or updated
- Created `src/wb_ops/integrations/feishu/__init__.py`.
- Created `src/wb_ops/integrations/feishu/config.py`.
- Created `src/wb_ops/integrations/feishu/client.py`.
- Created `src/wb_ops/integrations/feishu/interfaces.py`.
- Created `tests/test_feishu_framework.py`.
- Updated `docs/PROJECT_PROGRESS.md`.

### Known issues
- Feishu API methods are abstractions/placeholders only and do not yet implement real Bitable writes.

### Next phase plan
- Implement Phase 6 role/permission data model, repositories, services, and tests.

## Phase 6 Permission System

### Completed features
- Added role and permission data model.
- Added role-permission and operator-role mapping support.
- Implemented default roles: `admin`, `manager`, `operator`, and `viewer`.
- Implemented permission bootstrap, role assignment, duplicate validation, and permission checks.
- Added unit tests for default bootstrap and operator permission checks.

### Database changes
- Added `roles`.
- Added `permissions`.
- Added `role_permission`.
- Added `operator_role`.

### Files created or updated
- Updated `src/wb_ops/db/models.py`.
- Created `src/wb_ops/repositories/permission_repository.py`.
- Created `src/wb_ops/services/permission_service.py`.
- Updated repository and service exports.
- Created `tests/test_permission_service.py`.
- Updated `docs/PROJECT_PROGRESS.md`.

### Known issues
- Permission names are code-defined constants; no management UI exists yet.

### Next phase plan
- Implement Phase 7 dashboard API-ready service structures for sales, operator performance, SKU assignments, and inventory.

## Phase 7 Dashboard Framework

### Completed features
- Added API-ready dashboard service structures for sales statistics, operator performance, SKU assignment statistics, and inventory statistics.
- Implemented read-only aggregation service methods returning dataclasses with `to_dict()` helpers.
- Added unit tests for sales, operator, assignment, and inventory dashboard outputs.

### Database changes
- None in this phase; dashboard services read from existing assignment and metrics tables.

### Files created or updated
- Created `src/wb_ops/services/dashboard_service.py`.
- Updated service exports.
- Created `tests/test_dashboard_service.py`.
- Updated `docs/PROJECT_PROGRESS.md`.

### Known issues
- No HTTP API or frontend is implemented yet; this phase only prepares API-ready service structures.

### Next phase plan
- Add FastAPI or CLI endpoints for dashboard consumers, then integrate live WB metrics ingestion and Feishu reporting.

## Phase 8 FastAPI Framework

### Completed features
- Added FastAPI application factory and API package structure under `src/wb_ops/api`.
- Added health check endpoint.
- Added SKU APIs for listing, creation, update, and deletion.
- Added operator APIs for listing, creation, and update.
- Added assignment APIs for assigning operators to SKUs, removing assignments, and reading assignment history.
- Added dashboard APIs for sales statistics, operator statistics, SKU assignment statistics, and inventory statistics.
- Added Pydantic request/response schemas.
- Added dependency injection helpers for DB sessions and service construction.
- Added permission middleware foundation that captures request permission context without requiring auth credentials yet.

### Database changes
- None in this phase; APIs use existing SKU, operator, assignment, metrics, and dashboard service tables.

### Files created or updated
- Created `src/wb_ops/api/__init__.py`.
- Created `src/wb_ops/api/app.py`.
- Created `src/wb_ops/api/dependencies.py`.
- Created `src/wb_ops/api/middleware.py`.
- Created `src/wb_ops/api/schemas.py`.
- Created `src/wb_ops/api/routers/health.py`.
- Created `src/wb_ops/api/routers/skus.py`.
- Created `src/wb_ops/api/routers/operators.py`.
- Created `src/wb_ops/api/routers/assignments.py`.
- Created `src/wb_ops/api/routers/dashboard.py`.
- Created `src/wb_ops/api/routers/__init__.py`.
- Updated `requirements.txt` with FastAPI and Uvicorn.
- Updated `docs/PROJECT_PROGRESS.md`.

### Known issues
- Permission middleware is a foundation only; it does not yet enforce role permissions against `PermissionService`.
- API integration tests were not executed in this environment because FastAPI/SQLAlchemy dependencies are unavailable.

### Next phase plan
- Add API integration tests, wire route-level permission enforcement, and add startup database initialization/migration handling.
