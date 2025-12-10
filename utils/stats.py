# -*- coding: utf-8 -*-
"""统计工具模块 - 记录和分析游戏结果"""
import json
from typing import Dict, Any, List, Optional
from pathlib import Path
from collections import defaultdict
from datetime import datetime


class GameStats:
    """单局游戏统计"""
    
    def __init__(self, game_id: int):
        """初始化游戏统计
        
        Args:
            game_id: 游戏ID
        """
        self.game_id = game_id
        self.agents: Dict[str, Dict[str, Any]] = {}  # agent_name -> {role, won, ...}
        self.winner: str | None = None  # "werewolf" or "villager"
        self.rounds: int = 0
        self.timestamp: str = datetime.now().isoformat()
    
    def add_agent_result(
        self, 
        agent_name: str, 
        role: str, 
        won: bool,
        survived_rounds: int = 0
    ) -> None:
        """添加Agent的游戏结果
        
        Args:
            agent_name: Agent名称
            role: 角色（werewolf, villager, seer, witch, hunter）
            won: 是否获胜
            survived_rounds: 存活轮数
        """
        self.agents[agent_name] = {
            "role": role,
            "won": won,
            "survived_rounds": survived_rounds,
        }
    
    def set_winner(self, winner: str) -> None:
        """设置获胜方
        
        Args:
            winner: "werewolf" 或 "villager"
        """
        self.winner = winner
    
    def set_rounds(self, rounds: int) -> None:
        """设置游戏轮数
        
        Args:
            rounds: 游戏轮数
        """
        self.rounds = rounds
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "game_id": self.game_id,
            "winner": self.winner,
            "rounds": self.rounds,
            "timestamp": self.timestamp,
            "agents": self.agents,
        }


class AgentStats:
    """Agent累计统计"""
    
    def __init__(self, agent_name: str):
        """初始化Agent统计
        
        Args:
            agent_name: Agent名称
        """
        self.agent_name = agent_name
        self.total_games = 0
        self.total_wins = 0
        self.role_stats: Dict[str, Dict[str, int]] = defaultdict(
            lambda: {"games": 0, "wins": 0}
        )  # role -> {games, wins}
        self.total_rounds_survived = 0
        self.avg_survival_rounds = 0.0
    
    def add_game_result(
        self, 
        role: str, 
        won: bool, 
        survived_rounds: int = 0
    ) -> None:
        """添加游戏结果
        
        Args:
            role: 角色
            won: 是否获胜
            survived_rounds: 存活轮数
        """
        self.total_games += 1
        if won:
            self.total_wins += 1
        
        self.role_stats[role]["games"] += 1
        if won:
            self.role_stats[role]["wins"] += 1
        
        self.total_rounds_survived += survived_rounds
        self.avg_survival_rounds = (
            self.total_rounds_survived / self.total_games 
            if self.total_games > 0 else 0.0
        )
    
    def get_win_rate(self) -> float:
        """获取总体胜率"""
        return self.total_wins / self.total_games if self.total_games > 0 else 0.0
    
    def get_role_win_rate(self, role: str) -> float:
        """获取特定角色的胜率
        
        Args:
            role: 角色名称
        
        Returns:
            胜率（0-1之间）
        """
        stats = self.role_stats.get(role, {"games": 0, "wins": 0})
        return stats["wins"] / stats["games"] if stats["games"] > 0 else 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "agent_name": self.agent_name,
            "total_games": self.total_games,
            "total_wins": self.total_wins,
            "win_rate": self.get_win_rate(),
            "avg_survival_rounds": self.avg_survival_rounds,
            "role_stats": {
                role: {
                    "games": stats["games"],
                    "wins": stats["wins"],
                    "win_rate": stats["wins"] / stats["games"] 
                        if stats["games"] > 0 else 0.0,
                }
                for role, stats in self.role_stats.items()
            },
        }


