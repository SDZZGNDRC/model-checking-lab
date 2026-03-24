"""
实验五：CTL 模型检查器

本模块实现基于固定点计算的 CTL 模型检查算法：
- 状态集合的位集表示
- 前置函数 Pre 计算
- 固定点迭代算法（最小/最大固定点）
- 基本算子：EX, EU, EG 的实现
- 导出算子通过 De Morgan 律推导

CTL 模型检查的核心思想：
1. 对 CTL 公式进行递归满意度计算
2. 使用状态集合表示满足公式的状态
3. 通过固定点迭代计算 EU 和 EG
"""

import sys
sys.path.insert(0, __file__.rsplit('\\', 1)[0] + '\\..\\lab1')

from typing import Set, Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import deque

from transition_system import TransitionSystem, State
from ctl_formula import CTLFormula, CTLOp


@dataclass
class CTLCheckResult:
    """
    CTL 模型检查结果
    
    Attributes:
        holds: 公式是否在初始状态上成立
        satisfying_states: 满足公式的状态集合
        initial_states: 初始状态集合
        counterexample_path: 反例路径（如果公式不成立）
        formula: 被检查的公式
        iterations: 固定点迭代次数
    """
    holds: bool
    satisfying_states: Set[State]
    initial_states: Set[State]
    counterexample_path: Optional[List[State]]
    formula: str
    iterations: int
    
    def __repr__(self) -> str:
        if self.holds:
            return (f"CTLCheckResult(holds=True, "
                    f"satisfying_states={len(self.satisfying_states)}, "
                    f"formula='{self.formula}', "
                    f"iterations={self.iterations})")
        else:
            path_str = " -> ".join(s.name for s in self.counterexample_path) if self.counterexample_path else "N/A"
            return (f"CTLCheckResult(holds=False, "
                    f"counterexample=[{path_str}], "
                    f"formula='{self.formula}', "
                    f"iterations={self.iterations})")


class CTLModelChecker:
    """
    CTL 模型检查器
    
    基于固定点计算实现 CTL 公式的递归满意度计算。
    """
    
    def __init__(self, ts: TransitionSystem):
        """
        初始化模型检查器
        
        Args:
            ts: 要验证的 Transition System
        """
        self.ts = ts
        self.iteration_count = 0
        
        # 缓存所有可达状态
        self._reachable_states: Optional[Set[State]] = None
    
    def _get_reachable_states(self) -> Set[State]:
        """获取所有可达状态（带缓存）"""
        if self._reachable_states is None:
            self._reachable_states = self.ts.compute_reachable_states()
        return self._reachable_states
    
    def _pre(self, states: Set[State]) -> Set[State]:
        """
        前置集合计算 Pre(C) = {s ∈ S | ∃s' ∈ C, s → s'}
        
        Args:
            states: 目标状态集合 C
            
        Returns:
            能一步到达 C 中某个状态的状态集合
        """
        return self.ts.pre(states)
    
    def _pre_forall(self, states: Set[State]) -> Set[State]:
        """
        全称前置集合计算 Pre∀(C) = {s ∈ S | ∀s' : s → s' ⇒ s' ∈ C}
        
        即：所有后继都在 C 中的状态集合
        
        Args:
            states: 目标状态集合 C
            
        Returns:
            所有后继都在 C 中的状态集合
        """
        result = set()
        all_reachable = self._get_reachable_states()
        
        for state in all_reachable:
            successors = self.ts.get_successors(state)
            # 如果没有后继，或者所有后继都在 states 中
            if not successors or successors.issubset(states):
                result.add(state)
        
        return result
    
    def _get_states_with_label(self, label: str) -> Set[State]:
        """
        获取带有指定标签的所有状态
        
        Args:
            label: 原子命题标签
            
        Returns:
            带有该标签的状态集合
        """
        result = set()
        for state in self._get_reachable_states():
            if state.has_label(label):
                result.add(state)
        return result
    
    def check(self, formula: CTLFormula) -> CTLCheckResult:
        """
        检查 CTL 公式
        
        Args:
            formula: 要检查的 CTL 公式
            
        Returns:
            CTLCheckResult 对象
        """
        self.iteration_count = 0
        
        # 计算满足公式的状态集合
        satisfying_states = self._sat(formula)
        
        # 获取初始状态
        initial_states = self.ts.get_initial_states()
        
        # 检查所有初始状态是否都满足公式
        holds = initial_states.issubset(satisfying_states)
        
        # 如果不成立，生成反例路径
        counterexample = None
        if not holds:
            violating_init = initial_states - satisfying_states
            if violating_init:
                counterexample = self._generate_counterexample(
                    list(violating_init)[0], 
                    satisfying_states,
                    formula
                )
        
        return CTLCheckResult(
            holds=holds,
            satisfying_states=satisfying_states,
            initial_states=initial_states,
            counterexample_path=counterexample,
            formula=str(formula),
            iterations=self.iteration_count
        )
    
    def check_string(self, formula_str: str) -> CTLCheckResult:
        """
        从字符串解析并检查 CTL 公式
        
        Args:
            formula_str: 公式字符串
            
        Returns:
            CTLCheckResult 对象
        """
        from ctl_formula import parse_ctl
        formula = parse_ctl(formula_str)
        return self.check(formula)
    
    def _sat(self, formula: CTLFormula) -> Set[State]:
        """
        计算满足公式的状态集合 Sat(φ)
        
        这是 CTL 模型检查的核心递归函数。
        
        Args:
            formula: CTL 公式
            
        Returns:
            满足该公式的状态集合
        """
        op = formula.op
        
        # 基本情况
        if op == CTLOp.TRUE:
            return self._get_reachable_states()
        
        if op == CTLOp.FALSE:
            return set()
        
        if op == CTLOp.ATOM:
            return self._get_states_with_label(formula.atom or "")
        
        # 命题逻辑
        if op == CTLOp.NOT:
            # Sat(¬φ) = S \ Sat(φ)
            all_states = self._get_reachable_states()
            sat_phi = self._sat(formula.left)
            return all_states - sat_phi
        
        if op == CTLOp.AND:
            # Sat(φ ∧ ψ) = Sat(φ) ∩ Sat(ψ)
            sat_phi = self._sat(formula.left)
            sat_psi = self._sat(formula.right)
            return sat_phi & sat_psi
        
        if op == CTLOp.OR:
            # Sat(φ ∨ ψ) = Sat(φ) ∪ Sat(ψ)
            sat_phi = self._sat(formula.left)
            sat_psi = self._sat(formula.right)
            return sat_phi | sat_psi
        
        if op == CTLOp.IMPLIES:
            # Sat(φ → ψ) = Sat(¬φ ∨ ψ) = (S \ Sat(φ)) ∪ Sat(ψ)
            sat_phi = self._sat(formula.left)
            sat_psi = self._sat(formula.right)
            all_states = self._get_reachable_states()
            return (all_states - sat_phi) | sat_psi
        
        # CTL 时序算子
        if op == CTLOp.EX:
            # Sat(EX φ) = Pre(Sat(φ))
            sat_phi = self._sat(formula.left)
            return self._pre(sat_phi)
        
        if op == CTLOp.AX:
            # Sat(AX φ) = Pre∀(Sat(φ))
            sat_phi = self._sat(formula.left)
            return self._pre_forall(sat_phi)
        
        if op == CTLOp.EF:
            # Sat(EF φ) = Sat(E[true U φ])
            return self._sat_eu(ctl_true(), formula.left)
        
        if op == CTLOp.AF:
            # Sat(AF φ) 使用最大固定点计算
            return self._sat_af(formula.left)
        
        if op == CTLOp.EG:
            # Sat(EG φ) 使用最大固定点计算
            return self._sat_eg(formula.left)
        
        if op == CTLOp.AG:
            # Sat(AG φ) = Sat(¬EF¬φ) = S \ Sat(EF¬φ)
            all_states = self._get_reachable_states()
            sat_ef_not_phi = self._sat_eu(ctl_true(), neg(formula.left))
            return all_states - sat_ef_not_phi
        
        if op == CTLOp.EU:
            # Sat(E[φ U ψ]) 使用最小固定点计算
            return self._sat_eu(formula.left, formula.right)
        
        if op == CTLOp.AU:
            # Sat(A[φ U ψ]) 使用 AU 的展开公式
            return self._sat_au(formula.left, formula.right)
        
        return set()
    
    def _sat_eg(self, phi: CTLFormula) -> Set[State]:
        """
        计算 Sat(EG φ) 使用最大固定点迭代
        
        EG φ = νZ.(φ ∧ EX Z)
        
        最大固定点迭代：
        - Z₀ = Sat(φ) (所有满足 φ 的状态)
        - Z_{i+1} = Z_i ∩ Pre(Z_i)  即：在 Z_i 中且能一步到达 Z_i 的状态
        - 直到 Z_{i+1} = Z_i
        
        注意：EG φ 表示存在一条路径，使得 φ 在所有未来状态上都成立。
        这意味着状态必须满足 φ，并且存在一条路径可以永远保持在满足 φ 的状态中。
        """
        sat_phi = self._sat(phi)
        
        # 如果没有状态满足 φ，直接返回空集
        if not sat_phi:
            return set()
        
        # 初始：Z = Sat(φ)
        z_current = sat_phi.copy()
        
        iterations = 0
        max_iterations = len(self._get_reachable_states()) * 2
        
        while iterations < max_iterations:
            iterations += 1
            self.iteration_count += 1
            
            # 计算 Pre(Z)：能一步到达 Z 的状态
            pre_z = self._pre(z_current)
            
            # Z' = Z ∩ Pre(Z)
            # 状态必须在当前 Z 中，并且能一步到达 Z 中的某个状态
            z_next = z_current & pre_z
            
            if z_next == z_current:
                break
            
            z_current = z_next
        
        return z_current
    
    def _sat_af(self, phi: CTLFormula) -> Set[State]:
        """
        计算 Sat(AF φ) 使用最小固定点迭代
        
        AF φ = μZ.(φ ∨ AX Z)
        
        最小固定点迭代：
        - Z₀ = ∅
        - Z_{i+1} = Sat(φ) ∪ Pre∀(Z_i)
        - 直到 Z_{i+1} = Z_i
        """
        sat_phi = self._sat(phi)
        
        # 初始：Z = ∅
        z_current = set()
        
        iterations = 0
        max_iterations = len(self._get_reachable_states()) * 2
        
        while iterations < max_iterations:
            iterations += 1
            self.iteration_count += 1
            
            # Z' = Sat(φ) ∪ Pre∀(Z)
            z_next = sat_phi | self._pre_forall(z_current)
            
            if z_next == z_current:
                break
            
            z_current = z_next
        
        return z_current
    
    def _sat_eu(self, phi1: CTLFormula, phi2: CTLFormula) -> Set[State]:
        """
        计算 Sat(E[φ1 U φ2]) 使用最小固定点迭代
        
        E[φ1 U φ2] = μZ.(φ2 ∨ (φ1 ∧ EX Z))
        
        语义：存在一条路径，使得 φ2 在某个未来状态成立，
        且在此之前所有状态都满足 φ1。
        
        最小固定点迭代：
        - Z₀ = Sat(φ2)  (首先满足 φ2 的状态)
        - Z_{i+1} = Z_i ∪ (Sat(φ1) ∩ Pre(Z_i))
        - 直到 Z_{i+1} = Z_i
        """
        sat_phi1 = self._sat(phi1)
        sat_phi2 = self._sat(phi2)
        
        # 初始：Z = Sat(φ2)
        # 首先，满足 φ2 的状态肯定满足 E[φ1 U φ2]
        z_current = sat_phi2.copy()
        
        iterations = 0
        max_iterations = len(self._get_reachable_states()) * 2
        
        while iterations < max_iterations:
            iterations += 1
            self.iteration_count += 1
            
            # 计算能一步到达 Z 的状态
            pre_z = self._pre(z_current)
            
            # Z' = Z ∪ (Sat(φ1) ∩ Pre(Z))
            # 新加入的状态：满足 φ1 且能一步到达 Z 的状态
            z_next = z_current | (sat_phi1 & pre_z)
            
            if z_next == z_current:
                break
            
            z_current = z_next
        
        return z_current
    
    def _sat_au(self, phi1: CTLFormula, phi2: CTLFormula) -> Set[State]:
        """
        计算 Sat(A[φ1 U φ2]) 使用最小固定点迭代
        
        A[φ1 U φ2] = μZ.(φ2 ∨ (φ1 ∧ AX Z))
        
        语义：所有路径都满足 φ1 直到 φ2 成立。
        
        最小固定点迭代：
        - Z₀ = Sat(φ2)  (首先满足 φ2 的状态)
        - Z_{i+1} = Z_i ∪ (Sat(φ1) ∩ Pre∀(Z_i))
        - 直到 Z_{i+1} = Z_i
        """
        sat_phi1 = self._sat(phi1)
        sat_phi2 = self._sat(phi2)
        
        # 初始：Z = Sat(φ2)
        z_current = sat_phi2.copy()
        
        iterations = 0
        max_iterations = len(self._get_reachable_states()) * 2
        
        while iterations < max_iterations:
            iterations += 1
            self.iteration_count += 1
            
            # 计算 Pre∀(Z)：所有后继都在 Z 中的状态
            pre_forall_z = self._pre_forall(z_current)
            
            # Z' = Z ∪ (Sat(φ1) ∩ Pre∀(Z))
            z_next = z_current | (sat_phi1 & pre_forall_z)
            
            if z_next == z_current:
                break
            
            z_current = z_next
        
        return z_current
    
    def _generate_counterexample(self, start: State, 
                                  target_states: Set[State],
                                  formula: CTLFormula) -> List[State]:
        """
        生成反例路径
        
        对于不满足的 CTL 公式，生成一条从初始状态出发的路径作为反例。
        
        Args:
            start: 起始状态（违反公式的初始状态）
            target_states: 满足公式的状态集合
            formula: 被检查的公式
            
        Returns:
            反例路径上的状态列表
        """
        # 对于简单情况，返回从 start 到某个满足公式状态的最短路径
        # 或者返回一条展示违反的路径
        
        # 使用 BFS 找到一条路径
        visited = {start}
        queue = deque([(start, [start])])
        
        # 限制搜索深度
        max_depth = 50
        
        while queue:
            current, path = queue.popleft()
            
            if len(path) > max_depth:
                break
            
            # 获取后继状态
            successors = self.ts.get_successors(current)
            
            for succ in successors:
                if succ not in visited:
                    new_path = path + [succ]
                    
                    # 如果找到了满足公式的状态，返回路径
                    if succ in target_states:
                        return new_path
                    
                    visited.add(succ)
                    queue.append((succ, new_path))
        
        # 如果没有找到到满足状态的路径，返回从 start 出发的一条简单路径
        return self._get_simple_path(start, max_length=10)
    
    def _get_simple_path(self, start: State, max_length: int = 10) -> List[State]:
        """
        获取一条从 start 出发的简单路径
        
        Args:
            start: 起始状态
            max_length: 最大路径长度
            
        Returns:
            路径上的状态列表
        """
        path = [start]
        current = start
        visited = {start}
        
        for _ in range(max_length - 1):
            successors = self.ts.get_successors(current)
            unvisited = [s for s in successors if s not in visited]
            
            if not unvisited:
                # 如果没有未访问的后继，尝试任意后继
                if successors:
                    current = list(successors)[0]
                    path.append(current)
                break
            
            current = unvisited[0]
            visited.add(current)
            path.append(current)
        
        return path


# 导入需要的函数
from ctl_formula import neg, conj, ctl_true, ctl_false


def check_ctl_property(ts: TransitionSystem, 
                       formula: CTLFormula) -> CTLCheckResult:
    """
    便捷函数：检查 CTL 属性
    
    Args:
        ts: Transition System
        formula: CTL 公式
        
    Returns:
        CTLCheckResult 对象
        
    Examples:
        >>> from ctl_formula import ag, disj, neg, atom
        >>> formula = ag(disj(neg(atom("crit1")), neg(atom("crit2"))))
        >>> result = check_ctl_property(ts, formula)
        >>> if result.holds:
        ...     print("互斥属性成立")
        ... else:
        ...     print(f"反例路径: {' -> '.join(s.name for s in result.counterexample_path)}")
    """
    checker = CTLModelChecker(ts)
    return checker.check(formula)
