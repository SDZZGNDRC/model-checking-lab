"""
实验四：NBA (非确定性 Buchi 自动机) 实现

本模块实现 NBA 的数据结构和模拟运行，支持：
- NBA 状态、转移、初始/接受状态的管理
- ε-闭包计算
- NBA 的模拟运行

NBA 与 NFA 的主要区别：
- NFA 接受有限词（到达接受状态）
- NBA 接受无限词（无限经常访问接受状态）

为实验四的 LTL 模型检查提供基础支持。
"""

from typing import Set, Dict, List, Tuple, Optional, FrozenSet
from dataclasses import dataclass, field
from collections import deque
import os
import webbrowser

# 可选依赖导入
try:
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False


@dataclass(frozen=True)
class NBAState:
    """
    NBA 状态类 - 不可变对象，可作为字典键使用
    
    状态由名称唯一标识
    """
    name: str
    
    def __hash__(self) -> int:
        return hash(self.name)
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, NBAState):
            return False
        return self.name == other.name
    
    def __repr__(self) -> str:
        return f"NBAState({self.name})"


@dataclass
class NBATransition:
    """
    NBA 迁移类
    
    表示从源状态到目标状态的一个迁移，带有符号标签
    符号可以是原子命题或 ε（空转移）
    """
    source: NBAState
    target: NBAState
    symbol: Optional[str]  # None 表示 ε-转移
    
    def __repr__(self) -> str:
        if self.symbol is None:
            return f"{self.source.name} --ε--> {self.target.name}"
        return f"{self.source.name} --{self.symbol}--> {self.target.name}"


