# DAO, SQL, and Mapper XML generation rules

## Contents

1. DAO platform contract
2. Choosing the query implementation
3. DAO method rules
4. Mapper XML location and identity
5. Query and result mapping
6. Write boundaries and transactions
7. Table and migration SQL
8. Permission SQL
9. Performance and safety
10. Verification checklist

## 1. DAO platform contract

Use this reference before generating or changing a DAO, custom query, Mapper XML, table SQL, or permission SQL.

Place the DAO at:

```text
base-framework/src/main/java/system/store/functionModule/<PascalName>Module/dao/<PascalName>Dao.java
```

Use the package:

```text
system.store.functionModule.<PascalName>Module.dao
```

For a persistent module, use the current platform structure:

```java
@Mapper
public interface <PascalName>Dao extends BaseMapper<<PascalName>> {
}
```

Do not generate a repository abstraction beside the DAO. Do not add custom methods when MyBatis-Plus already expresses the required single-table operation clearly.

## 2. Choosing the query implementation

Choose the smallest platform-compatible option:

1. Use inherited `BaseMapper`/`ServiceImpl` methods for ordinary create, update, logical delete, ID lookup, and simple lists.
2. Use MyBatis-Plus wrappers for conditional single-table filters, scope, ordering, and pagination.
3. Add a DAO method with an annotation only when the project uses that style and the SQL remains short and maintainable.
4. Add Mapper XML for necessary multi-table joins, latest-record selection, grouped statistics, complex conditions, or a stable combined DTO/VO result.

Do not create Mapper XML for ordinary CRUD. Do not generate an empty XML file.

Use the `statistics_query` profile for read-only aggregate modules that persist no independent object; do not create a fake table merely to host a query.

## 3. DAO method rules

Every custom DAO method must have:

- A business-specific method name.
- Explicit parameter names with the platform's parameter annotation when XML references them.
- A return type matching the selected Entity, DTO, VO, scalar, list, or page strategy.
- One matching SQL statement ID in Mapper XML when XML is used.
- Defined empty-result behavior.
- Defined role/data-scope inputs when scope cannot be derived safely inside the SQL from other filters.

Do not pass a general map of unvalidated client fields into SQL. Do not accept raw order-by fragments, table names, or column names from the client.

Keep write orchestration in the Service. A DAO method should perform one database operation whose result can be checked.

## 4. Mapper XML location and identity

Place conditional Mapper XML at:

```text
base-framework/src/main/resources/mapper/function/<PascalName>Mapper.xml
```

The mapper namespace must exactly match:

```text
system.store.functionModule.<PascalName>Module.dao.<PascalName>Dao
```

Each statement ID must exactly match a DAO method. Parameter placeholders must match annotated parameter names. Result type or result map must use the actual fully qualified Entity, DTO, or VO class.

Use the project's MyBatis mapper DOCTYPE and XML encoding pattern. Ensure files are saved in a consistent encoding and replace malformed or placeholder comments.

## 5. Query and result mapping

For a combined result:

- Select explicit columns needed by the DTO/VO.
- Alias columns when their database names do not map unambiguously to Java properties.
- Use a result map when several tables have overlapping identifiers/names or when explicit mapping improves correctness.
- Keep the selected aliases, result map properties, and Java fields synchronized.
- Define how missing optional relations appear.

Avoid broad `table.*` selection in multi-table joins when columns can collide or the output contract should stay stable.

For latest-record or statistics queries, document:

- Source table and business date/time field.
- Grouping key.
- Tie behavior.
- Null handling.
- Calculation formula.
- Sorting and limit behavior.

Do not hardcode a role identifier, status meaning, or demonstration date unless it is a verified platform constant. Prefer confirmed configuration or a named server-side value.

## 6. Write boundaries and transactions

Ordinary Entity writes may use inherited MyBatis-Plus methods. Use a custom update when an invariant requires checking the affected-row count, for example conditional stock reduction.

The Service owns the transaction and calls DAO operations in business order. Mapper XML must not attempt to simulate a multi-step business transaction.

