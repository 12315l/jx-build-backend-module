---
name: jx-build-backend-module
description: Create, enhance, and audit backend business modules for this Spring Boot and MyBatis-Plus low-code platform. Use when Codex receives role-based feature lists, core business flows, project requirements, or existing code and needs to produce module specifications or generate Controller, Service, DAO, Entity, SQL, DTO, VO, or Mapper XML under system.store.functionModule.
---

# Build Low-Code Backend Modules

## Core outcome

Convert project requirements into a traceable module specification, then use that specification to generate and verify backend code that matches the current platform.

Treat the module specification as the contract between business requirements and code. Do not begin code generation while an outcome-changing field remains unresolved.

## Follow the source priority

Use facts in this order:

1. Apply the user's latest explicit corrections, goals, and prohibitions.
2. Use the current project's role-based feature list and core flows as the target state.
3. Inspect the database, Java code, APIs, permissions, and frontend calls to establish the current state.
4. Inspect `src/test/resources/KeyModule` and `ModuleMaker` for the platform's generation contract.
5. Use similar modules only as structural evidence.
6. Use bundled patterns only to detect gaps; never add requirements silently.

Mark a requested but absent capability as `to_develop`. Mark code excluded by the latest requirements as `to_remove`. Never report either as verified.

## Run checks and guarded scaffold

Use the bundled Python tools only as Skill infrastructure and never copy them into `base-framework`, `src/main/java`, or a generated business module. Inspection, validation, and trimming-plan tools are read-only. `scaffold_module.py` is read-only by default and is the only bundled tool in this phase that may write project files when all execution gates pass.

Run the relevant checks with the active Python runtime:

```text
python <skill-dir>/scripts/inspect_platform.py <project-root> --format json
python <skill-dir>/scripts/inspect_module.py <project-root> <ModuleName> --format json
python <skill-dir>/scripts/validate_project_requirements.py <requirements-file> --format json
python <skill-dir>/scripts/validate_traceability.py <project-root> <traceability-file> --gate mapping --format json
python <skill-dir>/scripts/validate_traceability.py <project-root> <traceability-file> --gate verification --format json
python <skill-dir>/scripts/validate_module_spec.py <spec-file> --gate analysis --format json
python <skill-dir>/scripts/validate_module_spec.py <spec-file> --gate generation --format json
python <skill-dir>/scripts/scaffold_module.py <project-root> <spec-file> --format json
python <skill-dir>/scripts/scaffold_module.py <project-root> <spec-file> --execute --confirm-authorized --format json
python <skill-dir>/scripts/plan_template_trim.py <project-root> <spec-file> --format json
python <skill-dir>/scripts/validate_module.py <project-root> <ModuleName> --spec <spec-file> --format json
```

Treat exit code `2` as a blocking result. Use `--format text` for a human-readable report and `--format json` when chaining results. `validate_module_spec.py` needs PyYAML for YAML input and also accepts JSON input without that dependency.

- Run `inspect_platform.py` before resolving output roots.
- Run `inspect_module.py` before enhancing an existing module or selecting a structural reference.
- Run `validate_project_requirements.py` after receiving a role/flow document; treat extracted IDs and signals as candidates until code evidence confirms them.
- Copy `assets/project-traceability-template.yaml`, complete every role feature and core-flow step, then run `validate_traceability.py --gate mapping` before splitting work into module specifications. Use the verification gate only after implementation and required checks are complete.
- Run the specification analysis gate while drafting and the generation gate immediately before project writes.
- Run `scaffold_module.py` without `--execute` first. Execute only after the user authorized implementation, the specification generation gate passes, the operation mode is `create_new`, and the target module does not exist.
- Treat the five generated Controller, Service, DAO, Entity, and SQL files as an untrimmed scaffold, not completed business code.
- Run `plan_template_trim.py`, apply enabled/disabled capability decisions across Controller, Service, Entity, permission SQL, and frontend calls, then add real fields, DTO/VO, actions, transactions, and queries.
- Run `validate_module.py` after changes. Resolve structural blockers before compilation and keep SQL generation, execution, and verification as separate states.
- Before Maven compilation, compare the Java level required by `pom.xml` with the runtime reported by `mvn -v`; do not rely on `java -version` alone. If a matching installed JDK is available, use a process-scoped `JAVA_HOME` and `PATH` for the compile command rather than changing machine-wide configuration.
- Recheck Git/worktree changes separately because the read-only scripts deliberately do not invoke Git or modify files.

