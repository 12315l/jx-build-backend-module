# Requirements-to-code mapping

## Contents

1. Purpose
2. Accepted requirement format
3. Assign stable IDs
4. Normalize role features
5. Derive shared modules
6. Normalize core flows
7. Separate online and offline behavior
8. Compare target and current states
9. Map business verbs to code
10. Build coverage matrices
11. Handle conflicts and revisions
12. Split module specifications
13. Completion checks

## 1. Purpose

Use this reference when the user provides role-based feature descriptions and core business flows for a project.

Convert those business descriptions into traceable implementation inputs without forcing the user to write technical fields. Preserve every original feature and flow step, then map it to modules, permissions, data, code layers, and acceptance checks.

Do not embed a project's specific menu list into the Skill as a universal requirement. Each project supplies its own target requirements.

## 2. Accepted requirement format

Accept plain business text such as:

```text
1. User side
Appointment center: Browse available services and submit an appointment.
My appointments: View submitted appointments and their processing results.

2. Administrator side
Appointment management: Review and process all appointment records.

Core flow
The user submits an appointment, the administrator confirms it, and the user views the result.
```

Do not require the user to provide class names, field names, table names, endpoint paths, or status numbers. Derive technical candidates only after inspecting the project.

Use [../assets/project-requirement-template.md](../assets/project-requirement-template.md) when the user wants a reusable input form. Use [../assets/requirement-traceability-template.md](../assets/requirement-traceability-template.md) for a readable analysis output and [../assets/project-traceability-template.yaml](../assets/project-traceability-template.yaml) as the machine-checkable project traceability source.

## 3. Assign stable IDs

Assign IDs before rewriting or grouping requirements:

- Role features: `REQ-<ROLE>-NNN`.
- Core processes: `FLOW-NNN`.
- Process steps: `FLOW-NNN-SNN`.
- Decisions and conflicts: `DECISION-NNN`.

Use stable English role labels where possible. Keep the original Chinese or business role name in a separate column.

Do not renumber unaffected requirements when a new item is inserted. Stable IDs are needed to update code safely after requirement changes.

## 4. Normalize role features

For each role feature, record:

- Original role and original wording.
- Feature name and intended business outcome.
- Action type: view, maintain, submit, review, confirm, statistics, or dedicated action.
- Data scope: self, own course, own team, assigned records, all records, or custom.
- Shared business object.
- Dependencies and explicit exclusions.
- Current coverage state.

Do not assume every feature equals one module. A feature can reuse a base module, combine multiple modules, or require no new backend code.

Do not assume every module equals one page. One module may expose separate role endpoints and management endpoints.

## 5. Derive shared modules

Group requirements by business object and lifecycle, not by role.

Example:

- A user submits an appointment.
- A staff member confirms the appointment.
- An administrator manages all appointments.

These normally share an appointment Entity, DAO, and core Service. They may use different Controller endpoints, permissions, and data scopes.

Reuse existing platform modules for users, roles, menus, passwords, and personal profiles. Do not create duplicate modules under `functionModule`.

Create a separate module when the object has an independent lifecycle, table, permissions, or business invariants. Keep statistics as read-only queries when no independent persistent object exists.

## 6. Normalize core flows

Split each core flow into ordered steps. For every step, capture:

- Actor.
- Trigger and frontend operation.
- Offline cooperation.
- Preconditions.
- System validation.
- Data changes.
- Quantity changes.
- State transition.
- Transaction boundary.
- Success result.
- Rejection, cancellation, repetition, over-limit, or failure outcome when required.
- Responsible module.

Do not combine several state-changing actions into one vague step. Separate submission, confirmation, completion, return, damage, or settlement when they change different data or actors.

## 7. Separate online and offline behavior

Classify each step:

- `online`: Completed through a real page and backend endpoint.
- `offline`: Happens in the real world and needs no automatic system behavior.
- `mixed`: An offline event occurs, then an authorized role records or confirms its result online.

Do not convert offline attendance, handoff, training, inspection, delivery, or service into QR codes, geolocation, automatic sensing, or messaging without explicit requirements and code support.

For mixed steps, identify the human confirmation endpoint and the data it records. The system must not claim to know that the offline event occurred before confirmation.

## 8. Compare target and current states

Use the requirement text to define the target state. Use project evidence to define the current state.

Set one coverage state:

- `platform_existing`: Direct implementation evidence exists.
- `partial`: Some code exists, but the full requirement or flow is incomplete.
- `to_develop`: The target requires a capability that does not exist.
- `to_remove`: The latest target excludes existing behavior.
- `verified`: The implementation and agreed checks passed.
- `to_confirm`: A conflict or ambiguity prevents a safe decision.

