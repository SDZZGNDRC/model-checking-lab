"""
实验六：CTL 模型检查与 Bisimulation 最小化集成

本模块实现 CTL 模型检查与 Bisimulation 最小化的集成：
- 允许用户选择是否先最小化再验证
- 提供性能对比（最小化前后）
- 验证最小化前后 CTL 结果的一致性
- 可视化对比展示
"""

import sys
import os
import time
sys.path.insert(0, __file__.rsplit('\\', 1)[0] + '\\..\\lab1')
sys.path.insert(0, __file__.rsplit('\\', 1)[0] + '\\..\\lab5')

from typing import Optional, Tuple
from dataclasses import dataclass

from transition_system import TransitionSystem
from ctl_formula import CTLFormula, atom, ef, ag, disj
from ctl_model_checker import CTLModelChecker, CTLCheckResult
from bisimulation_minimizer import minimize_transition_system, MinimizationResult
from ts_visualizer import TSVisualizer

# 输出目录
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                          'output', 'visualization')


@dataclass
class OptimizedCheckResult:
    """
    优化的 CTL 检查结果
    
    包含原始 TS 和最小化 TS 的检查结果对比。
    
    Attributes:
        formula: 被检查的 CTL 公式
        original_result: 原始 TS 的检查结果
        minimized_result: 最小化 TS 的检查结果（如果使用最小化）
        used_minimization: 是否使用了最小化
        minimization_time: 最小化耗时（秒）
        original_check_time: 原始 TS 检查耗时（秒）
        minimized_check_time: 最小化 TS 检查耗时（秒）
        results_match: 两种方法的结果是否一致
        minimization_result: 最小化结果详情
    """
    formula: str
    original_result: CTLCheckResult
    minimized_result: Optional[CTLCheckResult]
    used_minimization: bool
    minimization_time: float
    original_check_time: float
    minimized_check_time: float
    results_match: bool
    minimization_result: Optional[MinimizationResult]
    
    def __repr__(self) -> str:
        if self.used_minimization:
            speedup = (self.original_check_time / self.minimized_check_time 
                      if self.minimized_check_time > 0 else float('inf'))
            return (f"OptimizedCheckResult("
                    f"formula='{self.formula}', "
                    f"holds={self.original_result.holds}, "
                    f"minimized={self.used_minimization}, "
                    f"speedup={speedup:.2f}x)")
        else:
            return (f"OptimizedCheckResult("
                    f"formula='{self.formula}', "
                    f"holds={self.original_result.holds}, "
                    f"minimized={self.used_minimization})")
    
    def print_summary(self):
        """打印检查结果摘要"""
        print("=" * 70)
        print(f"CTL 公式: {self.formula}")
        print("=" * 70)
        
        print(f"\n原始 TS 检查结果:")
        print(f"  结果: {'✓ 满足' if self.original_result.holds else '✗ 不满足'}")
        print(f"  耗时: {self.original_check_time:.4f} 秒")
        
        if self.used_minimization and self.minimized_result:
            print(f"\n最小化 TS 检查结果:")
            print(f"  结果: {'✓ 满足' if self.minimized_result.holds else '✗ 不满足'}")
            print(f"  耗时: {self.minimized_check_time:.4f} 秒")
            
            print(f"\n最小化信息:")
            if self.minimization_result:
                print(f"  原始状态数: {self.minimization_result.original_state_count}")
                print(f"  最小化后状态数: {self.minimization_result.minimized_state_count}")
                print(f"  缩减比例: {self.minimization_result.reduction_ratio:.1%}")
            print(f"  最小化耗时: {self.minimization_time:.4f} 秒")
            
            print(f"\n性能对比:")
            total_orig = self.original_check_time
            total_min = self.minimization_time + self.minimized_check_time
            speedup = total_orig / total_min if total_min > 0 else float('inf')
            print(f"  原始方法总耗时: {total_orig:.4f} 秒")
            print(f"  最小化方法总耗时: {total_min:.4f} 秒")
            print(f"  加速比: {speedup:.2f}x")
            
            if self.results_match:
                print(f"\n✓ 两种方法结果一致")
            else:
                print(f"\n✗ 警告：两种方法结果不一致！")
        
        print()
    
    def visualize_comparison(self, output_dir: str = OUTPUT_DIR, 
                               original_ts: Optional[TransitionSystem] = None) -> Tuple[str, str]:
        """
        可视化原始TS和最小化TS的对比
        
        Args:
            output_dir: 输出目录
            original_ts: 原始迁移系统（可选，因为result中不包含ts引用）
            
        Returns:
            (原始TS的HTML路径, 最小化TS的HTML路径)
        """
        os.makedirs(output_dir, exist_ok=True)
        
        # 清理公式字符串作为文件名
        safe_formula = "".join(c if c.isalnum() else "_" for c in self.formula)[:30]
        
        original_html_path = ""
        minimized_html_path = ""
        
        if original_ts:
            # 可视化原始TS
            original_viz = TSVisualizer(original_ts)
            original_html_path = os.path.join(output_dir, f"ctl_check_{safe_formula}_original.html")
            original_viz.save_html(original_html_path, 
                                   title=f"CTL检查: {self.formula} - 原始TS")
        
        if self.used_minimization and self.minimization_result:
            # 可视化最小化TS
            minimized_viz = TSVisualizer(self.minimization_result.minimized_ts)
            minimized_html_path = os.path.join(output_dir, f"ctl_check_{safe_formula}_minimized.html")
            minimized_viz.save_html(minimized_html_path,
                                   title=f"CTL检查: {self.formula} - 最小化TS")
            
            # 同时生成分区可视化
            if original_ts:
                partition_path = os.path.join(output_dir, f"ctl_check_{safe_formula}_partition.html")
                from bisimulation_minimizer import BisimulationMinimizer
                minimizer = BisimulationMinimizer(original_ts)
                minimizer.visualize_partition(partition_path)
        
        return original_html_path, minimized_html_path


