"""
实验七：Ample 集计算 (Ample Set Computation)

偏序归约的核心是 ample 集的选择。对于每个状态， ample 集是可用动作的一个子集，
满足四个条件（A0-A3，或简化的 A4'），可以保证在 LTL\X 验证中的完备性。

本模块实现：
- Ample 集条件检查
- 基于进程局部性的 ample 集计算
- 循环条件处理（A4'）
"""

import sys
sys.path.insert(0, __file__.rsplit('\\', 1)[0] + '\\..\\lab1')

from typing import Set, Dict, List, Tuple, Optional, Callable
from collections import deque
from action_dependency import Action, ActionDependency


class AmpleSet:
    """
    Ample 集计算器
    
    Ample 集必须满足的条件：
    
    A0 (非空): ample(s) ⊆ enabled(s)，且如果 enabled(s) ≠ ∅，则 ample(s) ≠ ∅
    
    A1 (依赖): 对于 ample(s) 中的任何动作 α，以及不在 ample(s) 中的任何动作 β，
              如果 α 和 β 依赖，则 α 必须在 β 之前执行
              
    A2 (无可见动作): ample(s) 中不能包含可见动作（影响 LTL 公式的动作），
                   除非 enabled(s) 中所有动作都是可见的
                   
    A3 (无分歧): ample(s) 中的动作不能导致状态空间的分歧（简化实现中可忽略）
    
    A4' (强化循环条件): 在 DFS 搜索树中，如果 ample(s) ≠ enabled(s)，
                      则 ample(s) 中的动作不能指向栈中的状态
    
    简化策略：
    - 基于进程选择：选择一个进程，其所有 enabled 动作构成 ample 集
    - 优先选择只访问局部变量的进程
    """
    
    def __init__(self, dependency_analyzer: ActionDependency):
        """
        初始化 Ample 集计算器
        
        Args:
            dependency_analyzer: 动作依赖分析器
        """
        self.dependency = dependency_analyzer
        # DFS 栈（用于 A4' 条件）
        self._dfs_stack: Set[str] = set()  # 存储状态标识
        # 可见变量集合
        self._visible_vars: Set[str] = set()
    
    def set_visible_variables(self, visible_vars: Set[str]):
        """
        设置可见变量（用于 A2 条件）
        
        Args:
            visible_vars: 影响 LTL 公式的变量集合
        """
        self._visible_vars = visible_vars
    
    def set_dfs_stack(self, stack: Set[str]):
        """
        设置当前 DFS 栈（用于 A4' 条件）
        
        Args:
            stack: 栈中状态的标识集合
        """
        self._dfs_stack = stack
    
    def compute_ample(self, state_id: str, 
                      enabled_actions: Set[Action],
                      get_successor: Callable[[Action], str]) -> Optional[Set[Action]]:
        """
        计算状态的 ample 集
        
        Args:
            state_id: 当前状态标识
            enabled_actions: 当前状态下所有可用动作
            get_successor: 函数，输入动作，返回后继状态标识
            
        Returns:
            ample 集，如果无法找到满足条件的 ample 集，返回 None（使用完整 enabled 集）
        """
        if not enabled_actions:
            return set()
        
        # 如果只有一个可用动作，直接返回
        if len(enabled_actions) == 1:
            return enabled_actions
        
        # 按进程分组动作
        actions_by_process: Dict[int, Set[Action]] = {}
        for action in enabled_actions:
            pid = action.process_id
            if pid not in actions_by_process:
                actions_by_process[pid] = set()
            actions_by_process[pid].add(action)
        
        # 尝试为每个进程构造 ample 集
        for pid, process_actions in actions_by_process.items():
            if self._check_ample_conditions(state_id, enabled_actions, 
                                            process_actions, get_successor):
                return process_actions
        
        # 无法找到满足条件的 ample 集，使用完整 enabled 集
        return enabled_actions
    
    def _check_ample_conditions(self, state_id: str,
                                 enabled_actions: Set[Action],
                                 candidate: Set[Action],
                                 get_successor: Callable[[Action], str]) -> bool:
        """
        检查候选 ample 集是否满足所有条件
        
        Args:
            state_id: 当前状态标识
            enabled_actions: 所有可用动作
            candidate: 候选 ample 集
            get_successor: 获取后继状态的函数
            
        Returns:
            True 如果满足所有条件
        """
        # A0: 非空（已由调用者保证）
        if not candidate:
            return False
        
        # A1: 依赖条件
        if not self._check_A1(enabled_actions, candidate):
            return False
        
        # A2: 无可见动作条件
        if not self._check_A2(enabled_actions, candidate):
            return False
        
        # A4': 强化循环条件
        if not self._check_A4_prime(state_id, candidate, get_successor):
            return False
        
        return True
    
    def _check_A1(self, enabled_actions: Set[Action], 
                  candidate: Set[Action]) -> bool:
        """
        检查 A1 (依赖) 条件
        
        条件：对于 ample 集中的任何动作 α，以及不在 ample 集中的任何动作 β，
              如果 α 和 β 依赖，则必须保证 α 在 β 之前执行。
              
        简化实现：如果候选 ample 集是某个进程的所有 enabled 动作，
        且该进程的动作与其他进程的动作独立，则满足 A1。
        
        更强的条件：候选集中的所有动作必须与不在候选集中的所有动作独立。
        """
        other_actions = enabled_actions - candidate
        
        if not other_actions:
            # 没有其他动作，条件自动满足
            return True
        
        for ample_action in candidate:
            for other_action in other_actions:
                if self.dependency.are_dependent(ample_action, other_action):
                    # 存在依赖，检查是否满足顺序要求
                    # 简化：如果 ample_action 属于一个进程，且 other_action 属于另一个进程
                    # 且 ample_action 的进程 ID 较小，则认为满足顺序
                    # 更严格的实现需要分析依赖图
                    if ample_action.process_id > other_action.process_id:
                        return False
        
        return True
    
    def _check_A2(self, enabled_actions: Set[Action],
                  candidate: Set[Action]) -> bool:
        """
        检查 A2 (无可见动作) 条件
        
        条件：ample(s) 中不能包含可见动作，除非 enabled(s) 中所有动作都是可见的。
        """
        # 检查候选集中是否有可见动作
        has_visible_in_candidate = any(
            self.dependency.is_visible(a, self._visible_vars) 
            for a in candidate
        )
        
        if not has_visible_in_candidate:
            # 候选集中没有可见动作，条件满足
            return True
        
        # 候选集中有可见动作，检查是否所有 enabled 动作都是可见的
        all_visible = all(
            self.dependency.is_visible(a, self._visible_vars)
            for a in enabled_actions
        )
        
        return all_visible
    
    def _check_A4_prime(self, state_id: str,
                        candidate: Set[Action],
                        get_successor: Callable[[Action], str]) -> bool:
        """
        检查 A4' (强化循环条件)
        
        条件：如果 ample(s) ≠ enabled(s)，则 ample(s) 中的动作不能指向 DFS 栈中的状态。
        
        这是强化的循环条件，简化了 A4 的实现。
        """
        for action in candidate:
            successor_id = get_successor(action)
            if successor_id in self._dfs_stack:
                # 后继状态在栈中，违反 A4'
                return False
        
        return True
    
    def compute_ample_simple(self, state_id: str,
                             enabled_actions: Set[Action],
                             get_successor: Callable[[Action], str]) -> Set[Action]:
        """
        简化的 ample 集计算
        
        策略：
        1. 如果只有一个可用动作，返回该动作
        2. 尝试找到一个进程，其动作都是独立的（不依赖其他进程的动作）
        3. 如果找不到，返回所有可用动作
        
        Args:
            state_id: 当前状态标识
            enabled_actions: 可用动作集合
            get_successor: 获取后继状态的函数
            
        Returns:
            ample 集
        """
        if not enabled_actions:
            return set()
        
        if len(enabled_actions) == 1:
            return enabled_actions
        
        # 按进程分组
        by_process: Dict[int, Set[Action]] = {}
        for action in enabled_actions:
            pid = action.process_id
            by_process.setdefault(pid, set()).add(action)
        
        # 优先选择只包含不可见动作的进程
        for pid in sorted(by_process.keys()):
            process_actions = by_process[pid]
            
            # 检查是否包含可见动作
            has_visible = any(
                self.dependency.is_visible(a, self._visible_vars)
                for a in process_actions
            )
            
            # 检查 A4' 条件
            violates_A4 = any(
                get_successor(a) in self._dfs_stack
                for a in process_actions
            )
            
            if not has_visible and not violates_A4:
                # 检查与其他进程的独立性
                other_actions = enabled_actions - process_actions
                is_independent = all(
                    self.dependency.are_independent(a1, a2)
                    for a1 in process_actions
                    for a2 in other_actions
                )
                
                if is_independent:
                    return process_actions
        
        # 无法找到满足条件的 ample 集
        return enabled_actions
    
    def get_ample_statistics(self) -> Dict[str, int]:
        """
        获取 ample 集计算统计信息
        
        Returns:
            统计信息字典
        """
        return {
            "visible_variables": len(self._visible_vars),
            "dfs_stack_size": len(self._dfs_stack)
        }


