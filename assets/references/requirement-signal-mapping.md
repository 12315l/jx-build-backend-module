# Requirement signal mapping rules

## Contents

1. Purpose
2. Evidence and anti-invention rule
3. Business object extraction
4. Action signal catalog
5. Role and data-scope signals
6. State and quantity signals
7. Module grouping rules
8. Generation profile decision
9. Cross-layer destinations
10. Mapping checklist

## 1. Purpose

Use this reference after normalizing role features and core-flow steps, and before creating module specifications.

Convert business wording into implementation candidates. A wording signal identifies what to inspect; it does not prove that a feature exists or authorize adding it.

## 2. Evidence and anti-invention rule

For every candidate capability:

1. Keep the original requirement ID and wording.
2. Identify the actor, action, business object, scope, and expected outcome.
3. Inspect current Controller, Service, Entity, SQL, permissions, and frontend calls.
4. Mark the candidate as existing, partial, to develop, to remove, or to confirm.
5. Add it to a module specification only when the requirement or verified current behavior supports it.

Project archetypes, similar projects, KeyModule, menu names, and field names may expose gaps. They must not silently expand the target scope.

## 3. Business object extraction

Extract nouns and lifecycles before mapping actions to files.

| Requirement wording | Candidate business object | Required distinction |
|---|---|---|
| Course information, course center | Course | Separate course definition from concrete class schedule |
| Class session, training time | Course schedule | Separate schedule from enrollment and attendance |
| Enrollment, registration | Course order or enrollment | Identify self-enrollment versus administrator assignment |
| Sign-in, attendance review | Attendance | Identify learner action versus coach/admin confirmation |
| Equipment application, issue, return | Equipment claim | Separate equipment master inventory from circulation record |
| Damage, loss, write-off | Equipment circulation outcome | Define quantity and inventory consequence explicitly |
| Team, member selection | Team and membership relation | Separate team master from member relation |
| Match arrangement, lineup, performance | Match, lineup, player performance | Separate event, tactical assignment, and post-match record |
| Comment, like, collection | User action relation | Verify whether a shared existing interaction module applies |
| Dashboard, trend, rank | Statistics query | Do not create a table unless an independent record exists |

Do not create one module per page or role. Group requirements that share one business object and lifecycle.

## 4. Action signal catalog

| Business signals, including common Chinese wording | Candidate backend behavior | Mandatory decisions |
|---|---|---|
| 查看、浏览、查询、详情、列表 | Query endpoint and scoped Service query | Public/authenticated, filters, scope, response shape |
| 新增、录入、发布、创建 | Create operation | Actor, writable fields, defaults, duplicate rule |
| 修改、维护、编辑 | Ordinary edit or dedicated action | Editable fields, ownership, immutable fields |
| 删除、下架、停用 | Logical delete, physical delete, or enable switch | Lifecycle meaning, dependencies, recovery |
| 提交、申请、报名、预约 | Dedicated submit/create action | Eligibility, identity, initial state, duplicate/limit rule |
| 审核、审批、通过、驳回 | Dedicated review transition | Reviewer, source state, reason, target state |
| 确认、发放、核销、结算 | Dedicated confirmed transition | Offline prerequisite, quantities, transaction, idempotency |
| 归还、取消、撤回、退款 | Dedicated reverse/termination action | Allowed source state, restoration, final outcome |
| 补录、代报名、代操作 | Authorized action on behalf of another user | Operator versus owner, reason/source, audit |
| 上传、头像、附件、封面 | Existing upload capability plus stored path/reference | File type, size, ownership, deletion behavior |
| 评论、点赞、收藏、评分 | Interaction relation and scoped query | Target type, duplicate rule, cancellation behavior |
| 统计、趋势、排行、占比 | Read-only aggregation | Source, formula, date range, grouping, empty data |
| 推荐、智能选人、猜你喜欢 | Rule/algorithm result | Inputs, actual method, deduplication, explainable limits |
| 导入、导出 | Conditional batch capability | Permission, validation, data scope, enabled file model |

