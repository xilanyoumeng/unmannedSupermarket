"""任务跟踪器：拆解用户需求为子任务，持久化为临时文件，
在 ReAct 循环中跟踪进度，确保所有任务完成后才结束对话。
"""
import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent
TASK_DIR = BASE_DIR / "history" / "tasks"

# 常见购物流程的默认任务模板
DEFAULT_TASKS = {
    "买": [
        "搜索商品",
        "确认用户选择（品牌/规格/数量）",
        "加入购物车",
        "创建订单",
        "跳转订单确认页面",
    ],
    "加入购物车": [
        "搜索商品",
        "确认用户选择",
        "加入购物车",
        "跳转购物车页面",
    ],
    "推荐": [
        "根据历史偏好/热销数据获取推荐商品",
        "向用户介绍推荐商品",
    ],
    "购物车": [
        "获取购物车内容",
        "跳转购物车页面",
        "向用户展示购物车内容",
    ],
    "订单": [
        "获取订单列表/详情",
        "向用户展示订单信息",
    ],
    "搜索": [
        "搜索商品",
        "展示搜索结果",
        "根据用户反馈操作",
    ],
}

TASK_INTENT_KEYWORDS = (
    "买", "购买", "要一", "来一", "拿", "加购", "加入购物车", "购物车",
    "下单", "结算", "订单", "推荐", "热销", "搜索", "查找", "找",
    "看看", "商品", "价格", "多少钱", "库存", "饮料", "零食", "水果",
    "牛奶", "酸奶", "面包", "方便面", "矿泉水", "可乐", "薯片",
    "跳转", "打开", "进入", "去购物", "去订单", "去购物车",
)


