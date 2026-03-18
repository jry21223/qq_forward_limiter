# qq_forward_limiter

把 QQ 群里的 Bot 回复改成“合并转发消息”，主要处理两种场景：

- 单条回复过长
- 几秒内连续回复多条

## 行为

- 仅监听 `NormalMessageResponded`
- 仅在 QQ 适配器群聊里启用，当前按 `aiocqhttp` 和 `nakuru` 判断
- 超长回复会立即改成合并转发
- 短时间多次回复会先缓冲，等静默 `burst_window_seconds` 秒后统一发送
- 如果窗口内条数未达到 `burst_count_threshold`，会按普通文本逐条补发

## 说明

- 发送路径走的是插件 API `send_message(...)`，不是 `reply_message(...)`
- 当前 LangBot 事件只给插件暴露 `response_text`，所以这个插件按文本转发，不保留图片、文件等结构化回复组件
- 命令组件的直接输出不经过 `NormalMessageResponded`，默认不会被这个插件改写
- 主要适合 QQ 群聊防刷屏，不会保留引用回复

## 关键配置

- `long_text_threshold`: 单条回复超多少字符后直接转发
- `burst_window_seconds`: 多条回复的缓冲时间窗口
- `burst_count_threshold`: 窗口内达到多少条后改为合并转发
- `max_node_chars`: 单个转发节点最大长度，避免一个节点过长
- `node_sender_name`: 转发节点昵称，留空时使用 Bot 名称

## 目录

- `main.py`: 插件入口
- `components/event_listener/response_forwarder.py`: 事件监听
- `qq_forward_limiter_plugin/service.py`: 转发和缓冲逻辑
