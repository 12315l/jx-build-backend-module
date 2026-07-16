# Module specification reference

## Contents

1. Purpose and lifecycle
2. Requirement intake
3. Module identity
4. Generation profiles
5. Roles and data scopes
6. Persistence fields
7. Queries and template switches
8. Business actions and states
9. Transactions and invariants
10. Frontend contract
11. Generated files
12. Traceability
13. Readiness checks

## 1. Purpose and lifecycle

Use one module specification for one shared business module. Multiple roles may use the same module through different permissions and data scopes.

The specification is not a description-only document. It is structured input for generating Controller, Service, DAO, Entity, SQL, and conditional DTO, VO, and Mapper XML files.

Use this lifecycle:

1. `draft`: Requirements or project facts are incomplete.
2. `ready`: The module can be previewed without guessing.
3. `authorized`: The user requested implementation.
4. `implemented`: Code exists but checks remain.
5. `verified`: Required checks passed; unverified runtime items are named.

Never skip directly from `draft` to code.

## 2. Requirement intake

Accept business input in the user's normal format:

- Role-based features: `Feature name: one-sentence business description`.
- Core flows: actor, frontend action, offline cooperation, system checks, data changes, state result, and completion.
- Latest corrections and explicit exclusions.

Create stable IDs:

- Feature requirements: `REQ-<ROLE>-NNN`, such as `REQ-STUDENT-001`.
- Core flows: `FLOW-NNN`.
- Flow steps: `FLOW-NNN-SNN`.
- Fields: `FIELD-NNN`.
- Queries: `QUERY-NNN`.
- Actions: `ACTION-NNN`.

Keep the original requirement text in traceability records. Paraphrasing may clarify it but must not change its scope.

Distinguish target and current states:

| Coverage state | Meaning |
|---|---|
| `platform_existing` | Direct code evidence exists in the platform or target project |
| `partial` | Some required behavior exists, but the requirement is not complete |
| `to_develop` | The target requirement exists but supporting code does not |
| `to_remove` | Existing behavior conflicts with the latest target requirements |
| `verified` | Implementation and required checks are complete |

## 3. Module identity

Complete all identity fields before previewing files.

| Field | Rule |
|---|---|
| Chinese name | Use for business labels, API documentation, menu names, and SQL comments |
| Pascal name | Use for class names and `<PascalName>Module` |
| Camel name | Use for variables, endpoint prefix, and permission key |
| Snake name | Use for table and SQL file names |
| Package root | Default to `system.store.functionModule.<PascalName>Module` |
| Source root | Resolve from the current project's backend module |
| Table name | Follow the current platform prefix and inspected project conventions |
| Profile | Choose one of the four supported profiles |

Reject names that would collide with an existing module, class, route, permission key, or table unless the task is an explicit enhancement.

## 4. Generation profiles

### `quick_crud`

Use for single-table information management.

Generate Controller, concrete Service, DAO, Entity, and SQL. Enable optional KeyModule capabilities only when required.

### `standard_relation`

Use when a record relates to a user or another business object, returns associated names, enforces duplicate-business rules, or applies per-role data scope.

Add DTO, VO, or custom queries only as required. Prefer MyBatis-Plus for simple relations that do not need complex joins.

### `business_workflow`

Use for approval, work orders, orders, issue/return, settlement, completion, or other stateful flows.

Define dedicated actions, allowed source states, target states, transaction boundaries, idempotency, failure outcomes, and audit records. Do not expose critical state changes through generic edit.

### `statistics_query`

Use for trends, shares, rankings, and dashboards.

Do not force create, edit, remove, Entity, or independent SQL when the statistics read existing data. Define metric source, filters, date range, grouping, sorting, and empty-data behavior.

## 5. Roles and data scopes

For each role, record:

- Role code and business name.
- Allowed operations.
- Data scope, such as self, own course, own team, assigned records, or all records.
- Permission codes for page and action access.
- Whether a separate Controller endpoint is required.

Reuse Service logic across roles when the business rule is identical. Apply identity and data scope on the server; do not trust a submitted user ID to define ownership.

Map platform-level user, role, menu, password, and personal-profile requirements to existing base modules instead of generating duplicate business modules.

## 6. Persistence fields

For every persisted field, define:

- Business label, Java property, SQL column, Java type, and SQL type.
- Length, precision, scale, nullability, default, and uniqueness.
- Validation rules and failure message.
- Query, display, sorting, import, and export use.
- Association target and deletion impact.
- Source requirement IDs.

Keep Entity and SQL aligned. Do not store display-only associated names, calculated statistics, or temporary UI values in the Entity; use VO fields.

Treat these as high-risk fields requiring explicit semantics:

- Money, inventory, quota, count, duration, score, and percentage.
- Status and type values.
- User and business-object foreign keys.
- File, image, rich-text, and attachment paths.
- Creation, update, ownership, and logical-delete fields.

## 7. Queries and template switches

For each query, define endpoint, request Page/input type, access type, role permissions, filters, pagination, sort, result shape, implementation approach, and requirement sources. Use `CommonPage` only when its inspected properties cover the confirmed filters; otherwise name the dedicated Page class that will be generated.

Use these implementation choices:

- `mybatis_plus`: Standard single-table or simple related lookups.
- `custom_dao`: Custom annotated query when it matches existing project practice.
- `mapper_xml`: Necessary complex joins or aggregations.

Set every template switch explicitly:

| Switch | Safe default |
|---|---|
| Admin details | Enabled for managed records |
| Admin page | Enabled for managed records |
| Create/edit/remove | Unresolved until the module scope confirms writes |
| Public details/page | Disabled |
| Recover | Disabled |
| Batch status/sort | Disabled |
| Metadata | Enabled for standard low-code management |
| Excel import/export | Disabled |
| Permission SQL | Enabled only for retained pages and actions |

