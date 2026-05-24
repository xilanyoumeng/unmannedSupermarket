CREATE TABLE IF NOT EXISTS `user_multimodal_model_config` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键',
  `user_id` bigint NOT NULL COMMENT '用户ID',
  `provider` varchar(32) NOT NULL DEFAULT 'dashscope' COMMENT '多模态厂商，固定为阿里百炼DashScope',
  `api_key_ciphertext` varchar(2048) NOT NULL COMMENT '加密后的API Key',
  `api_key_last4` varchar(8) DEFAULT NULL COMMENT 'API Key末尾4位，用于页面掩码展示',
  `enabled` tinyint NOT NULL DEFAULT 1 COMMENT '是否启用：1启用，0禁用',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_user_multimodal_model_user_id` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户多模态模型配置表';
