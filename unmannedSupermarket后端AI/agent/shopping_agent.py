import asyncio
import json
import logging
import os
import re
from typing import AsyncGenerator, Optional

import yaml
from openai import AsyncOpenAI

from agent.api_client import ApiClient
from task_tracker import TaskTracker

logger = logging.getLogger(__name__)

MAX_REACT_ROUNDS = 10

# ── 工具定义 ────────────────────────────────────────────

FRONTEND_TOOLS = {"navigate", "click", "ask_user"}

BACKEND_TOOLS = {
    "search_products",
    "get_product_detail",
    "get_categories",
    "get_hot_products",
    "recommend_products",
    "get_carts",
    "get_cart_detail",
    "add_to_cart",
    "update_cart",
    "remove_cart_item",
    "get_orders",
    "get_order_detail",
    "create_order",
    "cancel_order",
    "get_user_info",
}

MUTATION_TOOLS = {
    "add_to_cart",
    "update_cart",
    "remove_cart_item",
    "create_order",
    "cancel_order",
}

NEGATIVE_MUTATION_KEYWORDS = (
    "不要加入购物车",
    "别加入购物车",
    "不要加购物车",
    "不要加购",
    "别加购",
    "只浏览",
    "只看看",
    "不要下单",
    "别下单",
    "不要创建订单",
    "不要支付",
)

RECOMMENDATION_KEYWORDS = ("推荐", "好物", "买什么", "值得买", "购物建议")
EXPLICIT_NAVIGATION_KEYWORDS = (
    "打开", "跳转", "带我去", "去看看", "进入", "页面", "浏览页面", "看页面"
)

