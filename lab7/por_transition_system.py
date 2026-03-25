"""
实验七：偏序归约迁移系统生成器 (POR Transition System)

本模块实现基于偏序归约的状态空间生成，通过 ample 集计算减少需要探索的状态数。

核心功能：
- 从程序图生成简化迁移系统
- 应用 ample 集条件进行状态空间剪枝
- 支持开关控制（启用/禁用偏序归约）
- 提供统计信息对比
"""

import sys
sys.path.insert(0, __file__.rsplit('\\', 1)[0] + '\\..\\lab1')

from typing import Set, Dict, List, Tuple, Optional, Any, Callable
from collections import deque
from dataclasses import dataclass, field

from transition_system import TransitionSystem, State
from program_graph import ProgramGraph, Location
from action_dependency import Action, ActionDependency
from ample_set import AmpleSetGenerator


@dataclass
class PORStatistics:
    """偏序归约统计信息"""
    original_states: int = 0
    reduced_states: int = 0
    original_transitions: int = 0
    reduced_transitions: int = 0
    ample_computations: int = 0
    reduction_failures: int = 0  # 无法应用 ample 的次数
    
    @property
    def state_reduction_rate(self) -> float:
        """状态减少率"""
        if self.original_states == 0:
            return 0.0
        return (self.original_states - self.reduced_states) / self.original_states
    
    @property
    def transition_reduction_rate(self) -> float:
        """迁移减少率"""
        if self.original_transitions == 0:
            return 0.0
        return (self.original_transitions - self.reduced_transitions) / self.original_transitions
    
    def __repr__(self) -> str:
        return (f"PORStatistics(\n"
                f"  原始状态数: {self.original_states}, 简化后: {self.reduced_states}, "
                f"减少率: {self.state_reduction_rate:.1%}\n"
                f"  原始迁移数: {self.original_transitions}, 简化后: {self.reduced_transitions}, "
                f"减少率: {self.transition_reduction_rate:.1%}\n"
                f"  Ample 计算次数: {self.ample_computations}\n"
                f")")


