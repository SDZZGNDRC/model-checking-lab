"""
Program Graph 可视化模块

本模块提供程序图的图形可视化功能，支持：
- 使用 Graphviz 生成 DOT 格式图
- 使用 matplotlib 绘制程序图
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

from program_graph import ProgramGraph, Location, Action, PGTransition


class PGVisualizer:
    """
    Program Graph 可视化器
    
    提供多种可视化方式：
    1. Graphviz DOT 格式输出
    2. Matplotlib 静态图形
    3. NetworkX 交互式图形
    4. HTML/SVG 交互式展示
    """
    
    def __init__(self, pg: ProgramGraph):
        """
        初始化可视化器
        
        Args:
            pg: 要可视化的程序图
        """
        self.pg = pg
    
    # ==================== Graphviz DOT 格式 ====================
    
    def to_dot(self, show_labels: bool = True,
               highlight_locations: Optional[Set[Location]] = None,
               highlight_path: Optional[List[Location]] = None) -> str:
        """
        生成 Graphviz DOT 格式字符串
        
        Args:
            show_labels: 是否显示位置标签
            highlight_locations: 要高亮显示的位置集合
            highlight_path: 要高亮显示的路径
            
        Returns:
            DOT 格式字符串
        """
        highlight_locations = highlight_locations or set()
        highlight_path = highlight_path or []
        path_edges = set()
        for i in range(len(highlight_path) - 1):
            path_edges.add((highlight_path[i], highlight_path[i+1]))
        
        lines = ['digraph ProgramGraph {']
        lines.append('    rankdir=TB;')
        lines.append('    node [shape=box, style=filled, fillcolor=lightblue, fontname="Arial"];')
        lines.append('    edge [fontname="Arial", fontsize=10];')
        lines.append('')
        
        # 定义位置节点
        locations = self.pg.get_locations()
        for loc in sorted(locations, key=lambda l: l.name):
            # 确定节点样式
            is_initial = loc == self.pg.get_initial_location()
            is_highlighted = loc in highlight_locations
            is_on_path = loc in highlight_path
            
            # 构建标签
            label = loc.name
            if show_labels:
                loc_labels = self.pg.get_location_labels(loc)
                if loc_labels:
                    label += f"\\n[{', '.join(sorted(loc_labels))}]"
            
            # 确定填充颜色
            if is_on_path:
                fillcolor = "gold"
            elif is_highlighted:
                fillcolor = "lightgreen"
            elif is_initial:
                fillcolor = "lightyellow"
            else:
                fillcolor = "lightblue"
            
            # 确定形状（初始位置用双层框）
            shape = "doubleoctagon" if is_initial else "box"
            
            lines.append(f'    "{loc.name}" [label="{label}", shape={shape}, '
                        f'fillcolor={fillcolor}];')
        
        lines.append('')
        
        # 定义迁移边
        for trans in self.pg.get_all_transitions():
            source_name = trans.source.name
            target_name = trans.target.name
            
            # 确定边的样式
            is_on_path = (trans.source, trans.target) in path_edges
            color = "red" if is_on_path else "black"
            penwidth = "2.0" if is_on_path else "1.0"
            
            # 构建边的标签
            label = trans.action.name if trans.action else ""
            if trans.guard and trans.guard != "True":
                label = f"[{trans.guard}] {label}" if label else f"[{trans.guard}]"
            
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
    
    def render_graphviz(self, output_file: str = "pg_graph",
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
                             highlight_locations: Optional[Set[Location]] = None,
                             highlight_path: Optional[List[Location]] = None,
                             save_path: Optional[str] = None):
        """
        使用 Matplotlib 可视化程序图
        
        Args:
            figsize: 图形大小
            layout: 布局算法 ("spring", "circular", "random", "shell")
            show_labels: 是否显示位置标签
            highlight_locations: 要高亮显示的位置集合
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
        locations = self.pg.get_locations()
        for loc in locations:
            G.add_node(loc.name, location=loc)
        
        # 添加边
        edge_labels = {}
        for trans in self.pg.get_all_transitions():
            G.add_edge(trans.source.name, trans.target.name)
            label = trans.action.name if trans.action else ""
            if trans.guard and trans.guard != "True":
                label = f"[{trans.guard}] {label}" if label else f"[{trans.guard}]"
            edge_labels[(trans.source.name, trans.target.name)] = label
        
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
        initial_location = self.pg.get_initial_location()
        highlight_locations = highlight_locations or set()
        highlight_path = highlight_path or []
        path_set = set(loc.name for loc in highlight_path)
        
        for loc in locations:
            if loc.name in path_set:
                node_colors.append('gold')
            elif loc in highlight_locations:
                node_colors.append('lightgreen')
            elif loc == initial_location:
                node_colors.append('lightyellow')
            else:
                node_colors.append('lightblue')
        
        # 绘制节点
        nx.draw_networkx_nodes(G, pos, node_color=node_colors,
                               node_size=3000, ax=ax, edgecolors='black',
                               node_shape='s')
        
        # 绘制边
        nx.draw_networkx_edges(G, pos, ax=ax, edge_color='gray',
                               arrows=True, arrowsize=20,
                               arrowstyle='->', node_size=3000,
                               connectionstyle='arc3,rad=0.1')
        
        # 绘制节点标签
        if show_labels:
            labels = {}
            for loc in locations:
                label = loc.name
                loc_labels = self.pg.get_location_labels(loc)
                if loc_labels:
                    label += f"\n[{', '.join(sorted(loc_labels))}]"
                labels[loc.name] = label
            nx.draw_networkx_labels(G, pos, labels, font_size=8, ax=ax)
        
        # 绘制边标签
        if edge_labels:
            nx.draw_networkx_edge_labels(G, pos, edge_labels,
                                         font_size=7, ax=ax)
        
        # 添加图例
        legend_elements = [
            mpatches.Patch(color='lightyellow', label='初始位置'),
            mpatches.Patch(color='lightblue', label='普通位置'),
            mpatches.Patch(color='lightgreen', label='高亮位置'),
            mpatches.Patch(color='gold', label='路径位置'),
        ]
        ax.legend(handles=legend_elements, loc='upper left')
        
        ax.set_title(f'Program Graph 可视化: {self.pg.name}')
        ax.axis('off')
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"图形已保存: {save_path}")
        else:
            plt.show()
    
    # ==================== HTML/SVG 可视化 ====================
    
    def to_html(self, title: str = "Program Graph 可视化") -> str:
        """
        生成 HTML 页面展示程序图
        
        使用 SVG 渲染程序图，支持简单的交互
        
        Args:
            title: 页面标题
            
        Returns:
            HTML 字符串
        """
        # 使用 DOT 格式并通过 d3-graphviz 渲染
        dot_content = self.to_dot().replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
        
        # 获取统计信息
        locations = self.pg.get_locations()
        transitions = self.pg.get_all_transitions()
        initial_loc = self.pg.get_initial_location()
        variables = self.pg.get_variables()
        shared_vars = self.pg.get_shared_variables()
        
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
            margin-bottom: 10px;
        }}
        .error {{
            color: red;
            padding: 20px;
            background-color: #ffebee;
            border-radius: 8px;
        }}
        .section {{
            background-color: white;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 15px;
            border: 1px solid #ddd;
        }}
        .variable-list {{
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
        }}
        .variable-item {{
            background-color: #f0f0f0;
            padding: 5px 10px;
            border-radius: 4px;
            font-family: monospace;
        }}
        .shared {{
            background-color: #fff3e0;
            border: 1px solid #ff9800;
        }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    
    <div class="info">
        <h3>统计信息</h3>
        <div class="stats">
            <strong>程序图名称:</strong> {self.pg.name}<br>
            <strong>位置数:</strong> {len(locations)}<br>
            <strong>迁移数:</strong> {len(transitions)}<br>
            <strong>初始位置:</strong> {initial_loc.name if initial_loc else "None"}
        </div>
        <div class="stats">
            <strong>变量数:</strong> {len(variables)}<br>
            <strong>共享变量:</strong> {', '.join(shared_vars) if shared_vars else "None"}
        </div>
    </div>
    
    <div class="section">
        <h3>变量声明</h3>
        <div class="variable-list">
            {''.join(f'<div class="variable-item{" shared" if var in shared_vars else ""}">{var}: {list(domain)} = {self.pg.get_initial_values().get(var, "?")}</div>' for var, domain in variables.items())}
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
    
    def save_html(self, filename: str = "pg_visualization.html",
                  title: str = "Program Graph 可视化"):
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
    
    def open_in_browser(self, filename: str = "pg_visualization.html"):
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
        生成 ASCII 艺术形式的程序图可视化
        
        Returns:
            ASCII 艺术字符串
        """
        lines = []
        lines.append("=" * 60)
        lines.append(f"Program Graph 结构图: {self.pg.name}")
        lines.append("=" * 60)
        
        initial_location = self.pg.get_initial_location()
        locations = self.pg.get_locations()
        transitions = self.pg.get_all_transitions()
        variables = self.pg.get_variables()
        shared_vars = self.pg.get_shared_variables()
        
        # 变量信息
        lines.append("\n【变量声明】")
        if variables:
            for var_name, domain in sorted(variables.items()):
                shared_mark = " [共享]" if var_name in shared_vars else ""
                init_val = self.pg.get_initial_values().get(var_name, "?")
                lines.append(f"  {var_name}: {sorted(domain)} = {init_val}{shared_mark}")
        else:
            lines.append("  (无变量)")
        
        # 位置列表
        lines.append("\n【位置列表】")
        for loc in sorted(locations, key=lambda l: l.name):
            markers = []
            if loc == initial_location:
                markers.append("[初始]")
            loc_labels = self.pg.get_location_labels(loc)
            if loc_labels:
                markers.append(f"标签: {', '.join(sorted(loc_labels))}")
            
            marker_str = f" ({', '.join(markers)})" if markers else ""
            lines.append(f"  □ {loc.name}{marker_str}")
        
        # 迁移列表
        lines.append("\n【迁移关系】")
        for trans in sorted(transitions, key=lambda t: (t.source.name, t.target.name)):
            guard_str = f"[{trans.guard}] " if trans.guard and trans.guard != "True" else ""
            action_str = trans.action.name if trans.action else "ε"
            lines.append(f"  {trans.source.name} --{guard_str}{action_str}--> {trans.target.name}")
        
        # 邻接表形式
        lines.append("\n【邻接表】")
        for loc in sorted(locations, key=lambda l: l.name):
            outgoing = self.pg.get_transitions(loc)
            if outgoing:
                targets = ', '.join(f"{t.target.name}({t.action.name if t.action else 'ε'})" 
                                   for t in sorted(outgoing, key=lambda t: t.target.name))
                lines.append(f"  {loc.name} → [{targets}]")
        
        lines.append("\n" + "=" * 60)
        return '\n'.join(lines)
    
    def print_ascii(self):
        """打印 ASCII 可视化"""
        print(self.visualize_ascii())


if __name__ == "__main__":
    # 测试可视化功能
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    
    # 创建一个简单的程序图用于测试
    pg = ProgramGraph("TestPG")
    
    # 声明变量
    pg.declare_variable("x", {0, 1, 2}, 0)
    pg.declare_variable("y", {True, False}, True, is_shared=True)
    
    # 添加位置
    pg.add_location("start", {"init"})
    pg.add_location("process")
    pg.add_location("check")
    pg.add_location("end", {"done"})
    
    # 设置初始位置
    pg.set_initial_location("start")
    
    # 添加迁移
    action1 = Action("init_x", {"x": "0"})
    action2 = Action("inc_x", {"x": "x + 1"})
    action3 = Action("check_y", {}, guard="y")
    action4 = Action("finish")
    
    pg.add_transition("start", "process", action1)
    pg.add_transition("process", "check", action2)
    pg.add_transition("check", "process", action3, guard="x < 2")
    pg.add_transition("check", "end", action4, guard="x >= 2")
    
    # 打印 ASCII 可视化
    print("\n" + "=" * 60)
    print("ASCII 可视化")
    print("=" * 60)
    viz = PGVisualizer(pg)
    viz.print_ascii()
    
    # 打印 DOT 格式
    print("\n" + "=" * 60)
    print("DOT 格式")
    print("=" * 60)
    print(viz.to_dot())
    
    # 保存 DOT 文件
    viz.save_dot("test_pg.dot")
    
    # 保存 HTML 文件
    viz.save_html("test_pg.html")
    
    print("\n可视化测试完成!")
    print("生成的文件:")
    print("  - test_pg.dot (Graphviz DOT 格式)")
    print("  - test_pg.html (HTML 可视化)")
