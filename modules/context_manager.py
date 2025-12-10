# -*- coding: utf-8 -*-
# flake8: noqa: E501
"""Context manager for efficient conversation history management."""
from typing import Any
from copy import deepcopy

from agentscope.message import Msg
from agentscope.module import StateModule
from agentscope._logging import logger


class ContextManager(StateModule):
    """上下文管理器，高效管理对话历史。
    
    该类实现分层记忆结构、对话压缩、关键信息提取、Token 监控
    和动态调整机制，确保智能体在30秒响应时间和2048字符限制内高效运行。
    
    继承自 StateModule 以支持状态持久化。
    """

    # Token 阈值配置
    TOKEN_THRESHOLDS = {
        "warning": 8000,      # 警告阈值：接近限制
        "compress": 10000,    # 压缩阈值：必须压缩
        "max": 12000,         # 最大限制：硬限制
    }

    # 关键信息关键词模式
    KEY_PATTERNS = {
        "vote": ["投票", "vote", "投给", "选择"],
        "identity": ["是狼", "是好人", "身份", "角色", "我是"],
        "death": ["死亡", "died", "killed", "被杀死", "出局"],
        "skill": ["解药", "毒药", "查验", "开枪", "救", "毒"],
        "decision": ["决定", "决策", "策略", "认为"],
        "phase": ["天黑", "天亮", "夜晚", "白天", "第一夜", "第一天"],
    }

    # 重要性评分
    IMPORTANCE_SCORES = {
        "vote": 1.0,
        "identity": 0.9,
        "death": 0.8,
        "skill": 0.7,
        "decision": 0.6,
        "discussion": 0.3,
    }

    def __init__(self, agent_name: str, config: dict[str, Any] | None = None):
        """Initialize the context manager.
        
        Args:
            agent_name (str): The name of the agent.
            config (dict, optional): Configuration dictionary.
        """
        super().__init__()
        self.agent_name = agent_name
        
        # 配置参数
        config = config or {}
        self.token_warning_threshold = config.get("token_warning_threshold", self.TOKEN_THRESHOLDS["warning"])
        self.token_compress_threshold = config.get("token_compress_threshold", self.TOKEN_THRESHOLDS["compress"])
        self.token_max_threshold = config.get("token_max_threshold", self.TOKEN_THRESHOLDS["max"])
        self.max_messages_before_compress = config.get("max_messages_before_compress", 100)
        
        # 中期记忆：存储当前游戏的关键事件
        self.medium_term_memory: dict[str, Any] = {
            "key_events": [],
            "summaries": [],
        }
        
        # 压缩历史统计
        self.compression_history: dict[str, Any] = {
            "last_compression_time": None,
            "compression_count": 0,
            "compressed_messages_count": 0,
        }
        
        # 注册需要持久化的状态
        self.register_state("agent_name")
        self.register_state("medium_term_memory")
        self.register_state("compression_history")

    def is_key_message_by_metadata(self, msg: Msg) -> bool:
        """基于结构化输出判断是否为关键消息（最准确）。
        
        Args:
            msg (Msg): The message to check.
        
        Returns:
            bool: True if the message is key message, False otherwise.
        """
        if not msg.metadata:
            return False
        
        # 检查投票结果
        if "vote" in msg.metadata:
            return True
        
        # 检查决策
        if "reach_agreement" in msg.metadata:
            return True
        
        # 检查技能使用
        if any(key in msg.metadata for key in ["resurrect", "poison", "shoot"]):
            return True
        
        # 检查预言家查验或女巫毒药中的 name 字段（有意义时）
        if "name" in msg.metadata and msg.metadata.get("name") is not None:
            # 如果有其他关键字段，说明是技能使用
            if any(key in msg.metadata for key in ["poison", "shoot", "resurrect"]):
                return True
        
        return False

    def is_key_message_by_keywords(self, msg: Msg) -> bool:
        """基于关键词判断是否为关键消息。
        
        Args:
            msg (Msg): The message to check.
        
        Returns:
            bool: True if the message is key message, False otherwise.
        """
        # 安全地获取文本内容（msg.content 可能是字符串或列表）
        text_content = msg.get_text_content() or ""
        content = text_content.lower() if text_content else ""
        
        # 检查关键词
        for pattern_type, keywords in self.KEY_PATTERNS.items():
            if any(keyword in content for keyword in keywords):
                return True
        
        return False

    def is_key_message_by_role(self, msg: Msg) -> bool:
        """基于消息角色判断是否为关键消息。
        
        Args:
            msg (Msg): The message to check.
        
        Returns:
            bool: True if the message is key message, False otherwise.
        """
        # 系统消息通常是关键信息
        if msg.role == "system":
            return True
        
        # 特定名称的消息（如"moderator"）通常是关键信息
        if msg.name and "moderator" in msg.name.lower():
            return True
        
        return False

    def is_key_message(self, msg: Msg) -> bool:
        """综合判断是否为关键消息。
        
        Args:
            msg (Msg): The message to check.
        
        Returns:
            bool: True if the message is key message, False otherwise.
        """
        # 优先使用结构化输出判断（最准确）
        if self.is_key_message_by_metadata(msg):
            return True
        
        # 使用关键词匹配（补充）
        if self.is_key_message_by_keywords(msg):
            return True
        
        # 使用角色判断（补充）
        if self.is_key_message_by_role(msg):
            return True
        
        return False

    def estimate_tokens(self, messages: list[Msg]) -> int:
        """估算 Token 使用量。
        
        使用简单的字符数估算：
        - 中文：约 1.5 字符/token
        - 英文：约 4 字符/token
        
        Args:
            messages (list[Msg]): List of messages to estimate.
        
        Returns:
            int: Estimated token count.
        """
        total_tokens = 0
        
        for msg in messages:
            # 安全地获取消息文本内容（msg.content 可能是字符串或列表）
            text_content = msg.get_text_content() or ""
            
            # 计算中文字符数
            chinese_chars = len([c for c in text_content if '\u4e00' <= c <= '\u9fff'])
            english_chars = len(text_content) - chinese_chars
            
            # 估算 Token（中文约1.5字符/token，英文约4字符/token）
            chinese_tokens = chinese_chars / 1.5
            english_tokens = english_chars / 4
            
            # 每个消息还需要额外的格式开销（估算为50 tokens）
            total_tokens += int(chinese_tokens + english_tokens) + 50
        
        return total_tokens

    def should_compress(self, messages: list[Msg]) -> bool:
        """判断是否需要压缩。
        
        Args:
            messages (list[Msg]): List of messages to check.
        
        Returns:
            bool: True if compression is needed, False otherwise.
        """
        # 检查消息数量
        if len(messages) > self.max_messages_before_compress:
            return True
        
        # 检查 Token 使用量
        token_count = self.estimate_tokens(messages)
        if token_count >= self.token_compress_threshold:
            return True
        
        return False

    def select_compression_strategy(self, token_count: int) -> str:
        """选择压缩策略。
        
        Args:
            token_count (int): Current token count.
        
        Returns:
            str: Compression strategy ("none", "light", "medium", "heavy").
        """
        if token_count < self.token_warning_threshold:
            return "none"  # 不需要压缩
        elif token_count < self.token_compress_threshold:
            return "light"  # 轻度压缩
        elif token_count < self.token_max_threshold:
            return "medium"  # 中度压缩
        else:
            return "heavy"  # 重度压缩

    def compress_history(
        self,
        messages: list[Msg],
        max_tokens: int | None = None,
    ) -> list[Msg]:
        """压缩对话历史。
        
        Args:
            messages (list[Msg]): List of messages to compress.
            max_tokens (int, optional): Maximum token limit.
        
        Returns:
            list[Msg]: Compressed message list.
        """
        if not messages:
            return messages
        
        # 判断是否需要压缩
        if not self.should_compress(messages):
            return messages
        
        # 估算当前 Token 使用量
        token_count = self.estimate_tokens(messages)
        
        # 选择压缩策略
        strategy = self.select_compression_strategy(token_count)
        
        if strategy == "none":
            return messages
        
        logger.info(
            f"[ContextManager] 开始压缩对话历史: "
            f"原始消息数={len(messages)}, Token数≈{token_count}, 策略={strategy}",
        )
        
        # 执行压缩
        if strategy == "light":
            compressed = self._compress_light(messages)
        elif strategy == "medium":
            compressed = self._compress_medium(messages)
        else:  # heavy
            compressed = self._compress_heavy(messages)
        
        # 更新压缩历史
        self.compression_history["compression_count"] += 1
        self.compression_history["compressed_messages_count"] += len(messages) - len(compressed)
        
        # 验证压缩效果
        compressed_tokens = self.estimate_tokens(compressed)
        logger.info(
            f"[ContextManager] 压缩完成: "
            f"压缩后消息数={len(compressed)}, Token数≈{compressed_tokens}, "
            f"减少={(1 - len(compressed)/len(messages))*100:.1f}%",
        )
        
        return compressed

    def _compress_light(self, messages: list[Msg]) -> list[Msg]:
        """轻度压缩：过滤明显的冗余消息。
        
        Args:
            messages (list[Msg]): List of messages to compress.
        
        Returns:
            list[Msg]: Compressed message list.
        """
        compressed = []
        seen_content = set()
        
        for msg in messages:
            # 保留所有关键消息
            if self.is_key_message(msg):
                compressed.append(msg)
                continue
            
            # 过滤重复内容（安全获取文本内容）
            text_content = msg.get_text_content() or ""
            content_hash = hash(text_content[:100])  # 使用前100个字符的哈希
            
            if content_hash not in seen_content:
                seen_content.add(content_hash)
                compressed.append(msg)
            # 否则跳过重复消息
        
        return compressed

    def _compress_medium(self, messages: list[Msg]) -> list[Msg]:
        """中度压缩：压缩非关键消息序列。
        
        Args:
            messages (list[Msg]): List of messages to compress.
        
        Returns:
            list[Msg]: Compressed message list.
        """
        compressed = []
        non_key_buffer = []
        
        for msg in messages:
            if self.is_key_message(msg):
                # 如果缓冲区有非关键消息，先压缩它们
                if non_key_buffer:
                    compressed.extend(self._compress_non_key_sequence(non_key_buffer))
                    non_key_buffer = []
                
                # 添加关键消息
                compressed.append(msg)
            else:
                # 添加到缓冲区
                non_key_buffer.append(msg)
        
        # 处理最后的非关键消息
        if non_key_buffer:
            compressed.extend(self._compress_non_key_sequence(non_key_buffer))
        
        return compressed

    def _compress_heavy(self, messages: list[Msg]) -> list[Msg]:
        """重度压缩：只保留关键事件和最近 N 条消息。
        
        Args:
            messages (list[Msg]): List of messages to compress.
        
        Returns:
            list[Msg]: Compressed message list.
        """
        # 提取所有关键消息
        key_messages = [msg for msg in messages if self.is_key_message(msg)]
        
        # 保留最近20条消息
        recent_messages = messages[-20:] if len(messages) > 20 else messages
        
        # 合并关键消息和最近消息，去重
        compressed_dict = {}
        for msg in key_messages + recent_messages:
            # 使用消息ID作为唯一标识
            msg_id = getattr(msg, 'id', id(msg))
            if msg_id not in compressed_dict:
                compressed_dict[msg_id] = msg
        
        # 保持时间顺序
        compressed = []
        for msg in messages:
            msg_id = getattr(msg, 'id', id(msg))
            if msg_id in compressed_dict:
                compressed.append(msg)
                del compressed_dict[msg_id]
        
        return compressed

    def _compress_non_key_sequence(self, messages: list[Msg]) -> list[Msg]:
        """压缩非关键消息序列。
        
        Args:
            messages (list[Msg]): List of non-key messages to compress.
        
        Returns:
            list[Msg]: Compressed message list (保留部分，过滤部分).
        """
        if not messages:
            return []
        
        # 如果消息数量少于5条，保留所有
        if len(messages) <= 5:
            return messages
        
        # 保留第一条和最后一条，中间压缩为摘要
        compressed = [messages[0]]
        
        # 如果中间有多条消息，生成摘要
        if len(messages) > 2:
            summary = self._generate_summary(messages[1:-1])
            if summary:
                # 创建摘要消息
                summary_msg = Msg(
                    name="system",
                    role="system",
                    content=f"[摘要] {summary}",
                )
                compressed.append(summary_msg)
        
        compressed.append(messages[-1])
        
        return compressed

    def _generate_summary(self, messages: list[Msg]) -> str:
        """生成消息摘要。
        
        Args:
            messages (list[Msg]): List of messages to summarize.
        
        Returns:
            str: Summary text.
        """
        if not messages:
            return ""
        
        # 提取关键信息点
        participants = set()
        key_points = []
        
        for msg in messages:
            if msg.name:
                participants.add(msg.name)
            
            # 提取简短的关键词（安全获取文本内容）
            text_content = msg.get_text_content() or ""
            if text_content and len(text_content) > 0:
                # 取前50个字符作为要点
                key_points.append(text_content[:50])
        
        # 生成摘要
        participant_str = "、".join(list(participants)[:3])  # 最多3个参与者
        if len(participants) > 3:
            participant_str += "等"
        
        points_str = "；".join(key_points[:3])  # 最多3个要点
        if len(key_points) > 3:
            points_str += "等"
        
        return f"{participant_str}进行了讨论，主要内容：{points_str}"

    def get_relevant_context(
        self,
        messages: list[Msg],
        current_role: str | None = None,
        limit: int | None = None,
    ) -> list[Msg]:
        """获取相关上下文。
        
        Args:
            messages (list[Msg]): List of all messages.
            current_role (str, optional): Current role of the agent.
            limit (int, optional): Maximum number of messages to return.
        
        Returns:
            list[Msg]: Filtered relevant messages.
        """
        # 目前先返回所有关键消息 + 最近消息
        key_messages = [msg for msg in messages if self.is_key_message(msg)]
        recent_messages = messages[-20:] if len(messages) > 20 else messages
        
        # 合并并去重
        relevant = []
        seen_ids = set()
        
        for msg in key_messages + recent_messages:
            msg_id = getattr(msg, 'id', id(msg))
            if msg_id not in seen_ids:
                seen_ids.add(msg_id)
                relevant.append(msg)
        
        # 保持时间顺序
        relevant_sorted = []
        for msg in messages:
            msg_id = getattr(msg, 'id', id(msg))
            if msg_id in seen_ids and msg not in relevant_sorted:
                relevant_sorted.append(msg)
        
        if limit:
            relevant_sorted = relevant_sorted[-limit:]
        
        return relevant_sorted

    def extract_key_events(self, messages: list[Msg]) -> list[dict[str, Any]]:
        """提取关键事件。
        
        Args:
            messages (list[Msg]): List of messages to analyze.
        
        Returns:
            list[dict]: List of key events.
        """
        events = []
        
        for msg in messages:
            if not self.is_key_message(msg):
                continue
            
            # 安全获取文本内容
            text_content = msg.get_text_content() or ""
            event = {
                "type": self._classify_event_type(msg),
                "timestamp": getattr(msg, 'timestamp', None),
                "content": text_content[:100] if text_content else "",
                "metadata": msg.metadata,
                "importance": self._calculate_importance(msg),
            }
            
            events.append(event)
        
        return events

    def _classify_event_type(self, msg: Msg) -> str:
        """分类事件类型。
        
        Args:
            msg (Msg): The message to classify.
        
        Returns:
            str: Event type.
        """
        if msg.metadata:
            if "vote" in msg.metadata:
                return "VOTE"
            if "resurrect" in msg.metadata or "poison" in msg.metadata:
                return "SKILL_USE"
            if "shoot" in msg.metadata:
                return "SKILL_USE"
            if "reach_agreement" in msg.metadata:
                return "DECISION"
        
        # 安全获取文本内容（msg.content 可能是字符串或列表）
        text_content = msg.get_text_content() or ""
        content = text_content.lower() if text_content else ""
        if any(kw in content for kw in ["死亡", "died", "killed"]):
            return "DEATH"
        if any(kw in content for kw in ["是狼", "是好人", "身份"]):
            return "IDENTITY_REVEAL"
        
        return "OTHER"

    def _calculate_importance(self, msg: Msg) -> float:
        """计算消息重要性。
        
        Args:
            msg (Msg): The message to evaluate.
        
        Returns:
            float: Importance score (0.0-1.0).
        """
        event_type = self._classify_event_type(msg)
        
        if event_type == "VOTE":
            return self.IMPORTANCE_SCORES.get("vote", 1.0)
        elif event_type == "IDENTITY_REVEAL":
            return self.IMPORTANCE_SCORES.get("identity", 0.9)
        elif event_type == "DEATH":
            return self.IMPORTANCE_SCORES.get("death", 0.8)
        elif event_type == "SKILL_USE":
            return self.IMPORTANCE_SCORES.get("skill", 0.7)
        elif event_type == "DECISION":
            return self.IMPORTANCE_SCORES.get("decision", 0.6)
        else:
            return self.IMPORTANCE_SCORES.get("discussion", 0.3)

    def reset_game(self) -> None:
        """重置游戏状态（清空中期记忆）。
        
        在游戏开始时调用，清空当前游戏的中期记忆。
        """
        self.medium_term_memory = {
            "key_events": [],
            "summaries": [],
        }
        logger.info(f"[ContextManager] {self.agent_name} 重置游戏状态")