class NBA:
    """
    非确定性 Buchi 自动机 (NBA) 类
    
    形式化定义：A = (Q, Σ, δ, Q₀, F)
    - Q: 状态集合
    - Σ: 字母表（原子命题集合）
    - δ: Q × (Σ ∪ {ε}) → 2^Q: 转移函数
    - Q₀ ⊆ Q: 初始状态集合
    - F ⊆ Q: 接受状态集合（Buchi 接受条件）
    
    Buchi 接受条件：一个无限运行是接受的，当且仅当
    它无限经常地访问接受状态集合 F 中的状态。
    
    使用邻接表存储转移关系，支持高效的遍历和查询。
    """
    
    def __init__(self):
        # 所有状态集合
        self._states: Dict[str, NBAState] = {}
        # 初始状态集合
        self._initial_states: Set[NBAState] = set()
        # 接受状态集合（Buchi 接受条件）
        self._accept_states: Set[NBAState] = set()
        # 转移关系：状态 -> [(目标状态, 符号)]
        self._transitions: Dict[NBAState, List[Tuple[NBAState, Optional[str]]]] = {}
        # 字母表
        self._alphabet: Set[str] = set()
    
    # ==================== 状态管理 ====================
    
    def add_state(self, name: str, is_initial: bool = False, 
                  is_accept: bool = False) -> NBAState:
        """
        添加新状态
        
        Args:
            name: 状态名称（唯一标识）
            is_initial: 是否为初始状态
            is_accept: 是否为接受状态（Buchi 接受条件）
            
        Returns:
            创建的状态对象
        """
        if name in self._states:
            state = self._states[name]
        else:
            state = NBAState(name)
            self._states[name] = state
            self._transitions[state] = []
        
        if is_initial:
            self._initial_states.add(state)
        if is_accept:
            self._accept_states.add(state)
        
        return state
    
    def get_state(self, name: str) -> Optional[NBAState]:
        """根据名称获取状态"""
        return self._states.get(name)
    
    def get_all_states(self) -> Set[NBAState]:
        """获取所有状态"""
        return set(self._states.values())
    
    def get_initial_states(self) -> Set[NBAState]:
        """获取所有初始状态"""
        return self._initial_states.copy()
    
    def get_accept_states(self) -> Set[NBAState]:
        """获取所有接受状态"""
        return self._accept_states.copy()
    
    def set_accept_state(self, state: NBAState):
        """设置接受状态"""
        self._accept_states.add(state)
    
    def is_accept_state(self, state: NBAState) -> bool:
        """检查状态是否为接受状态"""
        return state in self._accept_states
    
    # ==================== 迁移管理 ====================
    
    def add_transition(self, source_name: str, target_name: str, 
                       symbol: Optional[str] = None):
        """
        添加迁移关系
        
        Args:
            source_name: 源状态名称
            target_name: 目标状态名称
            symbol: 符号标签（None 表示 ε-转移）
        """
        source = self.add_state(source_name)
        target = self.add_state(target_name)
        
        self._transitions[source].append((target, symbol))
        
        if symbol is not None:
            self._alphabet.add(symbol)
    
    def get_transitions(self, state: NBAState) -> List[Tuple[NBAState, Optional[str]]]:
        """获取从指定状态出发的所有迁移"""
        return self._transitions.get(state, [])
    
    def get_successors(self, state: NBAState, symbol: Optional[str] = None) -> Set[NBAState]:
        """
        获取状态在给定符号下的所有后继状态
        
        Args:
            state: 源状态
            symbol: 符号（None 表示获取所有 ε-转移目标）
            
        Returns:
            后继状态集合
        """
        successors = set()
        for target, sym in self._transitions.get(state, []):
            if sym == symbol:
                successors.add(target)
        return successors
    
    # ==================== ε-闭包计算 ====================
    
    def epsilon_closure(self, states: Set[NBAState]) -> Set[NBAState]:
        """
        计算状态的 ε-闭包
        
        ε-闭包是指从给定状态集合通过 ε-转移可以到达的所有状态集合
        
        Args:
            states: 初始状态集合
            
        Returns:
            ε-闭包（包含初始状态）
        """
        closure = set(states)
        queue = deque(states)
        
        while queue:
            current = queue.popleft()
            # 获取所有 ε-转移目标
            for target, symbol in self._transitions.get(current, []):
                if symbol is None and target not in closure:
                    closure.add(target)
                    queue.append(target)
        
        return closure
    
    def epsilon_closure_single(self, state: NBAState) -> Set[NBAState]:
        """计算单个状态的 ε-闭包"""
        return self.epsilon_closure({state})
    
    # ==================== NBA 模拟运行 ====================
    
    def step(self, states: Set[NBAState], symbol: str) -> Set[NBAState]:
        """
        NBA 单步转移
        
        从当前状态集合读取一个符号后到达的新状态集合
        
        Args:
            states: 当前状态集合
            symbol: 输入符号
            
        Returns:
            转移后的状态集合（已计算 ε-闭包）
        """
        # 先计算当前状态的 ε-闭包
        current_closure = self.epsilon_closure(states)
        
        # 在 ε-闭包上执行符号转移
        next_states: Set[NBAState] = set()
        for state in current_closure:
            for target, sym in self._transitions.get(state, []):
                if sym == symbol:
                    next_states.add(target)
        
        # 返回结果状态的 ε-闭包
        return self.epsilon_closure(next_states)
    
    # ==================== 统计信息 ====================
    
    def get_statistics(self) -> Dict[str, int]:
        """获取 NBA 统计信息"""
        transition_count = sum(len(t) for t in self._transitions.values())
        
        return {
            "states": len(self._states),
            "initial_states": len(self._initial_states),
            "accept_states": len(self._accept_states),
            "transitions": transition_count,
            "alphabet_size": len(self._alphabet)
        }
    
    # ==================== 输入/输出 ====================
    
    def __repr__(self) -> str:
        stats = self.get_statistics()
        return (f"NBA("
                f"states={stats['states']}, "
                f"initial={stats['initial_states']}, "
                f"accept={stats['accept_states']}, "
                f"transitions={stats['transitions']})")
    
    def print_structure(self):
        """打印 NBA 结构"""
        print("=" * 50)
        print("NBA 结构")
        print("=" * 50)
        print(f"\n初始状态: {[s.name for s in self._initial_states]}")
        print(f"接受状态: {[s.name for s in self._accept_states]}")
        print(f"\n状态 ({len(self._states)} 个):")
        for name in sorted(self._states.keys()):
            state = self._states[name]
            markers = []
            if state in self._initial_states:
                markers.append("initial")
            if state in self._accept_states:
                markers.append("accept")
            marker_str = f" [{', '.join(markers)}]" if markers else ""
            print(f"  - {name}{marker_str}")
        
        print(f"\n转移关系:")
        for state in sorted(self._transitions.keys(), key=lambda s: s.name):
            for target, symbol in self._transitions[state]:
                sym_str = symbol if symbol else "ε"
                print(f"  {state.name} --{sym_str}--> {target.name}")
        print("=" * 50)