class TaskTracker:
    """管理单个会话的任务拆解与进度跟踪"""

    def __init__(self):
        TASK_DIR.mkdir(parents=True, exist_ok=True)

    def _task_path(self, session_id: str) -> Path:
        return TASK_DIR / f"{session_id}.json"

    def create_tasks(self, session_id: str, user_message: str) -> list[dict]:
        """根据用户消息创建任务列表。先尝试用 LLM，失败则用模板兜底。"""
        tasks = self._generate_tasks_by_template(user_message)
        self._save(session_id, user_message, tasks)
        logger.info("创建任务列表 [%s]: %s", session_id, [t["description"] for t in tasks])
        return tasks

    def try_merge_llm_tasks(self, session_id: str, user_message: str,
                            ai_text: str) -> Optional[list[dict]]:
        """尝试从 LLM 的文本回复中解析任务列表（数字序号开头的行）。
        如果解析成功则覆盖模板任务，返回新列表；否则返回 None。
        """
        # 匹配 "1. xxx" / "1、xxx" / "1) xxx" / "① xxx" 格式的行
        lines = ai_text.strip().split("\n")
        parsed = []
        pattern = re.compile(
            r"^[\s]*"  # leading whitespace
            r"(?:"
            r"  (?:步骤\s*)?\d+[\.\)、\s]"  # "1." "1)" "1、" "步骤1 "
            r"  |[①②③④⑤⑥⑦⑧⑨⑩]"  # circled numbers
            r"  |[一二三四五六七八九十]+\s*[\.\)、]"  # Chinese numbers
            r")"
            r"\s*(.+)$"
        )
        for line in lines:
            m = pattern.match(line)
            if m:
                task_desc = m.group(1).strip()
                if len(task_desc) >= 2 and len(task_desc) <= 60:
                    parsed.append(task_desc)

        if len(parsed) >= 2:
            tasks = [{"id": i + 1, "description": d, "status": "pending"}
                     for i, d in enumerate(parsed)]
            self._save(session_id, user_message, tasks)
            logger.info("从 LLM 回复中解析到 %d 个任务，覆盖模板", len(tasks))
            return tasks
        return None

    def mark_task_done(self, session_id: str, task_id: int) -> None:
        """标记某个任务为完成"""
        data = self._load(session_id)
        if not data:
            return
        for t in data["tasks"]:
            if t["id"] == task_id and t["status"] != "completed":
                t["status"] = "completed"
                self._save_raw(session_id, data)
                logger.info("任务 %d 已完成: %s", task_id, t["description"])
                break

    def mark_current_task(self, session_id: str, task_id: int) -> None:
        """标记某个任务为进行中（其余待处理任务保持 pending）"""
        data = self._load(session_id)
        if not data:
            return
        for t in data["tasks"]:
            if t["id"] == task_id:
                t["status"] = "in_progress"
            elif t["status"] == "in_progress":
                t["status"] = "pending"
        self._save_raw(session_id, data)

    def is_all_done(self, session_id: str) -> bool:
        """检查是否所有任务都已完成"""
        data = self._load(session_id)
        if not data:
            return True  # 没有任务，默认完成
        return all(t["status"] == "completed" for t in data["tasks"])

    def has_tasks(self, session_id: str) -> bool:
        """当前会话是否需要任务追踪。"""
        data = self._load(session_id)
        return bool(data and data.get("tasks"))

    def get_status_text(self, session_id: str) -> str:
        """生成任务状态文本，用于注入到 LLM 对话中"""
        data = self._load(session_id)
        if not data or not data.get("tasks"):
            return ""

        status_map = {
            "pending": "⬜ 未开始",
            "in_progress": "🔄 进行中",
            "completed": "✅ 已完成",
        }
        lines = ["", "## 📋 当前任务进度（必须全部完成才能结束对话）", ""]
        all_done = True
        for t in data["tasks"]:
            icon = status_map.get(t["status"], "⬜")
            if t["status"] != "completed":
                all_done = False
            lines.append(f"  {icon} 任务{t['id']}: {t['description']}")

        if all_done:
            lines.append("")
            lines.append("> ✅ 所有任务已完成，可以结束对话。")
        else:
            pending = [t for t in data["tasks"] if t["status"] != "completed"]
            lines.append("")
            next_task = next(
                (t for t in data["tasks"] if t["status"] == "pending"),
                pending[0] if pending else None,
            )
            if next_task:
                lines.append(f"> ⚠️ 请继续执行下一个任务：**{next_task['description']}**")
            lines.append("> 在完成所有任务之前，不要结束对话！")

        return "\n".join(lines)

    def auto_detect_progress(self, session_id: str,
                             tool_calls: list[dict]) -> None:
        """根据工具调用和结果自动更新任务进度"""
        data = self._load(session_id)
        if not data:
            return

        task_keywords = {
            "search_products": "搜索",
            "get_product_detail": "搜索",
            "get_categories": "搜索",
            "get_hot_products": "获取热销",
            "recommend_products": "推荐",
            "add_to_cart": "加入购物车",
            "get_carts": "购物车",
            "get_cart_detail": "购物车",
            "update_cart": "购物车",
            "create_order": "创建订单",
            "get_orders": "订单",
            "get_order_detail": "订单",
            "navigate_cart": "跳转购物车",
            "navigate_order": "跳转订单确认",
            "navigate_shopping": "跳转智慧购物",
            "ask_user": "确认",
        }

        # 导航路径到任务描述的映射
        navigate_path_keywords = {
            "/cart": "购物车",
            "/cart/": "购物车",
            "/order-confirm": "订单确认",
            "/shopping": "智慧购物",
            "/products": "商品",
        }

        for tc in tool_calls:
            tool_name = tc.get("name", "")
            tool_result = tc.get("result", "{}")
            success = "error" not in str(tool_result).lower()

            if not success:
                continue

            # 匹配关键词
            matched_keywords = set()
            for keyword, task_word in task_keywords.items():
                if keyword in tool_name:
                    matched_keywords.add(task_word)
                # 特殊：navigate 动作
                if tool_name == "navigate":
                    path = tc.get("args", {}).get("path", "")
                    for path_kw, task_kw in navigate_path_keywords.items():
                        if path_kw in path:
                            matched_keywords.add(task_kw)
                            break
                    # 如果没有精确匹配，标记为通用跳转
                    if not matched_keywords:
                        matched_keywords.add("跳转")

            # 根据匹配的关键词更新对应任务
            for t in data["tasks"]:
                for kw in matched_keywords:
                    if kw in t["description"] and t["status"] != "completed":
                        t["status"] = "completed"
                        logger.info("任务 %d 完成（工具 %s）: %s",
                                   t["id"], tool_name, t["description"])
                        break

            # 兜底：navigate 操作至少标记"执行用户要求的操作"为完成
            if tool_name == "navigate":
                for t in data["tasks"]:
                    if t["status"] != "completed":
                        if "执行" in t["description"] or "用户要求" in t["description"] \
                                or "展示最终结果" in t["description"] \
                                or "跳转" in t["description"]:
                            t["status"] = "completed"
                            logger.info("任务 %d 完成（导航兜底）: %s", t["id"], t["description"])
                            break

        # 标记第一个未完成任务为 in_progress
        for t in data["tasks"]:
            if t["status"] == "pending":
                t["status"] = "in_progress"
                break

        self._save_raw(session_id, data)

    def auto_detect_text_progress(self, session_id: str, ai_text: str) -> None:
        """根据已输出的自然语言回复，完成展示/介绍/确认类任务。"""
        if not ai_text or not ai_text.strip():
            return

        data = self._load(session_id)
        if not data:
            return

        text_task_keywords = (
            "展示", "介绍", "告知", "说明", "向用户",
            "确认用户选择", "根据用户反馈", "理解用户需求",
        )
        changed = False
        for t in data["tasks"]:
            if t["status"] == "completed":
                continue
            if any(keyword in t["description"] for keyword in text_task_keywords):
                t["status"] = "completed"
                changed = True
                logger.info("任务 %d 完成（文本回复）: %s", t["id"], t["description"])

        if changed:
            self._save_raw(session_id, data)

    def cleanup(self, session_id: str) -> None:
        """删除任务文件"""
        path = self._task_path(session_id)
        if path.exists():
            path.unlink()
            logger.info("删除任务文件: %s", path)

    # ── 内部方法 ──────────────────────────────────────────

    def _generate_tasks_by_template(self, user_message: str) -> list[dict]:
        """根据用户消息的关键词匹配默认任务模板"""
        for keyword, task_descriptions in DEFAULT_TASKS.items():
            if keyword in user_message:
                return [
                    {"id": i + 1, "description": d, "status": "pending"}
                    for i, d in enumerate(task_descriptions)
                ]
        if not self._has_actionable_intent(user_message):
            return []
        # 默认：通用购物流程
        generic = [
            "理解用户需求",
            "搜索/获取商品信息",
            "确认用户选择",
            "执行用户要求的操作",
            "展示最终结果给用户",
        ]
        return [
            {"id": i + 1, "description": d, "status": "pending"}
            for i, d in enumerate(generic)
        ]

    def _has_actionable_intent(self, user_message: str) -> bool:
        """只有明确购物/订单/导航意图才启用强制任务追踪。"""
        message = (user_message or "").strip().lower()
        if not message:
            return False
        return any(keyword in message for keyword in TASK_INTENT_KEYWORDS)

    def _load(self, session_id: str) -> Optional[dict]:
        path = self._task_path(session_id)
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning("读取任务文件失败: %s", e)
            return None

    def _save(self, session_id: str, user_message: str, tasks: list[dict]) -> None:
        data = {
            "session_id": session_id,
            "original_request": user_message,
            "tasks": tasks,
            "created_at": datetime.now().isoformat(),
        }
        self._save_raw(session_id, data)

    def _save_raw(self, session_id: str, data: dict) -> None:
        data["updated_at"] = datetime.now().isoformat()
        path = self._task_path(session_id)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
