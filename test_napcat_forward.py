"""
NapCat 合并转发测试插件
用于测试 NapCat 的合并转发 API 是否正确工作
"""

from __future__ import annotations

from langbot_plugin.api.definition.plugin import BasePlugin
from langbot_plugin.api.entities import context, events
from langbot_plugin.api.entities.builtin.platform.message import (
    MessageChain,
    Plain,
    ForwardMessageNode,
    ForwardMessageDiaplay,
    Forward,
)


class NapCatForwardTestPlugin(BasePlugin):
    """NapCat 合并转发测试插件"""
    
    async def initialize(self) -> None:
        self.ap.logger.info("🧪 NapCat 转发测试插件已加载")
        
        @self.handler(events.PersonMessageReceived)
        async def on_person_message(ctx: context.EventContext):
            """私聊消息触发测试"""
            command = ctx.event.query.message_chain.text_plain.strip()
            
            if command == "/test forward":
                ctx.prevent_default()
                
                # 构建合并转发消息
                nodes = [
                    ForwardMessageNode(
                        sender_id="123456",
                        sender_name="测试用户 1",
                        message_chain=MessageChain([Plain(text="这是第一条测试消息")])
                    ),
                    ForwardMessageNode(
                        sender_id="789012",
                        sender_name="测试用户 2",
                        message_chain=MessageChain([Plain(text="这是第二条测试消息")])
                    ),
                    ForwardMessageNode(
                        sender_id="345678",
                        sender_name="测试用户 3",
                        message_chain=MessageChain([Plain(text="这是第三条测试消息")])
                    ),
                ]
                
                display = ForwardMessageDiaplay(
                    title="测试合并转发",
                    brief="[聊天记录]",
                    source="NapCat Test",
                    preview=["这是第一条测试消息", "这是第二条测试消息"],
                    summary="查看 3 条转发消息"
                )
                
                forward = Forward(display=display, node_list=nodes)
                message_chain = MessageChain([forward])
                
                bot_uuid = await ctx.get_bot_uuid()
                await self.send_message(
                    bot_uuid,
                    ctx.event.query.launcher_type,
                    ctx.event.query.launcher_id,
                    message_chain
                )
                
                await ctx.event.query.send_text("✅ 合并转发测试消息已发送")
