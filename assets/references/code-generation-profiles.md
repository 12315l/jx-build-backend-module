# Java backend generation profiles

## Contents

1. Output boundary
2. Fixed project paths
3. Profile selection
4. Quick CRUD profile
5. Standard relation profile
6. Business workflow profile
7. Statistics query profile
8. Conditional Java and XML files
9. Generation sequence
10. Pre-write and completion checks

## 1. Output boundary

Generate project business code as Java, SQL, and conditional Mapper XML.

The Skill's own helper implementation may later contain Python files under `jx-build-backend-module/scripts`. Those files inspect requirements or generated code. They are Skill infrastructure and must never be copied into `base-framework/src/main/java`, `system.store.functionModule`, or a generated business module.

For a persistent business module, the normal output is:

- Java Controller.
- Concrete Java Service.
- Java DAO.
- Java Entity.
- SQL table and permission script.
- Conditional Java DTO and VO.
- Conditional MyBatis Mapper XML.

Never generate Python as project business code.

## 2. Fixed project paths

Use these current-repository defaults:

```text
base-framework/src/main/java/system/store/functionModule/<PascalName>Module/
├── controller/<PascalName>Controller.java
├── service/<PascalName>Service.java
├── dao/<PascalName>Dao.java
├── model/
│   ├── entity/<PascalName>.java
│   ├── dto/<Purpose>DTO.java          # conditional
│   └── vo/<Purpose>VO.java            # conditional
└── db/c_<snake_name>_table.sql

base-framework/src/main/resources/mapper/function/<PascalName>Mapper.xml  # conditional
```

Use these package names:

```text
system.store.functionModule.<PascalName>Module.controller
system.store.functionModule.<PascalName>Module.service
system.store.functionModule.<PascalName>Module.dao
system.store.functionModule.<PascalName>Module.model.entity
system.store.functionModule.<PascalName>Module.model.dto
system.store.functionModule.<PascalName>Module.model.vo
```

Resolve the backend module root from the current project and `ModuleMaker` before writing. If another same-platform project uses the `base-framework` directory as its working root, avoid duplicating that path segment. The canonical package root remains `system.store.functionModule` unless the user approves an exception.

Treat an output outside the resolved backend module as a blocking path error.

## 3. Profile selection

Choose exactly one primary profile per module.

| Profile | Choose when | Minimum output |
|---|---|---|
| `quick_crud` | One main table and standard information management | Controller, Service, DAO, Entity, SQL |
| `standard_relation` | User/object relations, combined names, duplicate-business checks, role data scope | Core files plus required DTO/VO and related queries |
| `business_workflow` | State actions, approval, issue/return, order, settlement, inventory, multi-record writes | Core files plus action DTO/VO, transactions, logs, conditional Mapper |
| `statistics_query` | Trend, share, rank, dashboard, aggregation | Controller and Service; reuse DAO/Entity or add read query only when needed |

Upgrade the profile when requirements introduce stronger behavior. Do not downgrade a workflow to CRUD to save files.

## 4. Quick CRUD profile

Use for categories, announcements, basic assets, simple reference data, and other single-table management.

Generate:

1. `<PascalName>Controller.java` with retained management endpoints and permissions.
2. `<PascalName>Service.java` extending `ServiceImpl<<PascalName>Dao, <PascalName>>`.
3. `<PascalName>Dao.java` extending `BaseMapper<<PascalName>>`.
4. `<PascalName>.java` with table mapping and actual persisted fields.
5. `c_<snake_name>_table.sql` with table and retained permission entries.

Use the Entity directly as request input only when client-writable fields are simple and sensitive server-owned fields are protected. Add a DTO when create and edit inputs differ or the Entity exposes fields that clients must not control.

Do not add Mapper XML for standard MyBatis-Plus single-table operations.

## 5. Standard relation profile

Use when a record links to a user, course, item, team, or another business object.

Generate the quick CRUD files, then add only the necessary boundaries:

- Create or edit DTO to accept business inputs without trusting ownership or computed values.
- Dedicated authenticated submission action when an ordinary user creates the relation; do not reuse the management `/create` authority.
- Details or list VO to return associated names and combined display data.
- Service lookups and existence checks for related records.
- Duplicate-business checks, such as one active registration per user and target.
- Role-specific data-scope filtering.
- Custom DAO/Mapper only when simple lookups cannot provide the required result efficiently or consistently.

