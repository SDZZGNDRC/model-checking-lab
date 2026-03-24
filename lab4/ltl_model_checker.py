"""
实验四：LTL 模型检查器（自动机法）

本模块实现基于自动机的 LTL 模型检查，包括：
- TS 与 NBA 的乘积构造
- 嵌套 DFS 算法检测接受循环
- 反例路径生成（包含循环部分）

LTL 模型检查的核心思想：
1. 将待验证的 LTL 公式 φ 取否定得到 ¬φ
2. 将 ¬φ 转换为 NBA A_¬φ
3. 构建 TS 与 A_¬φ 的乘积
4. 检测乘积中是否存在可达的接受循环
5. 如果存在，则 TS 不满足 φ，输出反例路径
6. 如果不存在，则 TS 满足 φ
"""

import sys
sys.path.insert(0, __file__.rsplit('\\', 1)[0] + '\\..\\lab1')

from typing import Set, Dict, List, Tuple, Optional
from dataclasses import dataclass
from collections import deque

from transition_system import TransitionSystem, State
from nba import NBA, NBAState


@dataclass(frozen=True)
class ProductState:
    """
    乘积状态类
    
    由 TS 状态和 NBA 状态组合而成
    """
    ts_state: State
    nba_state: NBAState
    
    def __hash__(self) -> int:
        return hash((self.ts_state, self.nba_state))
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ProductState):
            return False
        return (self.ts_state == other.ts_state and 
                self.nba_state == other.nba_state)
    
    def __repr__(self) -> str:
        return f"({self.ts_state.name}, {self.nba_state.name})"


@dataclass
class LTLCheckResult:
    """
    LTL 模型检查结果
    
    Attributes:
        holds: LTL 公式是否成立
        counterexample: 反例路径（如果公式不成立）
        counterexample_loop: 反例中的循环部分（状态列表）
        checked_states: 检查的乘积状态数量
        property_description: 被检查的属性描述
    """
    holds: bool
    counterexample: Optional[List[State]]
    counterexample_loop: Optional[List[State]]
    checked_states: int
    property_description: str
    
    def __repr__(self) -> str:
        if self.holds:
            return (f"LTLCheckResult(holds=True, "
                    f"checked_states={self.checked_states}, "
                    f"property='{self.property_description}')")
        else:
            path_str = " -> ".join(s.name for s in self.counterexample) if self.counterexample else "N/A"
            loop_str = ""
            if self.counterexample_loop:
                loop_str = f", loop=[{' -> '.join(s.name for s in self.counterexample_loop)}]"
            return (f"LTLCheckResult(holds=False, "
                    f"counterexample=[{path_str}]{loop_str}, "
                    f"checked_states={self.checked_states}, "
                    f"property='{self.property_description}')")


class ProductConstruction:
    """
    TS 与 NBA 的同步乘积构造
    
    乘积构造规则：
    - 状态：(s, q) 其中 s ∈ TS 状态，q ∈ NBA 状态
    - 初始状态：{(s₀, q₀) | s₀ ∈ I_TS, q₀ ∈ Q₀_NFA}
    - 转移：(s, q) --a--> (s', q') 当且仅当
      * s --a--> s' 在 TS 中
      * q --L(s')--> q' 在 NBA 中（NBA 读取目标状态的标签）
    - 接受状态：{(s, q) | q ∈ F_NBA}
    """
    
    def __init__(self, ts: TransitionSystem, nba: NBA):
        """
        初始化乘积构造
        
        Args:
            ts: Transition System
            nba: NBA（通常是否定后的公式 NBA）
        """
        self.ts = ts
        self.nba = nba
    
    def get_initial_states(self) -> Set[ProductState]:
        """获取乘积图的初始状态集合"""
        ts_initial = self.ts.get_initial_states()
        nba_initial = self.nba.get_initial_states()
        nba_initial_closure = self.nba.epsilon_closure(nba_initial)
        
        initial_states: Set[ProductState] = set()
        for ts_state in ts_initial:
            for nba_state in nba_initial_closure:
                initial_states.add(ProductState(ts_state, nba_state))
        
        return initial_states
    
    def get_accept_states(self, product_states: Set[ProductState]) -> Set[ProductState]:
        """获取乘积图中的接受状态"""
        nba_accept = self.nba.get_accept_states()
        return {ps for ps in product_states if ps.nba_state in nba_accept}
    
    def is_accept_state(self, state: ProductState) -> bool:
        """检查乘积状态是否为接受状态"""
        return self.nba.is_accept_state(state.nba_state)
    
    def get_successors(self, state: ProductState) -> List[ProductState]:
        """
        获取乘积状态的直接后继
        
        动态计算，不存储完整乘积图
        """
        successors = []
        ts_s = state.ts_state
        nba_q = state.nba_state
        
        # 获取 TS 的后继状态
        for ts_next, _ in self.ts.get_transitions(ts_s):
            labels = set(ts_next.labels)
            
            # 对于每个标签，找到 NBA 的转移
            for label in labels:
                nba_next_states = self.nba.get_successors(nba_q, label)
                nba_next_closure = self.nba.epsilon_closure(nba_next_states)
                
                for nba_next in nba_next_closure:
                    successors.append(ProductState(ts_next, nba_next))
        
        return successors


