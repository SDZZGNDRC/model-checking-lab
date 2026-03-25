"""
实验七：偏序归约状态空间可视化 (POR Visualizer)

本模块提供偏序归约前后状态空间的对比可视化功能：
- 原始状态空间（完整展开）可视化
- 偏序归约后状态空间可视化
- 两者对比的 HTML 页面
- 支持 DOT 格式导出
"""

import sys
import os
sys.path.insert(0, __file__.rsplit('\\', 1)[0] + '\\..\\lab1')

from typing import Optional, Set

from transition_system import TransitionSystem
from program_graph import ProgramGraph
from action_dependency import ActionDependency
from por_transition_system import PORTransitionSystemBuilder, PORStatistics


# 默认输出目录
DEFAULT_OUTPUT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'output', 'visualization'
)


def _ts_to_dot(ts: TransitionSystem, title: str = "Transition System",
               highlight_color: str = "lightblue") -> str:
    """
    将迁移系统转换为 Graphviz DOT 格式字符串

    Args:
        ts: 迁移系统
        title: 图形标题
        highlight_color: 非初始状态的填充颜色

    Returns:
        DOT 格式字符串
    """
    reachable_states = ts.compute_reachable_states()
    reachable_transitions = ts.get_reachable_transitions()
    initial_states = ts.get_initial_states()

    lines = [f'digraph "{title}" {{']
    lines.append('    rankdir=LR;')
    lines.append(f'    label="{title}";')
    lines.append('    labelloc="t";')
    lines.append(f'    node [shape=circle, style=filled, fillcolor={highlight_color}, fontname="Arial", fontsize=10];')
    lines.append('    edge [fontname="Arial", fontsize=9];')
    lines.append('')

    # 添加状态节点
    for state in sorted(reachable_states, key=lambda s: s.name):
        is_initial = state in initial_states
        shape = "doublecircle" if is_initial else "circle"
        fillcolor = "lightyellow" if is_initial else highlight_color

        label = state.name
        if state.labels:
            label += "\\n" + ", ".join(sorted(state.labels))

        lines.append(f'    "{state.name}" [label="{label}", shape={shape}, fillcolor={fillcolor}];')

    lines.append('')

    # 添加迁移边
    for t in reachable_transitions:
        action_label = t.action if t.action else ""
        lines.append(f'    "{t.source.name}" -> "{t.target.name}" [label="{action_label}"];')

    lines.append('}')
    return '\n'.join(lines)


def visualize_ts(ts: TransitionSystem, name: str,
                 output_dir: Optional[str] = None) -> str:
    """
    可视化单个迁移系统，生成 DOT 和 HTML 文件

    Args:
        ts: 迁移系统
        name: 输出文件名前缀（不含扩展名）
        output_dir: 输出目录（默认使用项目 output/visualization）

    Returns:
        HTML 文件路径
    """
    if output_dir is None:
        output_dir = DEFAULT_OUTPUT_DIR
    os.makedirs(output_dir, exist_ok=True)

    dot_path = os.path.join(output_dir, f"{name}.dot")
    html_path = os.path.join(output_dir, f"{name}.html")

    dot_content = _ts_to_dot(ts, title=name)

    # 保存 DOT 文件
    with open(dot_path, 'w', encoding='utf-8') as f:
        f.write(dot_content)
    print(f"DOT 文件已保存: {dot_path}")

    # 生成 HTML
    reachable_states = ts.compute_reachable_states()
    reachable_transitions = ts.get_reachable_transitions()
    initial_states = ts.get_initial_states()

    html = _generate_single_html(
        title=name,
        dot_content=dot_content,
        states_count=len(reachable_states),
        transitions_count=len(reachable_transitions),
        initial_states=', '.join(s.name for s in initial_states)
    )

    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"HTML 文件已保存: {html_path}")

    return html_path


