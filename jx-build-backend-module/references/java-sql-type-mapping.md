# Java and SQL type mapping rules

## Contents

1. Purpose and current platform facts
2. Selection order
3. Identifier types
4. Text and file references
5. Numbers, quantities, money, and scores
6. State and boolean-like values
7. Dates and time
8. Collections and nested data
9. Nullability and defaults
10. Alignment checklist

## 1. Purpose and current platform facts

Use this reference when defining Entity, DTO, VO, table, constraint, or query-result fields.

The inspected platform currently uses Java 17, Spring Boot 3.1.2, MyBatis-Plus 3.5.3.1, and MySQL Connector 8.2.0. Existing business Entities primarily use `Integer`, `String`, `Date`, `BigDecimal`, and some `Double`. Existing SQL commonly uses `bigint`, `int`, `tinyint`, `varchar`, `text`, `datetime`, and `decimal`.

These are project facts, not permission to copy a type blindly.

## 2. Selection order

Choose a type in this order:

1. Preserve the actual type of an existing column and all current Java consumers when modifying an existing module.
2. Match the identifier and time conventions of directly related tables and Services.
3. Use the business range and precision requirement for a new field.
4. Align Entity, DTO/VO, DAO parameters/results, Mapper XML, SQL column, and frontend contract.
5. Report an existing incompatible type instead of hiding it with an unverified conversion.

Do not perform broad type migrations as a side effect of adding one module.

## 3. Identifier types

The current project has Entities that use `Integer` while several SQL scripts declare `bigint`. Therefore:

- Inspect the actual target table, generated-key behavior, related Entity, DAO signature, and frontend number handling.
- Preserve `Integer` for a compatible existing module unless the requested change includes a coordinated migration.
- Use `Long` for a new or existing `BIGINT` identifier only when related Java signatures and response contracts are aligned.
- Never mix `Integer`, `Long`, and `String` for the same identifier across Controller, Service, DAO, Entity, and Mapper XML without an explicit conversion boundary.

For relation fields such as user, course, team, equipment, match, or order ID, use the same Java and SQL family as the referenced identifier.

## 4. Text and file references

| Business data | Java candidate | MySQL candidate | Rules |
|---|---|---|---|
| Name, title, location, label | `String` | `varchar(n)` | Choose length from current schema and validation |
| Short summary, opponent, result text | `String` | `varchar(n)` | Do not use unlimited text by default |
| Description, remarks, review, rich content | `String` | `text` or a justified larger text type | Define whether formatting/HTML is allowed |
| Image, avatar, cover, attachment reference | `String` | `varchar(n)` | Store the platform file path/reference, not binary data, unless project proves otherwise |
| Fixed business code | `String` | `varchar(n)` | Define uniqueness and case rules when needed |

Do not infer file upload support from a string path field alone. Reuse the platform upload capability only when requirements enable it.

## 5. Numbers, quantities, money, and scores

| Business data | Java candidate | MySQL candidate | Required rules |
|---|---|---|---|
| Count, stock, capacity, minutes, year | `Integer` | `int` | Range, non-negative/positive rule |
| Large aggregate count | `Long` | `bigint` | Use for count results that may exceed integer range |
| Rating, coordinate, precise score | `BigDecimal` | `decimal(p,s)` | Define precision, scale, rounding, range |
| Money or settlement amount | `BigDecimal` | `decimal(p,s)` | Never use binary floating point for new monetary fields |
| Existing approximate score stored as `Double` | Preserve `Double` if compatibility requires | Existing floating/decimal column | Do not silently change without migration and caller review |
| Percentage | `BigDecimal` or calculated VO value | `decimal(p,s)` only if persisted | Define zero-denominator behavior |

For calculated statistics, prefer a VO/result value and do not add a stored column unless the requirement needs a persisted snapshot.

## 6. State and boolean-like values

The current project commonly represents states and flags as `Integer` with `tinyint` or `int` columns.

Use this style for compatibility when the inspected module does so, but require:

- A named business meaning for every allowed value.
- A default matching the initial business action.
- Service validation of allowed transitions or values.
- SQL comment/dictionary data when the platform uses dictionaries.
- User-facing descriptions that avoid exposing raw numeric codes.

Do not use one generic status field for unrelated enable state, review result, circulation state, and deletion state.

Use Java `Boolean` only when the surrounding module, serialization, SQL type, and frontend contract already use it consistently.

## 7. Dates and time

The current business modules commonly use `java.util.Date` mapped to MySQL `datetime`.

- Preserve `Date` and `datetime` when extending those modules.
- For a new same-platform module, follow the directly related module unless the project has adopted a newer time API consistently.
- Use a date-only SQL type only when time-of-day has no business meaning.
- Define whether the database or Service supplies create/update timestamps.
- Avoid conflicting Java and database defaults.
- Keep timezone assumptions consistent with the application configuration and deployment.

Use separate fields for scheduled time, submission time, confirmation time, completion time, and update time only when the lifecycle requires them.

## 8. Collections and nested data

`List<T>`, nested DTOs, and combined objects normally belong to DTO/VO boundaries, not one relational Entity column.

Use a relation/detail table when each child has identity, ordering, quantity, state, or independent updates. Use JSON storage only when the existing project and requirement explicitly support it and query/update needs are understood.

Mark display-only Entity properties with the platform's non-persistent field annotation only when compatibility requires that pattern; prefer a dedicated VO for new combined outputs.

## 9. Nullability and defaults

For every field, decide:

- Required on create, optional on create, or server-generated.
- Editable, immutable, or calculated.
- Database `NOT NULL` versus nullable.
- Java validation and Service fallback.
- SQL default and its business meaning.

Use `NOT NULL` for true invariants, not to avoid deciding an optional meaning. Use nullable for information legitimately unknown until a later transition, such as return time before confirmed return.

Do not assign a harmless-looking zero or empty string when zero/empty has a different business meaning.

## 10. Alignment checklist

- Existing schema and related Java signatures were inspected.
- Identifier types are consistent across all layers.
- Text length and validation agree.
- Money/precision fields use decimal-safe types.
- Quantity ranges and non-negative rules are defined.
- State values have documented meanings and transition owners.
- Date/time type, source, and nullability are consistent.
- Collections and calculated fields are not accidentally persisted.
- Entity and SQL nullability/defaults agree with Service creation logic.
- Existing Integer/BIGINT or Double/DECIMAL mismatches are reported, not concealed.