class NestedDFS:
    """
    嵌套 DFS 算法
    
    用于检测图中是否存在可达的接受循环。
    
    算法思想：
    1. 外层 DFS：从初始状态开始搜索，记录访问顺序（栈）
    2. 当遇到接受状态时，启动内层 DFS
    3. 内层 DFS：从接受状态开始，检查是否能回到自身（形成循环）
    4. 如果内层 DFS 能找到回到接受状态的路径，则发现接受循环
    """
    
    def __init__(self, product: ProductConstruction):
        self.product = product
        self.outer_visited: Set[ProductState] = set()
        self.inner_visited: Set[ProductState] = set()
        self.stack: List[ProductState] = []  # 外层 DFS 栈
        self.cycle_start: Optional[ProductState] = None
        self.cycle_path: List[ProductState] = []
        self.checked_count = 0
    
    def search(self) -> Optional[Tuple[List[ProductState], List[ProductState]]]:
        """
        执行嵌套 DFS 搜索
        
        Returns:
            如果找到接受循环，返回 (前缀路径, 循环路径)
            否则返回 None
        """
        initial_states = self.product.get_initial_states()
        
        for init in initial_states:
            if init not in self.outer_visited:
                if self._outer_dfs(init):
                    # 找到接受循环，构建路径
                    return self._build_counterexample()
        
        return None
    
    def _outer_dfs(self, state: ProductState) -> bool:
        """
        外层 DFS
        
        Returns:
            如果找到接受循环，返回 True
        """
        self.outer_visited.add(state)
        self.stack.append(state)
        self.checked_count += 1
        
        # 检查是否是接受状态
        if self.product.is_accept_state(state):
            # 启动内层 DFS
            self.inner_visited.clear()
            if self._inner_dfs(state):
                self.cycle_start = state
                return True
        
        # 继续外层 DFS
        for successor in self.product.get_successors(state):
            if successor not in self.outer_visited:
                if self._outer_dfs(successor):
                    return True
        
        self.stack.pop()
        return False
    
    def _inner_dfs(self, state: ProductState) -> bool:
        """
        内层 DFS
        
        从接受状态开始，检查是否能回到外层 DFS 栈中的接受状态
        
        Returns:
            如果找到回到接受状态的路径，返回 True
        """
        self.inner_visited.add(state)
        
        for successor in self.product.get_successors(state):
            # 检查是否能回到外层栈中的接受状态
            if successor in self.stack and self.product.is_accept_state(successor):
                # 找到循环！
                self.cycle_path = [state, successor]
                return True
            
            if successor not in self.inner_visited:
                if self._inner_dfs(successor):
                    # 递归找到循环，记录路径
                    self.cycle_path.insert(0, state)
                    return True
        
        return False
    
    def _build_counterexample(self) -> Tuple[List[ProductState], List[ProductState]]:
        """
        构建反例路径
        
        Returns:
            (前缀路径, 循环路径)
        """
        # 前缀：从初始状态到 cycle_start
        prefix = []
        for state in self.stack:
            prefix.append(state)
            if state == self.cycle_start:
                break
        
        # 循环路径
        cycle = self.cycle_path
        
        return prefix, cycle


class LTLModelChecker:
    """
    LTL 模型检查器
    
    通过乘积构造和嵌套 DFS 检查 TS 是否满足 LTL 公式。
    """
    
    def __init__(self, ts: TransitionSystem):
        """
        初始化模型检查器
        
        Args:
            ts: 要验证的 Transition System
        """
        self.ts = ts
    
    def check(self, nba_neg_formula: NBA, 
              property_description: str = "") -> LTLCheckResult:
        """
        检查 TS 是否满足 LTL 公式
        
        注意：传入的 NBA 应该是公式否定的 NBA（即 A_¬φ）
        
        Args:
            nba_neg_formula: 公式否定的 NBA
            property_description: 属性描述（用于输出）
            
        Returns:
            LTLCheckResult 对象
        """
        product = ProductConstruction(self.ts, nba_neg_formula)
        
        # 使用嵌套 DFS 检测接受循环
        nested_dfs = NestedDFS(product)
        result = nested_dfs.search()
        
        if result is not None:
            # 找到接受循环，公式不满足
            prefix_product, cycle_product = result
            
            # 提取 TS 路径
            prefix_ts = [ps.ts_state for ps in prefix_product]
            cycle_ts = [ps.ts_state for ps in cycle_product]
            
            return LTLCheckResult(
                holds=False,
                counterexample=prefix_ts,
                counterexample_loop=cycle_ts,
                checked_states=nested_dfs.checked_count,
                property_description=property_description
            )
        else:
            # 没有找到接受循环，公式满足
            return LTLCheckResult(
                holds=True,
                counterexample=None,
                counterexample_loop=None,
                checked_states=nested_dfs.checked_count,
                property_description=property_description
            )


def check_ltl_property(ts: TransitionSystem, 
                       nba_neg_formula: NBA,
                       property_description: str = "") -> LTLCheckResult:
    """
    便捷函数：检查 LTL 属性
    
    Args:
        ts: Transition System
        nba_neg_formula: 公式否定的 NBA
        property_description: 属性描述
        
    Returns:
        LTLCheckResult 对象
        
    Examples:
        >>> from ltl_formula import always_eventually, ltl_to_nba
        >>> formula = always_eventually("green")
        >>> nba_neg = ltl_to_nba(neg(formula))  # 否定公式
        >>> result = check_ltl_property(ts, nba_neg, "□♦green")
        >>> if result.holds:
        ...     print("属性成立")
        ... else:
        ...     print(f"反例: {' -> '.join(s.name for s in result.counterexample)}")
    """
    checker = LTLModelChecker(ts)
    return checker.check(nba_neg_formula, property_description)
