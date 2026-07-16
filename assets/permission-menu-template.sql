-- 独立后台模块权限菜单模板
-- 使用前替换全部 __...__ 占位符，并按模块规格保留或扩展按钮。
-- 本脚本只生成权限数据，不代表已经执行。

SET @module_name = '__MODULE_NAME__';
SET @module_key = '__MODULE_KEY__';
SET @directory_code = CONCAT('manage:dir:', @module_key);
SET @page_code = CONCAT('manage:page:', @module_key, ':base');
SET @directory_route = CONCAT('/main/modules/', @module_key, '/pages');
SET @page_route = CONCAT(@directory_route, '/base');

-- 一级：模块目录。目录没有父级。
INSERT INTO `a_permission_table`
(`permission_name`, `permission_code`, `permission_match_type`, `permission_type`, `router_path`, `api_path`, `is_allowed`, `parent_id`, `parent_router`, `icon`, `remark`, `status`, `order_by`)
SELECT @module_name, @directory_code, 2, 0, @directory_route, NULL, 0, NULL, NULL, '__DIRECTORY_ICON__', CONCAT(@module_name, '目录'), 1, __DIRECTORY_ORDER__
WHERE NOT EXISTS (
    SELECT 1 FROM `a_permission_table` WHERE `permission_code` = @directory_code
);

SET @directory_id = (
    SELECT `id` FROM `a_permission_table` WHERE `permission_code` = @directory_code ORDER BY `id` LIMIT 1
);

-- 二级：业务页面。显示名称可以与模块目录相同。
INSERT INTO `a_permission_table`
(`permission_name`, `permission_code`, `permission_match_type`, `permission_type`, `router_path`, `api_path`, `is_allowed`, `parent_id`, `parent_router`, `icon`, `remark`, `status`, `order_by`)
SELECT @module_name, @page_code, 2, 1, @page_route, NULL, 0, @directory_id, @directory_route, '__PAGE_ICON__', CONCAT(@module_name, '页面'), 1, __PAGE_ORDER__
WHERE @directory_id IS NOT NULL
  AND NOT EXISTS (
      SELECT 1 FROM `a_permission_table` WHERE `permission_code` = @page_code
  );

SET @page_id = (
    SELECT `id` FROM `a_permission_table` WHERE `permission_code` = @page_code ORDER BY `id` LIMIT 1
);

-- 三级：操作按钮。仅保留模块规格已经启用的动作。
SET @create_code = CONCAT('manage:btn:', @module_key, ':create');
INSERT INTO `a_permission_table`
(`permission_name`, `permission_code`, `permission_match_type`, `permission_type`, `router_path`, `api_path`, `is_allowed`, `parent_id`, `parent_router`, `icon`, `remark`, `status`, `order_by`)
SELECT CONCAT('新增', @module_name), @create_code, 2, 2, NULL, NULL, 0, @page_id, @page_route, NULL, NULL, 1, 0
WHERE @page_id IS NOT NULL
  AND NOT EXISTS (
      SELECT 1 FROM `a_permission_table` WHERE `permission_code` = @create_code
  );

SET @edit_code = CONCAT('manage:btn:', @module_key, ':edit');
INSERT INTO `a_permission_table`
(`permission_name`, `permission_code`, `permission_match_type`, `permission_type`, `router_path`, `api_path`, `is_allowed`, `parent_id`, `parent_router`, `icon`, `remark`, `status`, `order_by`)
SELECT CONCAT('修改', @module_name), @edit_code, 2, 2, NULL, NULL, 0, @page_id, @page_route, NULL, NULL, 1, 0
WHERE @page_id IS NOT NULL
  AND NOT EXISTS (
      SELECT 1 FROM `a_permission_table` WHERE `permission_code` = @edit_code
  );

SET @remove_code = CONCAT('manage:btn:', @module_key, ':remove');
INSERT INTO `a_permission_table`
(`permission_name`, `permission_code`, `permission_match_type`, `permission_type`, `router_path`, `api_path`, `is_allowed`, `parent_id`, `parent_router`, `icon`, `remark`, `status`, `order_by`)
SELECT CONCAT('删除', @module_name), @remove_code, 2, 2, NULL, NULL, 0, @page_id, @page_route, NULL, NULL, 1, 0
WHERE @page_id IS NOT NULL
  AND NOT EXISTS (
      SELECT 1 FROM `a_permission_table` WHERE `permission_code` = @remove_code
  );
