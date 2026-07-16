# Frontend contract rules for backend generation

## Contents

1. Purpose and boundary
2. Current platform evidence
3. Page configuration to API mapping
4. Pagination and response shape
5. Select options and associated display data
6. Button permissions
7. Current-user and server-owned values
8. Custom rendering and DTO/VO decisions
9. Build and verification
10. Checklist

## 1. Purpose and boundary

Use this reference when a backend module has an existing or planned page in `jx-template-admin` or `jx-template-front`.

This is not a frontend-building guide. Use it to keep Controller inputs, Service results, permissions, fields, and frontend calls aligned. Inspect the current source before applying any convention because generated or older projects may differ.

Do not copy historical frontend examples, dependency versions, environment addresses, theme values, or component snippets into a new project without current source evidence.

## 2. Current platform evidence

The inspected platform currently contains:

- Management modules under `jx-template-admin/src/views/main/modules`.
- User-facing modules under `jx-template-front/src/views/main/modules`.
- Shared list loading in `src/hooks/useFetchList.ts`.
- Shared create/edit handling in `src/hooks/useModalHandler.ts`.
- Configurable forms and tables in `src/components/PageModal` and `src/components/PageContent`.
- Menu and button checks in `src/utils/map-menus.ts`.
- Current-user display state in `src/store/main/main.ts`.

Treat these paths as inspected facts for this platform version, not universal Vue conventions.

## 3. Page configuration to API mapping

When the module uses configuration files, trace each configured property to the backend contract:

| Frontend source | Backend question |
|---|---|
| `search.config.ts` property | Does the Controller accept it and does the Service actually filter by it? |
| `modal.config.ts` property | Is it client-writable, validated, and accepted by the Entity or action DTO? |
| `content.config.ts` property | Does the response Entity/VO expose the key with the expected meaning? |
| `details.config.ts` property | Does the details endpoint return it without exposing protected data? |
| module `service/index.ts` | Do method, path, HTTP verb, request shape, and response shape match the Controller? |

Do not generate a backend field merely because a page config mentions it. It may be display-only, calculated, associated, or obsolete. Conversely, do not claim a backend filter works because the search field exists; inspect the Service query.

If a form adds a value before submission, still classify it as client input. The Service must overwrite or reject current-user identity, creator, operator, workflow state, totals, inventory, audit time, and deletion markers.

## 4. Pagination and response shape

The current `useFetchList` expects a successful response whose `data` contains `list` and `total`. The backend convention uses `CommonPage` or a confirmed dedicated Page input, `PageList<T>`, `SimpleHttpResponse<T>`, and `PageUtil`.

Keep all four layers aligned:

1. Search and page properties sent by the page.
2. Controller input and declared response generic.
3. Service filtering and `PageUtil.toList` result.
4. Frontend consumption of `data.list` and `data.total`.

Do not revive an older module-specific page class solely because an old example used one. In the current platform, `CommonPage` exposes `name` and `type` in addition to inherited paging properties. Use it only when those properties cover the real request. When a page truly submits status, keyword, time range, relation identifiers, or other filters, define and verify a dedicated Page class instead of calling nonexistent `CommonPage` methods.

The frontend `transform` option may flatten or rename nested response values for display. Prefer a clear VO when several pages need the same associated result; prefer a local transform when the shape is presentation-specific and does not justify a persistent field.

## 5. Select options and associated display data

Current configurable selects consume option objects with `labelCode` and `labelValue`. Existing pages often transform domain results such as an identifier plus a display name into this shape.

Do not rename persistent backend properties to `labelCode` or `labelValue` merely to satisfy the component. Return the real domain fields and transform them on the page, unless a shared lookup endpoint is explicitly designed to return the option contract.

For dependent selects:

- Generate a lookup endpoint only when a real data dependency exists.
- Apply role data scope and active-state filters in the Service.
- Return an empty list for no matches, not invented options.
- Do not treat a dictionary selection as proof that another backend query is required.

## 6. Button permissions

Keep these aligned:

1. Controller `@PreAuthorize` authority.
2. Permission/menu SQL code.
3. Page route that owns the button permission.
4. Token passed to `hasButtonPermission`.

The current helper searches button permission codes with a substring check. Therefore use short, distinct action tokens and inspect collision risk; do not assume the helper performs an exact final-segment comparison.

Backend authorization remains mandatory. Hiding a button is not access control. A generic `edit` authority must not protect issue, return, settlement, completion, or approval when those are distinct business powers.

## 7. Current-user and server-owned values

The frontend store exposes `userInfo` for display and page behavior. It is not a trusted identity source for backend writes.

The Service obtains the current actor from the platform security utility. A submitted user identifier may select a business subject only when the actor is authorized to act for that subject, such as an administrator assigning a course. Otherwise ignore or reject it.

Do not infer role authorization from frontend branches such as `isCoach`. Recheck role, ownership, and related-record scope in the Service.

## 8. Custom rendering and DTO/VO decisions

A custom table slot, dialog, image preview, tag, or form slot is a presentation mechanism. It does not prove the backend needs a new table column or endpoint.

Use a DTO when the page sends a purpose-specific action or must exclude server-owned Entity fields. Use a VO when the page needs associated names, calculated values, or a stable aggregate shape. Use a local frontend transform when only one page needs a display-specific flattening.

File upload components submit or retain a file business key or path according to the current file module. Inspect the actual upload and preview calls before choosing the stored value. Do not store raw file content in a normal business Entity unless the project explicitly does so.

## 9. Build and verification

When frontend work is in scope, inspect `package.json` and use its current scripts. Do not hardcode historical Node, Vue, Vite, or dependency versions from an old document.

At minimum verify:

- Module service calls match Controller paths and HTTP methods.
- List responses still provide `list` and `total`.
- Form request properties match the allowed DTO or Entity fields.
- Search properties are actually enforced by the Service.
- Button tokens map to non-colliding permission codes.
- Current-user values cannot bypass backend identity or data scope.
- Frontend build status is reported separately from backend compile status.

## 10. Checklist

- Current admin and front source roots were inspected.
- Page service, config, custom page logic, and shared hooks were inspected when present.
- Every search field has a real Service filter or is removed.
- Every form field is classified as client-writable, server-owned, associated, or display-only.
- Every list/detail field maps to Entity, VO, or an explicit frontend transform.
- Pagination request and response shapes match.
- Select data uses real lookup evidence and correct role scope.
- Button visibility and backend authority are aligned without treating UI hiding as security.
- No frontend-only presentation detail caused an unnecessary database field.
- Backend compile and frontend build are verified and reported independently.
