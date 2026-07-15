# Project archetype composition rules

## Contents

1. Purpose and safety rule
2. Common capability library
3. Management master
4. Application and appointment master
5. Repair and work-order master
6. Commerce and order master
7. Campus and community service master
8. Course and content master
9. Recommendation and statistics enhancements
10. Mini Program and APP variants
11. Domain category mapping
12. Composition checklist

## 1. Purpose and safety rule

Use this reference only to classify a new project, select likely reusable capability groups, and detect missing requirement decisions.

An archetype is not a feature list. Never add a module, field, state, endpoint, permission, payment, message, rating, recommendation, or statistic solely because it appears in an archetype.

For every candidate capability, require a requirement ID or verified existing implementation before generating code.

## 2. Common capability library

Prefer existing platform base capabilities before creating business modules.

| Capability group | Typical functions | Reuse rule |
|---|---|---|
| Account | Register, login, profile, password | Reuse authentication/user modules |
| Administration | User, role, menu, permission | Reuse base management modules |
| Information management | Create, page, details, edit, remove, filter | Generate per real business object |
| Application/review | Submit, review, state result | Use dedicated workflow actions |
| Order | Cart, order, simulated payment, state | Include only explicitly required parts |
| Interaction | Like, collection, comment, rating | Reuse existing action modules when target types fit |
| News/notice | Publish, list, details | Reuse existing content patterns when compatible |
| Upload | Avatar, image, attachment reference | Reuse platform upload behavior |
| Statistics | Bar, line, pie, rank data | Generate real aggregate endpoints only |
| Recommendation | Popular, category, history, collection-based | State the actual rule; do not overclaim algorithms |
| Client API | Login, list, details, submit/order/comment | Reuse the same backend object and scope; do not duplicate tables per client |

## 3. Management master

Applicable domains include dormitory, library, warehouse, asset, medicine, contract, driving-school, and other information-management systems.

Minimum candidate structure:

- Existing account/role/permission base capability.
- One or more `quick_crud` business modules.
- Management page, details, create, edit, and only the deletion/status actions actually required.
- Optional statistics query based on real stored records.

Do not generate a user-facing workflow when the requirement is administrator-only management.

## 4. Application and appointment master

Applicable domains include venue booking, laboratory booking, registration, service appointment, ticket reservation, activity registration, leave, and other request/review systems.

Candidate structure:

- Target/service master module.
- Application/appointment relation module.
- Submit action and “my records” query.
- Administrator or staff review/confirmation action when required.
- State transition table, duplicate/time/capacity checks, and result query.

Use `standard_relation` when no reviewed lifecycle exists. Use `business_workflow` when review, cancellation, capacity changes, or confirmation changes state/data.

## 5. Repair and work-order master

Applicable domains include dormitory repair, property repair, equipment maintenance, after-sales, and service tickets.

Candidate structure:

- Issue/work-order record.
- Submitter, responsible handler, description, attachments when required.
- Dedicated accept/assign/process/complete actions actually present in the flow.
- Optional evaluation only when explicitly required after completion.
- Operation/history records when process traceability is required.

Do not invent assignment, messaging, technician location, parts, fees, or evaluation.

## 6. Commerce and order master

Applicable domains include book, agricultural product, snack, flower, eyewear, course, food-ordering, and similar sales platforms.

Candidate structure may include product/category, cart, address, order/detail, payment result, collection, comment, and inventory.

Enable each independently. If the requirement says simulated payment, do not integrate a real payment provider. Define order state, inventory timing, cancellation restoration, duplicate payment protection, and price source before generating workflow code.

Do not force a cart into a direct-purchase project or an address into an on-site service project.

## 7. Campus and community service master

Applicable domains include second-hand exchange, clubs, parcel pickup, lost-and-found, textbook ordering, volunteer service, household service, pet care, elder service, tool rental, and property service.

Classify the real core flow before choosing a backend master:

- Publish/browse/contact information: content or relation management.
- Request/review/result: application master.
- Appointment/service record/evaluation: appointment or work-order master.
- Borrow/issue/return/damage: circulation workflow with quantity invariants.
- Trade/order/payment: commerce master.

The domain label “campus” or “community” does not decide the workflow.

## 8. Course and content master

Applicable domains include online courses, book borrowing, reading/recommendation, question banks, programming learning, youth training, and content-learning platforms.

Separate confirmed objects:

- Course/book/content definition.
- Concrete schedule/chapter/question when independently managed.
- Enrollment, purchase, or borrowing relation.
- Attendance, learning, progress, or return record only when required.
- Comment/collection/recommendation/statistics as optional enhancements.

Do not conflate course information with class schedules, enrollment with attendance, or content browsing with verified learning completion.

## 9. Recommendation and statistics enhancements

Recommendation and statistics are enhancement profiles, not universal base modules.

For recommendation, choose only a confirmed method:

- Popular based on real counts.
- Category/tag matching.
- Browsing/collection/score history.
- Verified collaborative filtering.

Name the feature according to what is actually implemented. A rule-based result must not be described as AI or collaborative filtering.

For statistics, define each metric source, scope, time field, grouping, formula, and empty-data behavior. ECharts or another frontend chart is a consumer, not proof that the backend metric exists.

## 10. Mini Program and APP variants

Mini Program and APP are client variants, not separate business data architectures.

- Reuse the same Java business modules, tables, state machines, and invariants.
- Add or adapt authenticated client endpoints only when response/input contracts differ.
- Keep management actions in the authorized management interface.
- Define file upload, login identity, pagination, and error contracts for the client.
- Do not duplicate the same business record in separate “mini-program tables” or “APP tables”.

Environment, packaging, and client debugging are outside this backend Skill unless the user includes those projects in scope.

## 11. Domain category mapping

Use domain categories only as starting classifications:

| Domain category | Likely primary master | Common optional enhancement |
|---|---|---|
| Background information management | Management | Statistics, upload, notice |
| Appointment/registration/application | Application/appointment | Capacity, cancellation, statistics |
| Repair/work order/after-sales | Work order | Assignment, history, evaluation |
| Commerce/sales | Commerce/order | Inventory, comment, collection, statistics |
| Campus life | Determine from actual flow | Notice, interaction, upload |
| Education/course/book | Course/content or circulation | Attendance, progress, recommendation |
| Community services | Appointment/work order/circulation | Evaluation, statistics |
| Travel/hospitality/food | Appointment or commerce | Showcase, evaluation, statistics |
| Sports/entertainment | Management, registration, or course | Statistics, recommendation |
| Recommendation system | Existing domain master plus recommendation | Statistics |
| Data-statistics enhancement | Existing source modules plus statistics query | Dashboard API |
| Mini Program | Any master plus client API | Upload, client paging |
| APP | Any master plus client API | Upload, client paging |

## 12. Composition checklist

- Project is classified by real flow, not title alone.
- Every selected capability has a requirement ID.
- Base user/role/menu/upload capabilities are reused.
- Business modules remain under `system.store.functionModule.*`.
- One archetype did not silently add all optional functions.
- State, quantity, payment, recommendation, and evaluation details are explicit.
- Mini Program/APP reuse the same business lifecycle.
- Statistics and recommendations use real data and accurately named methods.
- Removed or prohibited features stay excluded even if common in the archetype.

