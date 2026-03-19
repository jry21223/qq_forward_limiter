from __future__ import annotations

import asyncio
import contextlib
from dataclasses import dataclass, field
from typing import Any

import langbot_plugin.api.entities.builtin.platform.message as platform_message


SUPPORTED_QQ_ADAPTERS = {"aiocqhttp", "nakuru", "napcat", "llmonebot", "onebotv11", "onebot"}


@dataclass(slots=True)
class BufferedConversation:
    bot_uuid: str
    target_type: str
    target_id: str
    sender_id: str
    sender_name: str
    texts: list[str] = field(default_factory=list)
    task: asyncio.Task[None] | None = None


class QQForwardLimiterService:
    def __init__(self, plugin: Any) -> None:
        self.plugin = plugin
        self._lock = asyncio.Lock()
        self._buffers: dict[str, BufferedConversation] = {}

    def close(self) -> None:
        for bucket in list(self._buffers.values()):
            if bucket.task is not None:
                bucket.task.cancel()
        self._buffers.clear()

    async def handle_response(self, ctx: Any) -> None:
        config = self._load_config()
        if not config["enabled"]:
            return

        event = ctx.event

        if config["ignore_function_call_notices"] and event.funcs_called and event.response_text.startswith("Call "):
            return

        if config["group_only"] and event.launcher_type != "group":
            return

        text = self._normalize_text(event.response_text)
        if not text:
            return

        bot_uuid = await ctx.get_bot_uuid()

        try:
            bot_info = await self.plugin.get_bot_info(bot_uuid)
        except Exception as e:
            self.plugin.ap.logger.error(f"[QQForwardLimiter] 获取 Bot 信息失败：{e}")
            return

        # 调试日志：检查适配器
        adapter = str(bot_info.get("adapter", "") or "")
        self.plugin.ap.logger.debug(f"[QQForwardLimiter] 适配器：{adapter}, 类型：{event.launcher_type}")
        
        if not self._is_supported_target(bot_info, event.launcher_type):
            self.plugin.ap.logger.warning(f"[QQForwardLimiter] 不支持的目标：adapter={adapter}, type={event.launcher_type}")
            return

        sender_id = self._resolve_sender_id(bot_info)
        sender_name = self._resolve_sender_name(bot_info, config)
        conversation_key = self._conversation_key(bot_uuid, event.launcher_type, event.launcher_id)

        if config["long_text_threshold"] > 0 and len(text) >= config["long_text_threshold"]:
            ctx.prevent_default()
            drained = await self._drain_conversation(conversation_key)
            texts = drained.texts if drained is not None else []
            texts.append(text)
            await self._send_forward_with_fallback(
                bot_uuid=bot_uuid,
                target_type=event.launcher_type,
                target_id=str(event.launcher_id),
                texts=texts,
                sender_id=sender_id,
                sender_name=sender_name,
                config=config,
                fallback_texts=texts,
                ctx=ctx,
            )
            return

        if config["burst_window_seconds"] <= 0:
            return

        ctx.prevent_default()
        await self._buffer_response(
            key=conversation_key,
            bot_uuid=bot_uuid,
            target_type=event.launcher_type,
            target_id=str(event.launcher_id),
            sender_id=sender_id,
            sender_name=sender_name,
            text=text,
            config=config,
        )

    async def _buffer_response(
        self,
        key: str,
        bot_uuid: str,
        target_type: str,
        target_id: str,
        sender_id: str,
        sender_name: str,
        text: str,
        config: dict[str, Any],
    ) -> None:
        async with self._lock:
            bucket = self._buffers.get(key)
            if bucket is None:
                bucket = BufferedConversation(
                    bot_uuid=bot_uuid,
                    target_type=target_type,
                    target_id=target_id,
                    sender_id=sender_id,
                    sender_name=sender_name,
                )
                self._buffers[key] = bucket

            bucket.sender_id = sender_id
            bucket.sender_name = sender_name
            bucket.texts.append(text)

            if bucket.task is not None:
                bucket.task.cancel()

            bucket.task = asyncio.create_task(self._flush_after_window(key, config))

    async def _flush_after_window(self, key: str, config: dict[str, Any]) -> None:
        try:
            await asyncio.sleep(config["burst_window_seconds"])
            bucket = await self._drain_conversation(key, cancel_task=False)
            if bucket is None or not bucket.texts:
                return

            if len(bucket.texts) >= config["burst_count_threshold"]:
                await self._send_forward_with_fallback(
                    bot_uuid=bucket.bot_uuid,
                    target_type=bucket.target_type,
                    target_id=bucket.target_id,
                    texts=bucket.texts,
                    sender_id=bucket.sender_id,
                    sender_name=bucket.sender_name,
                    config=config,
                    fallback_texts=bucket.texts,
                    ctx=None,
                )
            else:
                await self._send_plain_messages(
                    bot_uuid=bucket.bot_uuid,
                    target_type=bucket.target_type,
                    target_id=bucket.target_id,
                    texts=bucket.texts,
                )
        except asyncio.CancelledError:
            return

    async def _drain_conversation(
        self,
        key: str,
        cancel_task: bool = True,
    ) -> BufferedConversation | None:
        async with self._lock:
            bucket = self._buffers.pop(key, None)
            if bucket is None:
                return None
            if cancel_task and bucket.task is not None:
                bucket.task.cancel()
            bucket.task = None
            return bucket

    async def _send_plain_messages(
        self,
        bot_uuid: str,
        target_type: str,
        target_id: str,
        texts: list[str],
    ) -> None:
        for text in texts:
            message_chain = platform_message.MessageChain([platform_message.Plain(text=text)])
            with contextlib.suppress(Exception):
                await self.plugin.send_message(bot_uuid, target_type, target_id, message_chain)

    async def _send_forward_with_fallback(
        self,
        bot_uuid: str,
        target_type: str,
        target_id: str,
        texts: list[str],
        sender_id: str,
        sender_name: str,
        config: dict[str, Any],
        fallback_texts: list[str],
        ctx: Any | None,
    ) -> None:
        message_chain = self._build_forward_message_chain(
            texts=texts,
            sender_id=sender_id,
            sender_name=sender_name,
            config=config,
        )

        try:
            self.plugin.ap.logger.debug(f"[QQForwardLimiter] 发送合并转发：{len(texts)} 条消息到 {target_type}:{target_id}")
            await self.plugin.send_message(bot_uuid, target_type, target_id, message_chain)
            self.plugin.ap.logger.info(f"[QQForwardLimiter] ✅ 合并转发成功")
        except Exception as e:
            self.plugin.ap.logger.error(f"[QQForwardLimiter] ❌ 合并转发失败：{e}")
            self.plugin.ap.logger.debug(f"[QQForwardLimiter] 消息链：{message_chain}")
            
            if ctx is not None:
                combined = "\n\n".join(fallback_texts)
                ctx.event.reply_message_chain = platform_message.MessageChain(
                    [platform_message.Plain(text=combined)]
                )
            else:
                await self._send_plain_messages(bot_uuid, target_type, target_id, fallback_texts)

    def _build_forward_message_chain(
        self,
        texts: list[str],
        sender_id: str,
        sender_name: str,
        config: dict[str, Any],
    ) -> platform_message.MessageChain:
        nodes: list[platform_message.ForwardMessageNode] = []
        preview: list[str] = []

        for text in texts:
            preview_line = self._make_preview_line(text, config["preview_line_chars"])
            if preview_line and len(preview) < config["preview_line_limit"]:
                preview.append(preview_line)

            for chunk in self._split_text(text, config["max_node_chars"]):
                nodes.append(
                    platform_message.ForwardMessageNode(
                        sender_id=sender_id,
                        sender_name=sender_name,
                        message_chain=platform_message.MessageChain([platform_message.Plain(text=chunk)]),
                    )
                )

        if not preview:
            preview.append("查看转发消息")

        display = platform_message.ForwardMessageDiaplay(
            title=config["display_title"],
            brief="[聊天记录]",
            source=config["display_source"],
            preview=preview,
            summary=f"查看 {len(nodes)} 条转发消息",
        )

        forward = platform_message.Forward(display=display, node_list=nodes)
        return platform_message.MessageChain([forward])

    def _split_text(self, text: str, max_chars: int) -> list[str]:
        cleaned = text.strip()
        if not cleaned:
            return []

        if max_chars <= 0 or len(cleaned) <= max_chars:
            return [cleaned]

        parts: list[str] = []
        start = 0
        total = len(cleaned)

        while start < total:
            end = min(start + max_chars, total)
            if end < total:
                split_at = cleaned.rfind("\n", start, end)
                if split_at > start:
                    end = split_at + 1

            chunk = cleaned[start:end].strip("\n")
            if not chunk:
                chunk = cleaned[start : min(start + max_chars, total)]
                end = start + len(chunk)

            parts.append(chunk)
            start = end

        return parts

    def _make_preview_line(self, text: str, max_chars: int) -> str:
        content = ""
        for line in text.splitlines():
            stripped = line.strip()
            if stripped:
                content = stripped
                break

        if not content:
            content = text.strip()

        if not content:
            return ""

        if max_chars > 0 and len(content) > max_chars:
            return content[:max_chars].rstrip() + "..."

        return content

    def _normalize_text(self, text: str) -> str:
        return (text or "").strip()

    def _resolve_sender_id(self, bot_info: dict[str, Any]) -> str:
        adapter_runtime_values = bot_info.get("adapter_runtime_values", {}) or {}
        bot_account_id = adapter_runtime_values.get("bot_account_id")
        if bot_account_id not in (None, ""):
            return str(bot_account_id)
        return ""

    def _resolve_sender_name(self, bot_info: dict[str, Any], config: dict[str, Any]) -> str:
        configured_name = config["node_sender_name"].strip()
        if configured_name:
            return configured_name

        bot_name = bot_info.get("name")
        if isinstance(bot_name, str) and bot_name.strip():
            return bot_name.strip()

        return "Bot"

    def _is_supported_target(self, bot_info: dict[str, Any], launcher_type: str) -> bool:
        if launcher_type != "group":
            return False
        adapter = str(bot_info.get("adapter", "") or "")
        return adapter in SUPPORTED_QQ_ADAPTERS

    def _conversation_key(self, bot_uuid: str, launcher_type: str, launcher_id: Any) -> str:
        return f"{bot_uuid}:{launcher_type}:{launcher_id}"

    def _load_config(self) -> dict[str, Any]:
        raw = self.plugin.get_config() or {}
        return {
            "enabled": self._as_bool(raw.get("enabled"), True),
            "group_only": self._as_bool(raw.get("group_only"), True),
            "long_text_threshold": self._as_int(raw.get("long_text_threshold"), 280, minimum=0),
            "burst_window_seconds": self._as_int(raw.get("burst_window_seconds"), 3, minimum=0),
            "burst_count_threshold": self._as_int(raw.get("burst_count_threshold"), 2, minimum=1),
            "max_node_chars": self._as_int(raw.get("max_node_chars"), 1000, minimum=1),
            "node_sender_name": self._as_str(raw.get("node_sender_name"), ""),
            "display_title": self._as_str(raw.get("display_title"), "机器人转发消息"),
            "display_source": self._as_str(raw.get("display_source"), "LangBot"),
            "preview_line_limit": self._as_int(raw.get("preview_line_limit"), 4, minimum=1),
            "preview_line_chars": self._as_int(raw.get("preview_line_chars"), 48, minimum=1),
            "ignore_function_call_notices": self._as_bool(raw.get("ignore_function_call_notices"), True),
        }

    def _as_bool(self, value: Any, default: bool) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "yes", "on"}:
                return True
            if normalized in {"0", "false", "no", "off"}:
                return False
        return default

    def _as_int(self, value: Any, default: int, minimum: int | None = None) -> int:
        try:
            result = int(value)
        except (TypeError, ValueError):
            result = default

        if minimum is not None and result < minimum:
            return minimum
        return result

    def _as_str(self, value: Any, default: str) -> str:
        if value is None:
            return default
        return str(value)
