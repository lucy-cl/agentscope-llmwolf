# -*- coding: utf-8 -*-
"""配置加载工具 - 读取和验证Agent配置文件"""
import os
import yaml
from typing import Dict, Any, List
from pathlib import Path


def load_agents_config(config_path: str | None = None) -> List[Dict[str, Any]]:
    """加载Agent配置文件
    
    Args:
        config_path (str | None, optional): 配置文件路径。如果为None，则使用默认路径。
            默认路径为：config/agents_config.yaml
    
    Returns:
        List[Dict[str, Any]]: Agent配置列表，每个元素包含一个Agent的完整配置
    
    Raises:
        FileNotFoundError: 如果配置文件不存在
        ValueError: 如果配置文件格式不正确
    """
    # 确定配置文件路径
    if config_path is None:
        # 获取当前文件所在目录的父目录（werewolves目录）
        current_dir = Path(__file__).parent.parent
        config_path = current_dir / "config" / "agents_config.yaml"
    else:
        config_path = Path(config_path)
    
    # 检查文件是否存在
    if not config_path.exists():
        raise FileNotFoundError(
            f"配置文件不存在: {config_path}. "
            f"请确保配置文件存在或提供正确的路径。"
        )
    
    # 读取YAML文件
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ValueError(f"配置文件格式错误: {e}")
    except Exception as e:
        raise ValueError(f"读取配置文件时出错: {e}")
    
    # 验证配置结构
    if not isinstance(config_data, dict):
        raise ValueError("配置文件根节点必须是字典类型")
    
    if "agents" not in config_data:
        raise ValueError("配置文件中缺少 'agents' 键")
    
    agents = config_data["agents"]
    if not isinstance(agents, list):
        raise ValueError("'agents' 必须是列表类型")
    
    if len(agents) == 0:
        raise ValueError("配置文件中至少需要包含一个Agent配置")
    
    # 验证每个Agent配置
    validated_agents = []
    for idx, agent_config in enumerate(agents):
        try:
            validated_config = validate_agent_config(agent_config, idx)
            validated_agents.append(validated_config)
        except ValueError as e:
            raise ValueError(f"Agent配置验证失败（索引 {idx}）: {e}")
    
    return validated_agents


def validate_agent_config(agent_config: Dict[str, Any], index: int = 0) -> Dict[str, Any]:
    """验证单个Agent配置
    
    Args:
        agent_config: Agent配置字典
        index: Agent在列表中的索引（用于错误提示）
    
    Returns:
        Dict[str, Any]: 验证后的配置字典
    
    Raises:
        ValueError: 如果配置验证失败
    """
    if not isinstance(agent_config, dict):
        raise ValueError(f"Agent配置必须是字典类型，但得到 {type(agent_config)}")
    
    # 必需字段：name
    if "name" not in agent_config:
        raise ValueError(f"Agent配置缺少必需字段 'name'")
    
    name = agent_config["name"]
    if not isinstance(name, str) or not name.strip():
        raise ValueError(f"Agent 'name' 必须是非空字符串")
    
    # 可选字段：description
    if "description" in agent_config:
        if not isinstance(agent_config["description"], str):
            raise ValueError(f"Agent 'description' 必须是字符串类型")
    
    # 验证 personality（可选）
    if "personality" in agent_config:
        personality = agent_config["personality"]
        if not isinstance(personality, dict):
            raise ValueError(f"Agent 'personality' 必须是字典类型")
        
        # 验证personality字段（都是可选的）
        personality_fields = [
            "aggression", "trust_level", "logic_focus", 
            "deception_skill", "speech_style", "risk_tolerance"
        ]
        for field in personality_fields:
            if field in personality:
                value = personality[field]
                if field == "speech_style":
                    if not isinstance(value, str):
                        raise ValueError(f"personality.{field} 必须是字符串类型")
                else:
                    if not isinstance(value, (int, float)):
                        raise ValueError(f"personality.{field} 必须是数字类型")
                    # 对于数值字段，检查范围（1-10）
                    if field != "speech_style" and (value < 1 or value > 10):
                        raise ValueError(
                            f"personality.{field} 必须在 1-10 范围内，但得到 {value}"
                        )
    
    # 验证 strategy（可选）
    if "strategy" in agent_config:
        strategy = agent_config["strategy"]
        if not isinstance(strategy, dict):
            raise ValueError(f"Agent 'strategy' 必须是字典类型")
        
        # 验证strategy字段（都是可选的）
        strategy_fields = [
            "voting_basis", "speak_timing", "suspicion_threshold",
            "alliance_tendency", "special_habits"
        ]
        for field in strategy_fields:
            if field in strategy:
                value = strategy[field]
                if field == "suspicion_threshold":
                    if not isinstance(value, (int, float)):
                        raise ValueError(f"strategy.{field} 必须是数字类型")
                    if value < 0 or value > 1:
                        raise ValueError(
                            f"strategy.{field} 必须在 0-1 范围内，但得到 {value}"
                        )
                else:
                    if not isinstance(value, str):
                        raise ValueError(f"strategy.{field} 必须是字符串类型")
    
    # 验证 role_strategies（可选）
    if "role_strategies" in agent_config:
        role_strategies = agent_config["role_strategies"]
        if not isinstance(role_strategies, dict):
            raise ValueError(f"Agent 'role_strategies' 必须是字典类型")
        
        # 验证每个角色的策略（都是可选的）
        valid_roles = ["werewolf", "seer", "witch", "hunter", "villager"]
        for role, role_strategy in role_strategies.items():
            if role not in valid_roles:
                raise ValueError(
                    f"无效的角色名称 '{role}'，有效角色为: {valid_roles}"
                )
            if not isinstance(role_strategy, dict):
                raise ValueError(f"role_strategies.{role} 必须是字典类型")
    
    return agent_config


def get_agent_config_by_name(
    agents_config: List[Dict[str, Any]], 
    name: str
) -> Dict[str, Any] | None:
    """根据名称获取Agent配置
    
    Args:
        agents_config: Agent配置列表
        name: Agent名称
    
    Returns:
        Dict[str, Any] | None: 找到的配置，如果不存在则返回None
    """
    for agent_config in agents_config:
        if agent_config.get("name") == name:
            return agent_config
    return None


def get_all_agent_names(agents_config: List[Dict[str, Any]]) -> List[str]:
    """获取所有Agent的名称列表
    
    Args:
        agents_config: Agent配置列表
    
    Returns:
        List[str]: Agent名称列表
    """
    return [agent_config.get("name", "") for agent_config in agents_config]


# 便捷函数：直接加载并返回配置
def load_config() -> List[Dict[str, Any]]:
    """便捷函数：加载默认配置文件
    
    Returns:
        List[Dict[str, Any]]: Agent配置列表
    """
    return load_agents_config()

