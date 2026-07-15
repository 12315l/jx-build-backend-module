# Frontend page and theme rules

## Contents

1. Scope and source priority
2. Output roots
3. Admin configuration pages
4. User-facing pages and reusable cards
5. Theme variable changes
6. Cross-layer checks
7. Verification checklist

## 1. Scope and source priority

Use this reference only when frontend work is part of the user's request or is explicitly included in the approved module specification.

Inspect the active project's source before choosing a component, configuration property, route, or style token. Use evidence in this order:

1. The user's current requirements and visual constraints.
2. The active shared component's accepted properties and events.
3. The active module page and service contract.
4. A working sibling module in the same frontend project.
5. Historical starter snippets only as a candidate pattern.

Do not treat the `information` module as an error-free canonical template. Its four configuration files demonstrate the current structure, but individual properties may be stale or mismatched. Correct the new module from current component and API evidence instead of copying residual comments, unused imports, wrong `pageName` values, or properties unsupported by the selected control type.

## 2. Output roots

Resolve these roots from the active project before writing:

- Admin module: `jx-template-admin/src/views/main/modules/<camelName>`.
- Admin base page: `pages/base/index.vue`.
- Admin configurable page files: `pages/base/config/*.config.ts`.
- Admin API calls: module `service/index.ts` or the current equivalent.
- User-facing module: `jx-template-front/src/views/main/modules/<camelName>`.
- Admin theme source: `jx-template-admin/src/assets/css/variables.module.less`.
- User-facing theme source: inspect `jx-template-front/src/assets/css` and imports; do not assume the admin file is shared.

Use the platform's current module naming and import aliases. Do not place Vue or TypeScript files under `system.store.functionModule`; that package is reserved for Java backend code.

## 3. Admin configuration pages

### 3.1 Decide whether configuration is appropriate

Use the four-file configuration pattern for standard search, table, add/edit, and detail pages. Use explicit Vue page logic for workflow actions, multi-step forms, charts, drag-and-drop, tactical boards, or other interactions that the shared components do not support.

Create only files imported by the page:

- `search.config.ts` for query controls.
- `content.config.ts` for table, header actions, and pagination.
- `modal.config.ts` for standard add/edit forms and validation.
- `details.config.ts` when the page opens the shared details view.

Keep the same module `pageName` across the page and its configuration unless the inspected shared hook proves a deliberate exception.

### 3.2 Search configuration

For each `formItems` entry:

- Set `prop` to the exact request property accepted by the page service and enforced by the backend Service.
- Select only a control type supported by the current `PageSearch`; the inspected version supports input, date picker, and select controls.
- Provide select options in the shape consumed by the component. Current configurable selects use `labelCode` and `labelValue`.
- Put date-specific properties only on a date control.
- Remove a search item when the backend does not implement its filter.

Do not claim that a visible search field works until the backend query has been verified.

### 3.3 Content configuration

Use `header` for the visible title and authorized top actions, `pagination` for list paging, and `propsList` for table columns.

The inspected `PageContent` supports ordinary text plus timer, selection, tag, default tag, multiple tag, address, image preview, handler, rich text, download, multi-download, and custom slot rendering. Recheck the active component before using any type.

- Map every `prop` to an Entity field, VO field, or documented page transform.
- Use a dictionary name only when that dictionary exists and the stored value matches it.
- Use the built-in handler only for standard edit/delete behavior supported by the page.
- Use a custom slot for business actions such as approval, issue, return, completion, or review; enforce the matching backend authority independently.
- Enable export only when an implemented export call and authorized backend endpoint exist.
- Keep image and download properties tied to actual stored file keys or paths.

### 3.4 Modal configuration

For each `formItems` entry, classify the value as client-writable, server-owned, associated, or display-only. Include only client-writable or explicitly authorized subject-selection values in submission.

The inspected `PageModal` supports input, numeric input, switch, radio, cascader, select, tree select, time select, date picker, file upload, editor, address, map, and custom slots. Recheck the active component before use.

