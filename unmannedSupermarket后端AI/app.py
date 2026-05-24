import asyncio
import json
import logging
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agent.api_client import ApiClient
from agent.shopping_agent import ShoppingAgent
from product_vector_recognizer import ProductVectorRecognizer
from session_manager import SessionManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
TOOL_ACK_TIMEOUT_SECONDS = 10 * 60
FRONTEND_ACTION_ACK_TIMEOUT_SECONDS = 8

app = FastAPI(title="AI导购助手", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

agent = ShoppingAgent()
session_manager = SessionManager()
product_recognizer = ProductVectorRecognizer()


def normalize_user_id(value) -> Optional[int]:
    try:
        user_id = int(value)
    except (TypeError, ValueError):
        return None
    return user_id if user_id > 0 else None


def login_required_response():
    return {
        "code": 401,
        "message": "请先登录后再使用 AI 导购助手",
        "data": None,
    }


async def resolve_product_recognition_api_key(user_id: Optional[int]) -> Optional[str]:
    """商品图片向量库固定使用 DashScope embedding；只读取用户单独配置的 DashScope 密钥。"""
    if user_id is None:
        return None
    try:
        response = await ApiClient(user_id=str(user_id)).get_multimodal_model_config()
        data = response.get("data") if isinstance(response, dict) else None
        if not isinstance(data, dict) or not data.get("hasUserConfig"):
            return None

        provider = (data.get("provider") or "").strip().lower()
        api_key = (data.get("apiKey") or "").strip()
        if api_key and provider == "dashscope":
            logger.info("商品图片识别使用用户 DashScope API Key: user_id=%s", user_id)
            return api_key

        logger.info(
            "用户多模态配置不是 DashScope，商品图片识别回退系统 %s: user_id=%s provider=%s",
            product_recognizer.api_key_env, user_id, provider or "unknown",
        )
    except Exception as exc:
        logger.warning("读取用户多模态识别密钥失败，回退系统配置: user_id=%s error=%s", user_id, exc)
    return None


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.get("/api/product/vector-status")
async def product_vector_status():
    try:
        data = product_recognizer.status()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"code": 200, "message": "success", "data": data}


