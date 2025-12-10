# -*- coding: utf-8 -*-
"""提示词生成器模块 - 根据Agent配置生成个性化提示词"""
from typing import Dict, Any


class PromptGenerator:
    """根据Agent配置生成个性化提示词"""
    
    def __init__(self, base_prompt: str | None = None):
        """初始化提示词生成器
        
        Args:
            base_prompt: 基础提示词模板，如果为None则使用默认模板
        """
        if base_prompt is None:
            from prompt import ChinesePrompts
            base_prompt = ChinesePrompts.to_system
        self.base_prompt = base_prompt
    
    def generate(self, agent_config: Dict[str, Any], agent_name: str) -> str:
        """生成个性化提示词
        
        Args:
            agent_config: Agent配置字典，包含personality, strategy, role_strategies
            agent_name: Agent名称
            
        Returns:
            个性化系统提示词
        """
        # 1. 生成基础提示词（替换name）
        prompt = self.base_prompt.format(name=agent_name)
        
        # 2. 生成性格描述
        personality_section = self._generate_personality_section(
            agent_config.get("personality", {})
        )
        
        # 3. 生成策略描述
        strategy_section = self._generate_strategy_section(
            agent_config.get("strategy", {})
        )
        
        # 4. 生成角色策略
        role_strategies_section = self._generate_role_strategies_section(
            agent_config.get("role_strategies", {})
        )
        
        # 5. 组合所有部分
        personalized_prompt = f"""{prompt}

# 你的性格特点
{personality_section}

# 你的游戏策略
{strategy_section}

# 角色特定策略
{role_strategies_section}
"""
        return personalized_prompt
    
    def _generate_personality_section(self, personality: Dict[str, Any]) -> str:
        """生成性格描述部分"""
        sections = []
        
        # aggression (激进度)
        aggression = personality.get("aggression", 5)
        if aggression <= 3:
            sections.append("你是一个保守谨慎的玩家，倾向于观察和分析后再行动。")
        elif aggression <= 6:
            sections.append("你是一个平衡的玩家，会根据局势灵活调整策略。")
        else:
            sections.append("你是一个激进主动的玩家，倾向于主动出击和掌控局面。")
        
        # trust_level (信任度)
        trust_level = personality.get("trust_level", 5)
        if trust_level <= 3:
            sections.append("你对其他玩家保持高度怀疑，不轻易相信任何人的话。")
        elif trust_level <= 6:
            sections.append("你会适度信任其他玩家，但保持必要的警惕。")
        else:
            sections.append("你倾向于相信和合作，容易建立联盟关系。")
        
        # logic_focus (逻辑性)
        logic_focus = personality.get("logic_focus", 5)
        if logic_focus <= 3:
            sections.append("你更依赖直觉和第一印象，而不是严密的逻辑推理。")
        elif logic_focus <= 6:
            sections.append("你会在逻辑推理和直觉判断之间保持平衡。")
        else:
            sections.append("你擅长严密的逻辑推理，注重证据链和逻辑一致性。")
        
        # deception_skill (欺骗能力)
        deception_skill = personality.get("deception_skill", 5)
        if deception_skill <= 3:
            sections.append("你倾向于诚实直接，不擅长伪装和欺骗。")
        elif deception_skill <= 6:
            sections.append("你会适度使用策略和技巧，但不会过度伪装。")
        else:
            sections.append("你擅长伪装和误导，能够灵活切换角色和策略。")
        
        # speech_style (发言风格)
        speech_style = personality.get("speech_style", "")
        if speech_style:
            sections.append(f"你的发言风格是：{speech_style}。")
        
        # risk_tolerance (风险承受)
        risk_tolerance = personality.get("risk_tolerance", 5)
        if risk_tolerance <= 3:
            sections.append("你倾向于保守策略，避免高风险行动。")
        elif risk_tolerance <= 6:
            sections.append("你会在风险和收益之间保持平衡。")
        else:
            sections.append("你愿意承担高风险以获取高收益。")
        
        return "\n".join(sections) if sections else "你是一个平衡的玩家。"
    
    def _generate_strategy_section(self, strategy: Dict[str, Any]) -> str:
        """生成策略指导部分"""
        sections = []
        
        # voting_basis (投票依据)
        voting_basis = strategy.get("voting_basis", "")
        if voting_basis:
            sections.append(f"你的投票依据是：{voting_basis}。")
        
        # speak_timing (发言时机)
        speak_timing = strategy.get("speak_timing", "")
        if speak_timing:
            sections.append(f"你的发言时机：{speak_timing}。")
        
        # suspicion_threshold (怀疑阈值)
        suspicion_threshold = strategy.get("suspicion_threshold")
        if suspicion_threshold is not None:
            sections.append(f"你的怀疑阈值：{suspicion_threshold}（数值越高越不容易怀疑他人）。")
        
        # alliance_tendency (结盟倾向)
        alliance_tendency = strategy.get("alliance_tendency", "")
        if alliance_tendency:
            sections.append(f"你的结盟倾向：{alliance_tendency}。")
        
        # special_habits (特殊习惯)
        special_habits = strategy.get("special_habits", "")
        if special_habits:
            sections.append(f"你的特殊习惯：{special_habits}。")
        
        return "\n".join(sections) if sections else "你会根据局势灵活调整策略。"
    
    def _generate_role_strategies_section(self, role_strategies: Dict[str, Any]) -> str:
        """生成角色特定策略部分"""
        sections = []
        
        # 狼人策略
        werewolf = role_strategies.get("werewolf", {})
        if werewolf:
            werewolf_strategies = []
            disguise = werewolf.get("disguise_preference", "")
            if disguise:
                werewolf_strategies.append(f"伪装偏好：{disguise}")
            kill_priority = werewolf.get("kill_priority", "")
            if kill_priority:
                werewolf_strategies.append(f"击杀优先级：{kill_priority}")
            team_coord = werewolf.get("team_coordination", "")
            if team_coord:
                werewolf_strategies.append(f"团队协调：{team_coord}")
            if werewolf_strategies:
                sections.append(f"## 作为狼人时：\n" + "\n".join(f"- {s}" for s in werewolf_strategies))
        
        # 预言家策略
        seer = role_strategies.get("seer", {})
        if seer:
            seer_strategies = []
            reveal = seer.get("reveal_timing", "")
            if reveal:
                seer_strategies.append(f"暴露时机：{reveal}")
            check = seer.get("check_priority", "")
            if check:
                seer_strategies.append(f"查验优先级：{check}")
            info = seer.get("info_sharing", "")
            if info:
                seer_strategies.append(f"信息分享：{info}")
            if seer_strategies:
                sections.append(f"## 作为预言家时：\n" + "\n".join(f"- {s}" for s in seer_strategies))
        
        # 女巫策略
        witch = role_strategies.get("witch", {})
        if witch:
            witch_strategies = []
            heal = witch.get("heal_strategy", "")
            if heal:
                witch_strategies.append(f"解药策略：{heal}")
            poison = witch.get("poison_strategy", "")
            if poison:
                witch_strategies.append(f"毒药策略：{poison}")
            if witch_strategies:
                sections.append(f"## 作为女巫时：\n" + "\n".join(f"- {s}" for s in witch_strategies))
        
        # 猎人策略
        hunter = role_strategies.get("hunter", {})
        if hunter:
            hunter_strategies = []
            shoot = hunter.get("shoot_timing", "")
            if shoot:
                hunter_strategies.append(f"开枪时机：{shoot}")
            target = hunter.get("target_priority", "")
            if target:
                hunter_strategies.append(f"目标优先级：{target}")
            if hunter_strategies:
                sections.append(f"## 作为猎人时：\n" + "\n".join(f"- {s}" for s in hunter_strategies))
        
        # 村民策略
        villager = role_strategies.get("villager", {})
        if villager:
            villager_strategies = []
            analysis = villager.get("analysis_style", "")
            if analysis:
                villager_strategies.append(f"分析风格：{analysis}")
            support = villager.get("support_style", "")
            if support:
                villager_strategies.append(f"支持风格：{support}")
            if villager_strategies:
                sections.append(f"## 作为村民时：\n" + "\n".join(f"- {s}" for s in villager_strategies))
        
        return "\n\n".join(sections) if sections else "你会根据角色特点灵活调整策略。"

