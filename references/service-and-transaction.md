# Service and transaction generation rules

## Contents

1. Platform Service shape
2. Method responsibilities
3. Validation order
4. Query and pagination
5. Identity and data scope
6. State transitions
7. Transactions and quantity changes
8. Duplicate operations and concurrency
9. Results, exceptions, and logs
10. Generation checklist

## 1. Platform Service shape

Use this reference before generating or changing business logic, state transitions, inventory changes, or transactions.

The current platform uses one concrete Service class at:

```text
base-framework/src/main/java/system/store/functionModule/<PascalName>Module/service/<PascalName>Service.java
```

Use the package:

```text
system.store.functionModule.<PascalName>Module.service
```

For a persistent module, follow the inspected platform shape:

```java
@Service
public class <PascalName>Service
        extends ServiceImpl<<PascalName>Dao, <PascalName>> {
}
```

Do not create a parallel Service interface and implementation pair while the platform uses concrete Services extending `ServiceImpl`.

Reuse existing facilities such as `ResultMapUtil`, `PageUtil`, `SecurityUtil`, the existing global exception, MyBatis-Plus wrappers, and the current logger pattern. Do not establish a second business framework inside one module.

## 2. Method responsibilities

The Service owns:

- Input and business validation.
- Current actor identity and data-scope enforcement.
- Related-record existence and relationship checks.
- Duplicate-business checks.
- Allowed state-transition decisions.
- Server-owned field assignment.
- Multi-record writes and quantity adjustments.
- Transaction boundaries.
- Business operation logging or persistent flow records.

Keep public Service methods aligned with real Controller operations. Private helpers may centralize validation, query construction, scope rules, or state decisions.

Do not expose a generic method that permits callers to set protected state, stock, ownership, final score, or settlement fields.

## 3. Validation order

For a state-changing operation, use this order unless the business specification gives a stronger dependency:

1. Validate required input shape, identifiers, text length, date range, and positive quantities.
2. Load the target record and reject missing or logically deleted data.
3. Determine the current actor on the server.
4. Verify permission-related ownership or role data scope for the target.
5. Load and validate related users, courses, items, teams, schedules, or orders.
6. Verify the source state permits the requested action.
7. Verify quantities, capacity, uniqueness, and other invariants.
8. Calculate server-owned results.
9. Perform all required writes.
10. Record the business operation when required.
11. Return a result that describes the completed online action.

Fail before mutation whenever possible. Error messages should identify the business reason without exposing internal SQL or implementation details.

## 4. Query and pagination

Use the current MyBatis-Plus query and pagination facilities for ordinary single-table queries.

Inspect the actual `CommonPage` before writing filters. In the current platform it adds only `name` and `type` beyond inherited paging fields; it does not provide generic `keyword`, `status`, time-range, or arbitrary sort properties. Use `CommonPage` when those available fields are sufficient. Create a purpose-specific Page class extending the current paging base when confirmed filters require additional properties, and record that request type in the query specification.

Define every supported filter explicitly. A field appearing in `CommonPage` does not mean every module supports it, and a field absent from `CommonPage` must not be called as if it existed. Apply name, type, status, time, sorting, and role filters only when mapped to real request properties, Entity fields, and requirements.

For list queries:

- Apply logical deletion consistently.
- Apply data scope before pagination.
- Use a deterministic default order.
- Validate dynamic sorting against an allowed field list; do not trust a raw client column expression.
- Define empty-result behavior as an empty page/list, not fabricated demonstration data.
- Avoid one associated query per row when a join or batched lookup is required.

Use a VO for combined display data. Add a custom DAO method and Mapper XML only when the query is genuinely complex.

## 5. Identity and data scope

Obtain the current actor from the existing security utility. Ignore or reject client-submitted creator, owner, reviewer, coach, learner, or operator values when the actor must be the logged-in account.

Do not assume every non-administrator scope is creator-based. Derive scope from the real business relation:

- Course ownership may depend on the assigned coach.
- Learner records may depend on enrollment or team membership.
- Equipment records may depend on the claimant and administrator operations.
- Statistics may require role-scoped source queries.

Apply the same scope to details, pages, export, edit, delete, and workflow actions. A scoped page with an unscoped details endpoint is a security defect.

For administrator-created records on behalf of a user, distinguish the operator from the business owner. Store both only if the schema and requirements require both meanings.

## 6. State transitions

Write an explicit transition table in the module specification before implementing a workflow.

Each transition must define:

- Source state.
- Action name.
- Allowed actor and data scope.
- Required conditions.
- Destination state.
- Field and related-record changes.
- Failure outcome.
- Whether a transaction is required.

Implement dedicated public methods such as submit, review, issue, applyReturn, confirmReturn, complete, cancel, or reportLoss only when those actions exist in the requirements.

The Service must reload the persisted state during the action. Do not trust the state included in a request DTO. Reject transitions from an invalid source state rather than silently forcing the destination.

Do not invent intermediate states to make a diagram look complete. If the existing system lacks a required next step, mark it `to_develop` in traceability before generating it.

## 7. Transactions and quantity changes

Add `@Transactional` to a Service operation when one business result requires two or more writes to succeed together, including:

- Main record plus detail or relation records.
- Workflow state plus inventory quantity.
- Issue/return record plus stock flow record.
- Enrollment plus capacity or duplicate protection.
- Match result plus player performance and growth changes.
- Batch mutations that must be all-or-nothing.

The transaction belongs in the Service, not the Controller or Mapper XML.

For quantity changes:

- Validate that the requested quantity is positive.
- Reload the current inventory or capacity within the operation.
- Check the correct business quantity at the correct step.
- Change available quantity only at the confirmed step defined by the flow.
- Never allow available quantity or total quantity to become negative.
- Record the direction, quantity, reason, operator, business record, and time when a flow record is required.
- Restore, deduct, or write off only once for one confirmed action.

For the current equipment pattern, an application may check availability without reducing it; confirmed offline issue performs the deduction; confirmed return restores availability; confirmed damage or loss follows its separately specified write-off rules. Do not generalize this sequence to projects whose requirements differ.

## 8. Duplicate operations and concurrency

Protect business uniqueness at the Service level and, where appropriate, with a database unique constraint. Existing platform examples include one user per schedule, one user per course, one student per team, and one player record per year.

Design repeated actions explicitly:

- A duplicate submission may return the existing outcome or a clear rejection.
- A second confirmation must not adjust stock, capacity, totals, or growth twice.
- A retry after a network failure must not create a second business record.

Do not claim concurrency safety merely because a transaction exists. For contested quantities or unique enrollment, use a confirmed platform-compatible strategy such as a unique constraint or a conditional update whose affected-row count is checked. Do not invent distributed locks, queues, or cache locks without project support.

If concurrency protection cannot be verified in the current project, report the limitation instead of overstating it.

## 9. Results, exceptions, and logs

Follow the module's surrounding convention consistently:

- Return existing result maps where current Controllers wrap Service maps.
- Use the existing global exception for validation failures when that is the module convention.
- Do not mix several incompatible error mechanisms within one workflow.

Return business-facing messages. Keep internal exception messages and SQL details out of client responses.

Use ordinary application logs for diagnostics. Generate a persistent operation or flow record only when the business requires later review, reconciliation, or statistics. A logger line cannot replace an equipment flow, approval history, payment record, or attendance record.

## 10. Generation checklist

- Service is concrete and extends the current platform base where applicable.
- Public methods map to retained Controller operations.
- Input, target, actor, relation, state, quantity, and duplicate checks are present.
- Server-owned identity, time, state, totals, and ownership are assigned server-side.
- Details, pages, mutations, and exports enforce consistent data scope.
- Critical transitions have dedicated methods.
- Transition source state is reloaded and validated.
- Multi-write business operations are transactional.
- Stock or capacity changes occur at the correct confirmed step.
- Repeated confirmation cannot apply a quantity change twice.
- Database uniqueness and Service checks agree.
- Complex reads avoid row-by-row query expansion.
- Existing response, exception, pagination, and security facilities are reused.
- No unverified lock, message, payment, or offline detection behavior is claimed.