Evidence may include Controller endpoints, Service logic, DAO or Mapper queries, Entity fields, SQL, permission entries, frontend calls, and test results.

A menu name or database field alone is not enough to mark a requirement as implemented.

## 9. Map business verbs to code

Use verbs as signals, then verify context.

| Business wording | Likely code responsibility | Required check |
|---|---|---|
| View, browse, query | Controller query plus Service data scope | Public or protected access; filters and result shape |
| Maintain, manage | CRUD or dedicated management actions | Whether create, edit, delete, recovery, and batch actions are truly required |
| Submit, apply, register | Dedicated create or submit action | Identity source, duplicate prevention, eligibility, initial state |
| Review, approve, reject | Dedicated state action | Actor permission, allowed source state, reason, target state |
| Confirm, issue, return, settle | Dedicated transactional action | Offline prerequisite, quantity checks, idempotency, logs |
| Record, supplement | Dedicated write action | Who may record on behalf of whom; audit source |
| Analyze, statistics, rank | Read-only aggregation | Metric source, time range, grouping, empty data |
| Recommend | Rule or algorithm result | Input evidence, method, deduplication, title accuracy |
| Personal profile, password | Existing base-module capability | Do not generate a duplicate business module |

Do not translate every “management” feature into unrestricted generic CRUD. Workflow records may need read-only management plus dedicated actions.

## 10. Build coverage matrices

Create two matrices before module specifications.

### Feature coverage matrix

For every role feature, map:

- Requirement ID.
- Target module or base capability.
- Coverage state and evidence.
- Controller destination or no-new-endpoint decision.
- Service destination.
- DAO/Mapper and Entity/table destination.
- Permission and data scope.
- Acceptance case.

### Flow-to-code matrix

For every flow step, map:

- Online/offline/mixed classification.
- Controller action.
- Service validation.
- Data and quantity changes.
- State transition.
- Transaction and invariants.
- Failure outcomes.
- Actual files and verification result.

Every generated endpoint needs a requirement or flow source. Every in-scope feature needs a code destination or an explicit no-code explanation.

Before splitting the project into module specifications, run:

```text
python <skill-dir>/scripts/validate_traceability.py <project-root> <traceability-file> --gate mapping --format json
```

The mapping gate checks structure and real file evidence. It does not turn `partial`, `to_develop`, `to_remove`, or `to_confirm` into completed work. Run `--gate verification` only after implementation, module specifications, compilation, and agreed business checks are complete.

The structured traceability file must distinguish:

- Existing implementation evidence from target destinations that do not exist yet.
- Base-module reuse from a newly generated business module.
- Pure frontend or offline behavior from backend actions.
- A mixed offline/online step from an automatic system event by naming who confirms the real-world result.
- A removed requirement from a missing requirement by recording its disposition and affected code.

## 11. Handle conflicts and revisions

Apply the user's latest explicit correction first. When a newer document appears to reintroduce a previously removed capability, do not guess whether it is intentional; create a decision record when the new wording is not clearly a correction.

Detect these conflict types:

- A role uses a capability in a core flow but has no corresponding role feature.
- A management feature exists, but the core flow omits the state-changing action.
- A flow mentions damage, loss, cancellation, refund, or evaluation without defining its outcome.
- Two roles appear to own the same final decision.
- The feature list requests an operation that existing permissions forbid.
- Current code exposes a capability that the latest requirements remove.

Do not silently resolve conflicts with a project archetype or a similar module.

Record the decision, affected requirements, affected flows, and affected code files.

## 12. Split module specifications

After matrices are complete:

1. Group requirements by shared business object.
2. Decide whether each group maps to a base module, an existing business module, a new business module, or no backend change.
3. Select the generation profile.
4. Copy `assets/module-spec-template.yaml` for each business module.
5. Copy requirement IDs and flow-step IDs into module identity, roles, fields, queries, actions, and traceability.
6. Mark unresolved cross-module transactions and ownership decisions before implementation.

A cross-module flow must identify the Service responsible for transaction orchestration. Do not let several Controllers independently perform parts of one atomic business action.

## 13. Completion checks

Requirement mapping is complete only when:

- Every role feature has a stable ID and coverage state.
- Every role feature maps to a module, base capability, or no-code explanation.
- Every core flow has ordered steps.
- Every online or mixed step has an intended endpoint and Service destination.
- Every system validation has an enforcement location.
- Every data and state change has a persistence and transaction destination.
- Every required abnormal branch has a final outcome.
- Role permissions and data scopes do not conflict.
- Latest corrections are reflected in affected endpoints, permissions, SQL, and frontend calls.
- No extra capability was added from a mother template or similar project.
- All blocking conflicts are resolved before module status becomes `ready`.
- The mapping gate passes before module specifications are created, and the verification gate passes only when no unfinished coverage remains.