The word “manage” does not automatically enable create, edit, remove, recover, batch status, import, and export. Resolve each operation separately.

## 5. Role and data-scope signals

Map role wording to a scope candidate, then verify the real relation.

| Wording | Candidate scope | Required evidence |
|---|---|---|
| 我的、本人 | Current logged-in user | Server identity and ownership field/relation |
| 本人课程、所带学员 | Assigned coach scope | Course coach relation, enrollment, or team membership |
| 本队伍、负责队伍 | Assigned team scope | Team coach/manager relation |
| 指定学员、代报名 | Administrator or authorized operator | Permission plus target-user validation |
| 全部、全平台、统一管理 | Administrator/global scope | Page/action authority and role support |
| 公开、首页展示 | Anonymous/public scope | Security rule and safe public data set |

Never infer global access from the word “management” alone. Apply scope to details, pages, actions, exports, and statistics consistently.

## 6. State and quantity signals

Escalate a module from ordinary CRUD when wording implies lifecycle control.

State signals include pending, processing, approved, rejected, issued, in use, returning, completed, cancelled, damaged, lost, passed, or failed. For each state signal, require a transition table and dedicated actor/action decision.

Quantity signals include stock, available count, capacity, enrollment limit, returned count, lost count, score, points, amount, and remaining count. For each quantity signal, require:

- Source of truth.
- Positive/range rule.
- Exact step that increases, deducts, restores, or writes off.
- Duplicate-action protection.
- Transaction boundary.
- Non-negative or conservation invariant when applicable.

Do not convert a status word into a numeric code until existing code and SQL are inspected.

## 7. Module grouping rules

Create or retain one module when requirements share:

- One primary persisted object.
- One lifecycle and state machine.
- One permission family.
- One transaction owner.

Split modules when objects have independent lifecycles, separate master/relation records, or distinct transaction ownership. Examples include course versus schedule, equipment versus claim, team versus membership, and match versus player performance.

Reuse base modules for account, role, menu, dictionary, authentication, password, and existing upload behavior. Do not duplicate them under `functionModule`.

Keep a read-only statistics capability inside an analysis module or the owning Service unless it persists a real independent report record.

## 8. Generation profile decision

Choose the strongest matching profile:

| Signals | Profile |
|---|---|
| One master object, ordinary query/create/edit/remove | `quick_crud` |
| User/object relation, associated names, duplicate relation, scoped ownership | `standard_relation` |
| Review, confirm, state transition, quantity change, multi-record write | `business_workflow` |
| Trend, count, share, ranking, dashboard without independent persistence | `statistics_query` |

If one module contains workflow signals, do not downgrade it to relation or CRUD. Statistics attached to a workflow module do not change its primary workflow profile; add only the required read queries.

## 9. Cross-layer destinations

| Requirement result | Primary destination |
|---|---|
| Page/detail/action entry | Controller |
| Actor, scope, validation, transition, transaction | Service |
| Stored business attributes | Entity and table SQL |
| Purpose-specific client input | DTO |
| Associated/calculated display result | VO or DTO result model |
| Ordinary single-table access | Service/MyBatis-Plus and base DAO |
| Complex relation or aggregate query | Custom DAO and conditional Mapper XML |
| Page/button authority | Controller annotation and permission SQL |
| Offline event | No automatic code; optional confirmed online action only |

Every destination must retain the originating requirement or flow-step ID in traceability.

## 10. Mapping checklist

- Every feature retains its original wording and stable ID.
- Every action has an actor, object, scope, and outcome.
- Similar-project functions were not added without a requirement.
- Shared objects are grouped across roles.
- Independent lifecycles are not forced into one generic table.
- “Manage” was split into actual authorized operations.
- State and quantity wording escalated to explicit workflow rules.
- Offline steps remain offline or mixed human confirmations.
- Each module has one justified generation profile.
- Every code destination has a requirement source.

