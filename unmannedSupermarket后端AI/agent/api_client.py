"""Java 后端 API 客户端，提供所有业务数据接口的异步调用。"""
from collections import Counter
import logging
import os
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:8065"
INTERNAL_API_KEY = os.getenv("JAVA_INTERNAL_API_KEY", "lhmdejavaapi")
HEADERS = {
    "X-API-Key": INTERNAL_API_KEY,
    "X-User-Id": "1",
}


class ApiClient:
    """无人超市 Java 后端 API 客户端"""

    def __init__(self, base_url: str = BASE_URL, user_id: str = "1"):
        self.base_url = base_url
        self.headers = {
            "X-API-Key": os.getenv("JAVA_INTERNAL_API_KEY", INTERNAL_API_KEY),
            "X-User-Id": user_id,
        }

    async def _get(self, path: str, params: Optional[dict] = None) -> dict:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                f"{self.base_url}{path}", headers=self.headers, params=params
            )
            logger.info("GET %s → %d", path, r.status_code)
            return r.json()

    async def _post(self, path: str, json: Optional[dict] = None) -> dict:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(
                f"{self.base_url}{path}", headers=self.headers, json=json
            )
            logger.info("POST %s → %d", path, r.status_code)
            return r.json()

    # ── 商品 ────────────────────────────────────────────

    async def search_products(
        self,
        keyword: Optional[str] = None,
        category: Optional[str] = None,
        page: int = 1,
        pageSize: int = 10,
    ) -> dict:
        """搜索/浏览上架商品"""
        params = {"page": page, "pageSize": pageSize}
        if keyword:
            params["keyword"] = keyword
        if category:
            params["category"] = category
        return await self._get("/api/product/listed", params)

    async def get_product_detail(self, product_id: int) -> dict:
        """获取商品详情"""
        return await self._get(f"/api/product/detail/{product_id}")

    async def get_categories(self) -> dict:
        """获取商品分类列表"""
        return await self._get("/api/product/categories")

    async def get_hot_products(self) -> dict:
        """获取热销商品"""
        return await self._get("/api/product/hot")

    async def recommend_products(self, limit: int = 6) -> dict:
        """按已支付订单历史推导偏好推荐；无历史则热销；热销为空则取上架商品兜底。"""
        limit = max(1, min(int(limit or 6), 20))
        category_counts: Counter[str] = Counter()
        product_counts: Counter[str] = Counter()
        detail_cache: dict[int, dict] = {}
        purchased_product_ids: set[int] = set()
        paid_order_count = 0
        paid_item_count = 0

        orders = await self.get_paid_order_history()
        for order in orders:
            paid_order_count += 1
            for item in order.get("items") or []:
                quantity = item.get("quantity") or 1
                try:
                    quantity = int(quantity)
                except (TypeError, ValueError):
                    quantity = 1
                paid_item_count += quantity

                product_name = item.get("productName") or item.get("name")
                if product_name:
                    product_counts[product_name] += quantity

                product_id = item.get("productId") or item.get("product_id")
                if not product_id:
                    continue
                try:
                    product_id = int(product_id)
                except (TypeError, ValueError):
                    continue

                purchased_product_ids.add(product_id)
                if product_id not in detail_cache:
                    detail_cache[product_id] = self._data(
                        await self.get_product_detail(product_id)
                    )
                category = detail_cache[product_id].get("category")
                if category:
                    category_counts[category] += quantity

        if category_counts:
            products = []
            seen_ids = set()

            # 常购商品优先：无人超市场景里，复购本身就是强偏好。
            for product_id, detail in detail_cache.items():
                if not self._is_available_product(detail):
                    continue
                seen_ids.add(product_id)
                products.append(detail)
                if len(products) >= limit:
                    break

            for category, _count in category_counts.most_common(3):
                category_resp = await self.search_products(
                    category=category, page=1, pageSize=limit
                )
                for product in self._records(category_resp):
                    product_id = product.get("id")
                    if product_id in seen_ids:
                        continue
                    seen_ids.add(product_id)
                    products.append(product)
                    if len(products) >= limit:
                        break
                if len(products) >= limit:
                    break

            if products:
                return self._recommendation_result(
                    source="history",
                    reason="根据用户已支付订单历史中的常购商品和高频分类推荐",
                    products=products[:limit],
                    preference={
                        "basis": "paid_order_history",
                        "paidOrderCount": paid_order_count,
                        "paidItemCount": paid_item_count,
                        "categories": [
                            {"category": k, "score": v}
                            for k, v in category_counts.most_common(5)
                        ],
                        "products": [
                            {"name": k, "score": v}
                            for k, v in product_counts.most_common(5)
                        ],
                        "purchasedProductIds": list(purchased_product_ids)[:20],
                    },
                )

        hot_products = self._list_data(await self.get_hot_products())
        if hot_products:
            return self._recommendation_result(
                source="hot",
                reason="用户暂无已支付订单历史偏好，使用热销商品推荐",
                products=hot_products[:limit],
                preference=None,
            )

        fallback_products = self._records(
            await self.search_products(page=1, pageSize=limit)
        )
        return self._recommendation_result(
            source="fallback",
            reason="暂无已支付订单历史偏好和热销数据，随机取部分上架商品推荐",
            products=fallback_products[:limit],
            preference=None,
        )

    async def get_paid_order_history(
        self,
        max_pages: int = 5,
        pageSize: int = 50,
    ) -> list[dict]:
        """读取当前用户已支付订单历史，作为偏好分析的唯一依据。"""
        paid_orders: list[dict] = []
        for page in range(1, max_pages + 1):
            resp = await self.get_orders(page=page, pageSize=pageSize)
            records = self._records(resp)
            if not records:
                break

            for order in records:
                if self._is_paid_order(order):
                    paid_orders.append(order)

            total = self._total(resp)
            if total and page * pageSize >= total:
                break
            if len(records) < pageSize:
                break
        return paid_orders

    # ── 购物车 ──────────────────────────────────────────

    async def get_carts(self, page: int = 1, pageSize: int = 10) -> dict:
        """分页查询购物车"""
        return await self._get("/api/cart/page", {"page": page, "pageSize": pageSize})

    async def get_cart_detail(self, cart_id: int) -> dict:
        """购物车详情"""
        return await self._get(f"/api/cart/detail/{cart_id}")

    async def add_to_cart(self, product_id: int, quantity: int = 1) -> dict:
        """添加商品到购物车"""
        return await self._post(
            "/api/cart-item/add", {"productId": product_id, "quantity": quantity}
        )

    async def _put(self, path: str, json: Optional[dict] = None) -> dict:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.put(
                f"{self.base_url}{path}", headers=self.headers, json=json
            )
            logger.info("PUT %s → %d", path, r.status_code)
            return r.json()

    async def update_cart(self, cart_id: int, items: list[dict]) -> dict:
        """修改购物车商品"""
        return await self._put(
            "/api/cart-item/update", {"cartId": cart_id, "items": items}
        )

    async def remove_cart_item(self, item_id: int) -> dict:
        """删除购物车明细"""
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.delete(
                f"{self.base_url}/api/cart-item/delete/{item_id}", headers=self.headers
            )
            logger.info("DELETE /api/cart-item/delete/%d → %d", item_id, r.status_code)
            return r.json()

    # ── 订单 ────────────────────────────────────────────

    async def get_orders(self, page: int = 1, pageSize: int = 10) -> dict:
        """分页查询我的订单"""
        return await self._get("/api/orders/page", {"page": page, "pageSize": pageSize})

    async def get_order_detail(self, order_id: int) -> dict:
        """订单详情"""
        return await self._get(f"/api/orders/{order_id}")

    async def create_order(self, items: list[dict]) -> dict:
        """创建订单"""
        return await self._post("/api/orders", {"items": items})

    async def pay_order(self, order_id: int) -> dict:
        """支付订单"""
        return await self._post(f"/api/orders/{order_id}/pay")

    async def cancel_order(self, order_id: int) -> dict:
        """取消订单"""
        return await self._post(f"/api/orders/{order_id}/cancel")

    # ── 用户 ────────────────────────────────────────────

    async def get_user_info(self) -> dict:
        """获取当前用户信息"""
        return await self._get("/api/user/info")

    async def get_ai_model_config(self) -> dict:
        """获取当前用户的AI模型运行时配置。无用户配置时后端返回 hasUserConfig=false。"""
        return await self._get("/api/internal/ai-model/current")

    async def get_multimodal_model_config(self) -> dict:
        """获取当前用户的多模态模型运行时配置，仅用于 DashScope 图片向量识别。"""
        return await self._get("/api/internal/multimodal-model/current")

    # ── 响应解析/推荐辅助 ─────────────────────────────

    def _data(self, response: dict) -> dict:
        data = response.get("data") if isinstance(response, dict) else None
        return data if isinstance(data, dict) else {}

    def _list_data(self, response: dict) -> list[dict]:
        data = response.get("data") if isinstance(response, dict) else None
        return data if isinstance(data, list) else []

    def _records(self, response: dict) -> list[dict]:
        data = response.get("data") if isinstance(response, dict) else None
        if isinstance(data, dict):
            records = data.get("records")
            return records if isinstance(records, list) else []
        if isinstance(data, list):
            return data
        return []

    def _total(self, response: dict) -> int:
        data = response.get("data") if isinstance(response, dict) else None
        if not isinstance(data, dict):
            return 0
        try:
            return int(data.get("total") or 0)
        except (TypeError, ValueError):
            return 0

    def _is_paid_order(self, order: dict) -> bool:
        status = str(order.get("status") or "").strip()
        return status in {"PAID", "已支付"}

    def _is_available_product(self, product: dict) -> bool:
        if not product:
            return False
        stock = product.get("stock")
        try:
            if stock is not None and int(stock) <= 0:
                return False
        except (TypeError, ValueError):
            pass

        status = product.get("status")
        if status is None:
            return True
        return str(status) in {"1", "true", "True", "上架"}

    def _recommendation_result(
        self,
        source: str,
        reason: str,
        products: list[dict],
        preference: Optional[dict],
    ) -> dict:
        return {
            "code": 200,
            "message": "success",
            "data": {
                "source": source,
                "reason": reason,
                "preference": preference,
                "products": products,
            },
        }