class PORTransitionSystemBuilder:
    """
    偏序归约迁移系统构建器
    
    从程序图构建迁移系统，应用偏序归约减少状态空间。
    """
    
    def __init__(self, enable_por: bool = True):
        """
        初始化构建器
        
        Args:
            enable_por: 是否启用偏序归约
        """
        self.enable_por = enable_por
        self.statistics = PORStatistics()
        self._dependency_analyzer: Optional[ActionDependency] = None
        self._ample_generator: Optional[AmpleSetGenerator] = None
        
        # 状态映射：用于在展开过程中跟踪状态
        self._state_map: Dict[str, State] = {}
        
        # DFS 栈（用于 A4' 条件）
        self._dfs_stack: Set[str] = set()
        self._dfs_path: List[str] = []
    
    def build_from_program_graph(self, pg: ProgramGraph,
                                  dependency_analyzer: ActionDependency,
                                  visible_vars: Optional[Set[str]] = None) -> TransitionSystem:
        """
        从程序图构建迁移系统（应用偏序归约）
        
        Args:
            pg: 程序图
            dependency_analyzer: 动作依赖分析器
            visible_vars: 可见变量集合（用于 LTL\X 验证）
            
        Returns:
            构建的迁移系统
        """
        self._dependency_analyzer = dependency_analyzer
        self._ample_generator = AmpleSetGenerator(dependency_analyzer)
        
        if visible_vars:
            self._ample_generator.set_visible_variables(visible_vars)
        
        ts = TransitionSystem()
        
        if pg.get_initial_location() is None:
            return ts
        
        # 重置状态
        self._state_map = {}
        self._dfs_stack = set()
        self._dfs_path = []
        
        # 执行带偏序归约的 DFS 展开
        self._unfold_with_por(ts, pg)
        
        return ts
    
    def _unfold_with_por(self, ts: TransitionSystem, pg: ProgramGraph):
        """
        使用偏序归约展开程序图
        
        使用 DFS 遍历，在每个状态计算 ample 集。
        """
        initial_loc = pg.get_initial_location()
        initial_values = pg.get_initial_values()
        
        # 创建初始状态
        initial_state_name = self._make_state_name(initial_loc, initial_values)
        initial_labels = self._get_state_labels(initial_loc, initial_values, pg)
        
        ts.add_state(initial_state_name, initial_labels if initial_labels else None)
        ts.add_initial_state(initial_state_name)
        
        # DFS 栈元素：(状态名, 位置, 变量赋值)
        stack: List[Tuple[str, Location, Dict[str, Any]]] = []
        visited: Set[str] = set()
        
        # 初始化
        stack.append((initial_state_name, initial_loc, initial_values))
        visited.add(initial_state_name)
        self._dfs_stack.add(initial_state_name)
        self._dfs_path.append(initial_state_name)
        
        while stack:
            state_name, loc, valuation = stack.pop()
            self._dfs_path.remove(state_name)
            self._dfs_stack.discard(state_name)
            
            # 获取当前状态下所有可用的迁移
            available_transitions = pg.get_transitions(loc)
            
            # 过滤满足守卫条件的迁移
            enabled_transitions = []
            for trans in available_transitions:
                if self._evaluate_guard(trans.guard, valuation):
                    enabled_transitions.append(trans)
            
            if not enabled_transitions:
                continue
            
            # 将迁移转换为 Action 对象
            enabled_actions = self._transitions_to_actions(enabled_transitions)
            
            # 计算 ample 集（如果启用偏序归约）
            if self.enable_por and self._ample_generator:
                self.statistics.ample_computations += 1
                
                # 定义获取后继状态的函数
                def get_successor(action: Action) -> str:
                    # 找到对应的迁移
                    for trans in enabled_transitions:
                        if trans.action.name == action.name or f"P{action.process_id}:{trans.action.name}" == action.name:
                            new_valuation = self._apply_effect(trans.action.effect, valuation)
                            target_name = self._make_state_name(trans.target, new_valuation)
                            return target_name
                    return ""
                
                actions_to_explore = self._ample_generator.select_actions(
                    state_name, enabled_actions, get_successor, self._dfs_stack
                )
                
                if len(actions_to_explore) < len(enabled_actions):
                    self.statistics.reduction_failures += 1
            else:
                actions_to_explore = enabled_actions
            
            # 只探索 ample 集中的迁移
            transitions_to_explore = []
            for trans in enabled_transitions:
                trans_action_name = trans.action.name
                # 从完整动作名中提取基本名称（去掉 P{pid}: 前缀）
                trans_base_name = trans_action_name
                if trans_action_name.startswith("P") and ":" in trans_action_name:
                    try:
                        trans_base_name = trans_action_name[trans_action_name.index(":")+1:]
                    except:
                        pass
                
                for action in actions_to_explore:
                    # 匹配基本名称
                    if action.name == trans_base_name:
                        transitions_to_explore.append(trans)
                        break
            
            # 探索选中的迁移
            for trans in transitions_to_explore:
                # 应用效果函数
                new_valuation = self._apply_effect(trans.action.effect, valuation)
                
                # 验证新值在域内
                valid = True
                for var, val in new_valuation.items():
                    vars_dict = pg.get_variables()
                    if var in vars_dict and val not in vars_dict[var]:
                        valid = False
                        break
                
                if not valid:
                    continue
                
                # 生成目标状态
                target_state_name = self._make_state_name(trans.target, new_valuation)
                target_labels = self._get_state_labels(trans.target, new_valuation, pg)
                
                # 添加状态
                ts.add_state(target_state_name, target_labels if target_labels else None)
                ts.add_transition(state_name, target_state_name, trans.action.name)
                
                # 如果是新状态，加入 DFS 栈
                if target_state_name not in visited:
                    visited.add(target_state_name)
                    stack.append((target_state_name, trans.target, new_valuation))
                    self._dfs_stack.add(target_state_name)
                    self._dfs_path.append(target_state_name)
    
    def _transitions_to_actions(self, transitions: List) -> Set[Action]:
        """将程序图迁移转换为 Action 对象"""
        actions = set()
        for trans in transitions:
            # 从动作名称解析进程ID（格式："P{pid}:{name}"）
            full_name = trans.action.name
            process_id = 0
            name = full_name
            
            if full_name.startswith("P") and ":" in full_name:
                try:
                    process_id = int(full_name[1:full_name.index(":")])
                    name = full_name[full_name.index(":")+1:]
                except:
                    pass
            
            # 分析变量访问
            reads, writes = self._analyze_variable_access(trans.action)
            
            action = Action(name, process_id, frozenset(reads), frozenset(writes))
            actions.add(action)
        
        return actions
    
    def _analyze_variable_access(self, action) -> Tuple[Set[str], Set[str]]:
        """分析动作的变量访问（读/写）"""
        reads = set()
        writes = set()
        
        # 从效果函数分析写入
        for var in action.effect.keys():
            writes.add(var)
        
        # 从守卫条件分析读取
        if hasattr(action, 'guard') and action.guard:
            # 简单分析：提取变量名
            import re
            vars_in_guard = re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b', action.guard)
            for var in vars_in_guard:
                if var not in ['True', 'False', 'and', 'or', 'not']:
                    reads.add(var)
        
        # 从效果表达式分析读取
        for var, expr in action.effect.items():
            import re
            vars_in_expr = re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b', str(expr))
            for v in vars_in_expr:
                if v != var and v not in ['True', 'False']:
                    reads.add(v)
        
        return reads, writes
    
    def _make_state_name(self, loc: Location, valuation: Dict[str, Any]) -> str:
        """生成状态名称"""
        val_str = ",".join(f"{k}={v}" for k, v in sorted(valuation.items()))
        if val_str:
            return f"({loc.name},{val_str})"
        return f"({loc.name})"
    
    def _get_state_labels(self, loc: Location, valuation: Dict[str, Any], 
                          pg: ProgramGraph) -> Set[str]:
        """获取状态标签"""
        labels = set()
        
        # 添加位置标签
        pg_labels = pg.get_location_labels(loc)
        labels.update(pg_labels)
        
        # 根据变量值添加标签
        for var, val in valuation.items():
            labels.add(f"{var}={val}")
        
        return labels
    
    def _evaluate_guard(self, guard: str, valuation: Dict[str, Any]) -> bool:
        """评估守卫条件"""
        if guard == "True":
            return True
        if guard == "False":
            return False
        
        try:
            return bool(eval(guard, {"__builtins__": {}}, valuation))
        except:
            return False
    
    def _apply_effect(self, effect: Dict[str, str], 
                      valuation: Dict[str, Any]) -> Dict[str, Any]:
        """应用效果函数"""
        new_valuation = valuation.copy()
        
        for var, expr in effect.items():
            try:
                new_value = eval(expr, {"__builtins__": {}}, valuation)
                new_valuation[var] = new_value
            except:
                pass
        
        return new_valuation
    
    def compare_with_full_exploration(self, pg: ProgramGraph,
                                       dependency_analyzer: ActionDependency,
                                       visible_vars: Optional[Set[str]] = None) -> Tuple[TransitionSystem, TransitionSystem, PORStatistics]:
        """
        对比完整展开和偏序归约的结果
        
        Args:
            pg: 程序图
            dependency_analyzer: 动作依赖分析器
            visible_vars: 可见变量集合
            
        Returns:
            (完整 TS, 简化 TS, 统计信息)
        """
        # 完整展开
        self.enable_por = False
        full_ts = self.build_from_program_graph(pg, dependency_analyzer, visible_vars)
        full_stats = full_ts.get_statistics()
        
        # 偏序归约展开
        self.statistics = PORStatistics()
        self.enable_por = True
        reduced_ts = self.build_from_program_graph(pg, dependency_analyzer, visible_vars)
        reduced_stats = reduced_ts.get_statistics()
        
        # 更新统计信息
        self.statistics.original_states = full_stats['reachable_states']
        self.statistics.reduced_states = reduced_stats['reachable_states']
        self.statistics.original_transitions = full_stats['reachable_transitions']
        self.statistics.reduced_transitions = reduced_stats['reachable_transitions']
        
        return full_ts, reduced_ts, self.statistics