def visualize_por_comparison(pg: ProgramGraph,
                              dependency_analyzer: ActionDependency,
                              visible_vars: Optional[Set[str]] = None,
                              name: str = "lab7_por",
                              output_dir: Optional[str] = None) -> str:
    """
    对比可视化原始状态空间和偏序归约后的状态空间

    Args:
        pg: 程序图
        dependency_analyzer: 动作依赖分析器
        visible_vars: 可见变量集合（用于 A2 条件）
        name: 输出文件名前缀
        output_dir: 输出目录

    Returns:
        对比 HTML 文件路径
    """
    if output_dir is None:
        output_dir = DEFAULT_OUTPUT_DIR
    os.makedirs(output_dir, exist_ok=True)

    # 构建原始和归约后的迁移系统
    builder = PORTransitionSystemBuilder()
    full_ts, reduced_ts, stats = builder.compare_with_full_exploration(
        pg, dependency_analyzer, visible_vars
    )

    # 分别生成 DOT 字符串
    full_dot = _ts_to_dot(full_ts, title="原始状态空间（完整展开）",
                          highlight_color="lightblue")
    reduced_dot = _ts_to_dot(reduced_ts, title="偏序归约后状态空间",
                              highlight_color="lightgreen")

    # 保存独立的 DOT 文件
    full_dot_path = os.path.join(output_dir, f"{name}_full.dot")
    reduced_dot_path = os.path.join(output_dir, f"{name}_reduced.dot")

    with open(full_dot_path, 'w', encoding='utf-8') as f:
        f.write(full_dot)
    print(f"原始 DOT 已保存: {full_dot_path}")

    with open(reduced_dot_path, 'w', encoding='utf-8') as f:
        f.write(reduced_dot)
    print(f"归约 DOT 已保存: {reduced_dot_path}")

    # 保存独立 HTML 文件
    full_html_path = os.path.join(output_dir, f"{name}_full.html")
    reduced_html_path = os.path.join(output_dir, f"{name}_reduced.html")

    full_states = full_ts.compute_reachable_states()
    full_transitions = full_ts.get_reachable_transitions()
    full_initial = full_ts.get_initial_states()

    reduced_states = reduced_ts.compute_reachable_states()
    reduced_transitions = reduced_ts.get_reachable_transitions()
    reduced_initial = reduced_ts.get_initial_states()

    with open(full_html_path, 'w', encoding='utf-8') as f:
        f.write(_generate_single_html(
            title=f"{name} - 原始状态空间（完整展开）",
            dot_content=full_dot,
            states_count=len(full_states),
            transitions_count=len(full_transitions),
            initial_states=', '.join(s.name for s in full_initial)
        ))
    print(f"原始 HTML 已保存: {full_html_path}")

    with open(reduced_html_path, 'w', encoding='utf-8') as f:
        f.write(_generate_single_html(
            title=f"{name} - 偏序归约后状态空间",
            dot_content=reduced_dot,
            states_count=len(reduced_states),
            transitions_count=len(reduced_transitions),
            initial_states=', '.join(s.name for s in reduced_initial)
        ))
    print(f"归约 HTML 已保存: {reduced_html_path}")

    # 生成对比 HTML
    comparison_html_path = os.path.join(output_dir, f"{name}_comparison.html")
    comparison_html = _generate_comparison_html(
        name=name,
        full_dot=full_dot,
        reduced_dot=reduced_dot,
        stats=stats,
        full_states=len(full_states),
        full_transitions=len(full_transitions),
        reduced_states=len(reduced_states),
        reduced_transitions=len(reduced_transitions)
    )

    with open(comparison_html_path, 'w', encoding='utf-8') as f:
        f.write(comparison_html)
    print(f"对比 HTML 已保存: {comparison_html_path}")

    return comparison_html_path


