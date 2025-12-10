# -*- coding: utf-8 -*-
"""Utils package for werewolf game."""

# 导入配置加载器
from .config_loader import (
    load_agents_config,
    validate_agent_config,
    get_agent_config_by_name,
    get_all_agent_names,
    load_config,
)

# 导入统计工具
from .stats import (
    GameStats,
    AgentStats,
    StatsCollector,
)

# 导入游戏工具函数和类（从父目录的utils.py）
# 由于utils现在是包，需要从父目录导入utils.py的内容
# 使用importlib动态导入以避免循环导入
import sys
import importlib.util
from pathlib import Path

# 获取父目录路径（werewolves目录）
_parent_dir = Path(__file__).parent.parent
_utils_py_path = _parent_dir / "utils.py"

if _utils_py_path.exists():
    # 动态加载utils.py模块
    # 使用绝对路径避免路径问题
    spec = importlib.util.spec_from_file_location(
        "_original_utils", 
        str(_utils_py_path)
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Failed to load utils.py from {_utils_py_path}")
    
    _original_utils = importlib.util.module_from_spec(spec)
    
    # 临时修改sys.path以支持utils.py中的导入
    _parent_str = str(_parent_dir)
    _path_inserted = _parent_str not in sys.path
    if _path_inserted:
        sys.path.insert(0, _parent_str)
    
    try:
        spec.loader.exec_module(_original_utils)
    finally:
        # 恢复sys.path
        if _path_inserted:
            sys.path.remove(_parent_str)
    
    # 重新导出所有内容
    majority_vote = _original_utils.majority_vote
    names_to_str = _original_utils.names_to_str
    EchoAgent = _original_utils.EchoAgent
    Players = _original_utils.Players
    MAX_GAME_ROUND = _original_utils.MAX_GAME_ROUND
    MAX_DISCUSSION_ROUND = _original_utils.MAX_DISCUSSION_ROUND
else:
    raise ImportError(
        f"Cannot find utils.py at {_utils_py_path}. "
        "This file is required for the game to work."
    )

__all__ = [
    # 配置加载器
    "load_agents_config",
    "validate_agent_config",
    "get_agent_config_by_name",
    "get_all_agent_names",
    "load_config",
    # 统计工具
    "GameStats",
    "AgentStats",
    "StatsCollector",
    # 游戏工具
    "majority_vote",
    "names_to_str",
    "EchoAgent",
    "Players",
    "MAX_GAME_ROUND",
    "MAX_DISCUSSION_ROUND",
]

