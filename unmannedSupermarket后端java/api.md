# 无人超市 API 文档（普通用户）

> 仅包含普通用户可用的安全接口，不含管理员操作和用户信息修改。

## 通用说明

- **Base URL**: `http://localhost:8065`
- **统一响应格式**:

```json
{
  "code": 200,
  "message": "success",
  "data": { ... }
}
```

| code | 说明 |
|------|------|
| 200 | 成功 |
| 400 | 参数错误或业务异常 |
| 401 | 未认证 |

### 分页响应 (`PageResultVO`)

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "records": [ ... ],
    "total": 100,
    "page": 1,
    "pageSize": 10
  }
}
```

### 认证方式

| 调用方 | 请求头 |
|--------|--------|
| 普通前端 | `Authorization: Bearer <jwt_token>` |
| Python 服务 | `X-API-Key: <api_key>` + `X-User-Id: <user_id>` |

---

## 1. 商品 `/api/product`

### 商品字段

| 字段 | 类型 | 说明 |
|------|------|------|
| id | long | 商品 ID |
| name | string | 名称 |
| price | decimal | 单价（元） |
| stock | int | 库存 |
| category | string | 分类 |
| description | string | 描述 |
| image | string | 图片 URL |
| barcode | string | 条形码 |
| status | int | 1=上架, 0=下架 |
| createTime | datetime | 创建时间 |
| updateTime | datetime | 更新时间 |

### 1.1 上架商品分页

```
GET /api/product/listed?page=1&pageSize=10&keyword=可乐&category=饮料
```

仅返回 `status=1`（已上架）的商品。

| 参数 | 类型 | 必填 | 默认值 |
|------|------|------|--------|
| page | int | 否 | 1 |
| pageSize | int | 否 | 10 |
| keyword | string | 否 | - |
| category | string | 否 | - |

### 1.2 商品详情

```
GET /api/product/detail/{id}
```

### 1.3 商品分类列表

```
GET /api/product/categories
```

响应 `data`: `["饮料", "零食", "日用品"]`

### 1.4 热销商品

```
GET /api/product/hot
```

响应 `data`:

```json
[
  {
    "id": 1,
    "name": "可口可乐",
    "price": 3.50,
    "stock": 100,
    "category": "饮料",
    "description": "冰镇可乐",
    "image": "https://xxx.jpg",
    "barcode": "6901234567890",
    "status": 1,
    "hotCount": 256
  }
]
```

---

## 2. 购物车 `/api/cart`

### 2.1 分页查询购物车

```
GET /api/cart/page?page=1&pageSize=10
```

响应 `data.records`:

```json
[
  {
    "id": 1,
    "userId": 1,
    "name": "我的购物车",
    "items": [
      {
        "id": 1,
        "cartId": 1,
        "productId": 1,
        "productName": "可口可乐",
        "productPrice": 3.50,
        "productImage": "https://xxx.jpg",
        "quantity": 2,
        "createTime": "2026-01-01T12:00:00"
      }
    ],
    "createTime": "2026-01-01T12:00:00"
  }
]
```

### 2.2 购物车详情

```
GET /api/cart/detail/{id}
```

### 2.3 修改购物车名称

```
PUT /api/cart/update/{id}?name=新名称
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | 是 | 新名称 (Query) |

### 2.4 删除购物车

```
DELETE /api/cart/delete/{id}
```

---

## 3. 购物车明细 `/api/cart-item`

### 3.1 添加商品到购物车

```
POST /api/cart-item/add
```

请求体:

```json
{
  "productId": 1,
  "quantity": 2
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| productId | long | 是 | 商品 ID |
| quantity | int | 是 | 数量，最小 1 |

### 3.2 修改购物车商品

```
PUT /api/cart-item/update
```

请求体:

```json
{
  "cartId": 1,
  "items": [
    { "productId": 1, "quantity": 3 },
    { "productId": 2, "quantity": 1 }
  ]
}
```

### 3.3 删除购物车明细

```
DELETE /api/cart-item/delete/{id}
```

---

## 4. 订单 `/api/orders`

### 订单状态

| 值 | 说明 |
|------|------|
| PENDING | 待支付 |
| PAID | 已支付 |
| CANCELLED | 已取消 |

### 4.1 我的订单分页

```
GET /api/orders/page?page=1&pageSize=10
```

返回当前用户的订单。

### 4.2 订单详情

```
GET /api/orders/{id}
```

响应 `data`:

```json
{
  "id": 1,
  "orderNo": "20260101120000001",
  "amount": 10.50,
  "itemsCount": 2,
  "status": "PENDING",
  "username": "admin",
  "createdAt": "2026-01-01T12:00:00",
  "items": [
    {
      "productId": 1,
      "productName": "可口可乐",
      "price": 3.50,
      "quantity": 3,
      "subtotal": 10.50
    }
  ]
}
```

### 4.3 创建订单

```
POST /api/orders
```

请求体:

```json
{
  "items": [
    { "productId": 1, "quantity": 3 },
    { "productId": 2, "quantity": 1 }
  ]
}
```

### 4.4 支付订单

```
POST /api/orders/{id}/pay
```

### 4.5 取消订单

```
POST /api/orders/{id}/cancel
```

---

## 5. 文件上传 `/api/file`

### 5.1 上传图片

```
POST /api/file/upload
Content-Type: multipart/form-data
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| file | file | 是 | 图片文件，最大 10MB |

响应 `data`:

```json
{
  "url": "https://xxx.oss-cn-beijing.aliyuncs.com/announcement/xxx.jpg"
}
```

---

## 6. 用户辅助接口 `/api/user`

仅保留不涉及信息修改的接口。

### 6.1 获取当前用户信息

```
GET /api/user/info
```

响应 `data`:

```json
{
  "id": 1,
  "username": "admin",
  "nickname": "管理员",
  "phone": "13800000000",
  "email": "admin@test.com",
  "role": "ADMIN",
  "status": 1,
  "elderlyMode": 0,
  "createTime": "2026-01-01T12:00:00"
}
```

### 6.2 退出登录

```
POST /api/user/logout
```

### 6.3 验证身份（白名单接口，无需认证）

```
POST /api/user/verify-identity
```

请求体:

```json
{
  "username": "admin",
  "phone": "13800000000"
}
```

### 6.4 重置密码（白名单接口，无需认证）

```
POST /api/user/reset-password
```

请求体:

```json
{
  "username": "admin",
  "phone": "13800000000",
  "newPassword": "123456"
}
```

---

## Python 调用示例

```python
import requests

BASE = "http://localhost:8065"
HEADERS = {
    "X-API-Key": "unmannedSupermarket-api-key-2026",
    "X-User-Id": "1",
}

# 1. 浏览商品
r = requests.get(f"{BASE}/api/product/listed", params={"page": 1, "pageSize": 10}, headers=HEADERS)
print(r.json())

# 2. 添加到购物车
r = requests.post(f"{BASE}/api/cart-item/add", headers=HEADERS, json={
    "productId": 1, "quantity": 2
})
print(r.json())

# 3. 创建订单
r = requests.post(f"{BASE}/api/orders", headers=HEADERS, json={
    "items": [{"productId": 1, "quantity": 3}]
})
print(r.json())

# 4. 支付订单
r = requests.post(f"{BASE}/api/orders/1/pay", headers=HEADERS)
print(r.json())
```
