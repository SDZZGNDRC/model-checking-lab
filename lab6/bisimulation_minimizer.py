"""
实验六：Bisimulation 最小化

本模块实现基于分区细化算法的 Bisimulation 最小化：
- 初始分区：按原子命题标签划分状态
- 迭代细化：根据迁移关系分裂不一致的块
- Paige-Tarjan 算法优化实现
- 最小化 TS 的构造
- 分区可视化

Bisimulation 等价保持 CTL* 性质，最小化后的 TS 可用于高效模型检查。
"""

import sys
import os
sys.path.insert(0, __file__.rsplit('\\', 1)[0] + '\\..\\lab1')
sys.path.insert(0, __file__.rsplit('\\', 1)[0] + '\\..\\lab5')

from typing import Set, Dict, List, Tuple, Optional, FrozenSet
from collections import deque
from dataclasses import dataclass, field

from transition_system import TransitionSystem, State


@dataclass
class Block:
    """
    分区中的块（Block）
    
    一个块包含一组互相 Bisimilar 的状态。
    """
    id: int
    states: Set[State] = field(default_factory=set)
    
    def __hash__(self) -> int:
        return hash(self.id)
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Block):
            return False
        return self.id == other.id
    
    def __repr__(self) -> str:
        state_names = sorted(s.name for s in self.states)
        return f"Block({self.id}, states={state_names})"


@dataclass
class MinimizationResult:
    """
    Bisimulation 最小化结果
    
    Attributes:
        original_ts: 原始迁移系统
        minimized_ts: 最小化后的迁移系统
        partition: 最终的 Bisimulation 分区
        block_map: 状态到块的映射
        original_state_count: 原始状态数
        minimized_state_count: 最小化后状态数
        reduction_ratio: 状态缩减比例
        iterations: 分区细化迭代次数
    """
    original_ts: TransitionSystem
    minimized_ts: TransitionSystem
    partition: Set[Block]
    block_map: Dict[State, Block]
    original_state_count: int
    minimized_state_count: int
    reduction_ratio: float
    iterations: int
    
    def __repr__(self) -> str:
        return (f"MinimizationResult("
                f"original={self.original_state_count}, "
                f"minimized={self.minimized_state_count}, "
                f"reduction={self.reduction_ratio:.1%}, "
                f"iterations={self.iterations})")