class StatsCollector:
    """统计收集器"""
    
    def __init__(self):
        """初始化统计收集器"""
        self.game_stats: List[GameStats] = []
        self.agent_stats: Dict[str, AgentStats] = {}
    
    def add_game(self, game_stats: GameStats) -> None:
        """添加一局游戏统计
        
        Args:
            game_stats: 游戏统计对象
        """
        self.game_stats.append(game_stats)
        
        # 更新Agent统计
        for agent_name, agent_result in game_stats.agents.items():
            if agent_name not in self.agent_stats:
                self.agent_stats[agent_name] = AgentStats(agent_name)
            
            self.agent_stats[agent_name].add_game_result(
                role=agent_result["role"],
                won=agent_result["won"],
                survived_rounds=agent_result.get("survived_rounds", 0),
            )
    
    def get_agent_stats(self, agent_name: str) -> AgentStats | None:
        """获取Agent统计
        
        Args:
            agent_name: Agent名称
        
        Returns:
            Agent统计对象，如果不存在则返回None
        """
        return self.agent_stats.get(agent_name)
    
    def get_all_agent_stats(self) -> List[AgentStats]:
        """获取所有Agent统计
        
        Returns:
            Agent统计对象列表
        """
        return list(self.agent_stats.values())
    
    def get_ranking(self) -> List[Dict[str, Any]]:
        """获取Agent胜率排名
        
        Returns:
            按胜率降序排列的Agent统计列表
        """
        stats_list = self.get_all_agent_stats()
        stats_list.sort(key=lambda x: x.get_win_rate(), reverse=True)
        return [stats.to_dict() for stats in stats_list]
    
    def get_best_agent(self) -> str | None:
        """获取胜率最高的Agent
        
        Returns:
            Agent名称，如果没有数据则返回None
        """
        ranking = self.get_ranking()
        return ranking[0]["agent_name"] if ranking else None
    
    def save_to_file(self, filepath: str) -> None:
        """保存统计到文件
        
        Args:
            filepath: 文件路径
        """
        data = {
            "games": [game.to_dict() for game in self.game_stats],
            "agents": {
                name: stats.to_dict() 
                for name, stats in self.agent_stats.items()
            },
            "summary": {
                "total_games": len(self.game_stats),
                "total_agents": len(self.agent_stats),
                "best_agent": self.get_best_agent(),
            },
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def load_from_file(self, filepath: str) -> None:
        """从文件加载统计
        
        Args:
            filepath: 文件路径
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 加载游戏统计
        self.game_stats = []
        for game_data in data.get("games", []):
            game_stats = GameStats(game_data["game_id"])
            game_stats.winner = game_data.get("winner")
            game_stats.rounds = game_data.get("rounds", 0)
            game_stats.timestamp = game_data.get("timestamp", "")
            game_stats.agents = game_data.get("agents", {})
            self.game_stats.append(game_stats)
        
        # 重新计算Agent统计（确保一致性）
        self.agent_stats = {}
        for game_stats in self.game_stats:
            for agent_name, agent_result in game_stats.agents.items():
                if agent_name not in self.agent_stats:
                    self.agent_stats[agent_name] = AgentStats(agent_name)
                
                self.agent_stats[agent_name].add_game_result(
                    role=agent_result["role"],
                    won=agent_result["won"],
                    survived_rounds=agent_result.get("survived_rounds", 0),
                )
    
    def generate_report(self) -> str:
        """生成统计报告
        
        Returns:
            报告文本
        """
        lines = []
        lines.append("=" * 60)
        lines.append("狼人杀Agent训练统计报告")
        lines.append("=" * 60)
        lines.append("")
        
        # 总体统计
        lines.append(f"总游戏局数: {len(self.game_stats)}")
        lines.append(f"参与Agent数: {len(self.agent_stats)}")
        lines.append("")
        
        # Agent排名
        lines.append("Agent胜率排名:")
        lines.append("-" * 60)
        ranking = self.get_ranking()
        for idx, agent_data in enumerate(ranking, 1):
            name = agent_data["agent_name"]
            win_rate = agent_data["win_rate"]
            total_games = agent_data["total_games"]
            total_wins = agent_data["total_wins"]
            avg_survival = agent_data["avg_survival_rounds"]
            
            lines.append(
                f"{idx}. {name}: "
                f"胜率={win_rate:.2%} "
                f"({total_wins}/{total_games}) "
                f"平均存活轮数={avg_survival:.1f}"
            )
        lines.append("")
        
        # 最佳Agent
        best_agent = self.get_best_agent()
        if best_agent:
            best_stats = self.agent_stats[best_agent]
            lines.append(f"最佳Agent: {best_agent}")
            lines.append(f"  总体胜率: {best_stats.get_win_rate():.2%}")
            lines.append(f"  总游戏数: {best_stats.total_games}")
            lines.append("  各角色胜率:")
            for role, role_stats in best_stats.role_stats.items():
                win_rate = best_stats.get_role_win_rate(role)
                games = role_stats["games"]
                wins = role_stats["wins"]
                lines.append(f"    {role}: {win_rate:.2%} ({wins}/{games})")
            lines.append("")
        
        # 角色统计
        lines.append("各角色总体表现:")
        lines.append("-" * 60)
        role_totals = defaultdict(lambda: {"games": 0, "wins": 0})
        for agent_stats in self.agent_stats.values():
            for role, role_stats in agent_stats.role_stats.items():
                role_totals[role]["games"] += role_stats["games"]
                role_totals[role]["wins"] += role_stats["wins"]
        
        for role in sorted(role_totals.keys()):
            stats = role_totals[role]
            win_rate = stats["wins"] / stats["games"] if stats["games"] > 0 else 0.0
            lines.append(
                f"{role}: "
                f"胜率={win_rate:.2%} "
                f"({stats['wins']}/{stats['games']})"
            )
        
        lines.append("")
        lines.append("=" * 60)
        
        return "\n".join(lines)
    
    def export_to_csv(self, filepath: str) -> None:
        """导出为CSV格式
        
        Args:
            filepath: 文件路径
        """
        import csv
        
        with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            
            # 写入表头
            writer.writerow([
                "Agent名称", "总游戏数", "总胜利数", "总体胜率",
                "狼人游戏数", "狼人胜利数", "狼人胜率",
                "村民游戏数", "村民胜利数", "村民胜率",
                "预言家游戏数", "预言家胜利数", "预言家胜率",
                "女巫游戏数", "女巫胜利数", "女巫胜率",
                "猎人游戏数", "猎人胜利数", "猎人胜率",
                "平均存活轮数",
            ])
            
            # 写入数据
            ranking = self.get_ranking()
            for agent_data in ranking:
                name = agent_data["agent_name"]
                role_stats = agent_data["role_stats"]
                
                row = [
                    name,
                    agent_data["total_games"],
                    agent_data["total_wins"],
                    f"{agent_data['win_rate']:.4f}",
                ]
                
                # 各角色统计
                for role in ["werewolf", "villager", "seer", "witch", "hunter"]:
                    stats = role_stats.get(role, {"games": 0, "wins": 0, "win_rate": 0.0})
                    row.extend([
                        stats["games"],
                        stats["wins"],
                        f"{stats['win_rate']:.4f}",
                    ])
                
                row.append(f"{agent_data['avg_survival_rounds']:.2f}")
                writer.writerow(row)

