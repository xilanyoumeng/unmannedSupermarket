-- 无人智能超市系统数据库初始化脚本
-- 数据库：unmanned_supermarket
-- 默认账号：
--   superadmin / 123456（超级管理员）
--   admin      / 123456（管理员）
--   user       / 123456（普通用户）
-- 说明：本脚本会重建业务表并写入演示数据，请勿在生产库直接执行。

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

CREATE DATABASE IF NOT EXISTS `unmanned_supermarket`
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
USE `unmanned_supermarket`;

DROP TABLE IF EXISTS `order_item`;
DROP TABLE IF EXISTS `orders`;
DROP TABLE IF EXISTS `cart_item`;
DROP TABLE IF EXISTS `cart`;
DROP TABLE IF EXISTS `user_ai_model_config`;
DROP TABLE IF EXISTS `user_multimodal_model_config`;
DROP TABLE IF EXISTS `product`;
DROP TABLE IF EXISTS `user`;

CREATE TABLE `user` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键',
  `username` varchar(64) NOT NULL COMMENT '用户名',
  `password` varchar(64) NOT NULL COMMENT 'MD5加密后的密码',
  `phone` varchar(32) DEFAULT NULL COMMENT '手机号',
  `email` varchar(128) DEFAULT NULL COMMENT '邮箱',
  `nickname` varchar(64) DEFAULT NULL COMMENT '昵称',
  `role` varchar(32) NOT NULL DEFAULT 'user' COMMENT '角色：user/admin/super_admin',
  `status` int NOT NULL DEFAULT 1 COMMENT '状态：1启用，0禁用',
  `elderly_mode` int NOT NULL DEFAULT 0 COMMENT '适老模式：1开启，0关闭',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_user_username` (`username`),
  UNIQUE KEY `uk_user_phone` (`phone`),
  KEY `idx_user_role` (`role`),
  KEY `idx_user_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户表';

CREATE TABLE `product` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键',
  `name` varchar(128) NOT NULL COMMENT '商品名称',
  `price` decimal(10,2) NOT NULL COMMENT '价格',
  `stock` int NOT NULL DEFAULT 0 COMMENT '库存',
  `category` varchar(64) DEFAULT NULL COMMENT '分类',
  `description` varchar(512) DEFAULT NULL COMMENT '商品描述',
  `image` varchar(512) DEFAULT NULL COMMENT '商品图片地址',
  `barcode` varchar(64) DEFAULT NULL COMMENT '条形码',
  `status` int NOT NULL DEFAULT 1 COMMENT '状态：1上架，0下架',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_product_barcode` (`barcode`),
  KEY `idx_product_category` (`category`),
  KEY `idx_product_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='商品表';

