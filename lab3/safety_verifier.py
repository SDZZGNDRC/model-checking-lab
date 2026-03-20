"""
实验三：正则安全属性验证器

本模块实现正则安全属性的验证，包括：
- TS 与 NFA 的同步乘积构造
- 在乘积图中搜索接受状态是否可达
- 反例路径生成

安全属性验证的核心思想：
1. 将安全属性的"坏前缀"构造为 NFA（接受所有违反属性的有限路径）
2. 构建 TS 与 NFA 的同步乘积
3. 检查乘积中是否存在可达的接受状态
4. 如果存在，则原 TS 违反安全属性，输出反例路径
"""

import sys
sys.path.insert(0, __file__.rsplit('\\', 1)[0] + '\\..\\lab1')

from typing import Set, Dict, List, Tuple, Optional
from dataclasses import dataclass
from collections import deque

from transition_system import TransitionSystem, State
from nfa import NFA, NFAState


@dataclass(frozen=True)
class ProductState:
    """
    乘积状态类
    
    由 TS 状态和 NFA 状态组合而成
    """
    ts_state: State
    nfa_state: NFAState
    
    def __hash__(self) -> int:
        return hash((self.ts_state, self.nfa_state))
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ProductState):
            return False
        return (self.ts_state == other.ts_state and 
                self.nfa_state == other.nfa_state)
    
    def __repr__(self) -> str:
        return f"({self.ts_state.name}, {self.nfa_state.name})"


@dataclass
class SafetyCheckResult:
    """
    安全属性检查结果
    
    Attributes:
        holds: 安全属性是否成立
        counterexample: 反例路径（如果属性不成立）
        counterexample_labels: 反例路径上的标签序列
        checked_states: 检查的乘积状态数量
        property_description: 被检查的属性描述
    """
    holds: bool
    counterexample: Optional[List[State]]
    counterexample_labels: Optional[List[Set[str]]]
    checked_states: int
    property_description: str
    
    def __repr__(self) -> str:
        if self.holds:
            return (f"SafetyCheckResult(holds=True, "
                    f"checked_states={self.checked_states}, "
                    f"property='{self.property_description}')")
        else:
            path_str = " -> ".join(s.name for s in self.counterexample) if self.counterexample else "N/A"
            return (f"SafetyCheckResult(holds=False, "
                    f"counterexample=[{path_str}], "
                    f"checked_states={self.checked_states}, "
                    f"property='{self.property_description}')")


