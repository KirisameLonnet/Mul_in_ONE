"""Dynamic conversation scheduler for multi-agent natural dialogue."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict, Iterable, List


@dataclass(slots=True)
class PersonaState:
    name: str
    proactivity: float  # 主动性 0.0-1.0
    cooldown: int = 1  # 冷却轮数
    last_turn: int = -10
    consecutive_speaks: int = 0  # 连续发言次数


class TurnScheduler:
    """
    动态对话调度器，模拟自然多人对话：
    - Agent 根据上下文动态决定是否发言
    - 支持被 @ 时强制发言
    - 防止单个 Agent 霸占对话
    - 自动检测对话冷场并激活 Agent
    """
    
    def __init__(
        self, 
        personas: Iterable[PersonaState], 
        max_agents: int,
        silence_threshold: int = 2  # 多少轮无人发言视为冷场
    ) -> None:
        self.personas: Dict[str, PersonaState] = {p.name: p for p in personas}
        # max_agents <= 0 表示不限制，取全部 persona 数
        self.max_agents = len(self.personas) if max_agents <= 0 else max_agents
        self.turn = 0
        self.silence_threshold = silence_threshold
        self.silence_count = 0  # 连续沉默轮数

    def next_turn(
        self, 
        user_mentions: List[str] | None = None,
        agent_mentions: List[str] | None = None,
        last_speaker: str | None = None,
        is_user_message: bool = True
    ) -> List[str]:
        """
        决定下一轮谁应该发言。
        
        Args:
            user_mentions: 用户 @ 的 Agent 名称列表（最高优先级，保持顺序）
            agent_mentions: 其他 Agent @ 的名称列表（次高优先级，保持顺序）
            last_speaker: 上一个发言者
            is_user_message: 是否是用户新消息（而非 Agent 回复）
        
        Returns:
            本轮应该发言的 Agent 列表
        """
        user_mentions = user_mentions or []
        agent_mentions = agent_mentions or []

        def _pick_mentions(names: List[str], already: set[str]) -> List[str]:
            chosen: List[str] = []
            seen: set[str] = set()
            for name in names:
                if name in seen or name in already:
                    continue
                persona = self.personas.get(name)
                if not persona:
                    continue
                # 同一轮内不重复选择刚说过话的
                if (self.turn - persona.last_turn) <= 0:
                    continue
                chosen.append(name)
                seen.add(name)
                if len(chosen) + len(already) >= self.max_agents:
                    break
            return chosen
        
        # ===== 第一优先级：处理用户 @ 的 Agent（绝对优先，保持用户提及顺序） =====
        priority_picks: List[str] = _pick_mentions(user_mentions, set())

        # ===== 第二优先级：其他 Agent @ 的 Agent（优先级低于用户，但高于主动性） =====
        if len(priority_picks) < self.max_agents:
            picked_set = set(priority_picks)
            priority_picks.extend(_pick_mentions(agent_mentions, picked_set))

        if priority_picks:
            for persona in self.personas.values():
                if persona.name in priority_picks:
                    persona.last_turn = self.turn
                    persona.consecutive_speaks += 1
                else:
                    persona.consecutive_speaks = 0
            self.silence_count = 0
            self.turn += 1
            return priority_picks
        
        # ===== 第二优先级：主动发言计算（无人被 @ 时） =====
        candidates: List[tuple[str, float]] = []
        
        for persona in self.personas.values():
            since_last = self.turn - persona.last_turn
            
            # 基础分数：主动性
            score = persona.proactivity
            
            # 冷却惩罚：刚说过话的降低优先级
            if since_last <= persona.cooldown:
                score -= 0.6
                continue  # 冷却期内不考虑
            
            # 连续发言惩罚：避免霸占对话
            if persona.consecutive_speaks >= 2:
                score -= 0.3 * persona.consecutive_speaks
            
            # 时间奖励：很久没说话了应该说点什么
            if since_last > 5:
                score += min(0.3, since_last * 0.05)
            
            # 对话延续：回应上一个发言者（如果不是自己）
            if last_speaker and last_speaker != persona.name and since_last > 1:
                score += 0.15
            
            # 用户新消息时，更积极响应
            if is_user_message and persona.proactivity > 0.6:
                score += 0.2
            
            # 随机性：模拟人类对话的不可预测性
            score += random.uniform(-0.1, 0.1)
            
            candidates.append((persona.name, score))
        
        # --- 原有逻辑：处理主动发言的情况 ---
        # 按分数排序
        candidates.sort(key=lambda x: x[1], reverse=True)
        
        # 动态决定发言人数
        chosen = []
        threshold = 0.5  # 基础阈值
        
        # 冷场检测：如果连续多轮无人发言，降低阈值
        if self.silence_count >= self.silence_threshold:
            threshold = 0.3
        
        for name, score in candidates:
            # 根据分数和已选人数决定
            if score >= threshold and len(chosen) < self.max_agents:
                # 第一个人更容易被选中
                if len(chosen) == 0 and score >= 0.4:
                    chosen.append(name)
                # 后续人员门槛更高
                elif len(chosen) < self.max_agents and score >= threshold + 0.1 * len(chosen):
                    chosen.append(name)
        
        # 若无人入选且这是用户新消息，至少选出一名发言者（得分最高者）
        if not chosen and is_user_message and candidates:
            top_name, _ = candidates[0]
            chosen = [top_name]

        # 更新状态
        for persona in self.personas.values():
            if persona.name in chosen:
                persona.last_turn = self.turn
                persona.consecutive_speaks += 1
            else:
                persona.consecutive_speaks = 0
        
        # 更新沉默计数
        if chosen:
            self.silence_count = 0
        else:
            self.silence_count += 1
        
        self.turn += 1
        return chosen