TOOLS = [
    # ── 前端工具（需等待前端 ack） ──
    {
        "type": "function",
        "function": {
            "name": "navigate",
            "description": "导航到前端真实路由，例如商品页 /shopping、购物车 /cart、个人中心 /profile、订单确认页 /order-confirm/{order_id}；不要使用 /products 或 /orders",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "目标路由路径，如 /shopping、/cart、/profile、/order-confirm/{order_id}",
                    }
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "click",
            "description": "点击页面上的某个元素，如搜索框、商品卡片、按钮等",
            "parameters": {
                "type": "object",
                "properties": {
                    "selector": {
                        "type": "string",
                        "description": "目标元素的 CSS 选择器，如 #search-input、.product-card、[data-product-id='1']",
                    },
                    "label": {
                        "type": "string",
                        "description": "人类可读的操作描述，如「点击搜索框」「点击第一个商品」",
                    },
                },
                "required": ["selector", "label"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ask_user",
            "description": (
                "在同一轮任务中向前端请求用户确认、选择或填写缺失信息。"
                "前端会弹出确认/选择/表单窗口，用户提交后以 tool_ack.data 返回，"
                "mode=select 时前端会默认提供「其他商品」输入项；"
                "如果返回 isCustom=true 和 customInput，表示用户没有选择你的候选项，"
                "你必须根据 customInput 继续搜索/推荐。"
                "你必须读取返回值并继续完成任务，不要把问题留到下一条聊天消息。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "弹窗标题，如「确认商品」",
                    },
                    "message": {
                        "type": "string",
                        "description": "给用户看的说明文字，列清楚为什么需要确认",
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["confirm", "select", "form"],
                        "description": "confirm=确认/取消，select=单选，form=填写表单",
                    },
                    "options": {
                        "type": "array",
                        "description": "mode=select 时的选项",
                        "items": {
                            "type": "object",
                            "properties": {
                                "label": {"type": "string"},
                                "value": {
                                    "type": "string",
                                    "description": "选项值，商品ID/数量等也用字符串传递",
                                },
                            },
                            "required": ["label", "value"],
                        },
                    },
                    "fields": {
                        "type": "array",
                        "description": "mode=form 时需要用户填写的字段",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "label": {"type": "string"},
                                "type": {
                                    "type": "string",
                                    "enum": ["text", "number", "textarea", "select"],
                                },
                                "required": {"type": "boolean"},
                                "placeholder": {"type": "string"},
                                "default": {
                                    "type": "string",
                                    "description": "默认值",
                                },
                                "options": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "label": {"type": "string"},
                                            "value": {
                                                "type": "string",
                                                "description": "选项值",
                                            },
                                        },
                                        "required": ["label", "value"],
                                    },
                                },
                            },
                            "required": ["name", "label"],
                        },
                    },
                    "allowCustomInput": {
                        "type": "boolean",
                        "description": "mode=select 时是否允许用户输入其他商品/需求；默认允许",
                    },
                    "customInputLabel": {
                        "type": "string",
                        "description": "其他输入项的标签，如「其他商品」",
                    },
                    "customInputPlaceholder": {
                        "type": "string",
                        "description": "其他输入框占位提示，如「或者您想要其他商品，也可以输入，我帮您查找哦」",
                    },
                    "confirmText": {"type": "string"},
                    "cancelText": {"type": "string"},
                },
                "required": ["title", "message", "mode"],
            },
        },
    },
    # ── 后端商品工具 ──
    {
        "type": "function",
        "function": {
            "name": "search_products",
            "description": "搜索或浏览上架商品，可按关键词和分类筛选",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "搜索关键词，如「可乐」「牛奶」",
                    },
                    "category": {
                        "type": "string",
                        "description": "商品分类，如「饮料」「零食」「日用品」",
                    },
                    "page": {"type": "integer", "description": "页码，默认 1"},
                    "pageSize": {"type": "integer", "description": "每页数量，默认 10"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_product_detail",
            "description": "获取单个商品的详细信息，包括价格、库存、描述等",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "integer", "description": "商品 ID"},
                },
                "required": ["product_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_categories",
            "description": "获取所有商品分类列表",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_hot_products",
            "description": "获取热销商品排行榜",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "recommend_products",
            "description": (
                "推荐商品专用工具。先根据当前用户已支付订单历史推断购物偏好；"
                "如果没有已支付订单历史偏好则返回热销商品；如果热销也为空则返回部分上架商品兜底。"
                "仅返回推荐结果，不做页面跳转、不加购物车、不下单。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "推荐数量，默认 6，最多 20",
                    },
                },
            },
        },
    },
    # ── 后端购物车工具 ──
    {
        "type": "function",
        "function": {
            "name": "get_carts",
            "description": "查看当前用户的购物车列表",
            "parameters": {
                "type": "object",
                "properties": {
                    "page": {"type": "integer", "description": "页码，默认 1"},
                    "pageSize": {"type": "integer", "description": "每页数量，默认 10"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_cart_detail",
            "description": "查看某个购物车的详细内容",
            "parameters": {
                "type": "object",
                "properties": {
                    "cart_id": {"type": "integer", "description": "购物车 ID"},
                },
                "required": ["cart_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_to_cart",
            "description": "将商品添加到购物车",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {
                        "type": "integer",
                        "description": "商品 ID",
                    },
                    "quantity": {
                        "type": "integer",
                        "description": "数量，最小 1，默认 1",
                    },
                },
                "required": ["product_id", "quantity"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_cart",
            "description": "修改购物车中商品的数量",
            "parameters": {
                "type": "object",
                "properties": {
                    "cart_id": {"type": "integer", "description": "购物车 ID"},
                    "items": {
                        "type": "array",
                        "description": "商品列表",
                        "items": {
                            "type": "object",
                            "properties": {
                                "productId": {
                                    "type": "integer",
                                    "description": "商品 ID",
                                },
                                "quantity": {
                                    "type": "integer",
                                    "description": "新数量",
                                },
                            },
                            "required": ["productId", "quantity"],
                        },
                    },
                },
                "required": ["cart_id", "items"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "remove_cart_item",
            "description": "从购物车中删除某个商品",
            "parameters": {
                "type": "object",
                "properties": {
                    "item_id": {
                        "type": "integer",
                        "description": "购物车明细 ID",
                    },
                },
                "required": ["item_id"],
            },
        },
    },
    # ── 后端订单工具 ──
    {
        "type": "function",
        "function": {
            "name": "get_orders",
            "description": "查看当前用户的订单列表",
            "parameters": {
                "type": "object",
                "properties": {
                    "page": {"type": "integer", "description": "页码，默认 1"},
                    "pageSize": {"type": "integer", "description": "每页数量，默认 10"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_order_detail",
            "description": "查看某个订单的详细信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "integer", "description": "订单 ID"},
                },
                "required": ["order_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_order",
            "description": "根据购物车商品创建新订单",
            "parameters": {
                "type": "object",
                "properties": {
                    "items": {
                        "type": "array",
                        "description": "订单商品列表",
                        "items": {
                            "type": "object",
                            "properties": {
                                "productId": {
                                    "type": "integer",
                                    "description": "商品 ID",
                                },
                                "quantity": {
                                    "type": "integer",
                                    "description": "数量",
                                },
                            },
                            "required": ["productId", "quantity"],
                        },
                    },
                },
                "required": ["items"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_order",
            "description": "取消指定订单",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "integer", "description": "订单 ID"},
                },
                "required": ["order_id"],
            },
        },
    },
    # ── 用户工具 ──
    {
        "type": "function",
        "function": {
            "name": "get_user_info",
            "description": "获取当前登录用户的个人信息",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]

# ── Agent 主类 ──────────────────────────────────────────

class ShoppingAgent:
    """支持 ReAct 循环的 AI 导购助手"""

    def __init__(self, config_path: str = None):
        if config_path is None:
            from pathlib import Path
            config_path = str(Path(__file__).parent.parent / "config.yaml")
        self.config = self._load_config(config_path)
        self.system_prompt = self.config["system_prompt"]
        self._current_user_message = ""

        # 前端 tool_ack 同步机制
        self._ack_event: Optional[asyncio.Event] = None
        self._ack_data: Optional[dict] = None

    def _load_config(self, config_path: str) -> dict:
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def _default_llm_runtime_config(self) -> dict:
        llm_config = self.config["llm"]
        api_key_env = llm_config["api_key_env"]
        api_key = os.getenv(api_key_env)
        if not api_key:
            raise ValueError(
                f"当前用户未配置AI模型，且系统环境变量 {api_key_env} 未设置。"
                "请在个人中心配置AI模型，或由开发者在运行环境中设置默认模型密钥。"
            )
        return {
            "source": "default",
            "provider": "default",
            "api_key": api_key,
            "base_url": llm_config["base_url"],
            "model": llm_config["model"],
            "temperature": llm_config.get("temperature", 0.7),
            "max_tokens": llm_config.get("max_tokens", 2048),
            "top_p": llm_config.get("top_p", 0.9),
        }

    @staticmethod
    def _should_pass_reasoning_content(llm_config: dict) -> bool:
        """DeepSeek V4 thinking tool-call turns require reasoning_content passback."""
        provider = str(llm_config.get("provider") or "").lower()
        base_url = str(llm_config.get("base_url") or "").lower()
        model = str(llm_config.get("model") or "").lower()

        is_deepseek = (
            "deepseek" in provider
            or "deepseek" in base_url
            or "deepseek" in model
            or provider == "ds"
            or model.startswith("ds-")
        )
        is_v4_thinking_model = (
            "v4" in model
            or "v-4" in model
            or "v4pro" in model
            or "v4-pro" in model
        )
        return is_deepseek and is_v4_thinking_model

    async def _resolve_llm_runtime_config(self) -> dict:
        """优先使用当前用户保存在Java后端的模型配置；没有则回退到config.yaml。"""
        try:
            response = await self.api.get_ai_model_config()
            data = response.get("data") if isinstance(response, dict) else None
            if isinstance(data, dict) and data.get("hasUserConfig"):
                api_key = (data.get("apiKey") or "").strip()
                base_url = (data.get("baseUrl") or "").strip()
                model = (data.get("model") or "").strip()
                if api_key and base_url and model:
                    runtime = {
                        "source": "user",
                        "provider": data.get("provider") or "custom",
                        "api_key": api_key,
                        "base_url": base_url,
                        "model": model,
                        "temperature": data.get("temperature", 0.7),
                        "max_tokens": data.get("maxTokens", 2048),
                        "top_p": data.get("topP", 0.9),
                    }
                    logger.info(
                        "使用用户AI模型配置: provider=%s model=%s baseUrl=%s",
                        runtime["provider"], runtime["model"], runtime["base_url"],
                    )
                    return runtime
        except Exception as exc:
            logger.warning("读取用户AI模型配置失败，尝试回退默认配置: %s", exc)

        runtime = self._default_llm_runtime_config()
        logger.info(
            "使用默认AI模型配置: model=%s env=%s",
            runtime["model"], self.config["llm"]["api_key_env"],
        )
        return runtime

    # ── Tool Ack 接口 ───────────────────────────────────

    def receive_tool_ack(self, action_type: str, success: bool,
                         data: Optional[dict] = None) -> None:
        """前端执行完 action 后调用，唤醒等待中的 ReAct 循环"""
        self._ack_data = {
            "action_type": action_type,
            "success": success,
            "data": data or {},
        }
        if self._ack_event:
            self._ack_event.set()

    async def _wait_for_ack(self) -> dict:
        """等待前端返回 tool_ack。

        receive_tool_ack() 可能在 Event 创建之前就被 app.py 调用
        （agent 在 yield tool_call 后挂起，app.py 立即调用 receive_tool_ack），
        此时 _ack_data 已被设置但 Event 尚未创建。先检查 _ack_data 避免永久等待。
        """
        self._ack_event = asyncio.Event()
        if self._ack_data is not None:
            data = self._ack_data
            self._ack_data = None
            self._ack_event = None
            return data
        await self._ack_event.wait()
        data = self._ack_data
        self._ack_data = None
        self._ack_event = None
        return data

    # ── 后端工具执行 ────────────────────────────────────

    async def _execute_backend_tool(self, name: str, args: dict) -> dict:
        """直接调用 Java 后端 API"""
        try:
            if name in MUTATION_TOOLS and self._user_blocked_mutation():
                return {
                    "error": (
                        "用户明确要求只浏览或不要执行加购/下单等写操作，"
                        f"已拦截工具 {name}。"
                    )
                }
            if name == "search_products":
                return await self.api.search_products(
                    keyword=args.get("keyword"),
                    category=args.get("category"),
                    page=args.get("page", 1),
                    pageSize=args.get("pageSize", 10),
                )
            elif name == "get_product_detail":
                return await self.api.get_product_detail(args["product_id"])
            elif name == "get_categories":
                return await self.api.get_categories()
            elif name == "get_hot_products":
                return await self.api.get_hot_products()
            elif name == "recommend_products":
                return await self.api.recommend_products(args.get("limit", 6))
            elif name == "get_carts":
                return await self.api.get_carts(
                    page=args.get("page", 1),
                    pageSize=args.get("pageSize", 10),
                )
            elif name == "get_cart_detail":
                return await self.api.get_cart_detail(args["cart_id"])
            elif name == "add_to_cart":
                return await self.api.add_to_cart(
                    product_id=args["product_id"],
                    quantity=args.get("quantity", 1),
                )
            elif name == "update_cart":
                return await self.api.update_cart(
                    cart_id=args["cart_id"], items=args["items"]
                )
            elif name == "remove_cart_item":
                return await self.api.remove_cart_item(args["item_id"])
            elif name == "get_orders":
                return await self.api.get_orders(
                    page=args.get("page", 1),
                    pageSize=args.get("pageSize", 10),
                )
            elif name == "get_order_detail":
                return await self.api.get_order_detail(args["order_id"])
            elif name == "create_order":
                return await self.api.create_order(args["items"])
            elif name == "cancel_order":
                return await self.api.cancel_order(args["order_id"])
            elif name == "get_user_info":
                return await self.api.get_user_info()
            else:
                return {"error": f"未知的后端工具: {name}"}
        except Exception as e:
            logger.error("后端工具 %s 执行失败: %s", name, e)
            return {"error": str(e)}

    def _user_blocked_mutation(self) -> bool:
        message = self._current_user_message or ""
        return any(keyword in message for keyword in NEGATIVE_MUTATION_KEYWORDS)

    def _should_block_recommendation_navigation(self, name: str, args: dict) -> bool:
        if name != "navigate" or args.get("path") != "/shopping":
            return False
        message = self._current_user_message or ""
        is_recommendation = any(keyword in message for keyword in RECOMMENDATION_KEYWORDS)
        explicit_navigation = any(
            keyword in message for keyword in EXPLICIT_NAVIGATION_KEYWORDS
        )
        return is_recommendation and not explicit_navigation

    def _normalize_order_id(self, value) -> Optional[str]:
        if value is None:
            return None
        text = str(value).strip()
        return text if re.fullmatch(r"\d+", text) else None

    def _extract_order_id_from_response(self, value) -> Optional[str]:
        if isinstance(value, dict):
            for key in ("id", "orderId", "order_id"):
                order_id = self._normalize_order_id(value.get(key))
                if order_id:
                    return order_id
            for key in ("data", "order", "result"):
                order_id = self._extract_order_id_from_response(value.get(key))
                if order_id:
                    return order_id
        if isinstance(value, list):
            for item in value:
                order_id = self._extract_order_id_from_response(item)
                if order_id:
                    return order_id
        return None

    def _extract_order_id_from_path(self, path: str) -> Optional[str]:
        for pattern in (
            r"(?:[?&](?:id|orderId|order_id)=)(\d+)",
            r"^/(?:orders?|order-confirm)/(\d+)(?:[/?#]|$)",
        ):
            match = re.search(pattern, path)
            if match:
                return match.group(1)
        return None

    def _normalize_frontend_path(
        self,
        path: str,
        latest_created_order_id: Optional[str] = None,
    ) -> str:
        path = str(path or "/").strip()
        if not path:
            return "/"
        if path.startswith("#/"):
            path = path[1:]
        if not path.startswith("/"):
            path = "/" + path

        if path == "/products" or path.startswith("/products/"):
            return path.replace("/products", "/shopping", 1)

        if path.startswith("/order-confirm"):
            order_id = latest_created_order_id or self._extract_order_id_from_path(path)
            if order_id:
                return f"/order-confirm/{order_id}"
            return path

        if path == "/orders" or path.startswith("/orders/") or path.startswith("/orders?"):
            order_id = latest_created_order_id or self._extract_order_id_from_path(path)
            return f"/order-confirm/{order_id}" if order_id else "/profile"

        if path == "/order" or path.startswith("/order/") or path.startswith("/order?"):
            order_id = latest_created_order_id or self._extract_order_id_from_path(path)
            return f"/order-confirm/{order_id}" if order_id else "/profile"

        return path

    # ── 构建前端 action ─────────────────────────────────

    def _build_action(self, name: str, args: dict) -> dict:
        """将 LLM 的工具调用转为前端 action 格式"""
        if name == "navigate":
            path = self._normalize_frontend_path(args.get("path", "/"))
            return {
                "type": "navigate",
                "label": f"前往 {path}",
                "payload": path,
            }
        elif name == "click":
            return {
                "type": "click",
                "label": args.get("label", "点击元素"),
                "payload": {"selector": args.get("selector", "")},
            }
        elif name == "ask_user":
            return {
                "type": "ask_user",
                "label": args.get("title", "需要用户确认"),
                "payload": {
                    "title": args.get("title", "需要确认"),
                    "message": args.get("message", ""),
                    "mode": args.get("mode", "confirm"),
                    "options": args.get("options", []),
                    "fields": args.get("fields", []),
                    "allowCustomInput": args.get("allowCustomInput", True),
                    "customInputLabel": args.get("customInputLabel", "其他商品"),
                    "customInputPlaceholder": args.get(
                        "customInputPlaceholder",
                        "或者您想要其他商品，也可以输入，我帮您查找哦",
                    ),
                    "confirmText": args.get("confirmText", "确认并继续"),
                    "cancelText": args.get("cancelText", "取消"),
                },
            }
        return {"type": name, "label": name, "payload": args}

    # ── 操作描述（兜底：AI 没说话时自动生成） ────────────

    def _describe_frontend_action(self, action: dict, current_page: str = "") -> str:
        """根据 action 生成自然语言描述，让用户知道 agent 在做什么"""
        action_type = action.get("type", "")
        if action_type == "navigate":
            path = action.get("payload", "/")
            page_names = {
                "/": "首页",
                "/shopping": "智慧购物页面",
                "/cart": "购物车页面",
                "/assistant": "AI助手页面",
                "/profile": "个人中心",
                "/login": "登录页",
            }
            page_name = page_names.get(path, path)
            if path.startswith("/order-confirm"):
                page_name = "订单确认页"
            if current_page == path:
                return f"当前已在{page_name}，无需跳转。"
            return f"正在为您打开{page_name}..."
        elif action_type == "click":
            label = action.get("label", "点击")
            selector = action.get("payload", {}).get("selector", "")
            if "加入购物车" in label or "加入购物车" in selector:
                return "正在为您将商品加入购物车..."
            if "支付" in label or "结算" in label:
                return "正在为您点击结算按钮..."
            if "分类" in label:
                return "正在为您切换商品分类..."
            return f"正在{label}..."
        elif action_type == "ask_user":
            return "我需要您确认一下信息，确认后我会继续处理..."
        return f"正在执行 {action_type} 操作..."

    def _describe_backend_tools(self, parsed_calls: list[dict]) -> list[str]:
        """为后端工具调用生成自然语言描述（每个工具一条）"""
        descriptions = []
        tool_labels = {
            "search_products": "搜索商品",
            "get_product_detail": "获取商品详情",
            "get_categories": "获取商品分类",
            "get_hot_products": "查看热销商品",
            "recommend_products": "生成个性化推荐",
            "get_carts": "查看购物车",
            "get_cart_detail": "加载购物车详情",
            "add_to_cart": "加入购物车",
            "update_cart": "更新购物车",
            "remove_cart_item": "删除购物车商品",
            "get_orders": "查看订单列表",
            "get_order_detail": "加载订单详情",
            "create_order": "创建订单",
            "cancel_order": "取消订单",
            "get_user_info": "获取用户信息",
        }
        for pc in parsed_calls:
            name = pc["name"]
            if name not in FRONTEND_TOOLS:
                label = tool_labels.get(name, name)
                args = pc.get("args", {})
                if name == "search_products" and args.get("keyword"):
                    label = f"正在为您搜索「{args['keyword']}」"
                elif name == "add_to_cart":
                    qty = args.get("quantity", 1)
                    label = f"正在帮您加入购物车（数量: {qty}）"
                elif name == "create_order":
                    label = "正在为您创建订单..."
                descriptions.append(f"{label}...")
        return descriptions

    # ── LLM 调用辅助 ─────────────────────────────────

    def _is_tool_unsupported_error(self, error_msg: str) -> bool:
        """判断 API 错误是否因模型不支持 tools/function calling"""
        keywords = ["tool_choice", "tool_choice", "tools", "function",
                     "not supported", "unsupported", "unrecognized",
                     "unknown parameter", "invalid parameter"]
        msg_lower = error_msg.lower()
        return any(kw.lower() in msg_lower for kw in keywords)

    def _is_waiting_for_user_input(self, text: str) -> bool:
        """识别模型已在等待用户选择/确认，避免强制继续执行。"""
        if not text:
            return False
        if "？" not in text and "?" not in text:
            return False
        wait_keywords = (
            "是否", "确认", "哪款", "哪一款", "哪个", "选择",
            "需要我", "要不要", "可以吗", "是否加入", "是否下单",
            "您对", "你对", "感兴趣",
        )
        return any(keyword in text for keyword in wait_keywords)

    def _build_user_prompt_action_from_text(self, text: str) -> dict:
        """兜底：模型只用文本提问时，转成前端弹窗并在同一轮继续。"""
        confirm_keywords = ("是否", "确认", "可以吗", "要不要", "是否加入", "是否下单")
        if any(keyword in text for keyword in confirm_keywords):
            mode = "confirm"
            fields = []
        else:
            mode = "form"
            fields = [{
                "name": "answer",
                "label": "您的回复",
                "type": "text",
                "required": True,
                "placeholder": "请在这里填写需要补充的信息",
            }]
        return {
            "type": "ask_user",
            "label": "需要您补充信息",
            "payload": {
                "title": "请确认后继续",
                "message": text,
                "mode": mode,
                "fields": fields,
                "options": [],
                "confirmText": "提交并继续",
                "cancelText": "取消本次操作",
            },
        }

    async def _create_completion(
        self,
        client: AsyncOpenAI,
        messages: list[dict],
        llm_config: dict,
        tools_enabled: bool,
    ):
        """创建 LLM 补全请求，根据 tools_enabled 决定是否传工具定义"""
        kwargs = {
            "model": llm_config["model"],
            "messages": messages,
            "temperature": llm_config.get("temperature", 0.7),
            "max_tokens": llm_config.get("max_tokens", 2048),
            "top_p": llm_config.get("top_p", 0.9),
            "stream": True,
        }
        if tools_enabled:
            kwargs["tools"] = TOOLS
            kwargs["tool_choice"] = "auto"
        return await client.chat.completions.create(**kwargs)

    # ── 核心：ReAct 流式对话 ────────────────────────────

    async def chat_stream(
        self,
        user_message: str,
        history: Optional[list[dict]] = None,
        user_id: Optional[int] = None,
        username: str = "",
        session_id: str = "",
    ) -> AsyncGenerator[dict, None]:
        """ReAct 循环流式对话。

        Yields:
            {"type": "token", "content": str}   - 文本 token
            {"type": "tool_call", "action": dict} - 需要前端执行的动作
            {"type": "done"}                      - 对话结束
        """
        # 清除上一轮对话可能残留的 ack 数据，避免串扰
        self._ack_data = None
        self._ack_event = None
        self._current_user_message = user_message

        # 每次请求创建新的 ApiClient，使用当前用户的身份调用 Java 后端
        user_id_str = str(user_id) if user_id else "1"
        self.api = ApiClient(user_id=user_id_str)
        llm_config = await self._resolve_llm_runtime_config()
        llm_client = AsyncOpenAI(
            api_key=llm_config["api_key"],
            base_url=llm_config["base_url"],
        )

        # 构建消息列表（注入用户上下文）
        user_context = ""
        if username:
            user_context = f"当前用户: {username} (ID: {user_id_str})。"
        elif user_id:
            user_context = f"当前用户ID: {user_id_str}。"
        system_content = self.system_prompt
        if user_context:
            system_content = system_content + "\n\n" + user_context

        messages = [{"role": "system", "content": system_content}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": user_message})

        current_page = ""  # 跟踪当前所在页面路径
        latest_created_order_id: Optional[str] = None

        # ── 任务跟踪器 ──
        task_tracker = TaskTracker()
        if session_id:
            task_tracker.create_tasks(session_id, user_message)

        self._log_messages(messages)

        # 探测模型是否支持 tools；不支持则降级为纯对话模式
        tools_enabled = True

        # ReAct 循环
        for round_num in range(1, MAX_REACT_ROUNDS + 1):
            logger.info("── ReAct 第 %d 轮 ──", round_num)

            # 注入任务进度到系统消息（第一轮之后）
            if session_id and round_num >= 1:
                task_status = task_tracker.get_status_text(session_id)
                if task_status and messages[0]["role"] == "system":
                    # 替换动态部分：去掉上次注入的状态，追加最新状态
                    base_system = self.system_prompt
                    if user_context:
                        base_system = base_system + "\n\n" + user_context
                    messages[0]["content"] = base_system + task_status

            try:
                stream = await self._create_completion(
                    client=llm_client,
                    messages=messages,
                    llm_config=llm_config,
                    tools_enabled=tools_enabled,
                )
            except Exception as e:
                error_msg = str(e)
                # 如果 tools 不被支持，降级后重试
                if tools_enabled and self._is_tool_unsupported_error(error_msg):
                    logger.warning("模型不支持 tools，降级为纯对话模式: %s", error_msg[:100])
                    tools_enabled = False
                    stream = await self._create_completion(
                        client=llm_client,
                        messages=messages,
                        llm_config=llm_config,
                        tools_enabled=False,
                    )
                else:
                    raise

            # 累积流式响应
            text_parts: list[str] = []
            reasoning_parts: list[str] = []
            streamed_text_len = 0
            tool_call_acc: dict[int, dict] = {}
            finish_reason = None

            async for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                finish_reason = chunk.choices[0].finish_reason
                reasoning_delta = getattr(delta, "reasoning_content", None)
                if reasoning_delta:
                    reasoning_parts.append(reasoning_delta)

                # 累积 tool_calls
                if delta.tool_calls:
                    for tc_delta in delta.tool_calls:
                        idx = tc_delta.index
                        if idx not in tool_call_acc:
                            tool_call_acc[idx] = {
                                "id": "",
                                "type": "function",
                                "function": {"name": "", "arguments": ""},
                            }
                        acc = tool_call_acc[idx]
                        if tc_delta.id:
                            acc["id"] = tc_delta.id
                        if tc_delta.function:
                            if tc_delta.function.name:
                                acc["function"]["name"] += tc_delta.function.name
                            if tc_delta.function.arguments:
                                acc["function"]["arguments"] += tc_delta.function.arguments

                # 流式输出文本
                if delta.content:
                    text_parts.append(delta.content)
                    # 仅在还没有 tool_call 时流式输出，避免文本和 tool_call 交错
                    if not tool_call_acc:
                        yield {"type": "token", "content": delta.content}
                        streamed_text_len += len(delta.content)

            # ── 处理响应 ──
            if tool_call_acc:
                full_round_text = "".join(text_parts)
                if len(full_round_text) > streamed_text_len:
                    yield {"type": "token", "content": full_round_text[streamed_text_len:]}

                # LLM 决定调用工具 → 构建 assistant 消息
                tool_calls = [
                    tool_call_acc[i] for i in sorted(tool_call_acc.keys())
                ]

                assistant_msg = {
                    "role": "assistant",
                    "content": "".join(text_parts) if text_parts else None,
                    "tool_calls": tool_calls,
                }
                if reasoning_parts and self._should_pass_reasoning_content(llm_config):
                    assistant_msg["reasoning_content"] = "".join(reasoning_parts)
                messages.append(assistant_msg)

                # 解析所有工具调用参数
                parsed_calls: list[dict] = []
                for tc in tool_calls:
                    func_name = tc["function"]["name"]
                    try:
                        func_args = json.loads(tc["function"]["arguments"])
                    except json.JSONDecodeError:
                        func_args = {}
                    parsed_calls.append({
                        "tc": tc,
                        "name": func_name,
                        "args": func_args,
                    })

                # ── 第一步：并行执行所有后端工具 ──
                backend_tasks = []
                backend_indices = []
                created_order_id_this_round: Optional[str] = None
                for i, pc in enumerate(parsed_calls):
                    if pc["name"] not in FRONTEND_TOOLS:
                        logger.info("→ 工具调用: %s(%s)", pc["name"], pc["args"])
                        backend_tasks.append(
                            self._execute_backend_tool(pc["name"], pc["args"])
                        )
                        backend_indices.append(i)

                if backend_tasks:
                    # 兜底：先告诉用户要做什么，再执行后端工具
                    if not text_parts:
                        descriptions = self._describe_backend_tools(parsed_calls)
                        for desc in descriptions:
                            yield {"type": "token", "content": desc}

                    backend_results = await asyncio.gather(
                        *backend_tasks, return_exceptions=True
                    )

                    for idx, result in zip(backend_indices, backend_results):
                        if isinstance(result, Exception):
                            result_str = json.dumps({"error": str(result)})
                        else:
                            if parsed_calls[idx]["name"] == "create_order":
                                order_id = self._extract_order_id_from_response(result)
                                if order_id:
                                    latest_created_order_id = order_id
                                    created_order_id_this_round = order_id
                            result_str = json.dumps(result, ensure_ascii=False)
                        parsed_calls[idx]["result"] = result_str
                        logger.info(
                            "← 后端结果 [%s]: %s",
                            parsed_calls[idx]["name"],
                            result_str[:200] + "..." if len(result_str) > 200 else result_str,
                        )

                # ── 第二步：逐个执行前端工具（需等待 ack） ──
                for pc in parsed_calls:
                    if pc["name"] in FRONTEND_TOOLS:
                        if pc["name"] == "navigate":
                            pc["args"]["path"] = self._normalize_frontend_path(
                                pc["args"].get("path", "/"),
                                latest_created_order_id,
                            )
                        if self._should_block_recommendation_navigation(
                            pc["name"], pc["args"]
                        ):
                            pc["result"] = json.dumps({
                                "success": False,
                                "data": {
                                    "error": (
                                        "用户只是请求商品推荐，未明确要求打开智慧购物页面；"
                                        "推荐结果应直接在当前回复中展示。"
                                    )
                                },
                            }, ensure_ascii=False)
                            logger.info("拦截推荐场景下的默认跳转: %s", pc["args"])
                            continue

                        logger.info("→ 工具调用: %s(%s)", pc["name"], pc["args"])
                        action = self._build_action(pc["name"], pc["args"])
                        # 兜底：如果 AI 本轮没说话就动手，自动生成描述文本
                        if not text_parts:
                            description = self._describe_frontend_action(action, current_page)
                            yield {"type": "token", "content": description}
                        yield {"type": "tool_call", "action": action}
                        ack = await self._wait_for_ack()
                        pc["result"] = json.dumps(ack, ensure_ascii=False)
                        # 跟踪导航后的页面状态
                        if pc["name"] == "navigate" and ack.get("success"):
                            current_page = pc["args"].get("path", current_page)
                        logger.info("← tool_ack: %s", pc["result"])
                        if pc["name"] == "ask_user" and not ack.get("success"):
                            yield {"type": "token", "content": "\n已取消本次操作。"}
                            if session_id:
                                task_tracker.cleanup(session_id)
                            yield {"type": "done"}
                            return

                # 创建订单成功后，如果模型漏掉订单页跳转，agent 主动补发导航动作。
                has_frontend_navigate = any(
                    pc["name"] == "navigate" for pc in parsed_calls
                )
                has_user_prompt = any(
                    pc["name"] == "ask_user" for pc in parsed_calls
                )
                if created_order_id_this_round and not has_frontend_navigate and not has_user_prompt:
                    auto_path = f"/order-confirm/{created_order_id_this_round}"
                    action = self._build_action("navigate", {"path": auto_path})
                    yield {
                        "type": "token",
                        "content": "\n订单已创建，正在为您打开订单确认页...",
                    }
                    yield {"type": "tool_call", "action": action}
                    ack = await self._wait_for_ack()
                    nav_result = json.dumps(ack, ensure_ascii=False)
                    if ack.get("success"):
                        current_page = auto_path
                    parsed_calls.append({
                        "tc": None,
                        "name": "navigate",
                        "args": {"path": auto_path},
                        "result": nav_result,
                        "synthetic": True,
                    })
                    logger.info("← 自动订单页跳转 tool_ack: %s", nav_result)

                # ── 第三步：按 LLM 返回的顺序写入消息历史 ──
                for pc in parsed_calls:
                    if pc.get("synthetic"):
                        messages.append({
                            "role": "user",
                            "content": (
                                "系统已根据订单创建结果执行前端导航，结果："
                                + pc["result"]
                            ),
                        })
                        continue
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": pc["tc"]["id"],
                            "content": pc["result"],
                        }
                    )

                # ── 自动更新任务进度 ──
                if session_id and task_tracker.has_tasks(session_id):
                    # 尝试从第一轮的文本中解析 LLM 的任务列表
                    if round_num == 1 and text_parts:
                        full_round_text = "".join(text_parts)
                        task_tracker.try_merge_llm_tasks(
                            session_id, user_message, full_round_text
                        )
                    # 根据工具调用更新进度
                    task_tracker.auto_detect_progress(session_id, parsed_calls)

                # ── 核实闸门：注入核实提醒，强制 AI 在下一轮先验证结果 ──
                backend_was_called = any(
                    pc["name"] not in FRONTEND_TOOLS for pc in parsed_calls
                )
                if backend_was_called:
                    verify_msg = (
                        "【系统提示 — 请先核实上一步的操作结果】"
                        "在继续之前，请检查刚才的工具调用返回结果：\n"
                        "1. 搜索返回的商品是否和用户需求一致？有没有搜错？\n"
                        "2. 加入购物车 / 创建订单是否成功？返回的数据正常吗？\n"
                        "3. 如果发现结果不对（搜错商品、数量不对、价格异常等），"
                        "请立即停止并纠正，不要把错误继续下去！\n"
                        "如果一切正确，请告知用户当前进展，然后继续下一步。"
                    )
                    messages.append({"role": "user", "content": verify_msg})

                # 继续下一轮推理
                continue

            else:
                # LLM 给出了最终文本回复
                full_text = "".join(text_parts)
                if full_text:
                    logger.info("AI回复: %s", full_text)
                    if session_id and task_tracker.has_tasks(session_id):
                        task_tracker.auto_detect_text_progress(session_id, full_text)
                    if (
                        self._is_waiting_for_user_input(full_text)
                        and session_id
                        and task_tracker.has_tasks(session_id)
                        and not task_tracker.is_all_done(session_id)
                    ):
                        action = self._build_user_prompt_action_from_text(full_text)
                        yield {"type": "tool_call", "action": action}
                        ack = await self._wait_for_ack()
                        messages.append({
                            "role": "assistant",
                            "content": full_text,
                        })
                        if ack.get("success"):
                            messages.append({
                                "role": "user",
                                "content": (
                                    "用户通过前端弹窗补充了信息："
                                    + json.dumps(ack.get("data", {}), ensure_ascii=False)
                                    + "。请基于这些信息继续完成原任务。"
                                ),
                            })
                        else:
                            messages.append({
                                "role": "user",
                                "content": "用户取消了前端确认，请停止当前操作并说明原因。",
                            })
                        continue

                # ── 任务完成检查 ──
                if session_id and task_tracker.has_tasks(session_id) and not task_tracker.is_all_done(session_id):
                    # 还有未完成任务，注入提醒并强制继续
                    remaining_tasks = task_tracker.get_status_text(session_id)
                    logger.warning("⚠️ 任务未完成，强制继续。剩余:\n%s", remaining_tasks)
                    # 添加一条 system 消息提醒 AI 继续
                    reminder = (
                        "你还没有完成任务！请查看当前任务进度，"
                        "继续执行下一个未完成的任务。"
                        "在没有完成所有任务之前，不要结束对话！"
                    )
                    assistant_msg = {
                        "role": "assistant",
                        "content": full_text if full_text else None,
                    }
                    messages.append(assistant_msg)
                    messages.append({"role": "user", "content": reminder})
                    # 不 break，继续下一轮 ReAct
                    continue

                break

        # ── 清理任务文件 ──
        if session_id:
            task_tracker.cleanup(session_id)

        yield {"type": "done"}

    def _log_messages(self, messages: list[dict]) -> None:
        """输出对话历史到控制台，方便调试"""
        role_names = {
            "system": "系统",
            "user": "用户",
            "assistant": "AI",
            "tool": "工具",
        }
        logger.info("=" * 50)
        for i, msg in enumerate(messages):
            role = msg["role"]
            label = role_names.get(role, role)
            content = msg.get("content", "")
            if role == "tool":
                content = (
                    (content[:150] + "...") if len(content) > 150 else content
                )
            if role == "system":
                content = content[:100] + "..."
            if role == "assistant" and msg.get("tool_calls"):
                tc_names = [
                    tc["function"]["name"] for tc in msg["tool_calls"]
                ]
                content = f"[调用工具: {', '.join(tc_names)}]"
            logger.info("[%d] %s: %s", i + 1, label, content)
        logger.info("=" * 50)
