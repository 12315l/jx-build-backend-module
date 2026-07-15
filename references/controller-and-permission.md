# Controller and permission generation rules

## Contents

1. Purpose and platform shape
2. Controller responsibilities
3. Endpoint selection
4. Request and response boundaries
5. Permission generation
6. Identity and data scope
7. Workflow actions
8. Import, export, and metadata
9. Error and log handling
10. Generation checklist

## 1. Purpose and platform shape

Use this reference before generating or changing a Controller, its permission annotations, or its permission SQL.

The current platform uses a concrete Controller class at:

```text
base-framework/src/main/java/system/store/functionModule/<PascalName>Module/controller/<PascalName>Controller.java
```

Use the package:

```text
system.store.functionModule.<PascalName>Module.controller
```

Follow the current platform shape unless the inspected target project proves otherwise:

- `@Tag` describes the business module.
- `@RestController` exposes the module.
- `@RequestMapping` declares one stable module prefix.
- `@Operation` describes each retained operation.
- `@PreAuthorize` protects management pages and business buttons.
- `SimpleHttpResponse<T>` wraps ordinary responses.
- `PageList<T>` wraps paginated results.
- `CommonPage` carries the platform's common page input.

Do not introduce a second response wrapper, a second pagination system, or a parallel API layer.

## 2. Controller responsibilities

Keep the Controller thin. It may:

- Receive path, query, body, file, and page inputs.
- Bind inputs to an Entity or purpose-specific DTO when the specification permits it.
- Delegate one operation to the concrete Service.
- Convert the Service result into the existing response wrapper.
- Stream an authorized export when the current platform pattern is retained.

It must not:

- Decide inventory quantities, scores, prices, ownership, or workflow outcomes.
- Trust a client-submitted user identity as the current actor.
- Directly update several records to complete a business flow.
- Encode role data scope in scattered endpoint branches.
- Change a critical state through a generic edit endpoint.
- Claim that an offline handoff was detected automatically.

Place actor checks, state checks, quantity checks, duplicate checks, and transactional writes in the Service.

## 3. Endpoint selection

Generate only endpoints enabled by the module specification and selected profile.

| Capability | Current platform path pattern | Default decision |
|---|---|---|
| Public details | `GET /free/details/{id}` | Disabled unless anonymous details are required |
| Public page | `GET /free/page` | Disabled unless anonymous listing is required |
| Management page | `GET /page` | Retain for managed business records |
| Create | `POST /create` | Retain only when direct creation is a real operation |
| Edit | `POST /edit` | Retain only for ordinary editable fields |
| Remove | `POST /remove` | Retain only when deletion is allowed |
| Recover | `POST /recover` | Disabled unless recovery is required and supported |
| Batch status | `POST /batch/status` | Disabled unless status is ordinary enable/disable data |
| Batch sort | `POST /batch/sort` | Disabled unless manual sorting is required |
| Metadata | `GET /metadata` | Retain when the low-code management page consumes it |
| Export | `GET /export` | Disabled unless requirements enable export |
| Import | `POST /import` | Disabled unless requirements enable import |

Use a dedicated action path for confirmed business transitions, for example `/submit`, `/review`, `/confirm-issue`, `/apply-return`, `/confirm-return`, `/report-loss`, or `/complete`. The exact name must come from the module specification and match the frontend call.

Treat the scaffold `/create`, `/edit`, and `/remove` endpoints as management operations. A learner, customer, applicant, reporter, or other ordinary user submitting a business request needs a dedicated authenticated action and server-owned identity, even when the action also inserts one row. Do not expose the management create authority to make a user submission work.

Do not retain a KeyModule endpoint merely because it exists in the scaffold.

## 4. Request and response boundaries

Use the Entity as request input only for simple CRUD when all client-writable fields are safe and explicit.

Generate a DTO when:

- Create and edit accept different fields.
- The Entity contains server-owned identity, state, creator, quantity, total, audit, or deletion fields.
- A workflow action needs only a small, purpose-specific input.
- Validation rules differ by action.
- The request contains several related objects or identifiers.

Generate a VO when a response combines associated names, calculated values, statistics, or workflow display state. Do not add associated display names to the persistent Entity only to satisfy a list page.

Return the platform's existing response shape. Keep the declared generic type aligned with the actual Service result. For pagination, align `CommonPage`, `PageList<...>`, Service paging, and frontend expectations.

Never accept these values from the client when the server can determine them:

- Current user identity.
- Creator or operator identity.
- Privileged role or permission.
- Final workflow state.
- Calculated totals, remaining inventory, or aggregate scores.
- Creation time, update time, or logical-deletion marker.

## 5. Permission generation

Use the current naming convention unless the inspected project defines a different confirmed convention:

```text
manage:dir:<module-key>
manage:page:<module-key>:base
manage:btn:<module-key>:create
manage:btn:<module-key>:edit
manage:btn:<module-key>:remove
manage:btn:<module-key>:export
manage:btn:<module-key>:import
```

For a new independent admin module, register permissions as a three-level tree:

1. A top-level module directory with permission type `0`, route `/main/modules/<module-key>/pages`, and no parent.
2. A business page with permission type `1`, route `/main/modules/<module-key>/pages/base`, and the directory as its parent.
3. Retained action buttons with permission type `2` and the business page as their parent.

The directory and page may deliberately share the same visible name, such as both being “训练场地管理”. Their identity comes from `manage:dir:trainingVenue` and `manage:page:trainingVenue:base`, not from the visible name.

Use `create_module_directory` by default for an independent module. Use `attach_existing_directory` only when the module specification explicitly provides the existing parent permission code. Resolve parents by permission code, never by visible name or a fixed numeric ID. If an explicitly required existing parent is missing, block generation or execution; do not fall back to “系统管理” or another menu.

For workflow actions, create a specific button authority whose final segment describes the action. Reuse an existing authority only when it represents the same business power. Do not protect issue, return, settlement, approval, or completion with a generic edit authority merely to avoid adding permission data.

Set every action's access mode explicitly in the module specification:

- `authenticated`: any authenticated actor in the stated role and data scope may call it; no management button authority is implied.
- `authority`: the Controller must use the exact stated authority and permission SQL must register it.
- `public`: intentionally anonymous; use only when the requirement and security configuration both permit it.

Keep these artifacts synchronized:

1. Controller `@PreAuthorize` expression.
2. Permission/menu SQL authority string.
3. Frontend menu or button authority when it exists.
4. Requirement traceability matrix.

Public `/free` endpoints have no management authority annotation, so generate them only after confirming the data is intentionally public. Authentication without a button authority still requires the platform's security rules to support the path.

## 6. Identity and data scope

Permissions answer whether an actor may invoke an operation. Data scope answers which records that actor may see or change. Implement both.

The Controller must not accept a user identifier and assume it is the current user. The Service obtains the current identity from the platform security utility.

Define data scope in the module specification, then enforce it in Service queries and mutations. Examples include:

- Administrator sees all records.
- Creator sees records created by that account.
- Coach sees courses, teams, or learners actually assigned to that coach.
- Learner sees records owned by that learner.

Do not copy the KeyModule creator-only rule into every module. Relation modules must derive scope from their real associations.

## 7. Workflow actions

Every critical transition gets a dedicated Controller method and purpose-specific Service method.

A workflow endpoint should expose only the minimum input needed for the action. The Service must reload the current record and decide whether the transition is allowed. Typical Controller flow:

```java
@PostMapping("/confirm-return")
@PreAuthorize("hasAuthority('manage:btn:equipmentClaim:confirmReturn')")
public SimpleHttpResponse<String> confirmReturn(@RequestBody ConfirmReturnDTO input) {
    return new SimpleHttpResponse<String>().fromMap(service.confirmReturn(input));
}
```

Treat this as a structural pattern, not a requirement to create that exact equipment action in unrelated projects.

Do not place inventory restoration, loss deduction, score creation, settlement, or cross-table writes in the Controller.

## 8. Import, export, and metadata

Retain metadata only when the current low-code page consumes it. Metadata fields must match actual Entity, DTO, VO, query, and form capabilities; remove unresolved KeyModule placeholders.

Retain import or export only when explicitly required:

- Entity or DTO column annotations must match the chosen import/export model.
- Import must validate each row and must not bypass business invariants.
- Export must apply the same permission and data scope as the normal query.
- Large or asynchronous import/export is not invented unless the project already supports it.
- A generated export endpoint is not reported as verified until its response has been tested.

## 9. Error and log handling

Use the project's existing error response and global exception facilities. Do not create a new exception hierarchy for one module.

The Controller may catch stream-specific failures where an HTTP file response has already begun. Ordinary validation and business failures belong in the Service or global handler.

Log enough context to diagnose the operation, but do not log passwords, tokens, complete uploaded files, or unnecessary personal data. A log message is not a substitute for a persistent business-flow record when requirements need traceable issue, return, approval, or settlement history.

## 10. Generation checklist

- Controller path and package match the module directory.
- Module prefix does not collide with an existing Controller.
- Only specification-enabled endpoints remain.
- Every management/action endpoint has the correct authority.
- Controller authority strings match permission SQL exactly.
- Public endpoints expose only intentionally public data.
- Current identity is obtained by the server.
- Data scope is implemented in the Service for reads and writes.
- Workflow transitions use dedicated actions, not generic edit.
- Request DTO excludes server-owned fields.
- Response generic types match actual payloads.
- Pagination uses the current platform facilities.
- Import, export, and metadata are removed when disabled.
- No KeyModule placeholder remains.
