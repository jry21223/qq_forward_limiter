# NapCat API 兼容性检查清单

## 当前代码使用的 API

```python
from langbot_plugin.api.entities.builtin.platform.message import (
    MessageChain,
    Plain,
    ForwardMessageNode,
    ForwardMessageDiaplay,
    Forward,
)
```

## NapCat (OneBot 11) 合并转发格式

NapCat 使用 OneBot 11 标准，合并转发消息格式：

```json
{
    "message_type": "group",
    "message": [
        {
            "type": "node",
            "data": {
                "name": "发送者昵称",
                "uin": 123456,
                "content": [
                    {
                        "type": "text",
                        "data": {
                            "text": "消息内容"
                        }
                    }
                ]
            }
        }
    ]
}
```

## 可能的问题

### 1. 适配器识别问题

当前代码检查：
```python
adapter = str(bot_info.get("adapter", "") or "")
return adapter in SUPPORTED_QQ_ADAPTERS
```

NapCat 在 LangBot 中的适配器名称可能不是 "napcat"，需要检查实际名称。

**检查方法**:
```python
bot_info = await self.plugin.get_bot_info(bot_uuid)
print(f"Adapter: {bot_info.get('adapter')}")
print(f"Adapter runtime values: {bot_info.get('adapter_runtime_values')}")
```

### 2. 消息发送路径问题

当前代码使用：
```python
await self.plugin.send_message(bot_uuid, target_type, target_id, message_chain)
```

NapCat 可能需要特定的消息格式。

### 3. Forward 消息序列化问题

LangBot 的 `Forward` 类需要正确序列化为 OneBot 11 的 node 格式。

## 调试步骤

1. **检查适配器名称**
   - 在 `handle_response` 中添加日志
   - 打印 `bot_info.get("adapter")`

2. **检查消息格式**
   - 在发送前打印 `message_chain`
   - 确认 `Forward` 对象正确构建

3. **检查发送错误**
   - 捕获 `send_message` 的异常
   - 打印详细错误信息

## 建议修复

1. 添加调试日志
2. 支持更多适配器名称变体
3. 添加 fallback 逻辑（如果 Forward 失败，尝试普通消息）
