"""
实验七：动作依赖关系分析 (Action Dependency Analysis)

偏序归约的核心是识别独立的动作。两个动作独立意味着它们的执行顺序不影响最终结果。

本模块实现：
- 动作独立性分析（基于共享变量）
- 依赖关系图构建
- 进程局部性判断
"""

from typing import Set, Dict, List, Tuple, Optional, FrozenSet
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Action:
    """
    动作类 - 表示程序中的一个可执行动作
    
    Attributes:
        name: 动作名称
        process_id: 所属进程ID（用于偏序归约）
        reads: 读取的变量集合
        writes: 写入的变量集合
    """
    name: str
    process_id: int = 0
    reads: FrozenSet[str] = field(default_factory=frozenset)
    writes: FrozenSet[str] = field(default_factory=frozenset)
    
    def __hash__(self) -> int:
        return hash((self.name, self.process_id, self.reads, self.writes))
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Action):
            return False
        return (self.name == other.name and 
                self.process_id == other.process_id and
                self.reads == other.reads and
                self.writes == other.writes)
    
    def __repr__(self) -> str:
        return f"Action({self.name}, P{self.process_id})"
    
    def accesses_variable(self, var: str) -> bool:
        """检查动作是否访问指定变量（读或写）"""
        return var in self.reads or var in self.writes
    
    def get_accessed_vars(self) -> Set[str]:
        """获取动作访问的所有变量"""
        return set(self.reads) | set(self.writes)


class ActionDependency:
    """
    动作依赖关系分析器
    
    判断两个动作是否独立（independent）或依赖（dependent）。
    
    独立性定义：
    两个动作 α 和 β 独立，当且仅当：
    1. 它们不访问相同的共享变量，或者
    2. 它们只读共享变量，或者
    3. 它们属于同一进程（进程内顺序是固定的）
    
    依赖条件（满足任一即为依赖）：
    1. 两个动作写入同一变量（写-写冲突）
    2. 一个动作读、另一个动作写同一变量（读-写冲突）
    3. 动作涉及共享变量的同步操作
    """
    
    def __init__(self):
        # 缓存依赖关系
        self._dependency_cache: Dict[Tuple[str, str], bool] = {}
        # 所有动作集合
        self._actions: Dict[str, Action] = {}
    
    def register_action(self, action: Action):
        """
        注册动作到依赖分析器
        
        Args:
            action: 要注册的动作
        """
        self._actions[action.name] = action
    
    def register_actions(self, actions: List[Action]):
        """批量注册动作"""
        for action in actions:
            self.register_action(action)
    
    def are_independent(self, action1: Action, action2: Action) -> bool:
        """
        判断两个动作是否独立
        
        独立性条件：
        1. 同一进程内的动作视为依赖（必须保持程序顺序）
        2. 不同进程间，如果没有共享变量冲突，则独立
        
        Args:
            action1: 第一个动作
            action2: 第二个动作
            
        Returns:
            True 如果两个动作独立
        """
        # 同一进程内的动作视为依赖（必须保持交错语义）
        if action1.process_id == action2.process_id:
            return False
        
        # 检查缓存
        cache_key = (action1.name, action2.name)
        reverse_key = (action2.name, action1.name)
        
        if cache_key in self._dependency_cache:
            return not self._dependency_cache[cache_key]
        if reverse_key in self._dependency_cache:
            return not self._dependency_cache[reverse_key]
        
        # 分析变量访问冲突
        is_dependent = self._check_dependency(action1, action2)
        
        # 缓存结果
        self._dependency_cache[cache_key] = is_dependent
        self._dependency_cache[reverse_key] = is_dependent
        
        return not is_dependent
    
    def _check_dependency(self, action1: Action, action2: Action) -> bool:
        """
        检查两个动作是否依赖（内部实现）
        
        Returns:
            True 如果两个动作依赖
        """
        writes1 = action1.writes
        writes2 = action2.writes
        reads1 = action1.reads
        reads2 = action2.reads
        
        # 写-写冲突
        if writes1 & writes2:
            return True
        
        # 读-写冲突（任一方向）
        if (reads1 & writes2) or (reads2 & writes1):
            return True
        
        return False
    
    def are_dependent(self, action1: Action, action2: Action) -> bool:
        """判断两个动作是否依赖"""
        return not self.are_independent(action1, action2)
    
    def get_dependent_actions(self, action: Action) -> Set[Action]:
        """
        获取与指定动作依赖的所有动作
        
        Args:
            action: 指定动作
            
        Returns:
            依赖动作集合
        """
        dependent = set()
        for other in self._actions.values():
            if other.name != action.name and self.are_dependent(action, other):
                dependent.add(other)
        return dependent
    
    def get_independent_actions(self, action: Action) -> Set[Action]:
        """
        获取与指定动作独立的所有动作
        
        Args:
            action: 指定动作
            
        Returns:
            独立动作集合
        """
        independent = set()
        for other in self._actions.values():
            if other.name != action.name and self.are_independent(action, other):
                independent.add(other)
        return independent
    
    def is_visible(self, action: Action, visible_vars: Set[str]) -> bool:
        """
        判断动作是否是"可见的"（影响要验证的属性）
        
        在 LTL\X 模型检查中，只有改变可见命题的动作才被视为可见的。
        
        Args:
            action: 动作
            visible_vars: 可见变量集合（影响LTL公式的变量）
            
        Returns:
            True 如果动作是可见的
        """
        return bool(action.writes & visible_vars)
    
    def get_process_actions(self, process_id: int) -> Set[Action]:
        """
        获取指定进程的所有动作
        
        Args:
            process_id: 进程ID
            
        Returns:
            该进程的动作集合
        """
        return {a for a in self._actions.values() if a.process_id == process_id}
    
    def get_all_processes(self) -> Set[int]:
        """获取所有进程ID"""
        return {a.process_id for a in self._actions.values()}
    
    def build_dependency_graph(self) -> Dict[str, Set[str]]:
        """
        构建依赖关系图
        
        Returns:
            依赖图：动作名 -> 依赖动作名集合
        """
        graph: Dict[str, Set[str]] = {}
        
        for name in self._actions:
            graph[name] = set()
        
        for name1, action1 in self._actions.items():
            for name2, action2 in self._actions.items():
                if name1 != name2 and self.are_dependent(action1, action2):
                    graph[name1].add(name2)
        
        return graph
    
    def print_dependency_matrix(self):
        """打印依赖关系矩阵"""
        actions = sorted(self._actions.values(), key=lambda a: (a.process_id, a.name))
        names = [a.name for a in actions]
        
        print("\n动作依赖关系矩阵 (D=依赖, I=独立, -=同一进程):")
        print(" " * 15, end="")
        for name in names:
            print(f"{name[:10]:>10}", end="")
        print()
        
        for a1 in actions:
            print(f"{a1.name:>14}", end="")
            for a2 in actions:
                if a1.name == a2.name:
                    print(f"{'-':>10}", end="")
                elif a1.process_id == a2.process_id:
                    print(f"{'=':>10}", end="")
                elif self.are_dependent(a1, a2):
                    print(f"{'D':>10}", end="")
                else:
                    print(f"{'I':>10}", end="")
            print()