def create_dependency_analyzer_from_pg(pg: ProgramGraph) -> ActionDependency:
    """
    从程序图创建依赖分析器
    
    分析程序图中的所有动作，构建依赖关系。
    """
    analyzer = ActionDependency()
    
    # 收集所有动作
    for loc in pg.get_locations():
        for trans in pg.get_transitions(loc):
            action = trans.action
            
            # 解析进程ID
            name = action.name
            process_id = 0
            if name.startswith("P") and ":" in name:
                try:
                    process_id = int(name[1:name.index(":")])
                    name = name[name.index(":")+1:]
                except:
                    pass
            
            # 分析变量访问
            reads = set()
            writes = set()
            
            # 从效果函数分析
            for var in action.effect.keys():
                writes.add(var)
            
            # 检查是否涉及共享变量
            shared_vars = pg.get_shared_variables()
            
            # 如果动作涉及共享变量，记录依赖
            action_obj = Action(name, process_id, frozenset(reads), frozenset(writes))
            analyzer.register_action(action_obj)
    
    return analyzer


if __name__ == "__main__":
    print("=" * 60)
    print("偏序归约迁移系统生成器测试")
    print("=" * 60)
    
    # 创建一个简单的双计数器程序图
    from program_graph import Action as PGAction
    
    pg = ProgramGraph("TwoCounters")
    
    # 声明变量
    pg.declare_variable("count0", {0, 1, 2}, 0, is_shared=False)
    pg.declare_variable("count1", {0, 1, 2}, 0, is_shared=False)
    
    # 位置
    pg.add_location("start")
    pg.set_initial_location("start")
    
    # 迁移：递增 count0
    pg.add_transition("start", "start", PGAction("inc0", {"count0": "(count0 + 1) % 3"}))
    
    # 迁移：递增 count1
    pg.add_transition("start", "start", PGAction("inc1", {"count1": "(count1 + 1) % 3"}))
    
    print("\n程序图信息:")
    pg.print_info()
    
    # 创建依赖分析器
    analyzer = ActionDependency()
    
    # 手动注册动作
    action0 = Action("inc0", 0, frozenset(), frozenset({"count0"}))
    action1 = Action("inc1", 1, frozenset(), frozenset({"count1"}))
    analyzer.register_actions([action0, action1])
    
    # 对比完整展开和偏序归约
    print("\n【对比测试】")
    builder = PORTransitionSystemBuilder()
    full_ts, reduced_ts, stats = builder.compare_with_full_exploration(pg, analyzer)
    
    print(f"\n完整展开:")
    full_stats = full_ts.get_statistics()
    print(f"  可达状态: {full_stats['reachable_states']}")
    print(f"  可达迁移: {full_stats['reachable_transitions']}")
    
    print(f"\n偏序归约:")
    reduced_stats = reduced_ts.get_statistics()
    print(f"  可达状态: {reduced_stats['reachable_states']}")
    print(f"  可达迁移: {reduced_stats['reachable_transitions']}")
    
    print(f"\n{stats}")