class AmpleSetGenerator:
    """
    Ample 集生成器 - 用于在状态空间生成中动态计算 ample 集
    
    与 TransitionSystem 集成，在展开过程中应用偏序归约。
    """
    
    def __init__(self, dependency_analyzer: ActionDependency):
        self.ample_calculator = AmpleSet(dependency_analyzer)
        self._reduction_count = 0
        self._total_states = 0
    
    def set_visible_variables(self, visible_vars: Set[str]):
        """设置可见变量"""
        self.ample_calculator.set_visible_variables(visible_vars)
    
    def begin_state_expansion(self, state_id: str):
        """开始扩展一个状态（将状态加入 DFS 栈）"""
        self._total_states += 1
    
    def end_state_expansion(self, state_id: str):
        """结束扩展一个状态（将状态从 DFS 栈移除）"""
        pass
    
    def select_actions(self, state_id: str,
                       enabled_actions: Set[Action],
                       get_successor: Callable[[Action], str],
                       dfs_stack: Set[str]) -> Set[Action]:
        """
        选择要探索的动作（应用偏序归约）
        
        Args:
            state_id: 当前状态标识
            enabled_actions: 所有可用动作
            get_successor: 获取后继状态的函数
            dfs_stack: 当前 DFS 栈
            
        Returns:
            要探索的动作集合（ample 集或完整 enabled 集）
        """
        self.ample_calculator.set_dfs_stack(dfs_stack)
        
        ample = self.ample_calculator.compute_ample_simple(
            state_id, enabled_actions, get_successor
        )
        
        if len(ample) < len(enabled_actions):
            self._reduction_count += 1
        
        return ample
    
    def get_statistics(self) -> Dict[str, int]:
        """获取统计信息"""
        return {
            "reduced_states": self._reduction_count,
            "total_states": self._total_states,
            "reduction_rate": self._reduction_count / max(1, self._total_states)
        }