@app.post("/api/product/recognize")
async def recognize_product(image: UploadFile = File(...), user_id: Optional[int] = Form(default=None)):
    if not image.content_type or not image.content_type.startswith("image/"):
        return {"code": 400, "message": "Only image files are supported", "data": None}

    try:
        normalized_user_id = normalize_user_id(user_id)
        api_key = await resolve_product_recognition_api_key(normalized_user_id)
        image_bytes = await image.read()
        data = product_recognizer.recognize(
            image_bytes=image_bytes,
            filename=image.filename,
            content_type=image.content_type,
            api_key=api_key,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {"code": 200, "message": "success", "data": data}


# ──────────────────────────────────────────────────────────
# 会话管理 REST API
# ──────────────────────────────────────────────────────────

class CreateSessionRequest(BaseModel):
    user_id: Optional[int] = None
    username: str = ""


@app.post("/api/session/create")
async def create_session(req: CreateSessionRequest):
    """创建新会话"""
    user_id = normalize_user_id(req.user_id)
    if user_id is None:
        return login_required_response()
    session_data = session_manager.create_session(
        user_id=user_id, username=req.username
    )
    return {
        "code": 200,
        "message": "success",
        "data": {
            "session_id": session_data["session_id"],
            "title": session_data["title"],
            "created_at": session_data["created_at"],
            "is_existing": session_data.get("is_existing", False),
        },
    }


@app.get("/api/session/list")
async def list_sessions(user_id: Optional[int] = None):
    """查询用户的所有会话"""
    user_id = normalize_user_id(user_id)
    if user_id is None:
        return login_required_response()
    sessions = session_manager.list_sessions(user_id)
    return {
        "code": 200,
        "message": "success",
        "data": {"sessions": sessions},
    }


@app.get("/api/session/{session_id}/messages")
async def load_session(session_id: str, user_id: Optional[int] = None):
    """加载某个会话的消息列表"""
    user_id = normalize_user_id(user_id)
    if user_id is None:
        return login_required_response()
    session_data = session_manager.load_session(session_id, user_id=user_id)
    if session_data is None:
        return {
            "code": 200,
            "message": "success",
            "data": {"messages": [], "missing": True},
        }
    return {
        "code": 200,
        "message": "success",
        "data": {"messages": session_data.get("messages", [])},
    }


@app.delete("/api/session/{session_id}")
async def delete_session(session_id: str, user_id: Optional[int] = None):
    """删除会话"""
    user_id = normalize_user_id(user_id)
    if user_id is None:
        return login_required_response()
    ok = session_manager.delete_session(session_id, user_id=user_id)
    if not ok:
        return {
            "code": 200,
            "message": "success",
            "data": None,
        }
    return {
        "code": 200,
        "message": "success",
        "data": None,
    }


# ──────────────────────────────────────────────────────────
# WebSocket 聊天
# ──────────────────────────────────────────────────────────


@app.websocket("/ws/chat")
async def ws_chat(ws: WebSocket):
    """WebSocket 双向流式对话，支持会话管理 + ReAct tool_call / tool_ack 协议"""
    await ws.accept()
    logger.info("WebSocket 连接已建立")

    try:
        while True:
            raw = await ws.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await ws.send_json({"type": "error", "message": "请求格式错误"})
                continue

            msg_type = data.get("type", "")

            # ── 聊天消息（流式） ──
            if msg_type == "chat":
                session_id = data.get("session_id", "")
                message = data.get("message", "")
                user_id = normalize_user_id(data.get("user_id"))
                username = data.get("username", "")

                if not message:
                    await ws.send_json({
                        "type": "error",
                        "message": "消息不能为空",
                    })
                    continue

                if user_id is None:
                    await ws.send_json({
                        "type": "error",
                        "message": "请先登录后再使用 AI 导购助手",
                    })
                    continue

                # 如果没有 session_id，或 session_id 不属于当前用户，则创建该用户自己的会话
                if session_id and not session_manager.session_belongs_to_user(session_id, user_id):
                    logger.warning(
                        "会话归属不匹配，已拒绝复用: session=%s user_id=%s",
                        session_id,
                        user_id,
                    )
                    session_id = ""

                if not session_id:
                    session_data = session_manager.create_session(
                        user_id=user_id, username=username
                    )
                    session_id = session_data["session_id"]
                    # 通知前端新创建的会话 ID
                    await ws.send_json({
                        "type": "session_created",
                        "session_id": session_id,
                        "title": session_data["title"],
                        "created_at": session_data["created_at"],
                        "is_existing": session_data.get("is_existing", False),
                    })

                logger.info("收到消息: %s (user_id=%s, username=%s, session=%s)",
                            message[:100], user_id, username, session_id)

                # 加载当前会话的历史记录
                history_messages = []
                if session_id:
                    session_data = session_manager.load_session(session_id, user_id=user_id)
                    if session_data is None:
                        # 会话不存在（可能是服务重启丢失了），重新创建
                        session_data = session_manager.create_session(
                            user_id=user_id, username=username
                        )
                        session_id = session_data["session_id"]
                        await ws.send_json({
                            "type": "session_created",
                            "session_id": session_id,
                            "title": session_data["title"],
                            "created_at": session_data["created_at"],
                            "is_existing": session_data.get("is_existing", False),
                        })
                    history_messages = [
                        {"role": m["role"], "content": m["content"]}
                        for m in session_data.get("messages", [])
                    ]
                    # 保存用户消息到会话文件
                    session_manager.save_message(session_id, "user", message, user_id=user_id)

                # 累积助手完整回复，用于最终持久化
                full_response: list[str] = []
                # 记录本轮最后的前端 tool_call action
                last_action: dict | None = None

                def save_assistant_snapshot(action: dict | None = None) -> None:
                    assistant_content = "".join(full_response).strip()
                    snapshot_action = action or last_action
                    if not assistant_content and snapshot_action:
                        assistant_content = (
                            f"已执行："
                            f"{snapshot_action.get('label') or snapshot_action.get('type') or '前端操作'}"
                        )
                    if session_id and (assistant_content or snapshot_action):
                        session_manager.save_or_update_last_assistant_message(
                            session_id,
                            assistant_content,
                            action=snapshot_action,
                            user_id=user_id,
                        )

                try:
                    async for event in agent.chat_stream(
                        user_message=message,
                        history=history_messages,
                        user_id=user_id,
                        username=username,
                        session_id=session_id,
                    ):
                        if event["type"] == "token":
                            full_response.append(event["content"])
                            await ws.send_json(event)

                        elif event["type"] == "tool_call":
                            action = event.get("action", {})
                            action_type = action.get("type", "")
                            # 记录前端 action 用于保存到消息中
                            last_action = action
                            await ws.send_json(event)
                            logger.info("→ tool_call: %s", action_type)
                            if action_type == "ask_user":
                                save_assistant_snapshot(action)

                            # 所有前端工具都等待真实 ack。导航/点击由前端执行后回传；
                            # ask_user 会弹窗收集用户确认/输入，再把数据回传给 agent 继续本轮任务。
                            ack_timeout = (
                                TOOL_ACK_TIMEOUT_SECONDS
                                if action_type == "ask_user"
                                else FRONTEND_ACTION_ACK_TIMEOUT_SECONDS
                            )
                            try:
                                raw_ack = await asyncio.wait_for(
                                    ws.receive_text(), timeout=ack_timeout
                                )
                                ack_data = json.loads(raw_ack)
                                if ack_data.get("type") == "tool_ack":
                                    agent.receive_tool_ack(
                                        action_type=ack_data.get("action_type", action_type),
                                        success=ack_data.get("success", False),
                                        data=ack_data.get("data"),
                                    )
                                else:
                                    agent.receive_tool_ack(
                                        action_type=action_type,
                                        success=False,
                                        data={"error": "未收到有效工具回执"},
                                    )
                            except asyncio.TimeoutError:
                                agent.receive_tool_ack(
                                    action_type=action_type,
                                    success=False,
                                    data={"error": "等待前端工具回执超时"},
                                )
                            except json.JSONDecodeError:
                                agent.receive_tool_ack(
                                    action_type=action_type,
                                    success=False,
                                    data={"error": "工具回执格式错误"},
                                )
                            continue

                        elif event["type"] == "done":
                            await ws.send_json(event)

                    # 对话结束，持久化助手回复。工具型回复可能只有 action，没有 token，也要入历史。
                    save_assistant_snapshot()

                except Exception as e:
                    save_assistant_snapshot()
                    error_detail = str(e)
                    logger.error("AI 回复出错: %s", error_detail)
                    await ws.send_json({
                        "type": "error",
                        "message": f"AI服务出错: {error_detail[:200]}",
                    })

            # ── tool 执行回执 ──
            elif msg_type == "tool_ack":
                agent.receive_tool_ack(
                    action_type=data.get("action_type", ""),
                    success=data.get("success", False),
                    data=data.get("data"),
                )
                logger.info(
                    "← 独立 tool_ack: %s success=%s",
                    data.get("action_type"),
                    data.get("success"),
                )

            else:
                await ws.send_json({
                    "type": "error",
                    "message": f"未知的消息类型: {msg_type}",
                })

    except WebSocketDisconnect:
        logger.info("WebSocket 连接已断开")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