CREATE TABLE `cart` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键',
  `user_id` bigint NOT NULL COMMENT '用户ID',
  `name` varchar(64) DEFAULT '默认购物车' COMMENT '购物车名称',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_cart_user_id` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='购物车表';

CREATE TABLE `cart_item` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键',
  `cart_id` bigint NOT NULL COMMENT '购物车ID',
  `product_id` bigint NOT NULL COMMENT '商品ID',
  `quantity` int NOT NULL DEFAULT 1 COMMENT '数量',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_cart_product` (`cart_id`, `product_id`),
  KEY `idx_cart_item_product_id` (`product_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='购物车明细表';

CREATE TABLE `orders` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键',
  `order_no` varchar(64) NOT NULL COMMENT '订单号',
  `user_id` bigint NOT NULL COMMENT '用户ID',
  `amount` decimal(10,2) NOT NULL DEFAULT 0.00 COMMENT '订单金额',
  `items_count` int NOT NULL DEFAULT 0 COMMENT '商品总件数',
  `status` varchar(32) NOT NULL DEFAULT 'PENDING_PAYMENT' COMMENT '订单状态：PENDING_PAYMENT/PAID/CANCELLED',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_orders_order_no` (`order_no`),
  KEY `idx_orders_user_id` (`user_id`),
  KEY `idx_orders_status` (`status`),
  KEY `idx_orders_create_time` (`create_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='订单表';

CREATE TABLE `order_item` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键',
  `order_id` bigint NOT NULL COMMENT '订单ID',
  `product_id` bigint NOT NULL COMMENT '商品ID',
  `product_name` varchar(128) NOT NULL COMMENT '商品名称快照',
  `price` decimal(10,2) NOT NULL COMMENT '下单价格快照',
  `quantity` int NOT NULL DEFAULT 1 COMMENT '数量',
  `subtotal` decimal(10,2) NOT NULL COMMENT '小计',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_order_item_order_id` (`order_id`),
  KEY `idx_order_item_product_id` (`product_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='订单明细表';

CREATE TABLE `user_ai_model_config` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键',
  `user_id` bigint NOT NULL COMMENT '用户ID',
  `provider` varchar(64) NOT NULL COMMENT '聊天模型厂商',
  `base_url` varchar(512) NOT NULL COMMENT 'OpenAI兼容Base URL',
  `model` varchar(128) NOT NULL COMMENT '模型名称',
  `api_key_ciphertext` varchar(2048) NOT NULL COMMENT '加密后的API Key',
  `api_key_last4` varchar(8) DEFAULT NULL COMMENT 'API Key末尾4位',
  `temperature` decimal(4,2) DEFAULT 0.70 COMMENT '温度',
  `max_tokens` int DEFAULT 2048 COMMENT '最大输出Token数',
  `top_p` decimal(4,2) DEFAULT 0.90 COMMENT 'Top P',
  `enabled` tinyint NOT NULL DEFAULT 1 COMMENT '是否启用：1启用，0禁用',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_user_ai_model_user_id` (`user_id`),
  KEY `idx_user_ai_model_enabled` (`enabled`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户AI聊天模型配置表';

CREATE TABLE `user_multimodal_model_config` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键',
  `user_id` bigint NOT NULL COMMENT '用户ID',
  `provider` varchar(32) NOT NULL DEFAULT 'dashscope' COMMENT '多模态厂商，固定为阿里云DashScope',
  `api_key_ciphertext` varchar(2048) NOT NULL COMMENT '加密后的API Key',
  `api_key_last4` varchar(8) DEFAULT NULL COMMENT 'API Key末尾4位',
  `enabled` tinyint NOT NULL DEFAULT 1 COMMENT '是否启用：1启用，0禁用',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_user_multimodal_model_user_id` (`user_id`),
  KEY `idx_user_multimodal_model_enabled` (`enabled`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户多模态模型配置表';

INSERT INTO `user` (`id`, `username`, `password`, `phone`, `email`, `nickname`, `role`, `status`, `elderly_mode`, `create_time`, `update_time`) VALUES
(1, 'superadmin', 'e10adc3949ba59abbe56e057f20f883e', '13800000000', 'superadmin@example.com', '超级管理员', 'super_admin', 1, 0, NOW(), NOW()),
(2, 'admin', 'e10adc3949ba59abbe56e057f20f883e', '13800000001', 'admin@example.com', '管理员', 'admin', 1, 0, NOW(), NOW()),
(3, 'user', 'e10adc3949ba59abbe56e057f20f883e', '13800000002', 'user@example.com', '普通用户', 'user', 1, 0, NOW(), NOW());

-- 50条超市商品测试数据
INSERT INTO product (name, price, stock, category, description, image, barcode, status) VALUES
('康师傅红烧牛肉面', 4.50, 200, '方便食品', '经典红烧牛肉口味，袋装105g', 'https://img.example.com/ksf_hongshao.jpg', '6920152469127', 1),
('统一老坛酸菜牛肉面', 4.50, 180, '方便食品', '老坛酸菜口味，袋装120g', 'https://img.example.com/ty_suancai.jpg', '6920152468120', 1),
('农夫山泉天然水550ml', 2.00, 500, '饮料', '天然水源，pH值7.3±0.5', 'https://img.example.com/nfsq_550.jpg', '6921168509256', 1),
('怡宝纯净水555ml', 2.00, 450, '饮料', '二级反渗透纯净水', 'https://img.example.com/yibao_555.jpg', '6921168508259', 1),
('可口可乐330ml', 3.50, 300, '饮料', '经典碳酸饮料，罐装', 'https://img.example.com/coke_330.jpg', '6901234567890', 1),
('百事可乐330ml', 3.50, 280, '饮料', '百事碳酸饮料，罐装', 'https://img.example.com/pepsi_330.jpg', '6901234567891', 1),
('蒙牛纯牛奶250ml', 3.00, 400, '乳制品', '纯牛奶，利乐枕包装', 'https://img.example.com/mn_milk.jpg', '6907868523123', 1),
('伊利纯牛奶250ml', 3.00, 380, '乳制品', '纯牛奶，利乐枕包装', 'https://img.example.com/yl_milk.jpg', '6907868523124', 1),
('金龙鱼调和油5L', 89.90, 100, '粮油调味', '1:1:1黄金比例调和油', 'https://img.example.com/jly_oil.jpg', '6923644267890', 1),
('福临门大豆油5L', 79.90, 80, '粮油调味', '一级大豆油，非转基因', 'https://img.example.com/flm_oil.jpg', '6923644267891', 1),
('海天酱油500ml', 12.80, 150, '调味品', '特级酿造酱油', 'https://img.example.com/ht_soysauce.jpg', '6901234567900', 1),
('李锦记蚝油510g', 9.90, 120, '调味品', '鲜味蚝油，烹饪调味', 'https://img.example.com/ljj_oyster.jpg', '6901234567901', 1),
('太太乐鸡精200g', 7.50, 200, '调味品', '鲜味调味料', 'https://img.example.com/ttl_chicken.jpg', '6901234567902', 1),
('老干妈风味豆豉280g', 9.90, 180, '调味品', '贵州风味豆豉辣酱', 'https://img.example.com/lgm_douchi.jpg', '6901234567903', 1),
('康师傅冰红茶500ml', 3.00, 250, '饮料', '柠檬红茶饮料', 'https://img.example.com/ksf_tea.jpg', '6901234567910', 1),
('王老吉凉茶310ml', 5.00, 220, '饮料', '红罐凉茶', 'https://img.example.com/wlj_tea.jpg', '6901234567911', 1),
('红牛维生素饮料250ml', 6.00, 200, '饮料', '维生素功能饮料', 'https://img.example.com/hongniu.jpg', '6901234567912', 1),
('旺仔牛奶245ml', 5.50, 160, '乳制品', '复原乳饮料', 'https://img.example.com/wangzai_milk.jpg', '6901234567920', 1),
('安慕希酸奶205g', 5.00, 300, '乳制品', '希腊风味酸奶', 'https://img.example.com/ams_yogurt.jpg', '6901234567921', 1),
('德芙巧克力80g', 15.90, 120, '零食糖果', '丝滑牛奶巧克力', 'https://img.example.com/df_choco.jpg', '6901234567930', 1),
('奥利奥饼干97g', 6.90, 200, '零食糖果', '巧克力夹心饼干', 'https://img.example.com/oreo.jpg', '6901234567931', 1),
('乐事薯片104g', 8.90, 180, '零食糖果', '原味薯片', 'https://img.example.com/lays_chips.jpg', '6901234567932', 1),
('三只松鼠每日坚果175g', 29.90, 100, '零食糖果', '混合坚果，每日一袋', 'https://img.example.com/szss_nuts.jpg', '6901234567933', 1),
('良品铺子芒果干108g', 12.90, 150, '零食糖果', '芒果干，酸甜可口', 'https://img.example.com/lppz_mango.jpg', '6901234567934', 1),
('盼盼法式小面包200g', 7.90, 180, '方便食品', '法式软面包', 'https://img.example.com/pp_bread.jpg', '6901234567940', 1),
('达利园蛋黄派250g', 12.90, 140, '方便食品', '蛋黄夹心蛋糕', 'https://img.example.com/dly_cake.jpg', '6901234567941', 1),
('湾仔码头水饺720g', 32.90, 80, '速冻食品', '猪肉白菜水饺', 'https://img.example.com/wzmt_dumpling.jpg', '6901234567950', 1),
('思念汤圆500g', 14.90, 100, '速冻食品', '黑芝麻汤圆', 'https://img.example.com/sn_tangyuan.jpg', '6901234567951', 1),
('三全水饺1kg', 25.90, 90, '速冻食品', '猪肉韭菜水饺', 'https://img.example.com/sq_dumpling.jpg', '6901234567952', 1),
('维达抽纸130抽×3包', 15.90, 200, '个护清洁', '软抽纸巾', 'https://img.example.com/vinda_tissue.jpg', '6901234567960', 1),
('清风卷纸10卷', 29.90, 150, '个护清洁', '无芯卷纸', 'https://img.example.com/qf_paper.jpg', '6901234567961', 1),
('蓝月亮洗衣液3kg', 49.90, 80, '个护清洁', '深层洁净洗衣液', 'https://img.example.com/blue_moon.jpg', '6901234567970', 1),
('立白洗洁精1.5kg', 12.90, 120, '个护清洁', '柠檬去油洗洁精', 'https://img.example.com/libai.jpg', '6901234567971', 1),
('舒肤佳沐浴露720ml', 39.90, 100, '个护清洁', '纯白沐浴露', 'https://img.example.com/sfj_shower.jpg', '6901234567980', 1),
('海飞丝洗发水400ml', 49.90, 90, '个护清洁', '去屑洗发露', 'https://img.example.com/hfs_shampoo.jpg', '6901234567981', 1),
('云南白药牙膏210g', 39.90, 120, '个护清洁', '留兰香型牙膏', 'https://img.example.com/ynby_tooth.jpg', '6901234567982', 1),
('东北大米5kg', 39.90, 150, '粮油调味', '东北珍珠大米', 'https://img.example.com/db_rice.jpg', '6901234567990', 1),
('泰国香米5kg', 59.90, 100, '粮油调味', '进口茉莉香米', 'https://img.example.com/thai_rice.jpg', '6901234567991', 1),
('金龙鱼花生油5L', 109.90, 60, '粮油调味', '一级压榨花生油', 'https://img.example.com/jly_peanut.jpg', '6901234567992', 1),
('恒顺香醋500ml', 7.50, 130, '调味品', '镇江香醋', 'https://img.example.com/hs_vinegar.jpg', '6901234568000', 1),
('料酒500ml', 6.90, 140, '调味品', '烹饪料酒去腥', 'https://img.example.com/liaojiu.jpg', '6901234568001', 1),
('味极鲜酱油500ml', 15.80, 110, '调味品', '特级生抽', 'https://img.example.com/wjx_soy.jpg', '6901234568002', 1),
('青岛啤酒500ml', 6.00, 250, '酒类', '经典啤酒，罐装', 'https://img.example.com/tsingtao.jpg', '6901234568010', 1),
('雪花啤酒500ml', 5.00, 240, '酒类', '勇闯天涯，罐装', 'https://img.example.com/snow_beer.jpg', '6901234568011', 1),
('百威啤酒330ml', 8.00, 180, '酒类', '进口啤酒，瓶装', 'https://img.example.com/budweiser.jpg', '6901234568012', 1),
('张裕干红葡萄酒750ml', 89.00, 50, '酒类', '赤霞珠干红', 'https://img.example.com/zhangyu_wine.jpg', '6901234568013', 1),
('鲁花花生油5L', 129.90, 70, '粮油调味', '5S压榨工艺', 'https://img.example.com/luhua_oil.jpg', '6901234568020', 1),
('雀巢咖啡30条装', 39.90, 90, '饮料', '速溶咖啡，原味', 'https://img.example.com/nescafe.jpg', '6901234568030', 1),
('五常大米5kg', 69.90, 120, '粮油调味', '五常稻花香大米', 'https://img.example.com/wc_rice.jpg', '6901234568031', 1),
('双汇王中王火腿肠400g', 16.90, 180, '方便食品', '猪肉火腿肠', 'https://img.example.com/sh_ham.jpg', '6901234568040', 1);
INSERT INTO `cart` (`id`, `user_id`, `name`, `create_time`, `update_time`) VALUES
(1, 3, '默认购物车', NOW(), NOW());

INSERT INTO `cart_item` (`id`, `cart_id`, `product_id`, `quantity`, `create_time`, `update_time`) VALUES
(1, 1, 3, 2, NOW(), NOW()),
(2, 1, 5, 1, NOW(), NOW());

INSERT INTO `orders` (`id`, `order_no`, `user_id`, `amount`, `items_count`, `status`, `create_time`, `update_time`) VALUES
(1, '202605240001DEMO', 3, 7.50, 3, 'PENDING_PAYMENT', NOW(), NOW()),
(2, '202605240002DEMO', 3, 15.90, 3, 'PAID', NOW(), NOW());

INSERT INTO `order_item` (`id`, `order_id`, `product_id`, `product_name`, `price`, `quantity`, `subtotal`, `create_time`, `update_time`) VALUES
(1, 1, 3, '农夫山泉天然水550ml', 2.00, 2, 4.00, NOW(), NOW()),
(2, 1, 5, '可口可乐330ml', 3.50, 1, 3.50, NOW(), NOW()),
(3, 2, 1, '康师傅红烧牛肉面', 4.50, 2, 9.00, NOW(), NOW()),
(4, 2, 21, '奥利奥饼干97g', 6.90, 1, 6.90, NOW(), NOW());

SET FOREIGN_KEY_CHECKS = 1;