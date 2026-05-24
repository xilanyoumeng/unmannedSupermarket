"""会话管理器：持久化存储用户对话历史，按用户 ID 隔离。

目录结构:
  history/
    index.json                  # session_id → user_id 的映射索引
    user_1/
      <session_id>.json         # 会话消息文件
    user_2/
      <session_id>.json
"""

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent
HISTORY_DIR = BASE_DIR / "history"
INDEX_FILE = HISTORY_DIR / "index.json"


class SessionManager:
    def __init__(self):
        HISTORY_DIR.mkdir(parents=True, exist_ok=True)
        self._index = self._load_index()

    # ── 索引管理 ──────────────────────────────────────────

    def _load_index(self) -> dict:
        if INDEX_FILE.exists():
            try:
                with open(INDEX_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                # 索引文件损坏时，备份并重建
                backup = INDEX_FILE.with_suffix(".json.bak")
                INDEX_FILE.rename(backup)
                return {}
        return {}

    def _save_index(self) -> None:
        with open(INDEX_FILE, "w", encoding="utf-8") as f:
            json.dump(self._index, f, ensure_ascii=False, indent=2)

    def _load_session_file(self, session_id: str) -> Optional[dict]:
        """从文件加载会话数据"""
        if session_id not in self._index:
            return None
        user_id = self._index[session_id]["user_id"]
        file_path = self._get_session_path(user_id, session_id)
        if not file_path.exists():
            return None
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save_session_file(self, session_id: str, session_data: dict) -> None:
        """将会话数据写回文件"""
        if session_id not in self._index:
            logger.warning("save_session_file: session_id %s 不在索引中，跳过保存", session_id)
            return
        user_id = self._index[session_id]["user_id"]
        file_path = self._get_session_path(user_id, session_id)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(session_data, f, ensure_ascii=False, indent=2)

    # ── 路径工具 ──────────────────────────────────────────

    def _get_user_dir(self, user_id: int) -> Path:
        user_dir = HISTORY_DIR / f"user_{user_id}"
        user_dir.mkdir(parents=True, exist_ok=True)
        return user_dir

    def _get_session_path(self, user_id: int, session_id: str) -> Path:
        return self._get_user_dir(user_id) / f"{session_id}.json"

    # ── 会话操作 ──────────────────────────────────────────

    def create_session(self, user_id: int, username: str = "") -> dict:
        """创建新会话，如果已有空白会话则复用，返回 (session_data, is_existing)"""
        # 先检查是否已有空白会话（无消息的会话）
        existing = self._find_empty_session(user_id)
        if existing:
            return {**existing, "is_existing": True}

        session_id = str(uuid.uuid4())
        now = datetime.now()
        created_at = now.strftime("%Y-%m-%d %H:%M:%S")

        self._index[session_id] = {
            "user_id": user_id,
            "username": username,
            "created_at": created_at,
            "title": "新会话",
            "last_message": "",
        }
        self._save_index()

        session_data = {
            "session_id": session_id,
            "user_id": user_id,
            "username": username,
            "title": "新会话",
            "created_at": created_at,
            "updated_at": now.isoformat(),
            "last_message": "",
            "messages": [],
            "is_existing": False,
        }

        self._save_session_file(session_id, session_data)
        return session_data

    def _find_empty_session(self, user_id: int) -> Optional[dict]:
        """查找该用户的空白会话（无消息），返回最新一个"""
        candidates = []
        for sid, info in self._index.items():
            try:
                indexed_user_id = int(info.get("user_id", 0))
            except (TypeError, ValueError):
                continue
            if indexed_user_id != user_id:
                continue
            session_data = self._load_session_file(sid)
            if session_data and not session_data.get("messages"):
                candidates.append((info.get("created_at", ""), session_data))
        if candidates:
            # 返回最新创建的空会话
            candidates.sort(key=lambda x: x[0], reverse=True)
            return candidates[0][1]
        return None

    def load_session(self, session_id: str, user_id: Optional[int] = None) -> Optional[dict]:
        """根据 session_id 加载完整会话数据（包含 action 字段的消息列表）"""
        if user_id is not None and not self.session_belongs_to_user(session_id, user_id):
            return None
        return self._load_session_file(session_id)

    def save_message(
        self,
        session_id: str,
        role: str,
        content: str,
        action: Optional[dict] = None,
        user_id: Optional[int] = None,
    ) -> bool:
        """向已有会话追加一条消息"""
        if user_id is not None and not self.session_belongs_to_user(session_id, user_id):
            logger.warning(
                "save_message: session_id %s 不属于 user_id %s，拒绝保存",
                session_id,
                user_id,
            )
            return False

        session_data = self._load_session_file(session_id)
        if session_data is None:
            return False

        now = datetime.now()
        time_str = now.strftime("%H:%M")

        msg = {
            "role": role,
            "content": content,
            "time": time_str,
            "action": action,
        }
        session_data["messages"].append(msg)
        session_data["updated_at"] = now.isoformat()

        # 自动更新标题（取第一条用户消息的前 20 字）
        if role == "user" and session_data["title"] == "新会话":
            session_data["title"] = content[:20]

        # 更新 last_message 摘要
        summary = content[:50] if len(content) > 50 else content
        session_data["last_message"] = summary

        self._save_session_file(session_id, session_data)

        # 同步索引中的 title 和 last_message
        if session_id in self._index:
            self._index[session_id]["title"] = session_data["title"]
            self._index[session_id]["last_message"] = summary
            self._save_index()
        return True

    def save_or_update_last_assistant_message(
        self,
        session_id: str,
        content: str,
        action: Optional[dict] = None,
        user_id: Optional[int] = None,
    ) -> bool:
        """保存当前轮助手回复快照；如果上一条已经是助手消息，则更新它。"""
        if user_id is not None and not self.session_belongs_to_user(session_id, user_id):
            logger.warning(
                "save_or_update_last_assistant_message: session_id %s 不属于 user_id %s，拒绝保存",
                session_id,
                user_id,
            )
            return False

        session_data = self._load_session_file(session_id)
        if session_data is None:
            return False

        now = datetime.now()
        time_str = now.strftime("%H:%M")
        messages = session_data.setdefault("messages", [])
        msg = {
            "role": "assistant",
            "content": content,
            "time": time_str,
            "action": action,
        }

        if messages and messages[-1].get("role") == "assistant":
            messages[-1].update(msg)
        else:
            messages.append(msg)

        session_data["updated_at"] = now.isoformat()
        summary = content[:50] if len(content) > 50 else content
        if not summary and action:
            summary = action.get("label") or action.get("type") or "AI导购操作"
        session_data["last_message"] = summary

        self._save_session_file(session_id, session_data)

        if session_id in self._index:
            self._index[session_id]["title"] = session_data["title"]
            self._index[session_id]["last_message"] = summary
            self._save_index()
        return True

    # ── 辅助查询 ──────────────────────────────────────────

    def list_sessions(self, user_id: int) -> list[dict]:
        """获取某用户的所有会话摘要列表"""
        sessions = []
        stale_session_ids = []
        for sid, info in list(self._index.items()):
            try:
                indexed_user_id = int(info.get("user_id", 0))
            except (TypeError, ValueError):
                continue
            if indexed_user_id != user_id:
                continue

            session_data = self._load_session_file(sid)
            if not session_data:
                stale_session_ids.append(sid)
                continue
            if not session_data.get("messages"):
                continue

            sessions.append({
                "session_id": sid,
                "title": session_data.get("title") or info.get("title", "新会话"),
                "created_at": session_data.get("created_at") or info.get("created_at", ""),
                "updated_at": session_data.get("updated_at", ""),
                "last_message": session_data.get("last_message") or info.get("last_message", ""),
            })

        if stale_session_ids:
            for sid in stale_session_ids:
                self._index.pop(sid, None)
            self._save_index()

        sessions.sort(key=lambda s: s.get("updated_at") or s["created_at"], reverse=True)
        return sessions

    def delete_session(self, session_id: str, user_id: Optional[int] = None) -> bool:
        """删除会话（索引 + 文件），返回是否成功"""
        if session_id not in self._index:
            return False

        if user_id is not None and not self.session_belongs_to_user(session_id, user_id):
            return False

        user_id = self._index[session_id]["user_id"]
        file_path = self._get_session_path(user_id, session_id)

        # 删除会话文件
        if file_path.exists():
            file_path.unlink()

        # 从索引中移除
        del self._index[session_id]
        self._save_index()

        # 如果用户目录为空则清理
        user_dir = self._get_user_dir(user_id)
        if not any(user_dir.iterdir()):
            user_dir.rmdir()

        return True

    def session_belongs_to_user(self, session_id: str, user_id: int) -> bool:
        """校验会话是否属于指定用户"""
        if session_id not in self._index:
            return False
        try:
            indexed_user_id = int(self._index[session_id].get("user_id", 0))
        except (TypeError, ValueError):
            return False
        return indexed_user_id == user_id
