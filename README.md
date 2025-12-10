# 狼人杀 Agent 挑战赛 - PlayerAgent

这是为狼人杀 Agent 挑战赛开发的智能体实现，基于 AgentScope 1.0 框架和百炼平台的 qwen3-max 模型。

## 项目简介

本项目实现了一个智能狼人杀玩家 Agent，具备以下特性：

- ✅ **长期记忆系统**：跨多局游戏学习和经验积累
- ✅ **上下文管理**：智能压缩对话历史，优化 Token 使用
- ✅ **个性化提示词**：支持通过环境变量配置个性化游戏风格
- ✅ **结构化输出验证**：确保所有输出符合游戏要求
- ✅ **状态持久化**：支持多局游戏之间的状态连续

## 安装说明

### 1. 环境要求

- Python >= 3.10
- AgentScope >= 0.1.0

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

必须设置 DashScope API Key：

```bash
export DASHSCOPE_API_KEY="your_api_key_here"
```

（可选）如果希望使用个性化提示词，可以设置 Agent 配置：

```bash
export AGENT_CONFIG='{"personality": {"aggression": 7, "trust_level": 4}, "strategy": {...}, "role_strategies": {...}}'
```

## 使用方法

### 基本使用

```python
from agent import PlayerAgent

# 创建 Agent（只接受 name 参数）
agent = PlayerAgent(name="Player1")

# 观察游戏信息
await agent.observe(message)

# 生成响应
response = await agent(msg=input_message)

# 状态持久化
state = agent.state_dict()
agent.load_state_dict(state)
```

### 个性化配置（可选）

通过环境变量 `AGENT_CONFIG` 设置个性化配置：

```python
import os
import json

# 设置个性化配置
config = {
    "personality": {
        "aggression": 7,        # 激进度 1-10
        "trust_level": 4,        # 信任度 1-10
        "logic_focus": 8,        # 逻辑性 1-10
        "deception_skill": 6,    # 欺骗能力 1-10
        "speech_style": "简洁直接",
        "risk_tolerance": 5      # 风险承受 1-10
    },
    "strategy": {
        "voting_basis": "基于逻辑推理和证据",
        "speak_timing": "关键时机发言",
        "suspicion_threshold": 0.6,
        "alliance_tendency": "适度结盟"
    },
    "role_strategies": {
        "werewolf": {
            "disguise_preference": "伪装成村民",
            "kill_priority": "优先击杀预言家"
        },
        "seer": {
            "reveal_timing": "中后期暴露",
            "check_priority": "优先查验可疑玩家"
        }
    }
}

os.environ["AGENT_CONFIG"] = json.dumps(config)
agent = PlayerAgent(name="Player1")
```

## 比赛要求符合性

本实现完全符合比赛要求：

- ✅ 类名：`PlayerAgent`，定义在 `agent.py` 文件中
- ✅ 构造函数：只接受 `name` 参数
- ✅ 必需方法：
  - `observe(msg: Msg | list[Msg] | None) -> None`
  - `__call__(msg: Msg | list[Msg] | None = None) -> Msg`
  - `state_dict() -> dict`
  - `load_state_dict(state_dict: dict, strict: bool = False) -> None`
- ✅ 模型：使用 `qwen3-max`（DashScope）
- ✅ 结构化输出：支持 BaseModel 验证
- ✅ 响应限制：自动检查并截断超过 2048 字符的响应

## 核心模块

### 1. GameLongTermMemory
长期记忆系统，存储：
- 对手画像（行为模式、投票倾向）
- 策略经验（历史游戏策略和结果）
- 角色经验（各角色的胜率和有效策略）

### 2. ContextManager
上下文管理器，实现：
- 智能对话压缩（保留关键信息）
- Token 使用监控
- 关键事件提取

### 3. PromptGenerator
提示词生成器（可选），支持：
- 性格参数化配置
- 策略动态嵌入
- 角色特定策略

## 技术特点

1. **分层记忆结构**：短期/中期/长期三层记忆，确保信息高效利用
2. **智能压缩策略**：根据 Token 使用量动态调整压缩强度
3. **对手画像系统**：为每个对手建立行为模型，提升策略针对性
4. **在线学习能力**：从每局游戏中提取经验，持续优化策略

## 注意事项

1. **API Key 安全**：不要在代码中硬编码 API Key，使用环境变量
2. **响应时间**：每次发言必须在 30 秒内完成
3. **响应长度**：响应内容不能超过 2048 字符（会自动截断）
4. **结构化输出**：所有结构化输出必须合法，否则会使用降级方案

## 许可证

本项目为比赛提交作品，遵循比赛规则和许可证要求。