class BisimulationMinimizer:
    """
    Bisimulation 最小化器
    
    使用分区细化算法计算迁移系统的 Bisimulation 商系统。
    """
    
    def __init__(self, ts: TransitionSystem):
        """
        初始化最小化器
        
        Args:
            ts: 要最小化的 Transition System
        """
        self.ts = ts
        self.iteration_count = 0
        
        # 获取所有可达状态
        self.reachable_states = ts.compute_reachable_states()
        
        # 状态到后继块的缓存
        self._successor_blocks_cache: Dict[State, Set[int]] = {}
    
    def minimize(self) -> MinimizationResult:
        """
        执行 Bisimulation 最小化
        
        Returns:
            MinimizationResult 对象
        """
        self.iteration_count = 0
        
        # 步骤 1: 创建初始分区（按原子命题标签划分）
        partition = self._create_initial_partition()
        
        # 步骤 2: 迭代细化分区
        final_partition = self._refine_partition(partition)
        
        # 步骤 3: 构建状态到块的映射
        block_map = self._build_block_map(final_partition)
        
        # 步骤 4: 构造最小化 TS
        minimized_ts = self._build_minimized_ts(final_partition, block_map)
        
        # 计算缩减比例
        original_count = len(self.reachable_states)
        minimized_count = len(final_partition)
        reduction_ratio = 1.0 - (minimized_count / original_count) if original_count > 0 else 0.0
        
        return MinimizationResult(
            original_ts=self.ts,
            minimized_ts=minimized_ts,
            partition=final_partition,
            block_map=block_map,
            original_state_count=original_count,
            minimized_state_count=minimized_count,
            reduction_ratio=reduction_ratio,
            iterations=self.iteration_count
        )
    
    def _create_initial_partition(self) -> Set[Block]:
        """
        创建初始分区
        
        按原子命题标签对状态进行划分，具有相同标签的状态属于同一块。
        
        Returns:
            初始分区（块的集合）
        """
        # 按标签分组状态
        label_groups: Dict[FrozenSet[str], Set[State]] = {}
        
        for state in self.reachable_states:
            labels = state.labels
            if labels not in label_groups:
                label_groups[labels] = set()
            label_groups[labels].add(state)
        
        # 为每个组创建一个块
        partition: Set[Block] = set()
        block_id = 0
        
        for labels, states in label_groups.items():
            block = Block(id=block_id, states=states)
            partition.add(block)
            block_id += 1
        
        return partition
    
    def _refine_partition(self, initial_partition: Set[Block]) -> Set[Block]:
        """
        迭代细化分区
        
        使用 Paige-Tarjan 算法的简化版本：
        - 只要存在需要分裂的块，就继续细化
        - 一个块需要分裂，如果其中的状态在迁移到某个块的能力上不一致
        
        Args:
            initial_partition: 初始分区
            
        Returns:
            细化后的最终分区
        """
        partition = initial_partition.copy()
        
        # 构建状态到块的映射
        state_to_block: Dict[State, Block] = {}
        for block in partition:
            for state in block.states:
                state_to_block[state] = block
        
        # 迭代细化
        max_iterations = len(self.reachable_states) * 2
        changed = True
        
        while changed and self.iteration_count < max_iterations:
            changed = False
            self.iteration_count += 1
            
            new_partition: Set[Block] = set()
            
            for block in partition:
                # 尝试分裂这个块
                subblocks = self._split_block(block, state_to_block)
                
                if len(subblocks) > 1:
                    # 块被分裂了
                    changed = True
                    for subblock in subblocks:
                        new_partition.add(subblock)
                        # 更新状态到块的映射
                        for state in subblock.states:
                            state_to_block[state] = subblock
                else:
                    # 块没有被分裂
                    new_partition.add(block)
            
            partition = new_partition
        
        return partition
    
    def _split_block(self, block: Block, 
                     state_to_block: Dict[State, Block]) -> List[Block]:
        """
        尝试分裂一个块
        
        根据状态的后继块分布来分裂块。
        如果块中的状态有不同的后继块分布，则需要分裂。
        
        Args:
            block: 要分裂的块
            state_to_block: 状态到块的映射
            
        Returns:
            分裂后的子块列表（如果没有分裂则返回原块）
        """
        if len(block.states) <= 1:
            return [block]
        
        # 按后继块分布对状态分组
        # 两个状态属于同一组，当且仅当它们有相同的后继块集合
        groups: Dict[FrozenSet[int], Set[State]] = {}
        
        for state in block.states:
            # 获取状态的所有后继块 ID
            successor_blocks = self._get_successor_blocks(state, state_to_block)
            key = frozenset(successor_blocks)
            
            if key not in groups:
                groups[key] = set()
            groups[key].add(state)
        
        # 如果只有一个组，不需要分裂
        if len(groups) == 1:
            return [block]
        
        # 为每个组创建一个新块
        subblocks: List[Block] = []
        for i, (key, states) in enumerate(groups.items()):
            new_block = Block(id=block.id * 1000 + i, states=states)
            subblocks.append(new_block)
        
        return subblocks
    
    def _get_successor_blocks(self, state: State, 
                              state_to_block: Dict[State, Block]) -> Set[int]:
        """
        获取状态的后继块 ID 集合
        
        Args:
            state: 状态
            state_to_block: 状态到块的映射
            
        Returns:
            后继块 ID 集合
        """
        if state in self._successor_blocks_cache:
            return self._successor_blocks_cache[state]
        
        successors = self.ts.get_successors(state)
        successor_blocks = set()
        
        for succ in successors:
            if succ in state_to_block:
                successor_blocks.add(state_to_block[succ].id)
        
        self._successor_blocks_cache[state] = successor_blocks
        return successor_blocks
    
    def _build_block_map(self, partition: Set[Block]) -> Dict[State, Block]:
        """
        构建状态到块的映射
        
        Args:
            partition: 分区
            
        Returns:
            状态到块的映射字典
        """
        block_map: Dict[State, Block] = {}
        for block in partition:
            for state in block.states:
                block_map[state] = block
        return block_map
    
    def _build_minimized_ts(self, partition: Set[Block], 
                           block_map: Dict[State, Block]) -> TransitionSystem:
        """
        构造最小化后的迁移系统
        
        每个块成为新 TS 中的一个状态，块之间的迁移关系由原 TS 决定。
        
        Args:
            partition: 最终分区
            block_map: 状态到块的映射
            
        Returns:
            最小化后的 Transition System
        """
        minimized_ts = TransitionSystem()
        
        # 为每个块创建一个状态
        block_to_new_state: Dict[int, str] = {}
        
        for block in partition:
            # 使用块中第一个状态的标签作为新状态的标签
            # 同一 Bisimulation 类的状态具有相同的标签
            representative = next(iter(block.states))
            labels = set(representative.labels)
            
            # 状态名称：block_X
            state_name = f"block_{block.id}"
            block_to_new_state[block.id] = state_name
            
            minimized_ts.add_state(state_name, labels)
        
        # 设置初始状态
        # 如果原 TS 的某个初始状态属于某个块，则该块是最小化 TS 的初始状态
        original_initial = self.ts.get_initial_states()
        for init_state in original_initial:
            if init_state in block_map:
                block = block_map[init_state]
                minimized_ts.add_initial_state(block_to_new_state[block.id])
        
        # 添加迁移关系
        # 如果原 TS 中有从块 A 的某个状态到块 B 的某个状态的迁移
        # 则在最小化 TS 中添加从 block_A 到 block_B 的迁移
        added_transitions: Set[Tuple[int, int]] = set()
        
        for block in partition:
            for state in block.states:
                successors = self.ts.get_successors(state)
                for succ in successors:
                    if succ in block_map:
                        succ_block = block_map[succ]
                        transition_key = (block.id, succ_block.id)
                        
                        if transition_key not in added_transitions:
                            source_name = block_to_new_state[block.id]
                            target_name = block_to_new_state[succ_block.id]
                            minimized_ts.add_transition(source_name, target_name)
                            added_transitions.add(transition_key)
        
        return minimized_ts
    
    def compute_bisimulation_classes(self) -> Dict[int, Set[State]]:
        """
        计算 Bisimulation 等价类
        
        Returns:
            等价类 ID 到状态集合的映射
        """
        result = self.minimize()
        classes: Dict[int, Set[State]] = {}
        
        for block in result.partition:
            classes[block.id] = block.states
        
        return classes
    
    def visualize_partition(self, output_path: Optional[str] = None) -> str:
        """
        可视化当前分区（用不同颜色标记等价类）
        
        Args:
            output_path: 输出文件路径（可选，默认生成临时文件）
            
        Returns:
            生成的HTML文件路径
        """
        from ts_visualizer import TSVisualizer
        
        # 先执行最小化获取分区
        result = self.minimize()
        
        # 为每个块分配颜色
        colors = [
            "#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7",
            "#DDA0DD", "#98D8C8", "#F7DC6F", "#BB8FCE", "#85C1E9",
            "#F8B500", "#6C5CE7", "#A29BFE", "#FD79A8", "#FDCB6E"
        ]
        
        block_colors = {}
        for i, block in enumerate(sorted(result.partition, key=lambda b: b.id)):
            block_colors[block.id] = colors[i % len(colors)]
        
        # 构建DOT，用颜色标记等价类
        dot_lines = ['digraph Partition {', '  rankdir=TB;']
        dot_lines.append('  label="Bisimulation 分区（颜色标记等价类）";')
        dot_lines.append('  labelloc="t";')
        dot_lines.append('  node [shape=ellipse, style=filled, fontname="Arial"];')
        
        # 添加状态节点（带颜色）
        for state in self.reachable_states:
            block = result.block_map.get(state)
            if block:
                color = block_colors.get(block.id, "#CCCCCC")
                labels_str = "\\n".join(sorted(state.labels)) if state.labels else ""
                label = f"{state.name}\\n{labels_str}" if state.labels else state.name
                dot_lines.append(f'  "{state.name}" [fillcolor="{color}", label="{label}"];')
        
        # 添加迁移边
        for state in self.reachable_states:
            for succ in self.ts.get_successors(state):
                if succ in self.reachable_states:
                    dot_lines.append(f'  "{state.name}" -> "{succ.name}";')
        
        dot_lines.append('}')
        dot_content = "\\n".join(dot_lines)
        
        # 确定输出路径
        if output_path is None:
            output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                      'output', 'visualization')
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, "bisimulation_partition.html")
        
        # 保存DOT文件
        dot_path = output_path.replace('.html', '.dot')
        with open(dot_path, 'w', encoding='utf-8') as f:
            f.write(dot_content)
        
        # 生成HTML
        html_content = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Bisimulation 分区</title>
    <script src="https://unpkg.com/viz.js@2.1.0-pre.1/viz.js"></script>
    <script src="https://unpkg.com/viz.js@2.1.0-pre.1/full.render.js"></script>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #333; }}
        #graph {{ border: 1px solid #ddd; padding: 10px; }}
        .legend {{ margin-top: 20px; padding: 10px; background: #f5f5f5; border-radius: 5px; }}
        .legend-item {{ display: inline-block; margin: 5px 10px; padding: 5px; background: white; border-radius: 3px; }}
        .color-box {{ display: inline-block; width: 20px; height: 20px; margin-right: 5px; vertical-align: middle; border-radius: 3px; }}
        .stats {{ margin: 20px 0; padding: 15px; background: #e8f4f8; border-radius: 5px; }}
    </style>
</head>
<body>
    <h1>Bisimulation 分区可视化</h1>
    <div class="stats">
        <strong>统计信息:</strong><br>
        原始状态数: {result.original_state_count}<br>
        等价类数: {result.minimized_state_count}<br>
        缩减比例: {result.reduction_ratio:.1%}<br>
        迭代次数: {result.iterations}
    </div>
    <div id="graph"></div>
    <div class="legend">
        <h3>等价类（颜色标记）:</h3>
        {''.join(f'<div class="legend-item"><span class="color-box" style="background-color: {block_colors.get(block.id, "#CCCCCC")};"></span>Block {block.id}: {", ".join(sorted(s.name for s in block.states))}</div><br>' for block in sorted(result.partition, key=lambda b: b.id))}
    </div>
    <script>
        const dot = `{dot_content}`;
        const viz = new Viz();
        viz.renderSVGElement(dot).then(function(element) {{
            document.getElementById('graph').appendChild(element);
        }}).catch(function(error) {{
            console.error(error);
            document.getElementById('graph').innerHTML = '<p style="color: red;">渲染失败: ' + error + '</p>';
        }});
    </script>
</body>
</html>'''
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return output_path


def minimize_transition_system(ts: TransitionSystem) -> MinimizationResult:
    """
    便捷函数：最小化迁移系统
    
    Args:
        ts: 要最小化的 Transition System
        
    Returns:
        MinimizationResult 对象
        
    Examples:
        >>> from transition_system import TransitionSystem
        >>> ts = TransitionSystem()
        >>> # ... 构建 TS ...
        >>> result = minimize_transition_system(ts)
        >>> print(f"状态数: {result.original_state_count} -> {result.minimized_state_count}")
        >>> print(f"缩减比例: {result.reduction_ratio:.1%}")
    """
    minimizer = BisimulationMinimizer(ts)
    return minimizer.minimize()


def check_bisimulation_equivalence(ts1: TransitionSystem, 
                                   ts2: TransitionSystem) -> bool:
    """
    检查两个迁移系统是否 Bisimulation 等价
    
    通过比较它们的最小化形式来判断。
    
    Args:
        ts1: 第一个 Transition System
        ts2: 第二个 Transition System
        
    Returns:
        如果两个 TS 是 Bisimulation 等价的，返回 True
    """
    result1 = minimize_transition_system(ts1)
    result2 = minimize_transition_system(ts2)
    
    # 比较最小化后的 TS
    # 简化比较：状态数和迁移数
    stats1 = result1.minimized_ts.get_statistics()
    stats2 = result2.minimized_ts.get_statistics()
    
    if stats1['reachable_states'] != stats2['reachable_states']:
        return False
    
    if stats1['reachable_transitions'] != stats2['reachable_transitions']:
        return False
    
    # TODO: 更严格的同构检查
    return True