## Normalize project requirements

Read [references/requirements-to-code.md](references/requirements-to-code.md) completely when the user provides a project-wide role feature list or core flows.

Use [assets/project-requirement-template.md](assets/project-requirement-template.md) when the user needs a reusable business input form. Use [assets/requirement-traceability-template.md](assets/requirement-traceability-template.md) for a readable review document and [assets/project-traceability-template.yaml](assets/project-traceability-template.yaml) for the machine-checkable source of feature coverage, flow-to-code mappings, conflicts, decisions, and verification results.

Complete project-level traceability before splitting a project into module specifications. Do not create one backend module per role; group shared business objects and vary Controller permissions and data scopes.

## Build a module specification

Read [references/module-specification.md](references/module-specification.md) completely before creating or changing a specification.

Read [references/requirement-signal-mapping.md](references/requirement-signal-mapping.md) completely when converting business wording into shared objects, actions, data scopes, generation profiles, and code-layer destinations. Treat its signals as inspection prompts, never as authorization to add features.

Copy [assets/module-spec-template.yaml](assets/module-spec-template.yaml) for each target business module and fill it from requirements plus inspected project facts.

Perform these steps:

1. Assign requirement IDs to every role feature and flow-step IDs to every core-flow step.
2. Separate online operations from offline cooperation.
3. Identify the shared business object instead of creating duplicate modules for each role.
4. Set the canonical package to `system.store.functionModule.<PascalName>Module` unless the user explicitly approves a project-level exception.
5. Select one generation profile: `quick_crud`, `standard_relation`, `business_workflow`, or `statistics_query`.
6. Define fields, queries, permissions, data scopes, actions, state transitions, transactions, and invariants.
7. Decide every KeyModule capability switch explicitly.
8. Map every requirement and flow step to its intended Controller, Service, DAO, Entity, SQL, DTO, VO, or Mapper XML destination.
9. Record unresolved questions instead of guessing.

## Enforce specification gates

Use these statuses:

- `draft`: Important business information is missing. Analyze only.
- `ready`: The specification is complete enough for a file preview.
- `authorized`: The user explicitly requested implementation and the specification is complete.
- `implemented`: Files were written but verification is incomplete.
- `verified`: Required checks passed and remaining limitations are reported.

An explicit implementation request with a complete specification counts as authorization; do not ask for redundant confirmation. Stop when ambiguity changes permissions, data, states, quantities, or database structure.

## Keep the platform contract

- Use `base-framework/src/main/java/system/store/functionModule/<PascalName>Module` as the current repository's default business output path.
- Resolve the configured backend root before writing so the `base-framework` segment is not duplicated when another same-platform project opens that module as its root.
- Use the package root `system.store.functionModule.<PascalName>Module`.
- Generate Controller, concrete Service, DAO, Entity, and module SQL for persistent business modules.
- Add DTO and VO only for real input or combined-output boundaries.
- Add `src/main/resources/mapper/function/<PascalName>Mapper.xml` only for necessary complex joins or aggregations.
- Reuse existing user, role, menu, response, pagination, security, and exception facilities.
- Do not create a parallel Service interface layer when the platform uses concrete Service classes extending `ServiceImpl`.

## Plan Java backend output

Read [references/code-generation-profiles.md](references/code-generation-profiles.md) completely before planning or generating project files. Read [references/keymodule-template.md](references/keymodule-template.md) completely before using or trimming KeyModule.

Copy [assets/module-outline-template.md](assets/module-outline-template.md) to preview exact project-relative paths and retained capabilities before writing.

Generate project business code only as Java, SQL, and necessary Mapper XML. Keep any future Python helper scripts inside the Skill's own `scripts` directory; never copy them into `base-framework`, `src/main/java`, or `system.store.functionModule`.

