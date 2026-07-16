# KeyModule scaffold and capability switches

## Contents

1. Source of truth
2. Current five-file scaffold
3. ModuleMaker substitutions
4. Current Controller capabilities
5. Current Service capabilities
6. Current Entity and SQL defaults
7. Capability switch defaults
8. Capability dependency matrix
9. Synchronized removal rules
10. Scaffold completion checks

## 1. Source of truth

Inspect these project files before every generation because they may change:

```text
base-framework/src/test/resources/KeyModule
base-framework/src/test/java/ModuleMaker.java
```

The descriptions below reflect the current inspected scaffold. Project files remain authoritative.

## 2. Current five-file scaffold

```text
KeyModule/
├── controller/KeyController.java
├── service/KeyService.java
├── dao/KeyDao.java
├── model/entity/Key.java
└── db/c_key_table.sql
```

ModuleMaker targets `src/main/java/system/store/functionModule/<PascalName>Module` relative to its configured project path. In the current repository, this resolves under `base-framework`.

The scaffold does not include DTO, VO, or Mapper XML. Add them only for real requirements.

## 3. ModuleMaker substitutions

ModuleMaker uses these concepts:

- `Key`: Pascal-case module name and Java type names.
- `key`: camel-case route, variables, and permission key.
- Snake-case name: SQL file and database naming.
- `XX`: Chinese business label.
- `<PascalName>Module`: target module directory.

ModuleMaker refuses to generate when the target module directory already exists. Preserve this protection. Enhance existing modules incrementally instead of regenerating them.

After generation, search all new files for unresolved `Key`, `key`, `XX`, and naming placeholders.

The current raw substitutions have two cross-layer risks for multi-word names:

- Java template content turns `c_key_table` into a camel-case table token, while the SQL filename/content uses snake case.
- Permission SQL derives a camel key from a snake value by combining only the first and last segments, which is not reliable for names with more than two words.

Treat these as verified template limitations. The guarded scaffold must normalize the Entity table name and permission key to the completed module specification, then run cross-layer validation. Do not report raw ModuleMaker output as aligned merely because five files were created.

## 4. Current Controller capabilities

The current KeyController contains:

| Capability | Endpoint | Service destination | Permission |
|---|---|---|---|
| Public details | `GET /free/details/{id}` | `searchDetails` | None in template |
| Public page | `GET /free/page` | `searchFreePage` | None in template |
| Admin page | `GET /page` | `searchPage` | `manage:page:<key>:base` |
| Create | `POST /create` | `createNewRow` | `manage:btn:<key>:create` |
| Edit | `POST /edit` | `editRow` | `manage:btn:<key>:edit` |
| Logical remove | `POST /remove` | `removeRows` | `manage:btn:<key>:remove` |
| Recover | `POST /recover` | `recoverRows` | Edit permission in template |
| Batch status | `POST /batch/status` | `updateStatus` | Edit permission in template |
| Batch sort | `POST /batch/sort` | `updateSort` | Edit permission in template |
| Metadata | `GET /metadata` | `getModuleMetadata` | Page permission |
| Excel export | `GET /export` | Controller plus Service helpers | `manage:btn:<key>:export` |
| Excel import | `POST /import` | Controller plus `saveBatch` | `manage:btn:<key>:import` |

Do not treat the presence of an endpoint in KeyController as project authorization to expose it.

## 5. Current Service capabilities

The current KeyService provides:

- Details with missing/deleted-data feedback.
- Admin page with creator data scope for non-administrators.
- Public page limited to enabled, non-deleted data.
- Create with server-side creator, create time, and logical-delete initialization.
- Edit with existence and creator-ownership checks.
- Logical removal with batch reporting and ownership checks.
- Recovery through a logical-update condition.
- Batch status and batch sorting.
- Common status, type, and date filters.
- Default creation-time ordering and optional custom sort.
- Basic entity validation.
- Operation log points.
- Wrapper and ID-map helpers.
- Low-code field metadata.

Replace or remove template filters that do not match real fields. Do not leave commented or nonfunctional keyword conditions and claim search is complete.

## 6. Current Entity and SQL defaults

The active Entity fields are:

- `id`.
- `type`.
- `sort`.
- `status`.
- `creator`.
- `createTime`.
- `updateTime`.
- `isDelete` with logical-delete behavior.