def create_simple_dependency_analyzer() -> ActionDependency:
    """
    创建一个简单的依赖分析器示例
    
    两个独立计数器进程：
    - P0: 递增 count0
    - P1: 递增 count1
    
    两个动作完全独立（访问不同变量）
    """
    analyzer = ActionDependency()
    
    # 进程0的动作
    inc0 = Action("inc0", process_id=0, reads=frozenset(), writes=frozenset({"count0"}))
    
    # 进程1的动作
    inc1 = Action("inc1", process_id=1, reads=frozenset(), writes=frozenset({"count1"}))
    
    analyzer.register_actions([inc0, inc1])
    
    return analyzer


def create_shared_variable_dependency() -> ActionDependency:
    """
    创建共享变量依赖分析器示例
    
    两个进程共享一个计数器：
    - P0: 递增 shared_count
    - P1: 递增 shared_count
    
    两个动作依赖（写-写冲突）
    """
    analyzer = ActionDependency()
    
    # 进程0的动作
    inc0 = Action("inc0", process_id=0, reads=frozenset(), writes=frozenset({"shared_count"}))
    
    # 进程1的动作
    inc1 = Action("inc1", process_id=1, reads=frozenset(), writes=frozenset({"shared_count"}))
    
    analyzer.register_actions([inc0, inc1])
    
    return analyzer


if __name__ == "__main__":
    print("=" * 60)
    print("动作依赖关系分析测试")
    print("=" * 60)
    
    # 测试1：独立计数器
    print("\n【测试1：独立计数器】")
    analyzer1 = create_simple_dependency_analyzer()
    analyzer1.print_dependency_matrix()
    
    inc0 = analyzer1._actions["inc0"]
    inc1 = analyzer1._actions["inc1"]
    
    print(f"\ninc0 和 inc1 独立? {analyzer1.are_independent(inc0, inc1)}")
    
    # 测试2：共享变量
    print("\n【测试2：共享变量】")
    analyzer2 = create_shared_variable_dependency()
    analyzer2.print_dependency_matrix()
    
    inc0 = analyzer2._actions["inc0"]
    inc1 = analyzer2._actions["inc1"]
    
    print(f"\ninc0 和 inc1 独立? {analyzer2.are_independent(inc0, inc1)}")