def _generate_single_html(title: str, dot_content: str,
                           states_count: int, transitions_count: int,
                           initial_states: str) -> str:
    """生成单个迁移系统的 HTML 可视化页面"""
    dot_escaped = dot_content.replace('\\', '\\\\').replace('`', '\\`').replace('$', '\\$')

    return f'''<!DOCTYPE html>
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
        h1 {{ color: #333; }}
        .stats {{
            background-color: #e3f2fd;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
        }}
        .stats span {{
            display: inline-block;
            margin-right: 30px;
            font-size: 14px;
        }}
        #graph {{
            background-color: white;
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 20px;
            overflow: auto;
            text-align: center;
        }}
        #graph svg {{
            max-width: 100%;
            height: auto;
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
    <div class="stats">
        <span><strong>可达状态数：</strong>{states_count}</span>
        <span><strong>可达迁移数：</strong>{transitions_count}</span>
        <span><strong>初始状态：</strong>{initial_states}</span>
    </div>
    <div id="graph">
        <div id="loading">正在加载图形...</div>
    </div>
    <script>
        const dot = `{dot_escaped}`;
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


def _generate_comparison_html(name: str, full_dot: str, reduced_dot: str,
                               stats: PORStatistics,
                               full_states: int, full_transitions: int,
                               reduced_states: int, reduced_transitions: int) -> str:
    """生成原始 vs 归约对比的 HTML 页面"""
    full_dot_escaped = full_dot.replace('\\', '\\\\').replace('`', '\\`').replace('$', '\\$')
    reduced_dot_escaped = reduced_dot.replace('\\', '\\\\').replace('`', '\\`').replace('$', '\\$')

    state_reduction = stats.state_reduction_rate
    trans_reduction = stats.transition_reduction_rate

    return f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>偏序归约对比 - {name}</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <script src="https://unpkg.com/@hpcc-js/wasm@2.14.1/dist/graphviz.umd.js"></script>
    <script src="https://unpkg.com/d3-graphviz@5.1.0/build/d3-graphviz.min.js"></script>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        h1 {{ color: #2c3e50; text-align: center; }}
        .summary {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 25px;
            text-align: center;
        }}
        .summary h2 {{ margin: 0 0 15px 0; font-size: 18px; }}
        .metrics {{
            display: flex;
            justify-content: center;
            gap: 30px;
            flex-wrap: wrap;
        }}
        .metric {{
            background: rgba(255,255,255,0.2);
            padding: 12px 20px;
            border-radius: 8px;
            text-align: center;
        }}
        .metric .value {{
            font-size: 28px;
            font-weight: bold;
        }}
        .metric .label {{
            font-size: 12px;
            opacity: 0.9;
        }}
        .comparison {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }}
        .panel {{
            background: white;
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 15px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .panel-full {{ border-top: 4px solid #3498db; }}
        .panel-reduced {{ border-top: 4px solid #2ecc71; }}
        .panel h2 {{
            margin: 0 0 10px 0;
            font-size: 16px;
            color: #333;
        }}
        .panel-stats {{
            display: flex;
            gap: 20px;
            margin-bottom: 12px;
            font-size: 13px;
        }}
        .panel-stats span {{
            background: #f8f9fa;
            padding: 4px 10px;
            border-radius: 4px;
        }}
        .graph-container {{
            border: 1px solid #eee;
            border-radius: 4px;
            padding: 10px;
            min-height: 200px;
            overflow: auto;
            text-align: center;
        }}
        .graph-container svg {{
            max-width: 100%;
            height: auto;
        }}
        @media (max-width: 900px) {{
            .comparison {{ grid-template-columns: 1fr; }}
        }}
    </style>
</head>
<body>
    <h1>偏序归约（POR）状态空间对比</h1>

    <div class="summary">
        <h2>归约效果摘要</h2>
        <div class="metrics">
            <div class="metric">
                <div class="value">{full_states}</div>
                <div class="label">原始状态数</div>
            </div>
            <div class="metric">
                <div class="value">{reduced_states}</div>
                <div class="label">归约后状态数</div>
            </div>
            <div class="metric">
                <div class="value">{state_reduction:.1%}</div>
                <div class="label">状态减少率</div>
            </div>
            <div class="metric">
                <div class="value">{full_transitions}</div>
                <div class="label">原始迁移数</div>
            </div>
            <div class="metric">
                <div class="value">{reduced_transitions}</div>
                <div class="label">归约后迁移数</div>
            </div>
            <div class="metric">
                <div class="value">{trans_reduction:.1%}</div>
                <div class="label">迁移减少率</div>
            </div>
        </div>
    </div>

    <div class="comparison">
        <div class="panel panel-full">
            <h2>原始状态空间（完整展开）</h2>
            <div class="panel-stats">
                <span>状态数: <strong>{full_states}</strong></span>
                <span>迁移数: <strong>{full_transitions}</strong></span>
            </div>
            <div class="graph-container" id="graph-full">
                <div id="loading-full">正在加载图形...</div>
            </div>
        </div>
        <div class="panel panel-reduced">
            <h2>偏序归约后状态空间</h2>
            <div class="panel-stats">
                <span>状态数: <strong>{reduced_states}</strong></span>
                <span>迁移数: <strong>{reduced_transitions}</strong></span>
            </div>
            <div class="graph-container" id="graph-reduced">
                <div id="loading-reduced">正在加载图形...</div>
            </div>
        </div>
    </div>

    <script>
        const dotFull = `{full_dot_escaped}`;
        const dotReduced = `{reduced_dot_escaped}`;

        try {{
            d3.select("#graph-full").graphviz()
                .renderDot(dotFull)
                .on("end", function() {{
                    d3.select("#graph-full #loading-full").remove();
                }});
        }} catch (err) {{
            document.getElementById('graph-full').innerHTML =
                '<p style="color:red;">渲染失败: ' + err.message + '</p>';
        }}

        try {{
            d3.select("#graph-reduced").graphviz()
                .renderDot(dotReduced)
                .on("end", function() {{
                    d3.select("#graph-reduced #loading-reduced").remove();
                }});
        }} catch (err) {{
            document.getElementById('graph-reduced').innerHTML =
                '<p style="color:red;">渲染失败: ' + err.message + '</p>';
        }}
    </script>
</body>
</html>'''


if __name__ == "__main__":
    print("=" * 60)
    print("偏序归约状态空间可视化示例")
    print("=" * 60)

    # 导入示例程序
    from counter_example import (
        create_two_counter_program,
        create_dependency_analyzer
    )

    # 创建双计数器程序图（max_count=2 便于观察）
    max_count = 2
    print(f"\n创建双计数器程序（max_count={max_count}）...")
    pg = create_two_counter_program(max_count=max_count)
    analyzer = create_dependency_analyzer(max_count=max_count)

    print("\n生成状态空间对比可视化...")
    comparison_path = visualize_por_comparison(
        pg=pg,
        dependency_analyzer=analyzer,
        name="lab7_counter_por",
        output_dir=DEFAULT_OUTPUT_DIR
    )

    print(f"\n可视化完成！")
    print(f"对比页面: {comparison_path}")

    # 不同规模的演示
    print("\n" + "=" * 60)
    print("生成不同规模的对比图（max_count=3）")
    pg3 = create_two_counter_program(max_count=3)
    analyzer3 = create_dependency_analyzer(max_count=3)
    visualize_por_comparison(
        pg=pg3,
        dependency_analyzer=analyzer3,
        name="lab7_counter_por_n3",
        output_dir=DEFAULT_OUTPUT_DIR
    )