- Keep form `prop` names aligned with the action DTO or permitted Entity input.
- Add validation rules for required business input and use the control's correct trigger.
- Do not submit creator, current user, workflow state, stock totals, calculated totals, audit time, or deletion markers as trusted values.
- For business transitions, use a dedicated action dialog and endpoint rather than a generic edit form.
- For dynamic options, load real data within the page and update the config or custom slot using the current module pattern.

### 3.5 Details configuration

Use grouped `propsList` entries with their intended column count and labels. The inspected `PageDetails` supports ordinary text, image preview, dictionary tag, HTML, time, region text, and custom rendering.

- Return protected or internal values only when the role may view them.
- Use a VO for stable associated or calculated details.
- Use custom rendering only for presentation; it does not justify a new database field.

### 3.6 Page and service wiring

The page must import only the configuration files it renders. Keep page events aligned with the current hooks and components: query/reset, pagination, add, edit, delete, detail, export, selection, and custom actions.

Keep module service calls aligned with Controller path, HTTP method, parameters/body placement, and response shape. The current paged list hook expects `data.list` and `data.total`.

Button visibility must use the current permission helper, while the Controller and Service still enforce authorization and data scope.

## 4. User-facing pages and reusable cards

The inspected user-facing starter uses direct Vue pages rather than the admin four-file config convention:

- Home pages fetch banner and limited featured data, then map real response properties into reusable components.
- List pages keep paging and filters in a request object, use the shared list hook, show an explicit empty state, and render pagination only when meaningful.
- Detail pages obtain the record identifier from the route, call a real details endpoint, and show a failure or empty state when no record is returned.
- Reusable card components accept `itemConfig` mappings, a verified layout value, optional interaction switches, and an optional detail route.

Treat `itemConfig` as a presentation mapping, not a reason to rename backend fields. Verify that every configured key exists in the response. Enable likes, collections, prices, ratings, tags, avatars, or owner data only when the project's requirements and code implement them.

Use only layout names supported by the active component. Do not copy every starter layout into a module. Select one layout that fits the business content and preserve the existing component contract.

## 5. Theme variable changes

When the user supplies a theme palette or asks for global style configuration:

1. Read the complete active `variables.module.less` file.
2. Record the declaration order, exported mappings, and CSS-variable mappings.
3. Change requested values in place.
4. Keep every unrequested variable and unchanged line in its original position.
5. Keep each variable declared once; replace an old value instead of adding a second declaration.
6. Keep `:export` and `:root` mapping names and order unchanged unless the user explicitly requests a contract change.
7. Search consumers before renaming or removing any token.
8. Check text, icon, border, and state contrast. Report a supplied palette that does not meet the intended accessibility use instead of silently changing the user's brand choice.

Do not propagate one project's colors into the Skill as universal defaults. Store rules and mapping behavior in the Skill; obtain actual colors from each project's requirements.

## 6. Cross-layer checks

For every generated page, verify:

| Frontend concern | Required backend evidence |
|---|---|
| Search property | Controller accepts it and Service applies it |
| Form property | DTO/Entity permits it and Service validates it |
| Table/detail property | Entity/VO or explicit transform supplies it |
| Select options | Dictionary or authorized lookup supplies real values |
| Button action | Dedicated endpoint, permission, transition, and failure behavior exist |
| Paging | Request names and `list`/`total` response shape match |
| Current user | Service derives identity; page value is not trusted |
| File/image | Upload, storage value, preview, and download contracts match |

Do not add a frontend control for a requirement marked `to_develop` unless implementation of the matching backend capability is part of the same authorized task.

## 7. Verification checklist

- Active shared components and sibling module were inspected.
- Admin and user-facing roots were resolved separately.
- Only consumed configuration files were created.
- Configuration `pageName`, fields, control types, dictionary names, and routes are consistent.
- Search fields have real backend filters.
- Form fields exclude untrusted server-owned values.
- Custom workflow actions use dedicated permissions and endpoints.
- List and detail response properties exist.
- Empty, loading, success, and failure states follow current project facilities.
- Theme declarations, exports, and CSS variables retain their original order and uniqueness.
- Frontend build and backend compile were run and reported separately.