For conditional quantity changes, make the condition explicit and verify the affected-row count. A successful SQL execution with zero affected rows is a business conflict, not a successful issue or reservation.

Do not combine state, quantity, owner, and unrelated edits into a general-purpose SQL statement callable from generic edit.

## 7. Table and migration SQL

Keep module table SQL at:

```text
base-framework/src/main/java/system/store/functionModule/<PascalName>Module/db/c_<snake_name>_table.sql
```

For a new table, include only confirmed columns, primary key, defaults, comments, required unique constraints, indexes, and enabled permission records.

For an existing table, generate or document migration-safe `ALTER` operations after inspecting the live/current schema. Do not use `DROP TABLE` as an update strategy.

Treat `DROP TABLE IF EXISTS` in KeyModule as a development scaffold only. Never execute it automatically against an existing or unknown database.

Use SQL types and defaults that match the Entity and Service creation behavior. Do not rely on both Java and database defaults with conflicting meanings.

## 8. Permission SQL

Generate permission/menu SQL only for retained Controller capabilities.

For a new independent admin module, generate this hierarchy:

```text
module directory (permission type 0, parent NULL)
└── business page (permission type 1, parent = directory)
    └── retained action buttons (permission type 2, parent = page)
```

Use the same visible name for directory and page when that matches the product menu, but always use different permission codes. Use `manage:dir:<module-key>`, `manage:page:<module-key>:base`, and `manage:btn:<module-key>:<action>`.

Make the script repeatable:

1. Insert the directory only when its permission code does not exist.
2. Select the directory ID by its permission code after insertion or reuse.
3. Insert the page only when its permission code does not exist, using the resolved directory ID and directory route.
4. Select the page ID by its permission code after insertion or reuse.
5. Insert each retained button only when its permission code does not exist, using the resolved page ID and page route.

Use permission codes as stable identity. Do not search by `permission_name`, do not hardcode a parent ID, do not use `IFNULL` to redirect a missing parent, and do not rely only on `LAST_INSERT_ID()` because a repeated run may reuse an existing record. If the specification deliberately attaches a page to an existing directory, resolve the declared parent permission code and fail clearly when it is absent.

For every protected endpoint, verify:

- Permission authority string matches `@PreAuthorize` exactly.
- Page permission exists before child button permissions reference it.
- Directory permission exists before the child page references it when the module owns its directory.
- Button label describes the actual action.
- Menu/module key matches the frontend registration convention.
- Disabled KeyModule actions have no remaining permission insert.

Workflow actions should have action-specific permissions. Do not silently reuse create/edit/remove for approval, issue, return, loss, settlement, or completion when those are distinct powers.

Permission SQL generated is not permission SQL applied. Report execution and verification separately.

## 9. Performance and safety

Before finalizing custom SQL:

- Confirm filters and joins use actual indexed or indexable columns where appropriate.
- Avoid one query per output row.
- Avoid unbounded administrative exports when project constraints require limits.
- Parameterize values; never concatenate client input into SQL.
- Apply logical deletion and role data scope consistently.
- Use deterministic ordering for pages and rankings.
- Check aggregate null and division behavior.
- Check unique-constraint conflicts and translate them to business-facing failures where needed.

Do not claim a query is optimized until its actual execution plan or representative behavior has been inspected. Structural review alone is not performance verification.

## 10. Verification checklist

- DAO extends `BaseMapper` with the actual Entity.
- Custom DAO methods exist only when required.
- DAO parameters, XML placeholders, statement IDs, and return types match.
- Mapper namespace matches the DAO fully qualified name.
- XML path is under `resources/mapper/function`.
- Selected columns and result mappings match DTO/VO properties.
- Multi-table queries avoid ambiguous broad column selection.
- Logical deletion and role data scope are applied consistently.
- Transaction boundaries remain in the Service.
- Conditional quantity updates check affected rows.
- Entity and table SQL types/defaults/constraints agree.
- Existing tables are not destructively recreated.
- Controller authorities and permission SQL match exactly.
- No disabled KeyModule permission or SQL fragment remains.
- SQL generation, execution, and verification are reported as separate states.
- No placeholder module, table, method, field, or permission name remains.