class OptimizedCTLModelChecker:
    """
    优化的 CTL 模型检查器
    
    集成 Bisimulation 最小化，支持在验证前自动最小化 TS。
    """
    
    def __init__(self, ts: TransitionSystem, use_minimization: bool = False):
        """
        初始化优化的模型检查器
        
        Args:
            ts: 要验证的 Transition System
            use_minimization: 是否使用 Bisimulation 最小化
        """
        self.original_ts = ts
        self.use_minimization = use_minimization
        self._minimization_result: Optional[MinimizationResult] = None
        self._minimization_time: float = 0.0
        
        if use_minimization:
            self._perform_minimization()
    
    def _perform_minimization(self):
        """执行最小化"""
        start_time = time.time()
        self._minimization_result = minimize_transition_system(self.original_ts)
        self._minimization_time = time.time() - start_time
    
    def check(self, formula: CTLFormula) -> OptimizedCheckResult:
        """
        检查 CTL 公式
        
        如果使用最小化，则同时检查原始 TS 和最小化 TS，
        并验证结果的一致性。
        
        Args:
            formula: 要检查的 CTL 公式
            
        Returns:
            OptimizedCheckResult 对象
        """
        # 检查原始 TS
        start_time = time.time()
        checker_orig = CTLModelChecker(self.original_ts)
        original_result = checker_orig.check(formula)
        original_check_time = time.time() - start_time
        
        minimized_result: Optional[CTLCheckResult] = None
        minimized_check_time: float = 0.0
        results_match: bool = True
        
        if self.use_minimization and self._minimization_result:
            # 检查最小化 TS
            start_time = time.time()
            checker_min = CTLModelChecker(self._minimization_result.minimized_ts)
            minimized_result = checker_min.check(formula)
            minimized_check_time = time.time() - start_time
            
            # 验证结果一致性
            results_match = original_result.holds == minimized_result.holds
        
        return OptimizedCheckResult(
            formula=str(formula),
            original_result=original_result,
            minimized_result=minimized_result,
            used_minimization=self.use_minimization,
            minimization_time=self._minimization_time,
            original_check_time=original_check_time,
            minimized_check_time=minimized_check_time,
            results_match=results_match,
            minimization_result=self._minimization_result
        )
    
    def check_string(self, formula_str: str) -> OptimizedCheckResult:
        """
        从字符串解析并检查 CTL 公式
        
        Args:
            formula_str: 公式字符串
            
        Returns:
            OptimizedCheckResult 对象
        """
        from ctl_formula import parse_ctl
        formula = parse_ctl(formula_str)
        return self.check(formula)
    
    def get_minimization_result(self) -> Optional[MinimizationResult]:
        """获取最小化结果"""
        return self._minimization_result


