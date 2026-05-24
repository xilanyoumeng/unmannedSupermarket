# 智慧超市 API 接口文档

## Base URL

```
http://localhost:8065
```

所有接口路径以 `/api` 开头。

## 认证说明

除登录/注册外，所有接口需在 Header 中携带：

```
Authorization: Bearer <token>
```

## 通用响应格式

```json
{
  "code": 200,
  "message": "success",
  "data": {}
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| code | number | 业务状态码，200 表示成功 |
| message | string | 提示信息 |
| data | T | 响应数据 |

---

## 一、用户模块 `/api/user`

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | `/api/user/login` | 用户登录 | 否 |
| POST | `/api/user/register` | 用户注册 | 否 |
| GET | `/api/user/info` | 获取当前用户信息 | 是 |
| GET | `/api/user/page` | 分页查询用户列表 | 是 |

### POST /api/user/login

**请求体**:
```json
{
  "username": "admin",
  "password": "123456"
}
```

**响应**:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": 1,
    "username": "admin",
    "nickname": "管理员",
    "phone": "13800138000",
    "email": "admin@test.com",
    "role": "admin",
    "token": "eyJ..."
  }
}
```

### POST /api/user/register

**请求体**:
```json
{
  "username": "test",
  "password": "123456",
  "phone": "13800138001",
  "email": "test@test.com",
  "nickname": "测试"
}
```

**响应**:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": 2,
    "username": "test",
    "token": "eyJ..."
  }
}
```

### GET /api/user/info

**响应**:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": 1,
    "username": "admin",
    "nickname": "管理员",
    "phone": "13800138000",
    "email": "admin@test.com",
    "role": "admin",
    "status": 1,
    "createTime": "2026-05-07T12:00:00"
  }
}
```

### GET /api/user/page

**请求参数**: `?page=1&pageSize=10`

**响应**:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "records": [...],
    "total": 100,
    "page": 1,
    "pageSize": 10
  }
}
```

---

## 二、商品模块 `/api/product`

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| GET | `/api/product/page` | 分页查询商品列表 | 是 |
| GET | `/api/product/detail/{id}` | 查询商品详情 | 是 |
| POST | `/api/product/add` | 新增商品 | 是 |
| PUT | `/api/product/update/{id}` | 修改商品 | 是 |
| PUT | `/api/product/status/{id}` | 上架/下架 | 是 |
| DELETE | `/api/product/delete/{id}` | 删除商品 | 是 |
| GET | `/api/product/categories` | 商品分类列表 | 是 |

### GET /api/product/page

**请求参数**: `?page=1&pageSize=10&keyword=水&category=饮料`

**响应**:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "records": [
      {
        "id": 1,
        "name": "矿泉水",
        "price": 2.00,
        "stock": 100,
        "category": "饮料",
        "description": "天然矿泉水",
        "image": "https://...",
        "barcode": "6901234567890",
        "status": 1,
        "createTime": "2026-05-07T12:00:00",
        "updateTime": "2026-05-07T12:00:00"
      }
    ],
    "total": 50,
    "page": 1,
    "pageSize": 10
  }
}
```

### GET /api/product/detail/{id}

**路径参数**: `id` — 商品ID

**响应**:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": 1,
    "name": "矿泉水",
    "price": 2.00,
    "stock": 100,
    "category": "饮料",
    "description": "天然矿泉水",
    "image": "https://...",
    "barcode": "6901234567890",
    "status": 1,
    "createTime": "2026-05-07T12:00:00"
  }
}
```

### POST /api/product/add

**请求体**:
```json
{
  "name": "可乐",
  "price": 3.50,
  "stock": 200,
  "category": "饮料",
  "description": "碳酸饮料",
  "image": "https://...",
  "barcode": "6901234567891"
}
```

### PUT /api/product/update/{id}

**路径参数**: `id` — 商品ID

**请求体** (部分字段即可):
```json
{
  "name": "矿泉水(大)",
  "price": 3.00,
  "stock": 150
}
```

### PUT /api/product/status/{id}

**路径参数**: `id` — 商品ID

切换商品状态：上架↔下架，无请求体。

### DELETE /api/product/delete/{id}

**路径参数**: `id` — 商品ID

### GET /api/product/categories

**响应**:
```json
{
  "code": 200,
  "message": "success",
  "data": ["饮料", "零食", "日用品"]
}
```

---

## 三、文件模块 `/api/file`

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | `/api/file/upload` | 上传图片 | 是 |

### POST /api/file/upload

**Content-Type**: `multipart/form-data`

**表单字段**: `file` — 图片文件

**响应**:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "url": "https://java-ailhm.oss-cn-beijing.aliyuncs.com/announcement/2026/05/07/uuid.png"
  }
}
```

---

## 四、前端调用流程

```
进入智慧购物页面
├── GET /api/product/categories    → 获取分类列表 (string[])
├── GET /api/product/hot           → 热销商品 (后端暂未实现)
└── GET /api/product/page          → 商品分页列表

切换分类 → GET /api/product/page?category=饮料&page=1
翻页     → GET /api/product/page?category=饮料&page=2
查看详情 → GET /api/product/detail/:id
加入购物车 → POST /api/cart
AI识别   → POST /api/product/recognize (后端暂未实现)

管理后台
├── 商品管理 → CRUD /api/product/*
├── 用户管理 → GET /api/user/page
└── 图片上传 → POST /api/file/upload
```

---

## 错误码说明

| code | 含义 |
|------|------|
| 200 | 操作成功 |
| 400 | 请求参数有误 |
| 401 | 未登录或 token 已过期 |
| 403 | 权限不足 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |
