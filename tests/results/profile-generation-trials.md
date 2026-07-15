# 三类母版代码生成试验

## 试验范围

- 试验日期：2026-07-15
- 通用后台：`AssetCategoryTrialModule`，`quick_crud`
- 预约报名：`CourseEnrollmentTrialModule`，`standard_relation`
- 业务流程：`RepairWorkOrderTrialModule`，`business_workflow`
- 试验方式：在隔离项目副本中执行规格门禁、脚手架、能力裁剪、业务增强、静态验收和 Maven 编译；未执行 SQL。

## 第一轮骨架结果

- 三份授权规格均通过生成门禁，脚手架均在 `system.store.functionModule.*` 下生成 Controller、Service、DAO、Entity 和 SQL 五类文件。
- 未裁剪骨架分别产生 9、11、14 个静态阻断项，包括未启用入口仍存在、规格字段未写入实体和 SQL、业务动作缺失。
- 结论：脚手架只能作为起点，当前验收能够阻止把模板骨架误报为完成代码。

## 第二轮完整结果

| 样例 | 静态验收 | 整合编译 | 关键验证 |
|---|---|---|---|
| 资产分类 | 0 警告、0 阻断 | 通过 | 真实字段、管理增改删、元数据、权限 SQL、未启用入口裁剪 |
| 课程报名 | 0 警告、0 阻断 | 通过 | 专用提交 DTO、当前用户身份、课程存在性、本人范围、重复报名约束 |
| 报修工单 | 0 警告、0 阻断 | 通过 | 专用提交/受理/完成动作、明确权限、状态转换、终态与事务 |

隔离副本使用 Java 17 编译 357 个 Java 源文件，Maven 返回 `BUILD SUCCESS`。原项目基线也在 Java 17 下编译通过。编译产生的两条 Lombok 警告来自原有 `OtherModule` 页面类，不属于本轮模块。

## 试验推动的规则修正

1. 普通用户提交报名或报修必须使用独立的已登录业务动作，不能复用后台 `/create` 管理权限。
2. 每个业务动作必须声明 `authenticated`、`authority` 或 `public` 访问方式；权限动作必须同时给出 Controller 权限和权限 SQL。
3. `standard_relation` 必须明确真实关联模块、实体和目标属性。
4. 状态保存值必须与 Java/SQL 类型兼容，业务名称与保存值分离，动作和转换只能引用已定义状态。
5. DTO、VO 和 Mapper XML 虽为条件文件，但规格一旦声明就必须生成并纳入验收。
6. 验收工具同时支持普通建表和 `CREATE TABLE IF NOT EXISTS`。
7. 当前 `CommonPage` 只有 `name`、`type` 两个业务查询属性；其他真实筛选必须使用明确的专用 Page，不能调用不存在的通用属性。
8. Maven 必须明确使用项目要求的 Java 17；本机默认 Maven Java 8 会在 `--release` 参数处失败。

## 结论

三类母版均完成了从授权规格到可编译 Java/SQL 模块的隔离试验。试验代码未进入正式青训业务目录，SQL 未执行，运行级权限、数据库约束和并发行为仍需在具体项目实施时按需求验证。