if __name__ == "__main__":
    print("=" * 60)
    print("Ample 集计算测试")
    print("=" * 60)
    
    # 创建依赖分析器
    from action_dependency import create_simple_dependency_analyzer
    
    analyzer = create_simple_dependency_analyzer()
    ample_calc = AmpleSet(analyzer)
    
    # 设置可见变量
    ample_calc.set_visible_variables({"count0"})
    
    # 创建动作
    inc0 = analyzer._actions["inc0"]
    inc1 = analyzer._actions["inc1"]
    
    # 测试 ample 集计算
    enabled = {inc0, inc1}
    
    def get_successor(action):
        # 模拟后继状态
        return f"state_after_{action.name}"
    
    print("\n【测试1：独立计数器】")
    print(f"Enabled 动作: {enabled}")
    
    ample = ample_calc.compute_ample_simple("s0", enabled, get_successor)
    print(f"Ample 集: {ample}")
    print(f"归约效果: {len(enabled)} -> {len(ample)}")
    
    # 测试 DFS 栈影响
    print("\n【测试2：DFS 栈影响】")
    ample_calc.set_dfs_stack({"state_after_inc0"})
    ample2 = ample_calc.compute_ample_simple("s0", enabled, get_successor)
    print(f"DFS 栈包含 state_after_inc0 时的 Ample 集: {ample2}")
