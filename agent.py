# -*- coding: utf-8 -*-
# flake8: noqa: E501
"""PlayerAgent for werewolf game competition."""
import os
import json
from pathlib import Path
from typing import Any, Type

import yaml

from pydantic import BaseModel, ValidationError

from agentscope.agent import ReActAgent
from agentscope.memory import InMemoryMemory
from agentscope.message import Msg
from agentscope._logging import logger
from agentscope.model import DashScopeChatModel
from agentscope.formatter import DashScopeMultiAgentFormatter

from prompt import ChinesePrompts as Prompts
from modules.long_term_memory import GameLongTermMemory
from modules.context_manager import ContextManager
from modules.prompt_generator import PromptGenerator


class PlayerAgent(ReActAgent):
    """PlayerAgent for werewolf game competition.
    
    This agent is designed to participate in werewolf game competitions.
    It supports:
    - Long-term memory across multiple games
    - Context management for efficient token usage
    - Personalized prompts (via environment variable AGENT_CONFIG)
    - Structured output validation
    - State persistence
    """

    # 内置系统提示词
    _SYSTEM_PROMPT = Prompts.to_system

    def __init__(self, name: str):
        """Initialize PlayerAgent.

        Args:
            name (str): The name of the agent.
        """
        agent_config = None
        
        # 优先级1: 尝试从环境变量加载配置
        agent_config_str = os.environ.get("AGENT_CONFIG", "{}")
        if agent_config_str and agent_config_str != "{}":
            try:
                agent_config = json.loads(agent_config_str)
            except json.JSONDecodeError:
                logger.warning(
                    f"Failed to parse AGENT_CONFIG environment variable, "
                    f"trying to load from YAML file."
                )
        
        # 优先级2: 如果环境变量没有配置，尝试从YAML文件加载
        if agent_config is None:
            config_path = Path(__file__).parent / "config" / "agent_config.yaml"
            if config_path.exists():
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        yaml_data = yaml.safe_load(f)
                    
                    # 解析YAML结构：agent -> list -> 第一个元素
                    if isinstance(yaml_data, dict) and "agent" in yaml_data:
                        agents = yaml_data["agent"]
                        if isinstance(agents, list) and len(agents) > 0:
                            agent_config = agents[0]
                        elif isinstance(agents, dict):
                            # 如果agent直接是字典而不是列表
                            agent_config = agents
                except (yaml.YAMLError, KeyError, IndexError, Exception) as e:
                    logger.warning(
                        f"Failed to load config from {config_path}: {e}, "
                        f"using default prompt."
                    )
            else:
                # 文件不存在，静默跳过，使用默认提示词
                pass
        
        # 构建系统提示词
        if agent_config:
            # 使用个性化提示词生成器
            prompt_generator = PromptGenerator()
            sys_prompt = prompt_generator.generate(agent_config, name)
        else:
            # 使用默认提示词
            sys_prompt = PlayerAgent._SYSTEM_PROMPT.format(name=name)

        # 强制使用 DashScope 和 qwen3-max（比赛要求）
        model = DashScopeChatModel(
            api_key = os.environ.get("DASHSCOPE_API_KEY"),
            model_name="qwen3-max",
        )
        formatter = DashScopeMultiAgentFormatter()

        # 创建长期记忆系统
        long_term_memory = GameLongTermMemory(agent_name=name)
        
        # 调用父类构造函数（这会初始化 StateModule）
        super().__init__(
            name=name,
            sys_prompt=sys_prompt,
            model=model,
            formatter=formatter,
            memory=InMemoryMemory(),
            long_term_memory=long_term_memory,
        )

        # 创建上下文管理器
        # 注意：ContextManager 继承自 StateModule，会自动被识别为模块并支持持久化
        self.context_manager = ContextManager(agent_name=name)
        
        # 状态管理说明：
        # - name, _sys_prompt: 已在 ReActAgent 中注册
        # - long_term_memory: 已在 ReActAgent 中注册
        # - context_manager: 自动通过 StateModule 机制处理（无需手动注册）
        # 继承 ReActAgent 后自动支持 state_dict() 和 load_state_dict()

    async def observe(self, msg: Msg | list[Msg] | None) -> None:
        """Receive observing message(s) without generating a reply.

        This method is required by the competition rules. It receives
        game messages (like role assignment, game events) and stores
        them in memory for later reference.

        Args:
            msg (Msg | list[Msg] | None): The message(s) to be observed.
        """
        await super().observe(msg)

    async def __call__(
        self, 
        msg: Msg | list[Msg] | None = None, 
        **kwargs: Any
    ) -> Msg:
        """Call the agent to generate a reply with structured output validation.

        This method is required by the competition rules. It generates
        a response based on the input message(s) and returns a valid
        Msg object. Additionally, it validates structured output if requested.
        
        Before generating the response, this method compresses the conversation
        history using the context manager to ensure efficient token usage.

        Args:
            msg (Msg | list[Msg] | None, optional): The input message(s). 
                Defaults to None.
            **kwargs: Keyword arguments (e.g., structured_model).

        Returns:
            Msg: A valid message object containing the agent's response.
        """
        # 获取当前对话历史（不包括即将添加的输入消息）
        current_messages = await self.memory.get_memory()
        
        try:
            # 获取当前对话历史（不包括即将添加的输入消息）
            current_messages = await self.memory.get_memory()
            
            # 使用上下文管理器压缩对话历史（如果消息数量较多）
            if current_messages and len(current_messages) > 10:
                # 判断是否需要压缩
                if self.context_manager.should_compress(current_messages):
                    compressed_messages = self.context_manager.compress_history(current_messages)
                    
                    # 如果压缩后消息数量减少，临时替换记忆内容
                    if len(compressed_messages) < len(current_messages):
                        # 保存原始记忆内容
                        original_messages = current_messages.copy()
                        
                        # 临时替换为压缩后的消息
                        await self.memory.clear()
                        await self.memory.add(compressed_messages, allow_duplicates=True)
                        
                        # 调用父类方法（输入消息会被添加到压缩后的 memory）
                        # 如果 msg 不为 None，将其作为位置参数传递；否则不传位置参数
                        try:
                            if msg is not None:
                                response_msg = await super().__call__(msg, **kwargs)
                            else:
                                response_msg = await super().__call__(**kwargs)
                        finally:
                            # 恢复原始记忆内容
                            await self.memory.clear()
                            await self.memory.add(original_messages, allow_duplicates=True)
                            # 注意：输入消息会通过 observe 重新添加，所以不需要手动添加
                    else:
                        # 压缩效果不明显，直接调用父类方法
                        if msg is not None:
                            response_msg = await super().__call__(msg, **kwargs)
                        else:
                            response_msg = await super().__call__(**kwargs)
                else:
                    # 不需要压缩，直接调用父类方法
                    if msg is not None:
                        response_msg = await super().__call__(msg, **kwargs)
                    else:
                        response_msg = await super().__call__(**kwargs)
            else:
                # 消息数量较少，不需要压缩，直接调用父类方法
                if msg is not None:
                    response_msg = await super().__call__(msg, **kwargs)
                else:
                    response_msg = await super().__call__(**kwargs)

            # 如果请求了结构化输出，验证输出
            structured_model = kwargs.get("structured_model")
            if structured_model is not None:
                response_msg = self._validate_structured_output(
                    response_msg,
                    structured_model,
                )

            # 检查响应长度（2048字符限制）
            response_msg = self._check_response_length(response_msg)

            return response_msg
            
        except Exception as e:
            # 捕获所有异常，返回默认输出以确保游戏继续
            logger.error(
                f"{self.name}: Error in __call__: {e}, "
                f"returning default response.",
                exc_info=True,
            )
            
            # 创建默认响应消息
            from agentscope.message import Msg
            
            # 获取输入消息的内容（如果有）
            input_content = ""
            if msg is not None:
                if isinstance(msg, list):
                    input_content = " ".join([m.content for m in msg if hasattr(m, 'content')])
                elif hasattr(msg, 'content'):
                    input_content = msg.content
            
            # 创建默认响应
            default_content = f"抱歉，我暂时无法生成回复。{input_content[:50]}..."
            if not input_content:
                default_content = "我理解了，但我暂时无法生成详细回复。"
            
            default_msg = Msg(
                name=self.name,
                content=default_content,
                role="assistant",
            )
            
            # 如果请求了结构化输出，添加默认 metadata
            structured_model = kwargs.get("structured_model")
            if structured_model is not None:
                default_msg.metadata = self._get_fallback_metadata(structured_model)
            
            return default_msg

    def _check_response_length(self, msg: Msg) -> Msg:
        """Check and truncate response content if it exceeds the limit.
        
        Args:
            msg (Msg): The response message to check.
        
        Returns:
            Msg: The message with truncated content if necessary.
        """
        MAX_RESPONSE_LENGTH = 2048
        
        if not msg.content:
            return msg
        
        content = msg.content
        if len(content) <= MAX_RESPONSE_LENGTH:
            return msg
        
        # 响应过长，需要截断
        logger.warning(
            f"{self.name}: Response content length ({len(content)}) "
            f"exceeds limit ({MAX_RESPONSE_LENGTH}), truncating.",
        )
        
        # 保留前面部分，添加截断标记
        truncated = content[:MAX_RESPONSE_LENGTH - 20]
        truncated += "\n...[响应过长，已截断]"
        
        # 创建新的消息对象，保留其他属性
        from copy import deepcopy
        truncated_msg = deepcopy(msg)
        truncated_msg.content = truncated
        
        return truncated_msg

    def state_dict(self) -> dict:
        """Get the state dictionary for persistence.

        This method is required by the competition rules. It returns
        a dictionary containing all states that need to be persisted
        across game sessions.

        Returns:
            dict: A dictionary containing the agent's state, including:
                - name: The agent's name
                - _sys_prompt: The system prompt
                - Other registered states (if any)
        """
        # 调用父类方法，自动收集所有注册的状态
        return super().state_dict()

    def load_state_dict(self, state_dict: dict, strict: bool = False) -> None:
        """Load the state dictionary from persistence.

        This method is required by the competition rules. It loads
        the persisted state dictionary back into the agent, allowing
        the agent to continue from a previous game session.

        Args:
            state_dict (dict): The state dictionary to load.
            strict (bool, defaults to False): If True, raises an error
                if any registered key is missing in state_dict. If False,
                skips missing keys to allow backward compatibility with
                older state dictionaries.
        """
        # 调用父类方法，自动加载所有注册的状态
        # 使用 strict=False 允许向后兼容，即使状态字典缺少某些键也能正常加载
        super().load_state_dict(state_dict, strict=strict)

    def _validate_structured_output(
        self,
        msg: Msg,
        structured_model: Type[BaseModel],
    ) -> Msg:
        """Validate structured output in message metadata.

        This method validates that the structured output in the message
        metadata conforms to the expected model schema. If validation
        fails, it applies a fallback metadata to ensure the game continues.

        Args:
            msg: The message from the agent.
            structured_model: The expected structured output model.

        Returns:
            The message with validated/fallback metadata.
        """
        # 检查 metadata 是否存在
        if not msg.metadata:
            logger.warning(
                f"{self.name}: Missing metadata in structured output, "
                f"using fallback metadata.",
            )
            msg.metadata = self._get_fallback_metadata(structured_model)
            return msg

        # 验证结构化输出
        try:
            # 尝试使用模型验证
            if isinstance(msg.metadata, dict):
                validated_data = structured_model.model_validate(msg.metadata)
                msg.metadata = validated_data.model_dump()
            else:
                # 如果不是字典，尝试创建新的 metadata
                logger.warning(
                    f"{self.name}: Metadata is not a dict, using fallback.",
                )
                msg.metadata = self._get_fallback_metadata(structured_model)
            return msg
        except ValidationError as e:
            logger.warning(
                f"{self.name}: Structured output validation failed: {e}, "
                f"using fallback metadata.",
            )
            msg.metadata = self._get_fallback_metadata(structured_model)
            return msg
        except Exception as e:
            logger.warning(
                f"{self.name}: Unexpected error during validation: {e}, "
                f"using fallback metadata.",
            )
            msg.metadata = self._get_fallback_metadata(structured_model)
            return msg

    def _get_fallback_metadata(
        self,
        structured_model: Type[BaseModel],
    ) -> dict:
        """Get fallback metadata when structured output fails.

        This method provides safe default values for different types of
        structured output models to ensure the game can continue even
        when the model fails to generate valid structured output.

        Args:
            structured_model: The structured output model type.

        Returns:
            A dictionary with safe default values.
        """
        # 根据模型类型返回不同的默认值
        model_name = structured_model.__name__

        if "Vote" in model_name:
            # 投票模型：返回 None（允许弃权，避免误投）
            return {"vote": None}
        elif "Discussion" in model_name:
            # 讨论模型：返回 False（未达成一致，保守策略）
            return {"reach_agreement": False}
        elif "Resurrect" in model_name:
            # 复活模型：返回 False（不复活，保守策略，保留解药）
            return {"resurrect": False}
        elif "Poison" in model_name:
            # 毒药模型：返回不使用（保守策略，保留毒药）
            return {"poison": False, "name": None}
        elif "Seer" in model_name:
            # 预言家模型：返回 None（允许不查验）
            return {"name": None}
        elif "Hunter" in model_name:
            # 猎人模型：返回不开枪（保守策略）
            return {"shoot": False, "name": None}
        else:
            # 未知模型：尝试获取模型字段的默认值
            logger.warning(f"Unknown structured model: {model_name}")
            try:
                # 尝试创建模型实例获取默认值
                instance = structured_model()
                return instance.model_dump()
            except Exception:
                # 如果创建失败，返回空字典
                return {}
