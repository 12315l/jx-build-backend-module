# 后台模块代码预演清单

## 一、模块信息

- 模块规格编号：
- 中文名称：
- 大驼峰名称：
- 小驼峰名称：
- 下划线名称：
- 生成档位：quick_crud / standard_relation / business_workflow / statistics_query
- 操作方式：新建模块 / 增强现有模块 / 只审查
- 规格状态：draft / ready / authorized / implemented / verified

## 二、固定输出位置

- 后台模块根：`base-framework`
- Java 源码根：`base-framework/src/main/java`
- 业务包根：`system.store.functionModule.【模块名】Module`
- 业务目录：`base-framework/src/main/java/system/store/functionModule/【模块名】Module`
- Mapper 目录：`base-framework/src/main/resources/mapper/function`

> 本清单中的项目业务输出只允许 Java、SQL 和必要的 Mapper XML。Skill 自身辅助脚本不进入上述目录。

## 三、计划创建的业务文件

| 文件类型 | 项目相对路径 | 是否生成 | 生成依据 | 来源需求或流程 |
|---|---|---|---|---|
| Controller | `base-framework/src/main/java/system/store/functionModule/【模块名】Module/controller/【模块名】Controller.java` | 是 / 否 |  |  |
| Service | `base-framework/src/main/java/system/store/functionModule/【模块名】Module/service/【模块名】Service.java` | 是 / 否 |  |  |
| DAO | `base-framework/src/main/java/system/store/functionModule/【模块名】Module/dao/【模块名】Dao.java` | 是 / 否 |  |  |
| Entity | `base-framework/src/main/java/system/store/functionModule/【模块名】Module/model/entity/【模块名】.java` | 是 / 否 |  |  |
| SQL | `base-framework/src/main/java/system/store/functionModule/【模块名】Module/db/c_【下划线名】_table.sql` | 是 / 否 |  |  |
| DTO | `base-framework/src/main/java/system/store/functionModule/【模块名】Module/model/dto/【用途】DTO.java` | 是 / 否 |  |  |
| VO | `base-framework/src/main/java/system/store/functionModule/【模块名】Module/model/vo/【用途】VO.java` | 是 / 否 |  |  |
| Mapper XML | `base-framework/src/main/resources/mapper/function/【模块名】Mapper.xml` | 是 / 否 |  |  |

## 四、禁止进入业务目录的文件

| 文件类型 | 处理规则 |
|---|---|
| Python、Shell、Node 辅助脚本 | 只能存在于 Skill 自身工具目录，不能生成到业务模块 |
| 需求分析文档 | 保存在设计或工作产物目录，不进入 Java 包 |
| 临时扫描结果 | 保存在临时目录，不纳入项目业务源码 |
| 与当前模块无关的公共框架修改 | 不实施，除非用户单独授权 |

## 五、KeyModule 能力开关

| 能力 | 开启 / 关闭 / 待确认 | Controller 影响 | Service 影响 | Entity / SQL 影响 | 权限与前端影响 |
|---|---|---|---|---|---|
| 后台详情与分页 |  |  |  |  |  |
| 新增 |  |  |  |  |  |
| 修改 |  |  |  |  |  |
| 逻辑删除 |  |  |  |  |  |
| 公开详情 |  |  |  |  |  |
| 公开分页 |  |  |  |  |  |
| 删除恢复 |  |  |  |  |  |
| 批量状态 |  |  |  |  |  |
| 批量排序 |  |  |  |  |  |
| 低代码元数据 |  |  |  |  |  |
| Excel 导入 |  |  |  |  |  |
| Excel 导出 |  |  |  |  |  |
| 菜单与按钮权限 SQL |  |  |  |  |  |

## 六、Java 类内容预演

### 1. Controller

- 路径前缀：
- 保留的标准接口：
- 新增的专用业务接口：
- 公共接口：
- 页面权限：
- 按钮权限：
- 使用的 DTO / VO：

### 2. Service

- 继承结构：`ServiceImpl<【模块名】Dao, 【模块名】>`
- 分页与查询：
- 角色数据范围：
- 创建与修改校验：
- 专用业务动作：
- 状态流转：
- 事务边界：
- 数量或业务约束：
- 操作记录：

### 3. DAO 与 Mapper

- 基础 DAO：`BaseMapper<【模块名】>`
- 自定义 DAO 方法：
- 是否需要 Mapper XML：
- Mapper namespace：
- 查询参数与返回结构：

### 4. Entity 与 SQL

- 数据表：
- 主键：
- 业务字段：
- 关联字段：
- 状态与类型：
- 创建人及时间：
- 逻辑删除：
- 唯一约束：
- 查询索引：
- 新建表或增量修改：

## 七、现有文件修改计划

| 文件 | 修改原因 | 需要保留的用户改动 | 风险 |
|---|---|---|---|
|  |  |  |  |

## 八、需求与流程追踪摘要

| 需求或流程编号 | 计划接口 | 计划 Service 方法 | 数据或状态变化 | 目标文件 |
|---|---|---|---|---|
|  |  |  |  |  |

## 九、写入前检查

- [ ] 目标目录位于正确的 `system.store.functionModule` 路径。
- [ ] 目标模块不存在，或当前任务明确为增量增强。
- [ ] 所有业务输出都是 Java、SQL 或必要的 Mapper XML。
- [ ] 没有 Python 文件计划进入业务目录。
- [ ] Controller、Service、DAO、Entity、SQL 的生成依据完整。
- [ ] DTO、VO 和 Mapper XML 都有真实业务需要。
- [ ] KeyModule 每个能力开关已经确定。
- [ ] 公共接口、角色权限和数据范围已经明确。
- [ ] 状态、数量、事务和异常去向已经明确。
- [ ] 规格完整且用户已经授权实施。

## 十、实施后回填

- 实际创建文件：
- 实际修改文件：
- 未生成及原因：
- 后台编译结果：
- SQL 生成状态：
- SQL 执行状态：
- Mapper 对应检查：
- 权限对应检查：
- 尚未验证事项：