def compare_check_methods(ts: TransitionSystem, 
                          formula: CTLFormula) -> OptimizedCheckResult:
    """
    对比两种检查方法（原始 vs 最小化）
    
    Args:
        ts: Transition System
        formula: CTL 公式
        
    Returns:
        OptimizedCheckResult 对象
        
    Examples:
        >>> from ctl_formula import atom, ag
        >>> result = compare_check_methods(ts, ag(atom("safe")))
        >>> result.print_summary()
    """
    checker = OptimizedCTLModelChecker(ts, use_minimization=True)
    return checker.check(formula)


def check_with_optional_minimization(ts: TransitionSystem,
                                     formula: CTLFormula,
                                     use_minimization: bool = True) -> CTLCheckResult:
    """
    检查 CTL 公式，可选择是否使用最小化
    
    这是便捷的包装函数，根据 use_minimization 参数决定
    是否先最小化 TS 再验证。
    
    Args:
        ts: Transition System
        formula: CTL 公式
        use_minimization: 是否使用最小化
        
    Returns:
        CTLCheckResult 对象
        
    Examples:
        >>> from ctl_formula import atom, ag
        >>> result = check_with_optional_minimization(ts, ag(atom("safe")), True)
        >>> print(f"结果: {result.holds}")
    """
    if use_minimization:
        # 先最小化
        min_result = minimize_transition_system(ts)
        checker = CTLModelChecker(min_result.minimized_ts)
    else:
        checker = CTLModelChecker(ts)
    
    return checker.check(formula)


def demonstrate_integration():
    """演示 CTL 与最小化的集成"""
    print("=" * 70)
    print("CTL 模型检查与 Bisimulation 最小化集成演示")
    print("=" * 70)
    
    # 创建一个示例 TS
    ts = TransitionSystem()
    
    # 创建一些 Bisimilar 的状态
    ts.add_state("s0", {"start"})
    ts.add_state("s1", {"middle"})
    ts.add_state("s2", {"middle"})  # 与 s1 Bisimilar
    ts.add_state("s3", {"end"})
    
    ts.add_initial_state("s0")
    
    ts.add_transition("s0", "s1")
    ts.add_transition("s0", "s2")
    ts.add_transition("s1", "s3")
    ts.add_transition("s2", "s3")
    
    print("\n测试迁移系统:")
    stats = ts.get_statistics()
    print(f"  状态数: {stats['reachable_states']}")
    print(f"  迁移数: {stats['reachable_transitions']}")
    
    # ASCII可视化
    print("\n原始TS的ASCII可视化:")
    ts.visualize_ascii()
    
    # 定义测试公式
    formulas = [
        ("EF(end)", ef(atom("end"))),
        ("AG(start | middle | end)", ag(disj(disj(atom("start"), atom("middle")), atom("end")))),
    ]
    
    print("\n" + "=" * 70)
    print("对比原始方法和最小化方法")
    print("=" * 70)
    
    for name, formula in formulas:
        print(f"\n公式: {name}")
        
        # 方法 1: 原始方法
        start = time.time()
        checker_orig = CTLModelChecker(ts)
        result_orig = checker_orig.check(formula)
        time_orig = time.time() - start
        
        # 方法 2: 最小化方法
        start = time.time()
        min_result = minimize_transition_system(ts)
        checker_min = CTLModelChecker(min_result.minimized_ts)
        result_min = checker_min.check(formula)
        time_min = time.time() - start
        
        print(f"  原始方法: {'✓' if result_orig.holds else '✗'} (耗时: {time_orig:.4f}s)")
        print(f"  最小化方法: {'✓' if result_min.holds else '✗'} (耗时: {time_min:.4f}s)")
        print(f"  结果一致: {'✓' if result_orig.holds == result_min.holds else '✗'}")
        print(f"  状态缩减: {min_result.original_state_count} -> {min_result.minimized_state_count}")
        
        # ASCII可视化最小化TS
        print("\n  最小化后TS的ASCII可视化:")
        min_result.minimized_ts.visualize_ascii()
    
    print("\n" + "=" * 70)
    print("使用 OptimizedCTLModelChecker")
    print("=" * 70)
    
    checker = OptimizedCTLModelChecker(ts, use_minimization=True)
    
    for name, formula in formulas:
        result = checker.check(formula)
        result.print_summary()
        
        # 生成可视化对比
        print("\n生成可视化对比文件...")
        orig_path, min_path = result.visualize_comparison(original_ts=ts)
        if orig_path:
            print(f"  - 原始TS: {orig_path}")
        if min_path:
            print(f"  - 最小化TS: {min_path}")


if __name__ == "__main__":
    demonstrate_integration()