class ProductConstruction:
    """
    TS 与 NFA 的同步乘积构造
    
    乘积构造规则：
    - 状态：(s, q) 其中 s ∈ TS 状态，q ∈ NFA 状态
    - 初始状态：{(s₀, q₀) | s₀ ∈ I_TS, q₀ ∈ Q₀_NFA}
    - 转移：(s, q) --a--> (s', q') 当且仅当
      * s --a--> s' 在 TS 中
      * q --L(s')--> q' 在 NFA 中（NFA 读取目标状态的标签）
    - 接受状态：{(s, q) | q ∈ F_NFA}
    """
    
    def __init__(self, ts: TransitionSystem, nfa: NFA):
        """
        初始化乘积构造
        
        Args:
            ts: Transition System
            nfa: NFA（接受坏前缀）
        """
        self.ts = ts
        self.nfa = nfa
    
    def construct(self) -> Tuple[Set[ProductState], Dict[ProductState, List[ProductState]]]:
        """
        构建完整的乘积图
        
        Returns:
            (乘积状态集合, 转移关系字典)
        """
        states: Set[ProductState] = set()
        transitions: Dict[ProductState, List[ProductState]] = {}
        
        # 计算初始状态集合
        ts_initial = self.ts.get_initial_states()
        nfa_initial = self.nfa.get_initial_states()
        nfa_initial_closure = self.nfa.epsilon_closure(nfa_initial)
        
        # 初始乘积状态
        initial_product_states: Set[ProductState] = set()
        for ts_state in ts_initial:
            for nfa_state in nfa_initial_closure:
                ps = ProductState(ts_state, nfa_state)
                initial_product_states.add(ps)
                states.add(ps)
                transitions[ps] = []
        
        # BFS 构建乘积图
        queue = deque(initial_product_states)
        visited = set(initial_product_states)
        
        while queue:
            current = queue.popleft()
            ts_s = current.ts_state
            nfa_q = current.nfa_state
            
            # 获取 TS 的后继状态
            for ts_next, _ in self.ts.get_transitions(ts_s):
                # NFA 读取目标状态的标签
                labels = set(ts_next.labels)
                
                # 对于每个标签，找到 NFA 的转移
                for label in labels:
                    nfa_next_states = self.nfa.get_successors(nfa_q, label)
                    # 计算 ε-闭包
                    nfa_next_closure = self.nfa.epsilon_closure(nfa_next_states)
                    
                    for nfa_next in nfa_next_closure:
                        next_product = ProductState(ts_next, nfa_next)
                        
                        if current not in transitions:
                            transitions[current] = []
                        transitions[current].append(next_product)
                        
                        if next_product not in visited:
                            visited.add(next_product)
                            states.add(next_product)
                            transitions[next_product] = []
                            queue.append(next_product)
        
        return states, transitions
    
    def get_initial_states(self) -> Set[ProductState]:
        """获取乘积图的初始状态集合"""
        ts_initial = self.ts.get_initial_states()
        nfa_initial = self.nfa.get_initial_states()
        nfa_initial_closure = self.nfa.epsilon_closure(nfa_initial)
        
        initial_states: Set[ProductState] = set()
        for ts_state in ts_initial:
            for nfa_state in nfa_initial_closure:
                initial_states.add(ProductState(ts_state, nfa_state))
        
        return initial_states
    
    def get_accept_states(self, product_states: Set[ProductState]) -> Set[ProductState]:
        """获取乘积图中的接受状态"""
        nfa_accept = self.nfa.get_accept_states()
        return {ps for ps in product_states if ps.nfa_state in nfa_accept}
    
    def get_successors(self, state: ProductState) -> List[ProductState]:
        """
        获取乘积状态的直接后继
        
        动态计算，不存储完整乘积图
        """
        successors = []
        ts_s = state.ts_state
        nfa_q = state.nfa_state
        
        # 获取 TS 的后继状态
        for ts_next, _ in self.ts.get_transitions(ts_s):
            labels = set(ts_next.labels)
            
            # 对于每个标签，找到 NFA 的转移
            for label in labels:
                nfa_next_states = self.nfa.get_successors(nfa_q, label)
                nfa_next_closure = self.nfa.epsilon_closure(nfa_next_states)
                
                for nfa_next in nfa_next_closure:
                    successors.append(ProductState(ts_next, nfa_next))
        
        return successors