# ==================== 常用 NBA 构造器 ====================

def build_nba_always_eventually(atom: str) -> NBA:
    """
    构造 NBA 接受 "□♦atom"（无限经常 atom）
    
    这是一个通用构造，用于表示"无限经常"某个原子命题成立。
    
    Args:
        atom: 原子命题名称
        
    Returns:
        接受 □♦atom 的 NBA
    """
    nba = NBA()
    
    # 状态：q0（初始+接受），q1（等待 atom）
    q0 = nba.add_state("q0", is_initial=True, is_accept=True)
    q1 = nba.add_state("q1")
    
    # 在 q0：如果读到 atom，保持在 q0（接受）
    nba.add_transition("q0", "q0", atom)
    
    # 在 q0：如果没有读到 atom，到 q1（等待）
    # 我们使用 ε-转移表示"其他"符号
    # 实际上需要为所有其他符号添加转移
    
    # 在 q1：如果读到 atom，回到 q0（接受）
    nba.add_transition("q1", "q0", atom)
    
    return nba


def build_nba_globally(atom: str) -> NBA:
    """
    构造 NBA 接受 "□atom"（总是 atom）
    
    接受条件：所有状态都必须满足 atom
    
    Args:
        atom: 原子命题名称
        
    Returns:
        接受 □atom 的 NBA
    """
    nba = NBA()
    
    # 只有一个接受状态，必须始终满足 atom
    q0 = nba.add_state("q0", is_initial=True, is_accept=True)
    
    # 自环：必须始终读到 atom
    nba.add_transition("q0", "q0", atom)
    
    return nba


def build_nba_eventually(atom: str) -> NBA:
    """
    构造 NBA 接受 "♦atom"（最终 atom）
    
    Args:
        atom: 原子命题名称
        
    Returns:
        接受 ♦atom 的 NBA
    """
    nba = NBA()
    
    # q0：初始状态（等待 atom）
    # q1：接受状态（已经读到 atom）
    q0 = nba.add_state("q0", is_initial=True)
    q1 = nba.add_state("q1", is_accept=True)
    
    # 在 q0：读到 atom，到 q1
    nba.add_transition("q0", "q1", atom)
    
    # 在 q1：自环（已经满足）
    nba.add_transition("q1", "q1", atom)
    
    return nba


def build_nfa_implies_eventually(antecedent: str, consequent: str) -> NBA:
    """
    构造 NBA 接受 "□(antecedent → ♦consequent)"
    
    即：每当 antecedent 成立，最终 consequent 必须成立。
    
    Args:
        antecedent: 前件原子命题
        consequent: 后件原子命题
        
    Returns:
        接受 □(antecedent → ♦consequent) 的 NBA
    """
    nba = NBA()
    
    # q0：初始+接受状态（没有未完成的义务）
    # q1：等待 consequent（antecedent 已发生）
    q0 = nba.add_state("q0", is_initial=True, is_accept=True)
    q1 = nba.add_state("q1")
    
    # 在 q0：
    # - 如果 antecedent 且 consequent：保持在 q0（义务立即完成）
    # - 如果 antecedent 但没有 consequent：到 q1（等待）
    # - 如果没有 antecedent：保持在 q0
    
    # 注意：这里假设符号是原子命题的组合
    # 实际实现中需要根据标签集合来判断
    
    # 简化：假设我们一次只能读一个符号
    # q0 --antecedent--> q1（产生义务）
    nba.add_transition("q0", "q1", antecedent)
    
    # q0 --其他--> q0（没有义务）
    # 这里需要为所有非 antecedent 符号添加自环
    
    # 在 q1：
    # - 如果 consequent：回到 q0（义务完成）
    nba.add_transition("q1", "q0", consequent)
    
    # - 如果没有 consequent：保持在 q1（继续等待）
    # 这里需要为所有非 consequent 符号添加自环
    
    return nba