Disabled capabilities must be removed consistently from backend code, annotations, permission SQL, and frontend calls.

When `permission_sql` is enabled, complete `permission_menu` before generation:

- Select `create_module_directory` for an independent admin module. Define a top-level directory, a business page beneath it, and the retained action buttons beneath the page.
- Select `attach_existing_directory` only when the product requirement explicitly places the page in an existing module directory; record that parent's unique permission code.
- Keep visible menu names separate from unique permission codes. A directory and child page may share a visible name.
- Require repeatable inserts keyed by permission code and forbid fixed parent IDs or fallback menus.
- Keep page and button permission codes aligned with roles, Controller authorities, frontend tokens, and traceability.

## 8. Business actions and states

For each dedicated action, define:

- Endpoint, HTTP method, access mode, exact authority when required, roles, data scope, and request DTO.
- Allowed source states and target state.
- Preconditions and validation order.
- Records and quantities written.
- Transaction and idempotency rules.
- Operation log.
- Expected business errors and failure outcome.
- Requirement IDs and flow-step IDs.

For state machines, list all states and transitions. A transition must identify its actor, preconditions, data effects, and failure behavior. Treat terminal states as immutable unless an explicit recovery rule exists.

Keep each state's persisted `code` compatible with the Java/SQL type of `state_property`, and keep its readable `business_name` separate. Every action and transition must reference a defined persisted code; do not put a Chinese display label into an integer state field.

Offline cooperation is a prerequisite, not an automatic system event. For example, an administrator may confirm a real-world handoff through a dedicated endpoint after it occurs.

Treat KeyModule `/create`, `/edit`, and `/remove` as management operations tied to management permissions. When an ordinary user submits an application, registration, repair request, return request, or similar business event, define a dedicated authenticated action such as `/submit` or `/apply`; do not silently reuse a management create button as the user-facing boundary.

## 9. Transactions and invariants

Create a transaction when one action changes multiple records, quantities, or logs that must succeed together.

Define invariants such as:

- Available quantity never becomes negative.
- Returned plus lost quantity never exceeds issued quantity.
- One user cannot create duplicate active registrations for the same business object.
- A completed or settled record cannot be completed again.
- A role cannot view or modify records outside its data scope.

For each invariant, record its enforcement layer and verification case. Prefer Service validation plus database constraints where appropriate.

## 10. Frontend contract

Complete `frontend_contract` when an existing or planned page must call the module. This section describes data and permission alignment only; it does not define visual style.

For an existing page, record the inspected page, service, search, form, table, and details configuration files that provide evidence. For a planned page, mark `source_status` as `planned` and record the agreed request, response, lookup, pagination, and button contracts without pretending files already exist.

Classify every submitted property as client-writable, server-owned, associated, or display-only. Map every returned property to an Entity, VO, aggregate, or explicit frontend transform. A page property alone is not proof that a database column or backend filter should exist.

Keep pagination keys, lookup value/label properties, Controller authority, permission SQL, and frontend button tokens synchronized. The current platform button helper uses substring matching, so every retained action token must be checked for collisions. Backend authorization and current-user scope remain mandatory even when the page hides a button or submits a user identifier.

Read [frontend-contract.md](frontend-contract.md) for the current platform evidence and detailed checks.

## 11. Generated files

Persistent business modules normally generate:

```text
src/main/java/system/store/functionModule/<PascalName>Module/
├── controller/<PascalName>Controller.java
├── service/<PascalName>Service.java
├── dao/<PascalName>Dao.java
├── model/entity/<PascalName>.java
└── db/c_<snake_name>_table.sql
```

Generate conditionally:

```text
model/dto/*DTO.java
model/vo/*VO.java
src/main/resources/mapper/function/<PascalName>Mapper.xml
```

Use the current concrete Service pattern extending `ServiceImpl<Dao, Entity>`. Do not add an interface layer solely because it is common in other projects.

For existing tables, generate an incremental SQL change plan. Do not use drop-and-recreate as a migration. Do not claim SQL was executed unless it was run and verified.

## 12. Traceability

Create two mappings.

### Feature coverage

Map each role feature to:

- Module and public/base-module ownership.
- Coverage state.
- Controller endpoint or no-new-endpoint decision.
- Service method or shared business logic.
- Entity/table or read-only source.
- Permission and data scope.
- Acceptance case.

### Flow-to-code

Map each flow step to:

- Actor and online/offline classification.
- Controller action.
- Service validation and data changes.
- State transition.
- Transaction and invariant.
- Failure outcome.
- Actual file locations after implementation.

Every generated endpoint must have a requirement source. Every in-scope requirement must have a code destination or an explicit no-code explanation.

## 13. Readiness checks

The specification is `ready` only when all applicable checks pass:

- Identity names and target paths are complete and collision-free.
- Target/current coverage is recorded for each requirement.
- Fields and table strategy are complete.
- Roles, permissions, and server-side data scopes are defined.
- Permission-menu strategy, directory/page/button parent chain, and repeatability rules are complete when permission SQL is enabled.
- Queries and template switches are explicit.
- Existing or planned frontend request, response, pagination, lookup, and permission contracts are explicit when in scope.
- Dedicated actions, states, and terminal outcomes are complete.
- Transactions and invariants name their enforcement location.
- Mandatory and conditional files are known.
- Feature and flow traceability has no unexplained gap.
- Unresolved questions do not change permissions, data, states, quantities, or database structure.
- Implementation authorization is explicit before writing project code.
