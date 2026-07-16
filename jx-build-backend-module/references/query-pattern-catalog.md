# Query pattern catalog

## Contents

1. Purpose
2. Query decision order
3. Simple entity queries
4. Role-scoped queries
5. Relation and combined-output queries
6. Duplicate and eligibility queries
7. Latest-record and history queries
8. Statistics and ranking queries
9. Conditional quantity updates
10. Query checklist

## 1. Purpose

Use this reference when filling the query section of a module specification or deciding whether to add DAO methods and Mapper XML.

Every query must name its source, filters, scope, order, result shape, empty-data behavior, and acceptance check.

## 2. Query decision order

Use the smallest sufficient mechanism:

1. Inherited Service/DAO operation for ID lookup and basic persistence.
2. MyBatis-Plus lambda wrapper for simple single-table conditions, scope, order, and pagination.
3. Batched related lookup when a small number of known relations can be combined safely in Service.
4. Custom DAO query for stable joins, latest-per-group selection, grouped statistics, or performance-sensitive combined results.
5. Mapper XML only when custom SQL is necessary and the DAO/XML contract is complete.

Do not use Mapper XML only to mirror a wrapper query. Do not create one database query per output row.

## 3. Simple entity queries

### Details by identifier

- Input: one identifier.
- Checks: existence, deletion, authentication/public boundary, and role data scope.
- Output: Entity only when no associated display data is needed; otherwise a VO/DTO.
- Empty result: business-facing not-found result.

### Management page

- Input: `CommonPage` plus explicitly supported module filters.
- Scope: administrator/global or verified role scope.
- Order: deterministic default, usually a real time or business sort field.
- Output: `PageList<Entity>` or `PageList<VO>`.
- Implementation: wrapper for one table; custom query for necessary combined page data.

### Public page

- Generate only when requirements and security rules permit anonymous access.
- Filter to intentionally visible records.
- Do not reuse an unscoped management query.

## 4. Role-scoped queries

### Current user's records

Obtain user identity from the server and filter the real owner/relation column. Do not accept an arbitrary user ID for a “my” endpoint.

### Assigned coach/staff records

Derive records through confirmed assignment relations such as course coach, team coach, enrollment, or membership. Do not fall back to creator scope when the creator is not the business owner.

### Administrator query

Require the management page authority and apply the intended global filters. Administrator access does not remove ordinary validation, deletion, or sensitive-field rules.

Apply scope before pagination and aggregation.

## 5. Relation and combined-output queries

Use a DTO/VO when a page or details result needs associated names, covers, coach information, user profiles, schedule data, or calculated values.

Choose one strategy:

- Join in a custom DAO query when the relation is stable and needed for most rows.
- Batch-load related rows and map them in Service when relationships are simple and query counts remain bounded.
- Use a dedicated latest-record subquery when one current value is selected from a history table.

For custom joins, select explicit columns and aliases. Define inner versus left join based on whether a missing relation removes the business record or leaves optional display data empty.

## 6. Duplicate and eligibility queries

Use existence/count queries for rules such as one active enrollment per user/course, one attendance record per user/schedule, one member per team, or one yearly player record.

The query condition must match the database unique constraint and lifecycle behavior. If logical deletion or cancellation permits a later resubmission, define how the unique key supports it.

Eligibility may also require:

- Target record exists and is enabled/open.
- Actor belongs to the allowed role or relation.
- Capacity or inventory is sufficient at the correct step.
- Requested date/time is valid.

A pre-check improves messages; a database constraint or conditional write protects the invariant under concurrent requests where needed.

## 7. Latest-record and history queries

For growth, annual assessment, newest status, or latest performance data, define:

- Partition/group key, such as user.
- Ordering field, such as year or creation time.
- Tie-breaker when two rows share the same value.
- Whether missing history returns no row or default values.
- Whether the endpoint returns one latest record or the ordered history.

Use a deterministic subquery/window-compatible strategy supported by the actual MySQL version and project convention. Do not assume `MAX(year)` uniquely identifies one row without a uniqueness rule or tie decision.

## 8. Statistics and ranking queries

For each metric, record:

- Metric name and business definition.
- Source table/module and included states.
- Role/data scope.
- Time field and date range.
- Grouping dimension.
- Calculation and null/zero behavior.
- Ordering and maximum result size.
- Output VO fields.

Use wrapper `count`, grouped `selectMaps`, or custom DAO/Mapper based on complexity. Do not return fixed sample data. Do not describe a chart as implemented until a real data query and caller exist.

For percentages, define the denominator and return zero or empty behavior explicitly. For rankings, use deterministic tie ordering.

## 9. Conditional quantity updates

For stock, capacity, points, balance, or remaining quantity under concurrent access, a read-then-write sequence may be insufficient.

When required and compatible with the project:

- Generate a DAO update whose condition includes the allowed state and sufficient current quantity.
- Apply an arithmetic update in SQL.
- Check the affected-row count in Service.
- Treat zero affected rows as a business conflict.
- Run the state/quantity change and related flow record in one Service transaction.

Do not claim a reservation, lock, or concurrency guarantee unless the implemented query and test prove it.

## 10. Query checklist

- Query has a requirement or flow source.
- Input filters map to real fields.
- Authentication and data scope are explicit.
- Logical deletion and enabled/workflow state are handled.
- Default ordering is deterministic.
- Pagination occurs after scope/filtering.
- Empty-data behavior is defined.
- Associated output uses DTO/VO.
- No row-by-row query expansion is introduced.
- Duplicate query and unique constraint express the same invariant.
- Latest-record ties and statistics denominators are defined.
- Conditional quantity writes check affected rows.
- DAO method, Mapper XML, result mapping, and caller agree.

