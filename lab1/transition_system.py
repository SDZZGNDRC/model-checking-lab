"""
实验一：Transition System (迁移系统) 实现

本模块实现了模型检查的基础数据结构 - Transition System。
设计考虑了后续实验的可扩展性，包括：
- 实验二：不变性检查（需要遍历可达状态）
- 实验三：NFA 乘积构造（需要状态同步）
- 实验四：LTL 模型检查（需要嵌套 DFS）
- 实验五：CTL 模型检查（需要 Pre 计算）
- 实验六：Bisimulation 最小化（需要分区细化）
- 实验七：偏序归约（需要 ample 集计算）
"""

from typing import Set, Dict, List, Tuple, Optional, FrozenSet, Iterator
from collections import deque
from dataclasses import dataclass, field
import os
import webbrowser

# 可视化相关导入（可选依赖）
try:
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False


@dataclass(frozen=True)
class State:
    """
    状态类 - 不可变对象，可作为字典键使用
    
    状态由名称唯一标识，可以带有原子命题标签
    """
    name: str
    labels: FrozenSet[str] = field(default_factory=frozenset)
    
    def __hash__(self) -> int:
        return hash((self.name, self.labels))
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, State):
            return False
        return self.name == other.name and self.labels == other.labels
    
    def __repr__(self) -> str:
        if self.labels:
            return f"State({self.name}, {set(self.labels)})"
        return f"State({self.name})"
    
    def has_label(self, label: str) -> bool:
        """检查状态是否带有指定原子命题标签"""
        return label in self.labels


@dataclass
class Transition:
    """
    迁移类
    
    表示从源状态到目标状态的一个迁移，可选地带有动作标签
    """
    source: State
    target: State
    action: Optional[str] = None
    
    def __repr__(self) -> str:
        if self.action:
            return f"{self.source.name} --[{self.action}]--> {self.target.name}"
        return f"{self.source.name} --> {self.target.name}"