class SafetyVerifier:
    """
    正则安全属性验证器
    
    通过乘积构造检查 TS 是否满足正则安全属性。
    安全属性通过其补集（坏前缀）的 NFA 表示。
    """
    
    def __init__(self, ts: TransitionSystem):
        """
        初始化验证器
        
        Args:
            ts: 要验证的 Transition System
        """
        self.ts = ts
    
    def verify(self, bad_prefix_nfa: NFA, 
               property_description: str = "") -> SafetyCheckResult:
        """
        验证 TS 是否满足安全属性
        
        Args:
            bad_prefix_nfa: 接受坏前缀的 NFA
            property_description: 属性描述（用于输出）
            
        Returns:
            SafetyCheckResult 对象
        """
        product = ProductConstruction(self.ts, bad_prefix_nfa)
        
        # 使用 BFS 搜索可达的接受状态
        return self._search_accept_bfs(product, bad_prefix_nfa, property_description)
    
    def _search_accept_bfs(self, product: ProductConstruction, 
                           nfa: NFA,
                           property_description: str) -> SafetyCheckResult:
        """
        使用 BFS 搜索乘积图中是否存在可达的接受状态
        
        如果存在，则安全属性被违反
        """
        initial_states = product.get_initial_states()
        
        if not initial_states:
            return SafetyCheckResult(
                holds=True,
                counterexample=None,
                counterexample_labels=None,
                checked_states=0,
                property_description=property_description
            )
        
        # 接受状态集合
        nfa_accept = nfa.get_accept_states()
        
        # BFS
        visited: Set[ProductState] = set()
        parent: Dict[ProductState, Optional[ProductState]] = {}
        ts_parent: Dict[State, Optional[State]] = {}  # 用于提取 TS 路径
        
        queue: deque = deque()
        
        for init in initial_states:
            # 检查初始状态是否是接受状态
            if init.nfa_state in nfa_accept:
                # 找到违反
                ts_path = [init.ts_state]
                labels_path = [set(init.ts_state.labels)]
                return SafetyCheckResult(
                    holds=False,
                    counterexample=ts_path,
                    counterexample_labels=labels_path,
                    checked_states=1,
                    property_description=property_description
                )
            
            visited.add(init)
            parent[init] = None
            ts_parent[init.ts_state] = None
            queue.append(init)
        
        checked_count = len(visited)
        
        while queue:
            current = queue.popleft()
            
            for successor in product.get_successors(current):
                if successor not in visited:
                    checked_count += 1
                    
                    # 检查是否是接受状态
                    if successor.nfa_state in nfa_accept:
                        # 找到违反，构建反例路径
                        parent[successor] = current
                        ts_parent[successor.ts_state] = current.ts_state
                        
                        counterexample = self._build_counterexample(
                            parent, ts_parent, initial_states, successor
                        )
                        
                        return SafetyCheckResult(
                            holds=False,
                            counterexample=counterexample[0],
                            counterexample_labels=counterexample[1],
                            checked_states=checked_count,
                            property_description=property_description
                        )
                    
                    visited.add(successor)
                    parent[successor] = current
                    ts_parent[successor.ts_state] = current.ts_state
                    queue.append(successor)
        
        # 没有发现违反
        return SafetyCheckResult(
            holds=True,
            counterexample=None,
            counterexample_labels=None,
            checked_states=checked_count,
            property_description=property_description
        )
    
    def _build_counterexample(self, 
                              parent: Dict[ProductState, Optional[ProductState]],
                              ts_parent: Dict[State, Optional[State]],
                              initial_states: Set[ProductState],
                              target: ProductState) -> Tuple[List[State], List[Set[str]]]:
        """
        构建反例路径
        
        从目标状态回溯到初始状态，提取 TS 路径和标签序列
        """
        # 回溯乘积状态路径
        product_path: List[ProductState] = []
        current: Optional[ProductState] = target
        
        while current is not None:
            product_path.append(current)
            current = parent.get(current)
        
        product_path.reverse()
        
        # 提取 TS 路径
        ts_path = [ps.ts_state for ps in product_path]
        labels_path = [set(ps.ts_state.labels) for ps in product_path]
        
        return ts_path, labels_path
    
    def verify_regex(self, bad_prefix_regex: str, 
                     property_description: str = "") -> SafetyCheckResult:
        """
        从正则表达式构建 NFA 并验证
        
        Args:
            bad_prefix_regex: 坏前缀的正则表达式
            property_description: 属性描述
            
        Returns:
            SafetyCheckResult 对象
        """
        from nfa import build_nfa_from_regex
        
        nfa = build_nfa_from_regex(bad_prefix_regex)
        return self.verify(nfa, property_description)


def check_safety_property(ts: TransitionSystem, 
                          bad_prefix_nfa: NFA,
                          property_description: str = "") -> SafetyCheckResult:
    """
    便捷函数：检查安全属性
    
    Args:
        ts: Transition System
        bad_prefix_nfa: 接受坏前缀的 NFA
        property_description: 属性描述
        
    Returns:
        SafetyCheckResult 对象
        
    Examples:
        >>> nfa = build_bad_prefix_nfa_red_yellow()
        >>> result = check_safety_property(ts, nfa, "red后必须紧跟yellow")
        >>> if result.holds:
        ...     print("属性成立")
        ... else:
        ...     print(f"反例: {' -> '.join(s.name for s in result.counterexample)}")
    """
    verifier = SafetyVerifier(ts)
    return verifier.verify(bad_prefix_nfa, property_description)


