# -*- coding: utf-8 -*-
# flake8: noqa: E501
"""Long-term memory system for werewolf game."""
from typing import Any

from agentscope.memory import LongTermMemoryBase
from agentscope.message import Msg
from agentscope._logging import logger


class GameLongTermMemory(LongTermMemoryBase):
    """长期记忆系统，存储多局游戏的经验。
    
    该类存储对手画像、策略经验和角色经验，支持在多局游戏之间
    保持连续的学习和改进。
    """

    def __init__(self, agent_name: str):
        """Initialize the long-term memory system.
        
        Args:
            agent_name (str): The name of the agent.
        """
        super().__init__()
        self.agent_name = agent_name
        
        # 对手画像：记录每个对手的行为模式
        self.opponent_profiles: dict[str, dict[str, Any]] = {}
        
        # 策略日志：记录每局游戏的策略和经验
        self.strategy_log: list[dict[str, Any]] = []
        
        # 角色经验：按角色统计胜率和策略
        self.role_experience: dict[str, dict[str, Any]] = {
            "werewolf": {
                "win_rate": 0.0,
                "total_games": 0,
                "win_games": 0,
                "strategies": [],
                "common_mistakes": [],
            },
            "villager": {
                "win_rate": 0.0,
                "total_games": 0,
                "win_games": 0,
                "strategies": [],
                "common_mistakes": [],
            },
            "seer": {
                "win_rate": 0.0,
                "total_games": 0,
                "win_games": 0,
                "strategies": [],
                "common_mistakes": [],
            },
            "witch": {
                "win_rate": 0.0,
                "total_games": 0,
                "win_games": 0,
                "strategies": [],
                "common_mistakes": [],
            },
            "hunter": {
                "win_rate": 0.0,
                "total_games": 0,
                "win_games": 0,
                "strategies": [],
                "common_mistakes": [],
            },
        }
        
        # 游戏统计
        self.game_statistics: dict[str, Any] = {
            "total_games": 0,
            "total_wins": 0,
            "overall_win_rate": 0.0,
        }
        
        # 注册需要持久化的状态
        self.register_state("agent_name")
        self.register_state("opponent_profiles")
        self.register_state("strategy_log")
        self.register_state("role_experience")
        self.register_state("game_statistics")

    async def record(
        self,
        msgs: list[Msg | None],
        **kwargs: Any,
    ) -> None:
        """Record game experience to long-term memory.
        
        This method extracts key information from messages and updates
        opponent profiles, strategy logs, and role experience.
        
        Args:
            msgs: List of messages containing game information.
            **kwargs: Additional keyword arguments.
                - game_id: Optional game identifier
                - role: Optional role played in this game
                - result: Optional game result ("win" or "lose")
                - opponents: Optional list of opponent names
        """
        if not msgs:
            return
        
        # 从kwargs中获取游戏信息
        game_id = kwargs.get("game_id", f"game_{self.game_statistics['total_games']}")
        role = kwargs.get("role")
        result = kwargs.get("result")  # "win" or "lose"
        opponents = kwargs.get("opponents", [])
        
        # 更新对手画像
        if opponents:
            self._update_opponent_profiles(opponents, role, result, game_id)
        
        # 记录策略经验
        if role and result:
            self._record_strategy_experience(game_id, role, result, kwargs)
        
        # 更新角色经验
        if role and result:
            self._update_role_experience(role, result, kwargs)
        
        # 更新游戏统计
        if result:
            self._update_game_statistics(result)

    async def retrieve(
        self,
        msg: Msg | list[Msg] | None,
        limit: int = 5,
        **kwargs: Any,
    ) -> str:
        """Retrieve relevant memories based on the current game state.
        
        Args:
            msg: Message(s) containing query information.
            limit: Maximum number of memories to retrieve.
            **kwargs: Additional keyword arguments.
                - opponent_name: Optional opponent name to retrieve profile
                - role: Optional role to retrieve experience
                - query_type: Optional query type ("opponent", "role", "strategy")
        
        Returns:
            Formatted string containing relevant memories.
        """
        query_type = kwargs.get("query_type", "general")
        opponent_name = kwargs.get("opponent_name")
        role = kwargs.get("role")
        
        memories = []
        
        # 基于查询类型检索记忆
        if query_type == "opponent" and opponent_name:
            # 检索对手画像
            profile = self._get_opponent_profile(opponent_name)
            if profile:
                memories.append(f"对手 {opponent_name} 的画像：{self._format_opponent_profile(profile)}")
        
        elif query_type == "role" and role:
            # 检索角色经验
            experience = self.role_experience.get(role, {})
            if experience:
                memories.append(f"角色 {role} 的经验：{self._format_role_experience(experience)}")
        
        elif query_type == "strategy":
            # 检索策略经验
            strategies = self._get_relevant_strategies(role, limit)
            if strategies:
                memories.append(f"相关策略：{self._format_strategies(strategies)}")
        
        else:
            # 通用检索：返回所有相关信息
            if opponent_name:
                profile = self._get_opponent_profile(opponent_name)
                if profile:
                    memories.append(f"对手 {opponent_name}：{self._format_opponent_profile(profile)}")
            
            if role:
                experience = self.role_experience.get(role, {})
                if experience:
                    memories.append(f"角色 {role} 经验：{self._format_role_experience(experience)}")
            
            # 添加游戏统计
            if self.game_statistics["total_games"] > 0:
                memories.append(f"游戏统计：总游戏数 {self.game_statistics['total_games']}，"
                              f"总胜利数 {self.game_statistics['total_wins']}，"
                              f"总体胜率 {self.game_statistics['overall_win_rate']:.2%}")
        
        # 限制返回的记忆数量
        memories = memories[:limit]
        
        if not memories:
            return "暂无相关记忆。"
        
        return "\n".join(memories)

    def _update_opponent_profiles(
        self,
        opponents: list[str],
        role: str | None,
        result: str | None,
        game_id: str,
    ) -> None:
        """Update opponent profiles based on game information.
        
        Args:
            opponents: List of opponent names.
            role: Current role.
            result: Game result.
            game_id: Game identifier.
        """
        for opponent in opponents:
            if opponent == self.agent_name:
                continue
            
            if opponent not in self.opponent_profiles:
                # 初始化对手画像
                self.opponent_profiles[opponent] = {
                    "voting_patterns": [],
                    "speech_style": "",
                    "suspicious_level": 0.0,
                    "game_count": 0,
                    "win_rate_against": 0.0,
                    "role_tendencies": {
                        "werewolf": 0.0,
                        "villager": 0.0,
                        "seer": 0.0,
                        "witch": 0.0,
                        "hunter": 0.0,
                    },
                    "behavior_patterns": [],
                }
            
            profile = self.opponent_profiles[opponent]
            
            # 更新游戏次数
            profile["game_count"] += 1
            
            # 更新角色倾向（如果知道对手角色）
            # 注意：在实际游戏中，可能不知道对手的真实角色
            # 这里只是示例，实际实现需要根据游戏信息推断

    def _record_strategy_experience(
        self,
        game_id: str,
        role: str,
        result: str,
        kwargs: dict[str, Any],
    ) -> None:
        """Record strategy experience for a game.
        
        Args:
            game_id: Game identifier.
            role: Role played.
            result: Game result.
            kwargs: Additional game information.
        """
        strategy_entry = {
            "game_id": game_id,
            "role": role,
            "strategy": kwargs.get("strategy", ""),
            "result": result,
            "key_decisions": kwargs.get("key_decisions", []),
            "opponents": kwargs.get("opponents", []),
            "win": result == "win",
        }
        
        self.strategy_log.append(strategy_entry)
        
        # 限制策略日志长度（只保留最近100局）
        if len(self.strategy_log) > 100:
            self.strategy_log = self.strategy_log[-100:]

    def _update_role_experience(
        self,
        role: str,
        result: str,
        kwargs: dict[str, Any],
    ) -> None:
        """Update role experience statistics.
        
        Args:
            role: Role played.
            result: Game result.
            kwargs: Additional game information.
        """
        if role not in self.role_experience:
            return
        
        experience = self.role_experience[role]
        
        # 更新游戏统计
        experience["total_games"] += 1
        if result == "win":
            experience["win_games"] += 1
        
        # 更新胜率
        if experience["total_games"] > 0:
            experience["win_rate"] = experience["win_games"] / experience["total_games"]
        
        # 记录策略（如果有效）
        strategy = kwargs.get("strategy")
        if strategy and result == "win":
            if strategy not in experience["strategies"]:
                experience["strategies"].append(strategy)
                # 限制策略数量
                if len(experience["strategies"]) > 20:
                    experience["strategies"] = experience["strategies"][-20:]

    def _update_game_statistics(self, result: str) -> None:
        """Update overall game statistics.
        
        Args:
            result: Game result.
        """
        self.game_statistics["total_games"] += 1
        if result == "win":
            self.game_statistics["total_wins"] += 1
        
        # 更新总体胜率
        if self.game_statistics["total_games"] > 0:
            self.game_statistics["overall_win_rate"] = (
                self.game_statistics["total_wins"] / self.game_statistics["total_games"]
            )

    def _get_opponent_profile(self, opponent_name: str) -> dict[str, Any] | None:
        """Get opponent profile by name.
        
        Args:
            opponent_name: Name of the opponent.
        
        Returns:
            Opponent profile dictionary or None if not found.
        """
        return self.opponent_profiles.get(opponent_name)

    def _format_opponent_profile(self, profile: dict[str, Any]) -> str:
        """Format opponent profile as a string.
        
        Args:
            profile: Opponent profile dictionary.
        
        Returns:
            Formatted string.
        """
        parts = []
        parts.append(f"一起游戏 {profile['game_count']} 次")
        
        if profile["suspicious_level"] > 0:
            parts.append(f"可疑度 {profile['suspicious_level']:.2f}")
        
        if profile["win_rate_against"] > 0:
            parts.append(f"对此玩家的胜率 {profile['win_rate_against']:.2%}")
        
        if profile["voting_patterns"]:
            parts.append(f"投票模式：{len(profile['voting_patterns'])} 条记录")
        
        return "；".join(parts) if parts else "暂无详细信息"

    def _format_role_experience(self, experience: dict[str, Any]) -> str:
        """Format role experience as a string.
        
        Args:
            experience: Role experience dictionary.
        
        Returns:
            Formatted string.
        """
        parts = []
        parts.append(f"总游戏数 {experience['total_games']}")
        parts.append(f"胜利数 {experience['win_games']}")
        parts.append(f"胜率 {experience['win_rate']:.2%}")
        
        if experience["strategies"]:
            parts.append(f"有效策略：{', '.join(experience['strategies'][:3])}")
            if len(experience["strategies"]) > 3:
                parts[-1] += f" 等 {len(experience['strategies'])} 种"
        
        return "；".join(parts)

    def _get_relevant_strategies(
        self,
        role: str | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Get relevant strategies based on role.
        
        Args:
            role: Optional role to filter strategies.
            limit: Maximum number of strategies to return.
        
        Returns:
            List of strategy dictionaries.
        """
        strategies = self.strategy_log.copy()
        
        # 如果指定了角色，过滤相关策略
        if role:
            strategies = [s for s in strategies if s.get("role") == role]
        
        # 优先返回胜利的策略
        strategies.sort(key=lambda x: (x.get("win", False), x.get("game_id", "")), reverse=True)
        
        return strategies[:limit]

    def _format_strategies(self, strategies: list[dict[str, Any]]) -> str:
        """Format strategies as a string.
        
        Args:
            strategies: List of strategy dictionaries.
        
        Returns:
            Formatted string.
        """
        if not strategies:
            return "暂无策略记录"
        
        parts = []
        for strategy in strategies:
            role = strategy.get("role", "未知")
            result = "胜利" if strategy.get("win", False) else "失败"
            strategy_desc = strategy.get("strategy", "无描述")
            parts.append(f"{role}角色，{result}：{strategy_desc}")
        
        return "；".join(parts[:3])  # 最多显示3条

