# Phase 02 Component Inventory

## Application shell

- **AppShell:** responsive sidebar/topbar, route-aware active state, mobile menu, collapsed desktop navigation, profile/notification popovers, accessible toast region.
- **AppStateProvider:** isolated browser-demo state, local metadata persistence, project/audit/document operations, and toast notifications. Screenshot object URLs are excluded from persistent storage.
- **Icon:** small inline SVG icon set; no external icon package or third-party asset requests.

## Shared interface

- **PageHeader**, **SectionTitle**, **Button**, **Badge**, **SeverityBadge**, **MetricCard**, **EmptyState**, **Modal**.
- Modal behavior includes Escape/backdrop dismissal, initial focus, focus restoration, and keyboard focus containment.
- CSS custom properties define surfaces, typography, spacing-oriented layout, radii, shadows, status colors, and interaction states.

## Audit workflow

- **NewAuditForm:** mode selection, client-only PNG/JPEG previews, file validation, screen naming/removal, keyboard and drag reordering, context/focus inputs, project selection, explicit demo submission.
- **AuditWorkspace:** screen panel, viewer, normalized SVG/HTML box overlay, issue marker/card selection, finding selection, multi-screen flow view, state banners, and demo prompt editor.
- **PromptDialog:** editable text area, regenerate/copy feedback, focus management, and explicit local-only behavior.
- **FlowOverview:** ordered screen nodes and connectors; labels explain that these do not verify product navigation.

## Feature routes

- Dashboard activity table, project cards/list, project details/forms/confirmation, filterable history, knowledge uploader/metadata table/details, empty design-system pattern cards, and local settings controls.
- Demonstration fixtures and metadata are isolated in `lib/demo-data.ts`; reusable presentation components contain no embedded audit datasets.
- Future API contracts are defined in `lib/services/contracts.ts`; no production service implementation is included.