## Generate each backend layer

Read the reference for every layer that the planned change touches:

- Read [references/controller-and-permission.md](references/controller-and-permission.md) completely before generating Controller endpoints, request boundaries, permission annotations, or permission SQL.
- Read [references/frontend-contract.md](references/frontend-contract.md) completely when an admin or user-facing frontend module exists, frontend integration is in scope, or backend fields, filters, permissions, and response shapes must match current low-code page configuration.
- Read [references/service-and-transaction.md](references/service-and-transaction.md) completely before generating business validation, role data scope, workflow transitions, quantity changes, or transactions.
- Read [references/entity-and-database.md](references/entity-and-database.md) completely before generating Entity, DTO, VO, table fields, constraints, indexes, or database migration plans.
- Read [references/sql-and-mapper.md](references/sql-and-mapper.md) completely before generating DAO methods, Mapper XML, table SQL, migration SQL, or permission SQL.

Generate Java source files beneath `system.store.functionModule.<PascalName>Module`, SQL inside that module's `db` directory, and conditional Mapper XML under `src/main/resources/mapper/function`. These references do not authorize Python output in the business project.

Apply the cross-layer rules as one contract:

1. Controller exposes only specification-enabled operations and delegates business decisions.
2. Service obtains server identity, enforces data scope, validates transitions, and owns transactions.
3. Entity, DTO, and VO separate persistence, client input, and combined output.
4. DAO and Mapper implement only necessary data access.
5. Table SQL, permission SQL, Java types, endpoint permissions, and frontend calls remain aligned.

## Select reusable rules

Load only the references relevant to the current specification:

- Read [references/java-sql-type-mapping.md](references/java-sql-type-mapping.md) completely before deciding or changing Java fields, SQL columns, identifiers, dates, quantities, states, precision, nullability, or defaults.
- Read [references/query-pattern-catalog.md](references/query-pattern-catalog.md) completely before selecting MyBatis-Plus, custom DAO, Mapper XML, latest-record, aggregate, ranking, duplicate, or conditional-quantity queries.
- Read [references/project-archetype-composition.md](references/project-archetype-composition.md) completely only when classifying a new project or composing reusable graduation-project capability groups.

Use project archetypes to find questions and reuse opportunities. Never use them to add optional capabilities without a requirement ID or verified existing behavior.

## Control KeyModule capabilities

Treat KeyModule as a scaffold, not as confirmed business scope.

- Keep admin details, admin page, and low-code metadata when the module needs standard management.
- Default public details, public page, recovery, batch status, batch sort, Excel import, and Excel export to disabled unless requirements enable them.
- Keep create, edit, remove, and permission SQL only when the module's profile and requirements need them.
- Remove disabled capabilities consistently from Controller, Service, Entity annotations, permission SQL, and frontend calls.

## Preserve traceability

Before implementation, produce:

- A feature coverage matrix mapping each role feature to a module, implementation state, permission, code layer, and acceptance check.
- A flow-to-code matrix mapping every flow step to online/offline handling, validation, data changes, state changes, transactions, failure outcomes, and files.

After implementation, update both matrices with actual file locations and verification results.

Run the traceability mapping gate before creating module specifications. It must reject duplicate or malformed IDs, missing module ownership, online steps without Controller and Service destinations, mixed steps without a named human confirmation, pure offline steps that claim automatic state changes, missing evidence files, and removed capabilities without a disposition. A successful mapping gate means the mapping is structurally complete; it does not mean the implementation is verified.

## Never invent behavior

- Do not turn offline handoffs into QR codes, positioning, automatic sensing, payment, or messaging unless requirements and code support them.
- Do not use generic edit endpoints to change critical workflow states, inventory, or settlement results.
- Do not trust client-submitted user identity, calculated totals, or privileged states.
- Do not describe generated SQL as executed unless it was actually run and verified.
- Do not overwrite an existing module with ModuleMaker. Inspect and enhance it incrementally.
- Preserve unrelated user changes and report any overlap before editing.
