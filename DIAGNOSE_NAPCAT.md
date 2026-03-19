# 🔍 NapCat API 诊断指南

## 问题现象

QQForwardLimiter 插件在 NapCat 适配器上转发合并消息失败。

## 诊断步骤

### 1. 检查适配器名称

在 LangBot 中查看 Bot 信息：

```python
# 在插件中添加调试代码
bot_info = await self.plugin.get_bot_info(bot_uuid)
print(f"Adapter: {bot_info.get('adapter')}")
print(f"Adapter runtime values: {bot_info.get('adapter_runtime_values')}")
```

NapCat 的适配器名称可能是：
- `napcat`
- `llmonebot`
- `onebot`
- 其他变体

### 2. 检查 LangBot 日志

查看 LangBot 运行日志，搜索 `[QQForwardLimiter]`：

```bash
tail -f langbot.log | grep QQForwardLimiter
```

应该看到类似：
```
[QQForwardLimiter] 适配器：napcat, 类型：group
[QQForwardLimiter] 发送合并转发：3 条消息到 group:123456789
[QQForwardLimiter] ✅ 合并转发成功
```

或错误信息：
```
[QQForwardLimiter] ❌ 合并转发失败：xxx
[QQForwardLimiter] 消息链：Forward(...)
```

### 3. 测试合并转发 API

使用测试插件发送合并转发：

```bash
# 在私聊中发送
/test forward
```

如果测试插件也失败，说明是 LangBot 与 NapCat 的 Forward API 兼容性问题。

### 4. 检查 NapCat 版本

确保 NapCat 是最新版本：
- NapCat 1.x 和 2.x 的 API 可能不同
- 检查是否支持合并转发消息

### 5. 检查 OneBot 实现

NapCat 基于 OneBot 11 标准，合并转发需要特殊处理：

```json
{
    "action": "send_group_forward_msg",
    "params": {
        "group_id": 123456789,
        "messages": [
            {
                "type": "node",
                "data": {
                    "name": "昵称",
                    "uin": 123456,
                    "content": "消息内容"
                }
            }
        ]
    }
}
```

## 常见解决方案

### 方案 1: 更新 SUPPORTED_QQ_ADAPTERS

```python
SUPPORTED_QQ_ADAPTERS = {"aiocqhttp", "nakuru", "napcat", "llmonebot", "onebot"}
```

### 方案 2: 使用 NapCat 原生 API

如果 LangBot 的 Forward 消息类不兼容，可能需要直接使用 NapCat API：

```python
# 通过 HTTP API 直接发送
import aiohttp

async def send_napcat_forward(group_id, nodes):
    async with aiohttp.ClientSession() as session:
        await session.post(
            "http://localhost:6099/send_group_forward_msg",
            json={
                "group_id": group_id,
                "messages": nodes
            }
        )
```

### 方案 3: 降级为普通消息

如果 Forward 完全不可用，可以始终使用普通消息：

```python
# 在 _send_forward_with_fallback 中
# 直接使用普通消息，不尝试 Forward
await self._send_plain_messages(...)
```

## 验证修复

修复后，测试以下场景：

1. **单条长消息** (>280 字符)
   - 应该立即转为合并转发
   
2. **连续短消息** (3 秒内 2 条)
   - 应该合并为一条转发消息
   
3. **单条短消息**
   - 应该正常发送，不转发

## 联系支持

如果问题仍未解决，请提供：
- LangBot 日志
- NapCat 版本
- Bot 适配器信息
- 错误详情
