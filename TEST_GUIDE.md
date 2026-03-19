# 🧪 QQForwardLimiter 测试指南

## 前置准备

### 1. 安装插件

```bash
# 进入 LangBot 插件目录
cd /path/to/langbot/plugins

# 克隆插件
git clone https://github.com/jry21223/qq_forward_limiter.git

# 确认文件结构
ls qq_forward_limiter/
# 应该看到：
# main.py, manifest.yaml, components/, qq_forward_limiter_plugin/
```

### 2. 配置插件

在 LangBot 管理页面配置：

```yaml
enabled: true
group_only: true
long_text_threshold: 280        # 测试时设小一点，比如 10
burst_window_seconds: 3
burst_count_threshold: 2
max_node_chars: 1000
node_sender_name: ""            # 留空使用 Bot 名称
display_title: "机器人转发消息"
display_source: "LangBot"
ignore_function_call_notices: true
```

### 3. 重启 LangBot

```bash
# 根据你的部署方式选择
systemctl restart langbot
# 或
docker restart langbot
# 或
pkill -f langbot && cd /path/to/langbot && python -m langbot
```

---

## 测试场景

### 场景 1: 单条长消息转发

**步骤**:
1. 在 QQ 群中对 Bot 说：`请回复一段很长的话`
2. Bot 回复超过 280 字符

**预期结果**:
- Bot 的回复应该显示为"合并转发消息"卡片
- 点击卡片可以看到完整内容

**验证日志**:
```bash
tail -f /path/to/langbot/logs/app.log | grep QQForwardLimiter
```

应该看到：
```
[QQForwardLimiter] 适配器：onebotv11, 类型：group
[QQForwardLimiter] 发送合并转发：1 条消息到 group:XXX
[QQForwardLimiter] ✅ 合并转发成功
```

---

### 场景 2: 连续短消息合并

**步骤**:
1. 在 QQ 群中快速连续发送 2 条消息给 Bot：
   - `你好`
   - `在吗`
2. 等待 Bot 回复

**预期结果**:
- Bot 的两条回复应该合并为一条"合并转发消息"
- 卡片显示 2 条消息预览

**验证日志**:
```
[QQForwardLimiter] 消息已加入队列 (1/2)
[QQForwardLimiter] 消息已加入队列 (2/2)
[QQForwardLimiter] 合并消息：2 条
[QQForwardLimiter] 发送合并转发：2 条消息到 group:XXX
[QQForwardLimiter] ✅ 合并转发成功
```

---

### 场景 3: 普通消息不转发

**步骤**:
1. 发送单条短消息：`你好`
2. Bot 回复短消息

**预期结果**:
- Bot 正常回复，不转为合并转发
- 直接显示文本消息

---

### 场景 4: 函数调用通知忽略

**步骤**:
1. 触发 Bot 的函数调用功能
2. Bot 回复 `Call tool xxx...`

**预期结果**:
- 函数调用通知不被转发
- 正常显示

---

## 故障排查

### 问题 1: 日志中没有 `[QQForwardLimiter]` 输出

**原因**: 插件未加载

**解决**:
```bash
# 检查插件目录
ls /path/to/langbot/plugins/qq_forward_limiter/

# 检查 LangBot 启动日志
grep -i "qq_forward_limiter" /path/to/langbot/logs/app.log

# 确认 manifest.yaml 格式正确
cat qq_forward_limiter/manifest.yaml
```

---

### 问题 2: 显示"不支持的目标"

**原因**: 适配器名称不匹配

**解决**:
```bash
# 查看日志中的适配器名称
grep "适配器：" /path/to/langbot/logs/app.log

# 如果不是 onebotv11，需要添加到 service.py
# SUPPORTED_QQ_ADAPTERS = {"aiocqhttp", "nakuru", "napcat", "llmonebot", "onebotv11", "onebot"}
```

---

### 问题 3: 合并转发失败

**原因**: NapCat API 不兼容

**解决**:
```bash
# 查看详细错误
grep "合并转发失败" /path/to/langbot/logs/app.log

# 检查 NapCat 版本
# 确保 NapCat 支持合并转发消息
```

---

## 测试报告模板

测试完成后，请提供以下信息：

```markdown
## 测试环境
- LangBot 版本：x.x.x
- NapCat 版本：x.x.x
- Python 版本：x.x.x

## 测试结果

### 场景 1: 长消息转发
- [ ] 成功
- [ ] 失败
- 日志：[粘贴日志]

### 场景 2: 连续消息合并
- [ ] 成功
- [ ] 失败
- 日志：[粘贴日志]

### 场景 3: 普通消息
- [ ] 正常
- [ ] 异常
- 说明：

## 问题描述
[如果有问题，请详细描述]
```

---

## 快速测试命令

在 QQ 群中发送以下命令快速测试：

```
# 测试长消息
请回复一段超过 280 个字符的很长很长的话，用来测试转发功能是否正常

# 测试连续消息
1
2
3

# 查看插件状态
/qq_forward_limiter status
```

---

**测试完成后，请告诉我结果！** 📊