def check_safety_property_regex(ts: TransitionSystem,
                                 bad_prefix_regex: str,
                                 property_description: str = "") -> SafetyCheckResult:
    """
    便捷函数：从正则表达式检查安全属性
    
    Args:
        ts: Transition System
        bad_prefix_regex: 坏前缀的正则表达式
        property_description: 属性描述
        
    Returns:
        SafetyCheckResult 对象
    """
    verifier = SafetyVerifier(ts)
    return verifier.verify_regex(bad_prefix_regex, property_description)


# ==================== 常用坏前缀 NFA 构造器 ====================

def build_bad_prefix_nfa_red_must_follow_yellow() -> NFA:
    """
    构造"red 后必须紧跟 yellow"的坏前缀 NFA
    
    坏前缀：red 后紧跟的不是 yellow（如 red -> green）
    NFA 接受所有违反该属性的有限路径
    """
    nfa = NFA()
    
    # 状态
    q0 = nfa.add_state("q0", is_initial=True)  # 初始状态
    q1 = nfa.add_state("q1")                    # 刚读到 red
    q2 = nfa.add_state("q2", is_accept=True)    # 接受状态（违反）
    
    # 转移
    # 在 q0：读 red 到 q1，读其他保持在 q0
    nfa.add_transition("q0", "q1", "red")
    nfa.add_transition("q0", "q0", "green")
    nfa.add_transition("q0", "q0", "yellow")
    
    # 在 q1：如果读的不是 yellow，则进入接受状态（违反）
    nfa.add_transition("q1", "q2", "green")  # red -> green 是坏的
    nfa.add_transition("q1", "q2", "red")    # red -> red 也是坏的
    nfa.add_transition("q1", "q0", "yellow") # red -> yellow 是好的，回到初始
    
    # 在 q2（接受状态）：自环保持
    nfa.add_transition("q2", "q2", "red")
    nfa.add_transition("q2", "q2", "green")
    nfa.add_transition("q2", "q2", "yellow")
    
    return nfa


def build_bad_prefix_nfa_no_consecutive_red() -> NFA:
    """
    构造"不允许连续两个 red"的坏前缀 NFA
    
    坏前缀：出现 "red red"
    """
    nfa = NFA()
    
    q0 = nfa.add_state("q0", is_initial=True)
    q1 = nfa.add_state("q1")  # 刚读到 red
    q2 = nfa.add_state("q2", is_accept=True)  # 连续两个 red（违反）
    
    # q0 的转移
    nfa.add_transition("q0", "q1", "red")
    nfa.add_transition("q0", "q0", "green")
    nfa.add_transition("q0", "q0", "yellow")
    
    # q1 的转移
    nfa.add_transition("q1", "q2", "red")    # 连续 red -> 违反
    nfa.add_transition("q1", "q0", "green")  # red -> green 是好的
    nfa.add_transition("q1", "q0", "yellow") # red -> yellow 是好的
    
    # q2 的自环
    nfa.add_transition("q2", "q2", "red")
    nfa.add_transition("q2", "q2", "green")
    nfa.add_transition("q2", "q2", "yellow")
    
    return nfa


def build_bad_prefix_nfa_pattern_must_follow(pattern: str, must_follow: str) -> NFA:
    """
    通用构造器：pattern 后必须紧跟 must_follow
    
    Args:
        pattern: 前导模式
        must_follow: 必须紧跟的模式
        
    Returns:
        接受坏前缀的 NFA
    """
    nfa = NFA()
    
    q0 = nfa.add_state("q0", is_initial=True)
    q1 = nfa.add_state("q1")  # 刚读到 pattern
    q2 = nfa.add_state("q2", is_accept=True)  # 违反状态
    
    # 这里假设只有 pattern 和 must_follow 两种符号
    # 实际使用时可能需要扩展
    nfa.add_transition("q0", "q1", pattern)
    nfa.add_transition("q0", "q0", must_follow)
    
    nfa.add_transition("q1", "q0", must_follow)
    nfa.add_transition("q1", "q2", pattern)
    
    nfa.add_transition("q2", "q2", pattern)
    nfa.add_transition("q2", "q2", must_follow)
    
    return nfa
