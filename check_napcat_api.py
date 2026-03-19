"""
检查 NapCat API 支持
"""

# NapCat (基于 OneBot 11) 的合并转发 API
# https://napcat.dev/docs/

# NapCat 支持以下合并转发消息格式：

# 方式 1: node 数组 (推荐)
"""
{
    "message": [
        {
            "type": "node",
            "data": {
                "id": "消息 ID"  # 可选，引用已有消息
            }
        },
        {
            "type": "node",
            "data": {
                "name": "发送者昵称",
                "uin": 发送者 QQ 号，
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
"""

# 方式 2: forward 类型 (旧版)
"""
{
    "message": {
        "type": "forward",
        "data": {
            "content": [
                {
                    "type": "node",
                    "data": {
                        "name": "昵称",
                        "uin": QQ 号，
                        "content": "消息内容"
                    }
                }
            ]
        }
    }
}
"""

# NapCat 适配器在 LangBot 中应该使用 platform_message.Forward
# 但需要检查是否正确实现了 NapCat 的 node 格式

print("NapCat 合并转发 API 检查完成")
print("关键问题:")
print("1. 当前代码使用 platform_message.ForwardMessageNode")
print("2. 需要确认 LangBot 是否正确转换为 NapCat 的 node 格式")
print("3. 检查 display 和 node_list 是否正确映射")
