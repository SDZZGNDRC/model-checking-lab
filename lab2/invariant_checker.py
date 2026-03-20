"""
实验二：不变性检查器

本模块实现不变性检查算法，包括：
- 遍历所有可达状态
- 检查每个状态是否满足给定的不变式
- 当发现违反时，生成从初始状态到违反状态的路径（反例）

基于实验一的 Transition System 实现。
"""

import sys
sys.path.insert(0, __file__.rsplit('\\', 1)[0] + '\\..\\lab1')

from typing import Set, List, Optional, Tuple, Dict
from dataclasses import dataclass
from collections import deque

from transition_system import TransitionSystem, State
from propositional_formula import PropositionalFormula, parse_formula


@dataclass
class InvariantCheckResult:
    """
    不变性检查结果
    
    Attributes:
        holds: 不变式是否在所有可达状态上成立
        violated_state: 违反不变式的状态（如果不成立）
        counterexample: 从初始状态到违反状态的路径（如果不成立）
        checked_states: 检查的状态数量
        formula: 被检查的公式字符串
    """
    holds: bool
    violated_state: Optional[State]
    counterexample: Optional[List[State]]
    checked_states: int
    formula: str
    
    def __repr__(self) -> str:
        if self.holds:
            return (f"InvariantCheckResult(holds=True, "
                    f"checked_states={self.checked_states}, "
                    f"formula='{self.formula}')")
        else:
            path_str = " -> ".join(s.name for s in self.counterexample) if self.counterexample else "N/A"
            return (f"InvariantCheckResult(holds=False, "
                    f"violated_state={self.violated_state.name if self.violated_state else 'N/A'}, "
                    f"counterexample=[{path_str}], "
                    f"checked_states={self.checked_states}, "
                    f"formula='{self.formula}')")