Keep associated display names out of the persistent Entity unless they are real stored fields.

## 6. Business workflow profile

Use when the module has dedicated state-changing actions or quantity changes.

Generate the standard relation output that is actually needed, then add:

- Dedicated Controller endpoints for submit, review, confirm, issue, return, settle, complete, cancel, or other confirmed actions.
- Explicit `authenticated`, `authority`, or `public` access mode for every dedicated action, with exact permission SQL for authority-protected actions.
- Purpose-specific DTO for action inputs.
- Service methods that validate actor, data scope, source state, related records, quantities, and idempotency.
- Transactions covering all records and quantities that must succeed together.
- Operation logs or business records required by the flow.
- VO for combined workflow status or settlement results when required.
- Mapper XML only for necessary complex reads, not for ordinary writes.

Do not allow generic edit to set critical state, inventory, settlement, score, or ownership fields.

For offline/online mixed steps, generate only the authorized confirmation endpoint. Do not claim the system automatically detected the offline event.

## 7. Statistics query profile

Use for read-only aggregation over existing business data.

Generate or modify:

- Controller query endpoints.
- Service methods that define role scope, filters, date range, grouping, sorting, and empty-data behavior.
- VO or structured maps when a named result improves clarity.
- DAO or Mapper XML only for aggregation that cannot be expressed cleanly with current query facilities.

Do not create an Entity, table, create endpoint, edit endpoint, or remove endpoint when statistics persist no independent business object.

Every returned metric must have a real data source and documented calculation. Do not return fixed demonstration data as implemented statistics.

## 8. Conditional Java and XML files

### DTO

Generate when:

- Client inputs differ from stored fields.
- Server-owned identity, state, totals, or ownership must be excluded.
- A dedicated action has its own parameters.
- Validation groups or nested inputs are needed.

### VO

Generate when:

- Lists or details combine associated names.
- Results contain calculated, aggregate, or display-only values.
- A workflow result combines several records.

### Mapper XML

Generate at `base-framework/src/main/resources/mapper/function/<PascalName>Mapper.xml` when:

- A complex join or aggregation is genuinely required.
- The DAO method signature, parameters, namespace, and result type are known.
- Existing project conventions use Mapper XML for the same query type.

Do not generate empty DTO, VO, or Mapper files to make a directory look complete.

## 9. Generation sequence

1. Inspect the project root, `KeyModule`, `ModuleMaker`, target module, and related modules.
2. Complete requirement coverage and flow traceability.
3. Complete the module specification and select the profile.
4. Produce a backend file plan using `assets/module-outline-template.md`.
5. Confirm that every planned project output is Java, SQL, or conditional Mapper XML at an allowed path.
6. For a new module, use KeyModule and ModuleMaker for the five-file scaffold.
7. Remove unused KeyModule capabilities and unresolved placeholders.
8. Add real fields, DTO/VO, actions, transactions, and queries from the specification.
9. Align Controller permissions, Service methods, Entity, SQL, DAO/Mapper, and frontend calls.
10. Compile and run applicable structure and business checks.

## 10. Pre-write and completion checks

Before writing:

- The target path resolves inside the intended backend module.
- The target module does not already exist, or the operation is explicitly an enhancement.
- All required names and file destinations are known.
- No Python output is present in the project business file plan.
- All critical permissions, states, quantities, and database changes are resolved.

Before reporting completion:

- No `Key`, `key`, `XX`, `${pascal_name}`, `${camel_name}`, or `${snake_name}` placeholder remains in generated project files.
- Package declarations match directories.
- The Controller imports the actual Service and request/response types.
- The Service uses actual DAO and Entity types.
- Entity and SQL fields, defaults, logical-delete behavior, and constraints match.
- DAO methods and Mapper XML statements match when XML exists.
- Permission SQL matches retained Controller permissions.
- `mvn -v` uses a Java runtime compatible with the level required by `pom.xml`; a separate `java -version` result is not sufficient evidence for Maven.
- Backend compilation passes or the exact blocker is reported.
- SQL generated, SQL executed, and SQL verified are reported as separate facts.

On Windows, Maven may inherit an older `JAVA_HOME` even when `java` on `PATH` is newer. When a matching JDK is already installed, set `JAVA_HOME` and prepend its `bin` directory only for the current compile process. Do not silently persist system environment changes. Compile the unchanged project baseline when practical, then compile the isolated or in-scope module change so pre-existing failures are not attributed to generated code.