The Entity also contains commented examples for name, image, attachment, and rich-text fields. They are examples only and must not be reported as active fields.

The SQL creates the matching base table and inserts menu/button permissions for:

- Management page.
- Create.
- Edit.
- Remove.
- Export.
- Import.

The SQL currently begins with a drop-if-exists statement. Treat it as new-table initialization content only. Never use drop-and-recreate to alter an existing project table, and never execute generated SQL without explicit authority.

## 7. Capability switch defaults

Use these defaults unless the module specification overrides them:

| Capability | Default | Reason |
|---|---|---|
| Admin details/page | Enabled for a managed persistent module | Standard management entry |
| Create/edit/remove | Unresolved | Read-only, log, and workflow modules differ |
| Public details/page | Disabled | Public exposure requires explicit business need |
| Recover | Disabled | Not every project exposes deleted records or recovery UI |
| Batch status | Disabled | Requires a real common enable/disable field and operation |
| Batch sort | Disabled | Requires a real sort field and page operation |
| Metadata | Enabled for standard low-code management | Supports current frontend adaptation |
| Excel import | Disabled | Requires field, duplicate, validation, and failure rules |
| Excel export | Disabled | Requires field selection and data-scope rules |
| Permission SQL | Enabled only for retained page/actions | Must match actual Controller permissions |

A `null` switch in the module specification is unresolved and blocks implementation when the capability affects generated files.

## 8. Capability dependency matrix

| Capability | Required fields or structures | Additional decisions |
|---|---|---|
| Public page | Usually status and logical delete | Public data scope, filters, safe fields |
| Recover | Logical-delete field | Recovery role, ownership, UI entry |
| Batch status | Status field | Allowed values, roles, state-versus-enable distinction |
| Batch sort | Sort field | Nonnegative rule, roles, order semantics |
| Metadata | Actual list/search/form definitions | Keep field metadata aligned with Entity and UI |
| Excel import | Importable Entity/DTO fields | Duplicate handling, validation, partial failure, audit |
| Excel export | Export annotations or export VO | Role scope, selected IDs, sensitive fields |
| Creator scope | Creator field and server identity | Admin bypass and ownership rules |
| Type filter | Type field | Dictionary or allowed value source |
| Time filter | Creation or business time field | Inclusive range and timezone expectations |

Do not keep a capability when its required fields or decisions are absent.

## 9. Synchronized removal rules

When disabling a capability, update every affected layer.

### Public details or page

- Remove the Controller endpoint.
- Remove the dedicated Service method when no other caller uses it.
- Remove frontend service calls and public page dependencies.
- Do not add public permissions merely to replace a removed free endpoint.

### Recover

- Remove the Controller endpoint and Service method.
- Keep logical deletion internally if ordinary remove still uses it.
- Remove recovery buttons and related permission decisions.

### Batch status or sort

- Remove Controller and Service methods.
- Remove metadata actions and frontend buttons.
- Remove `status` or `sort` fields only when no remaining business behavior needs them.

### Excel import or export

- Remove Controller endpoints, imports, EasyExcel handlers, and unused annotations.
- Remove import/export permission SQL.
- Remove frontend buttons and calls.
- Keep Excel annotations only when another retained export/import path uses them.

### Create, edit, or remove

- Remove Controller endpoints and permissions individually.
- Remove Service methods only when no dedicated action uses their validation helpers.
- Remove permission SQL and frontend buttons.
- Do not replace a removed workflow action with generic edit.

### Metadata

- Remove the Controller and Service metadata methods only when the frontend does not consume them.
- If retained, rebuild search, list, and form metadata from actual fields; do not leave KeyModule example metadata.

## 10. Scaffold completion checks

- Target directory and package root resolve to `system.store.functionModule.<PascalName>Module`.
- Exactly the intended scaffold files exist at the planned paths.
- No Python file exists in the business module output.
- No unresolved `Key`, `key`, `XX`, or module-name placeholder remains.
- Disabled capability endpoints and permissions are absent.
- Retained capability methods, fields, annotations, SQL permissions, and frontend calls are aligned.
- Commented example fields were either intentionally implemented or removed from generated code.
- Existing modules were not overwritten.
- Generated SQL was not reported as executed without evidence.
- Entity table name, SQL table name, Controller permission key, and permission SQL key remain aligned for multi-word module names.