class TransitionSystem:
    """
    迁移系统 (Transition System) 类
    
    形式化定义：TS = (S, Act, ->, I, AP, L)
    - S: 状态集合
    - Act: 动作集合
    - -> ⊆ S × Act × S: 迁移关系
    - I ⊆ S: 初始状态集合
    - AP: 原子命题集合
    - L: S → 2^AP: 标签函数
    
    使用邻接表存储迁移关系，支持高效的遍历和查询。
    """
    
    def __init__(self):
        # 所有状态集合
        self._states: Dict[str, State] = {}
        # 初始状态集合
        self._initial_states: Set[State] = set()
        # 迁移关系：状态 -> [(目标状态, 动作)]
        self._transitions: Dict[State, List[Tuple[State, Optional[str]]]] = {}
        # 反向迁移（用于 Pre 计算，实验五需要）
        self._reverse_transitions: Dict[State, List[Tuple[State, Optional[str]]]] = {}
        # 动作集合
        self._actions: Set[str] = set()
    
    # ==================== 状态管理 ====================
    
    def add_state(self, name: str, labels: Optional[Set[str]] = None) -> State:
        """
        添加新状态
        
        Args:
            name: 状态名称（唯一标识）
            labels: 原子命题标签集合
            
        Returns:
            创建的状态对象
        """
        if name in self._states:
            # 如果状态已存在，更新标签
            existing = self._states[name]
            if labels is not None:
                new_labels = frozenset(labels)
                if new_labels != existing.labels:
                    # 创建新状态对象（因为 State 是不可变的）
                    new_state = State(name, new_labels)
                    self._states[name] = new_state
                    return new_state
            return existing
        
        state = State(name, frozenset(labels) if labels else frozenset())
        self._states[name] = state
        self._transitions[state] = []
        self._reverse_transitions[state] = []
        return state
    
    def get_state(self, name: str) -> Optional[State]:
        """根据名称获取状态"""
        return self._states.get(name)
    
    def get_all_states(self) -> Set[State]:
        """获取所有状态"""
        return set(self._states.values())
    
    def add_initial_state(self, name: str) -> State:
        """添加初始状态"""
        state = self.add_state(name)
        self._initial_states.add(state)
        return state
    
    def get_initial_states(self) -> Set[State]:
        """获取所有初始状态"""
        return self._initial_states.copy()
    
    # ==================== 迁移管理 ====================
    
    def add_transition(self, source_name: str, target_name: str, action: Optional[str] = None):
        """
        添加迁移关系
        
        Args:
            source_name: 源状态名称
            target_name: 目标状态名称
            action: 动作标签（可选）
        """
        source = self.add_state(source_name)
        target = self.add_state(target_name)
        
        self._transitions[source].append((target, action))
        self._reverse_transitions[target].append((source, action))
        
        if action is not None:
            self._actions.add(action)
    
    def get_transitions(self, state: State) -> List[Tuple[State, Optional[str]]]:
        """获取从指定状态出发的所有迁移"""
        return self._transitions.get(state, [])
    
    def get_successors(self, state: State) -> Set[State]:
        """获取状态的所有后继状态"""
        return {target for target, _ in self._transitions.get(state, [])}
    
    def get_predecessors(self, state: State) -> Set[State]:
        """获取状态的所有前驱状态（用于实验五 CTL 的 Pre 计算）"""
        return {source for source, _ in self._reverse_transitions.get(state, [])}
    
    def pre(self, states: Set[State]) -> Set[State]:
        """
        前置集合计算 Pre(C) = {s ∈ S | ∃s' ∈ C, s → s'}
        
        这是 CTL 模型检查中的核心操作（实验五需要）
        """
        result: Set[State] = set()
        for state in states:
            result.update(self.get_predecessors(state))
        return result
    
    # ==================== 可达状态计算 ====================
    
    def compute_reachable_states(self, method: str = "bfs") -> Set[State]:
        """
        计算所有从初始状态可达的状态
        
        Args:
            method: "bfs" 或 "dfs"
            
        Returns:
            可达状态集合
        """
        if not self._initial_states:
            return set()
        
        if method.lower() == "bfs":
            return self._bfs_reachable()
        elif method.lower() == "dfs":
            return self._dfs_reachable()
        else:
            raise ValueError(f"Unknown method: {method}. Use 'bfs' or 'dfs'.")
    
    def _bfs_reachable(self) -> Set[State]:
        """使用 BFS 计算可达状态"""
        visited: Set[State] = set()
        queue: deque = deque(self._initial_states)
        
        for init in self._initial_states:
            visited.add(init)
        
        while queue:
            current = queue.popleft()
            for successor, _ in self._transitions.get(current, []):
                if successor not in visited:
                    visited.add(successor)
                    queue.append(successor)
        
        return visited
    
    def _dfs_reachable(self) -> Set[State]:
        """使用 DFS 计算可达状态"""
        visited: Set[State] = set()
        
        def dfs(state: State):
            visited.add(state)
            for successor, _ in self._transitions.get(state, []):
                if successor not in visited:
                    dfs(successor)
        
        for init in self._initial_states:
            if init not in visited:
                dfs(init)
        
        return visited
    
    def get_reachable_transitions(self) -> List[Transition]:
        """
        获取所有可达状态之间的迁移
        
        Returns:
            可达迁移列表
        """
        reachable = self.compute_reachable_states()
        transitions: List[Transition] = []
        
        for state in reachable:
            for target, action in self._transitions.get(state, []):
                if target in reachable:
                    transitions.append(Transition(state, target, action))
        
        return transitions
    
    # ==================== 路径生成（实验二需要）====================
    
    def find_path(self, start: State, target: State) -> Optional[List[State]]:
        """
        使用 BFS 查找从 start 到 target 的最短路径
        
        用于生成反例路径（实验二不变性检查需要）
        
        Args:
            start: 起始状态
            target: 目标状态
            
        Returns:
            路径上的状态列表，如果不可达则返回 None
        """
        if start == target:
            return [start]
        
        visited: Set[State] = {start}
        queue: deque = deque([(start, [start])])
        
        while queue:
            current, path = queue.popleft()
            
            for successor, _ in self._transitions.get(current, []):
                if successor == target:
                    return path + [successor]
                
                if successor not in visited:
                    visited.add(successor)
                    queue.append((successor, path + [successor]))
        
        return None
    
    # ==================== 统计信息 ====================
    
    def get_statistics(self) -> Dict[str, int]:
        """获取迁移系统统计信息"""
        reachable = self.compute_reachable_states()
        reachable_transitions = self.get_reachable_transitions()
        
        return {
            "total_states": len(self._states),
            "reachable_states": len(reachable),
            "initial_states": len(self._initial_states),
            "total_transitions": sum(len(t) for t in self._transitions.values()),
            "reachable_transitions": len(reachable_transitions),
            "actions": len(self._actions)
        }
    
    # ==================== 输入/输出 ====================
    
    def __repr__(self) -> str:
        stats = self.get_statistics()
        return (f"TransitionSystem("
                f"states={stats['total_states']}, "
                f"initial={stats['initial_states']}, "
                f"transitions={stats['total_transitions']})")
    
    def print_reachable_graph(self):
        """打印可达状态图"""
        reachable = self.compute_reachable_states()
        transitions = self.get_reachable_transitions()
        
        print("=" * 50)
        print("可达状态图")
        print("=" * 50)
        print(f"\n初始状态: {[s.name for s in self._initial_states]}")
        print(f"\n可达状态 ({len(reachable)} 个):")
        for state in sorted(reachable, key=lambda s: s.name):
            labels = f"  [{', '.join(sorted(state.labels))}]" if state.labels else ""
            print(f"  - {state.name}{labels}")
        
        print(f"\n迁移关系 ({len(transitions)} 个):")
        for t in transitions:
            print(f"  {t}")
        print("=" * 50)

    # ==================== 可视化方法 ====================
    
    def _get_visualizer(self):
        """获取可视化器实例（延迟导入避免循环依赖）"""
        from ts_visualizer import TSVisualizer
        return TSVisualizer(self)
    
    def visualize(self, **kwargs):
        """使用 Matplotlib 可视化"""
        viz = self._get_visualizer()
        viz.visualize_matplotlib(**kwargs)
    
    def visualize_dot(self, **kwargs) -> str:
        """生成 DOT 格式字符串"""
        viz = self._get_visualizer()
        return viz.to_dot(**kwargs)
    
    def save_dot(self, filename: str, **kwargs):
        """保存 DOT 文件"""
        viz = self._get_visualizer()
        viz.save_dot(filename, **kwargs)
    
    def render_graphviz(self, output_file: str = "ts_graph", **kwargs) -> str:
        """使用 Graphviz 渲染"""
        viz = self._get_visualizer()
        return viz.render_graphviz(output_file, **kwargs)
    
    def visualize_html(self, filename: str = "ts_visualization.html", **kwargs):
        """生成 HTML 可视化"""
        viz = self._get_visualizer()
        viz.save_html(filename, **kwargs)
    
    def open_visualization(self, filename: str = "ts_visualization.html"):
        """在浏览器中打开可视化"""
        viz = self._get_visualizer()
        viz.open_in_browser(filename)
    
    def visualize_ascii(self):
        """打印 ASCII 可视化"""
        viz = self._get_visualizer()
        viz.print_ascii()
