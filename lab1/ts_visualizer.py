"""
Transition System 可视化模块

本模块提供迁移系统的图形可视化功能，支持：
- 使用 Graphviz 生成 DOT 格式图
- 使用 matplotlib 绘制状态图
- 支持 HTML/SVG 交互式可视化
"""

from typing import Set, Dict, List, Tuple, Optional, Callable
from collections import defaultdict
import os
import tempfile
import webbrowser
from pathlib import Path

try:
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False

from transition_system import TransitionSystem, State, Transition


class TSVisualizer:
    """
    Transition System 可视化器
    
    提供多种可视化方式：
    1. Graphviz DOT 格式输出
    2. Matplotlib 静态图形
    3. NetworkX 交互式图形
    4. HTML/SVG 交互式展示
    """
    
    def __init__(self, ts: TransitionSystem):
        """
        初始化可视化器
        
        Args:
            ts: 要可视化的迁移系统
        """
        self.ts = ts
        self.reachable_states = ts.compute_reachable_states()
        self.reachable_transitions = ts.get_reachable_transitions()
    
    # ==================== Graphviz DOT 格式 ====================
    
    def to_dot(self, show_labels: bool = True, 
               highlight_states: Optional[Set[State]] = None,
               highlight_path: Optional[List[State]] = None) -> str:
        """
        生成 Graphviz DOT 格式字符串
        
        Args:
            show_labels: 是否显示状态标签
            highlight_states: 要高亮显示的状态集合
            highlight_path: 要高亮显示的路径
            
        Returns:
            DOT 格式字符串
        """
        highlight_states = highlight_states or set()
        highlight_path = highlight_path or []
        path_edges = set()
        for i in range(len(highlight_path) - 1):
            path_edges.add((highlight_path[i], highlight_path[i+1]))
        
        lines = ['digraph TransitionSystem {']
        lines.append('    rankdir=LR;')
        lines.append('    node [shape=circle, style=filled, fillcolor=lightblue];')
        lines.append('    edge [fontname="Arial", fontsize=10];')
        lines.append('')
        
        # 定义状态节点
        for state in sorted(self.reachable_states, key=lambda s: s.name):
            # 确定节点样式
            is_initial = state in self.ts.get_initial_states()
            is_highlighted = state in highlight_states
            is_on_path = state in highlight_path
            
            # 构建标签
            label = state.name
            if show_labels and state.labels:
                label += f"\\n{', '.join(sorted(state.labels))}"
            
            # 确定填充颜色
            if is_on_path:
                fillcolor = "gold"
            elif is_highlighted:
                fillcolor = "lightgreen"
            elif is_initial:
                fillcolor = "lightyellow"
            else:
                fillcolor = "lightblue"
            
            # 确定形状（初始状态用双层圆）
            shape = "doublecircle" if is_initial else "circle"
            
            lines.append(f'    "{state.name}" [label="{label}", shape={shape}, '
                        f'fillcolor={fillcolor}];')
        
        lines.append('')
        
        # 定义迁移边
        for t in self.reachable_transitions:
            source_name = t.source.name
            target_name = t.target.name
            
            # 确定边的样式
            is_on_path = (t.source, t.target) in path_edges
            color = "red" if is_on_path else "black"
            penwidth = "2.0" if is_on_path else "1.0"
            
            # 构建边的标签
            label = t.action if t.action else ""
            
            lines.append(f'    "{source_name}" -> "{target_name}" '
                        f'[label="{label}", color={color}, penwidth={penwidth}];')
        
        lines.append('}')
        return '\n'.join(lines)
    
    def save_dot(self, filename: str, **kwargs):
        """
        保存 DOT 格式到文件
        
        Args:
            filename: 输出文件名
            **kwargs: 传递给 to_dot 的参数
        """
        dot_content = self.to_dot(**kwargs)
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(dot_content)
        print(f"DOT 文件已保存: {filename}")
    
    def render_graphviz(self, output_file: str = "ts_graph", 
                        format: str = "png",
                        engine: str = "dot",
                        **kwargs) -> str:
        """
        使用 Graphviz 渲染图形
        
        需要系统安装 Graphviz
        
        Args:
            output_file: 输出文件名（不含扩展名）
            format: 输出格式 (png, svg, pdf, etc.)
            engine: 布局引擎 (dot, neato, circo, etc.)
            **kwargs: 传递给 to_dot 的参数
            
        Returns:
            生成的文件路径
        """
        # 先生成 DOT 文件
        dot_file = f"{output_file}.dot"
        self.save_dot(dot_file, **kwargs)
        
        # 调用 Graphviz 渲染
        output_path = f"{output_file}.{format}"
        cmd = f'{engine} -T{format} "{dot_file}" -o "{output_path}"'
        
        result = os.system(cmd)
        if result == 0:
            print(f"图形已渲染: {output_path}")
            return output_path
        else:
            print(f"Graphviz 渲染失败，请确保 Graphviz 已安装")
            print(f"命令: {cmd}")
            return ""
    
    # ==================== Matplotlib 可视化 ====================
    
    def visualize_matplotlib(self, figsize: Tuple[int, int] = (12, 10),
                             layout: str = "spring",
                             show_labels: bool = True,
                             highlight_states: Optional[Set[State]] = None,
                             highlight_path: Optional[List[State]] = None,
                             save_path: Optional[str] = None):
        """
        使用 Matplotlib 可视化迁移系统
        
        Args:
            figsize: 图形大小
            layout: 布局算法 ("spring", "circular", "random", "shell")
            show_labels: 是否显示状态标签
            highlight_states: 要高亮显示的状态集合
            highlight_path: 要高亮显示的路径
            save_path: 保存路径（如果为 None 则显示图形）
        """
        if not MATPLOTLIB_AVAILABLE:
            print("错误: 需要安装 matplotlib: pip install matplotlib")
            return
        
        if not NETWORKX_AVAILABLE:
            print("错误: 需要安装 networkx: pip install networkx")
            return
        
        # 创建 NetworkX 图
        G = nx.DiGraph()
        
        # 添加节点
        for state in self.reachable_states:
            G.add_node(state.name, state=state)
        
        # 添加边
        edge_labels = {}
        for t in self.reachable_transitions:
            G.add_edge(t.source.name, t.target.name)
            if t.action:
                edge_labels[(t.source.name, t.target.name)] = t.action
        
        # 计算布局
        if layout == "spring":
            pos = nx.spring_layout(G, k=2, iterations=50, seed=42)
        elif layout == "circular":
            pos = nx.circular_layout(G)
        elif layout == "random":
            pos = nx.random_layout(G, seed=42)
        elif layout == "shell":
            pos = nx.shell_layout(G)
        else:
            pos = nx.spring_layout(G, seed=42)
        
        # 创建图形
        fig, ax = plt.subplots(figsize=figsize)
        
        # 确定节点颜色
        node_colors = []
        initial_states = self.ts.get_initial_states()
        highlight_states = highlight_states or set()
        highlight_path = highlight_path or []
        path_set = set(s.name for s in highlight_path)
        
        for state in self.reachable_states:
            if state.name in path_set:
                node_colors.append('gold')
            elif state in highlight_states:
                node_colors.append('lightgreen')
            elif state in initial_states:
                node_colors.append('lightyellow')
            else:
                node_colors.append('lightblue')
        
        # 绘制节点
        nx.draw_networkx_nodes(G, pos, node_color=node_colors, 
                               node_size=2000, ax=ax, edgecolors='black')
        
        # 绘制边
        nx.draw_networkx_edges(G, pos, ax=ax, edge_color='gray',
                               arrows=True, arrowsize=20, 
                               arrowstyle='->', node_size=2000,
                               connectionstyle='arc3,rad=0.1')
        
        # 绘制节点标签
        if show_labels:
            labels = {}
            for state in self.reachable_states:
                label = state.name
                if state.labels:
                    label += f"\n{', '.join(sorted(state.labels))}"
                labels[state.name] = label
            nx.draw_networkx_labels(G, pos, labels, font_size=8, ax=ax)
        
        # 绘制边标签
        if edge_labels:
            nx.draw_networkx_edge_labels(G, pos, edge_labels, 
                                         font_size=7, ax=ax)
        
        # 添加图例
        legend_elements = [
            mpatches.Patch(color='lightyellow', label='初始状态'),
            mpatches.Patch(color='lightblue', label='普通状态'),
            mpatches.Patch(color='lightgreen', label='高亮状态'),
            mpatches.Patch(color='gold', label='路径状态'),
        ]
        ax.legend(handles=legend_elements, loc='upper left')
        
        ax.set_title('Transition System 可视化')
        ax.axis('off')
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"图形已保存: {save_path}")
        else:
            plt.show()
    
    # ==================== HTML/SVG 可视化 ====================
    
    def to_html(self, title: str = "Transition System 可视化") -> str:
        """
        生成 HTML 页面展示迁移系统
        
        使用 SVG 渲染状态图，支持简单的交互
        
        Args:
            title: 页面标题
            
        Returns:
            HTML 字符串
        """
        # 使用 DOT 格式并通过 d3-graphviz 渲染
        dot_content = self.to_dot().replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
        
        html = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <script src="https://unpkg.com/@hpcc-js/wasm@2.14.1/dist/graphviz.umd.js"></script>
    <script src="https://unpkg.com/d3-graphviz@5.1.0/build/d3-graphviz.min.js"></script>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        h1 {{
            color: #333;
        }}
        #graph {{
            background-color: white;
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 20px;
            margin-top: 20px;
            overflow: auto;
            text-align: center;
        }}
        #graph svg {{
            max-width: 100%;
            height: auto;
        }}
        .info {{
            background-color: #e3f2fd;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
        }}
        .stats {{
            display: inline-block;
            margin-right: 20px;
        }}
        .error {{
            color: red;
            padding: 20px;
            background-color: #ffebee;
            border-radius: 8px;
        }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    
    <div class="info">
        <h3>统计信息</h3>
        <div class="stats">
            <strong>可达状态数:</strong> {len(self.reachable_states)}<br>
            <strong>可达迁移数:</strong> {len(self.reachable_transitions)}<br>
            <strong>初始状态:</strong> {', '.join(s.name for s in self.ts.get_initial_states())}
        </div>
    </div>
    
    <div id="graph">
        <div id="loading">正在加载图形...</div>
    </div>
    
    <script>
        const dot = "{dot_content}";
        
        try {{
            d3.select("#graph").graphviz()
                .renderDot(dot)
                .on("end", function() {{
                    d3.select("#loading").remove();
                }});
        }} catch (error) {{
            document.getElementById('graph').innerHTML = 
                '<div class="error">渲染失败: ' + error.message + '</div>';
        }}
    </script>
</body>
</html>'''
        return html
    
    def save_html(self, filename: str = "ts_visualization.html", 
                  title: str = "Transition System 可视化"):
        """
        保存 HTML 可视化文件
        
        Args:
            filename: 输出文件名
            title: 页面标题
        """
        html = self.to_html(title)
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"HTML 文件已保存: {filename}")
    
    def open_in_browser(self, filename: str = "ts_visualization.html"):
        """
        在浏览器中打开可视化
        
        Args:
            filename: HTML 文件名
        """
        self.save_html(filename)
        abs_path = os.path.abspath(filename)
        webbrowser.open(f'file://{abs_path}')
        print(f"已在浏览器中打开: {abs_path}")
    
    # ==================== 文本可视化 ====================
    
    def visualize_ascii(self) -> str:
        """
        生成 ASCII 艺术形式的迁移系统可视化
        
        Returns:
            ASCII 艺术字符串
        """
        lines = []
        lines.append("=" * 60)
        lines.append("Transition System 结构图")
        lines.append("=" * 60)
        
        initial_states = self.ts.get_initial_states()
        
        # 状态列表
        lines.append("\n【状态列表】")
        for state in sorted(self.reachable_states, key=lambda s: s.name):
            markers = []
            if state in initial_states:
                markers.append("[初始]")
            if state.labels:
                markers.append(f"标签: {', '.join(sorted(state.labels))}")
            
            marker_str = f" ({', '.join(markers)})" if markers else ""
            lines.append(f"  ● {state.name}{marker_str}")
        
        # 迁移列表
        lines.append("\n【迁移关系】")
        for t in self.reachable_transitions:
            action_str = f" --[{t.action}]--> " if t.action else " --> "
            lines.append(f"  {t.source.name}{action_str}{t.target.name}")
        
        # 邻接表形式
        lines.append("\n【邻接表】")
        for state in sorted(self.reachable_states, key=lambda s: s.name):
            successors = self.ts.get_successors(state)
            if successors:
                succ_names = ', '.join(s.name for s in sorted(successors, key=lambda s: s.name))
                lines.append(f"  {state.name} → [{succ_names}]")
        
        lines.append("\n" + "=" * 60)
        return '\n'.join(lines)
    
    def print_ascii(self):
        """打印 ASCII 可视化"""
        print(self.visualize_ascii())


if __name__ == "__main__":
    # 测试可视化功能
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    
    from transition_system import TransitionSystem
    
    # 创建一个简单的迁移系统用于测试
    ts = TransitionSystem()
    
    # 添加状态
    ts.add_state("s0", {"start"})
    ts.add_state("s1", {"running"})
    ts.add_state("s2", {"running"})
    ts.add_state("s3", {"end"})
    
    # 设置初始状态
    ts.add_initial_state("s0")
    
    # 添加迁移
    ts.add_transition("s0", "s1", "a")
    ts.add_transition("s0", "s2", "b")
    ts.add_transition("s1", "s3", "c")
    ts.add_transition("s2", "s3", "d")
    ts.add_transition("s1", "s2", "e")
    
    # 打印 ASCII 可视化
    print("\n" + "=" * 60)
    print("ASCII 可视化")
    print("=" * 60)
    viz = TSVisualizer(ts)
    viz.print_ascii()
    
    # 打印 DOT 格式
    print("\n" + "=" * 60)
    print("DOT 格式")
    print("=" * 60)
    print(viz.to_dot())
    
    # 保存 DOT 文件
    viz.save_dot("test_ts.dot")
    
    # 保存 HTML 文件
    viz.save_html("test_ts.html")
    
    print("\n可视化测试完成!")
    print("生成的文件:")
    print("  - test_ts.dot (Graphviz DOT 格式)")
    print("  - test_ts.html (HTML 可视化)")