class InvariantChecker:
    """
    不变性检查器
    
    检查 Transition System 中所有可达状态是否满足给定的不变式。
    如果发现违反，生成反例路径。
    """
    
    def __init__(self, ts: TransitionSystem):
        """
        初始化检查器
        
        Args:
            ts: 要检查的 Transition System
        """
        self.ts = ts
    
    def check(self, formula: PropositionalFormula, method: str = "bfs") -> InvariantCheckResult:
        """
        检查不变式在所有可达状态上是否成立
        
        遍历所有可达状态，对每个状态计算公式真值。
        如果发现违反，立即返回并生成反例路径。
        
        Args:
            formula: 要检查的不变式（命题公式）
            method: 遍历方法，"bfs" 或 "dfs"
            
        Returns:
            InvariantCheckResult 对象
        """
        if method.lower() == "bfs":
            return self._check_bfs(formula)
        elif method.lower() == "dfs":
            return self._check_dfs(formula)
        else:
            raise ValueError(f"Unknown method: {method}. Use 'bfs' or 'dfs'.")
    
    def check_string(self, formula_str: str, method: str = "bfs") -> InvariantCheckResult:
        """
        从字符串解析并检查不变式
        
        Args:
            formula_str: 公式字符串，如 "¬(crit0 ∧ crit1)"
            method: 遍历方法
            
        Returns:
            InvariantCheckResult 对象
        """
        formula = parse_formula(formula_str)
        return self.check(formula, method)
    
    def _check_bfs(self, formula: PropositionalFormula) -> InvariantCheckResult:
        """使用 BFS 检查不变式"""
        initial_states = self.ts.get_initial_states()
        
        if not initial_states:
            return InvariantCheckResult(
                holds=True,
                violated_state=None,
                counterexample=None,
                checked_states=0,
                formula=str(formula)
            )
        
        # 记录访问过的状态和路径
        visited: Set[State] = set()
        # 记录每个状态的前驱（用于反例路径生成）
        parent: Dict[State, Optional[State]] = {}
        
        queue: deque = deque()
        
        # 初始化队列
        for init_state in initial_states:
            result = self._check_state(formula, init_state)
            if not result:
                # 初始状态就违反
                return InvariantCheckResult(
                    holds=False,
                    violated_state=init_state,
                    counterexample=[init_state],
                    checked_states=1,
                    formula=str(formula)
                )
            visited.add(init_state)
            parent[init_state] = None
            queue.append(init_state)
        
        checked_count = len(visited)
        
        while queue:
            current = queue.popleft()
            
            for successor, _ in self.ts.get_transitions(current):
                if successor not in visited:
                    # 检查新状态
                    result = self._check_state(formula, successor)
                    checked_count += 1
                    
                    if not result:
                        # 发现违反，生成反例路径
                        parent[successor] = current
                        counterexample = self._build_path(parent, successor)
                        return InvariantCheckResult(
                            holds=False,
                            violated_state=successor,
                            counterexample=counterexample,
                            checked_states=checked_count,
                            formula=str(formula)
                        )
                    
                    visited.add(successor)
                    parent[successor] = current
                    queue.append(successor)
        
        # 所有状态都满足
        return InvariantCheckResult(
            holds=True,
            violated_state=None,
            counterexample=None,
            checked_states=checked_count,
            formula=str(formula)
        )
    
    def _check_dfs(self, formula: PropositionalFormula) -> InvariantCheckResult:
        """使用 DFS 检查不变式"""
        initial_states = self.ts.get_initial_states()
        
        if not initial_states:
            return InvariantCheckResult(
                holds=True,
                violated_state=None,
                counterexample=None,
                checked_states=0,
                formula=str(formula)
            )
        
        visited: Set[State] = set()
        # 记录路径（当前 DFS 栈）
        path: List[State] = []
        checked_count = [0]  # 使用列表以便在嵌套函数中修改
        
        def dfs(state: State) -> Optional[State]:
            """DFS 遍历，返回违反状态或 None"""
            if state in visited:
                return None
            
            # 检查当前状态
            result = self._check_state(formula, state)
            checked_count[0] += 1
            
            if not result:
                return state
            
            visited.add(state)
            path.append(state)
            
            for successor, _ in self.ts.get_transitions(state):
                violation = dfs(successor)
                if violation is not None:
                    return violation
            
            path.pop()
            return None
        
        # 从每个初始状态开始 DFS
        for init_state in initial_states:
            path = [init_state]
            result = self._check_state(formula, init_state)
            checked_count[0] += 1
            
            if not result:
                return InvariantCheckResult(
                    holds=False,
                    violated_state=init_state,
                    counterexample=[init_state],
                    checked_states=checked_count[0],
                    formula=str(formula)
                )
            
            visited.add(init_state)
            
            for successor, _ in self.ts.get_transitions(init_state):
                violation = dfs(successor)
                if violation is not None:
                    # 找到从 init_state 到 violation 的路径
                    counterexample = self._find_path_from_init(init_state, violation)
                    return InvariantCheckResult(
                        holds=False,
                        violated_state=violation,
                        counterexample=counterexample,
                        checked_states=checked_count[0],
                        formula=str(formula)
                    )
            
            path.pop()
        
        return InvariantCheckResult(
            holds=True,
            violated_state=None,
            counterexample=None,
            checked_states=checked_count[0],
            formula=str(formula)
        )
    
    def _check_state(self, formula: PropositionalFormula, state: State) -> bool:
        """
        检查单个状态是否满足公式
        
        Args:
            formula: 命题公式
            state: 要检查的状态
            
        Returns:
            公式在该状态下的真值
        """
        return formula.evaluate(set(state.labels))
    
    def _build_path(self, parent: Dict[State, Optional[State]], 
                    target: State) -> List[State]:
        """
        根据 parent 映射构建从初始状态到目标状态的路径
        
        Args:
            parent: 状态到其父状态的映射
            target: 目标状态
            
        Returns:
            路径上的状态列表
        """
        path = []
        current: Optional[State] = target
        
        while current is not None:
            path.append(current)
            current = parent.get(current)
        
        path.reverse()
        return path
    
    def _find_path_from_init(self, init: State, target: State) -> List[State]:
        """
        使用 BFS 查找从初始状态到目标状态的路径
        
        Args:
            init: 初始状态
            target: 目标状态
            
        Returns:
            路径上的状态列表
        """
        if init == target:
            return [init]
        
        visited: Set[State] = {init}
        queue: deque = deque([(init, [init])])
        
        while queue:
            current, path = queue.popleft()
            
            for successor, _ in self.ts.get_transitions(current):
                if successor == target:
                    return path + [successor]
                
                if successor not in visited:
                    visited.add(successor)
                    queue.append((successor, path + [successor]))
        
        return [init, target]  # 保底返回


def check_invariant(ts: TransitionSystem, formula_str: str, 
                    method: str = "bfs") -> InvariantCheckResult:
    """
    便捷函数：检查不变式
    
    Args:
        ts: Transition System
        formula_str: 公式字符串
        method: 遍历方法
        
    Returns:
        InvariantCheckResult 对象
        
    Examples:
        >>> result = check_invariant(ts, "¬(crit0 ∧ crit1)")
        >>> if result.holds:
        ...     print("不变式成立")
        ... else:
        ...     print(f"反例路径: {' -> '.join(s.name for s in result.counterexample)}")
    """
    checker = InvariantChecker(ts)
    return checker.check_string(formula_str, method)
