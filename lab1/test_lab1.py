"""
实验一测试用例

验证 Transition System 的实现正确性，包括：
1. 状态管理
2. 迁移关系
3. 可达状态计算（DFS/BFS）
4. Peterson 互斥算法模型
"""

import sys
from pathlib import Path

sys.path.insert(0, __file__.rsplit('\\', 1)[0])

from transition_system import TransitionSystem, State
from peterson_example import create_simplified_peterson, PetersonTS, verify_mutual_exclusion

# 可视化输出目录
OUTPUT_DIR = Path(__file__).parent.parent / "output" / "visualization"


def test_basic_state_management():
    """测试基本状态管理"""
    print("\n测试 1: 基本状态管理")
    print("-" * 40)
    
    ts = TransitionSystem()
    
    # 添加状态
    s1 = ts.add_state("s1", {"a", "b"})
    s2 = ts.add_state("s2", {"b", "c"})
    s3 = ts.add_state("s3")
    
    # 验证状态创建
    assert s1.name == "s1"
    assert s1.has_label("a")
    assert s1.has_label("b")
    assert not s1.has_label("c")
    
    # 验证状态去重
    s1_dup = ts.add_state("s1", {"a", "b"})
    assert s1 == s1_dup, "相同状态应该返回同一对象"
    
    # 验证状态更新
    s1_new = ts.add_state("s1", {"x"})
    assert s1_new.has_label("x")
    
    print("  ✓ 状态创建和标签管理正确")
    print("  ✓ 状态去重功能正常")


def test_transition_management():
    """测试迁移关系管理"""
    print("\n测试 2: 迁移关系管理")
    print("-" * 40)
    
    ts = TransitionSystem()
    
    # 添加迁移
    ts.add_transition("s1", "s2", "a")
    ts.add_transition("s1", "s3")
    ts.add_transition("s2", "s3", "b")
    
    s1 = ts.get_state("s1")
    s2 = ts.get_state("s2")
    s3 = ts.get_state("s3")
    
    # 验证后继状态
    successors_s1 = ts.get_successors(s1)
    assert len(successors_s1) == 2
    assert s2 in successors_s1
    assert s3 in successors_s1
    
    # 验证前驱状态（用于 Pre 计算）
    predecessors_s3 = ts.get_predecessors(s3)
    assert len(predecessors_s3) == 2
    assert s1 in predecessors_s3
    assert s2 in predecessors_s3
    
    print("  ✓ 迁移关系创建正确")
    print("  ✓ 后继状态查询正确")
    print("  ✓ 前驱状态查询正确（Pre 计算基础）")


def test_reachable_states():
    """测试可达状态计算"""
    print("\n测试 3: 可达状态计算")
    print("-" * 40)
    
    # 构建测试用例
    # s0 -> s1 -> s2
    #   \-> s3
    ts = TransitionSystem()
    ts.add_initial_state("s0")
    ts.add_state("s1")
    ts.add_state("s2")
    ts.add_state("s3")
    ts.add_state("s4")  # 不可达状态
    
    ts.add_transition("s0", "s1")
    ts.add_transition("s1", "s2")
    ts.add_transition("s0", "s3")
    
    # 测试 BFS
    reachable_bfs = ts.compute_reachable_states("bfs")
    reachable_names_bfs = {s.name for s in reachable_bfs}
    assert reachable_names_bfs == {"s0", "s1", "s2", "s3"}, f"BFS 可达状态错误: {reachable_names_bfs}"
    
    # 测试 DFS
    reachable_dfs = ts.compute_reachable_states("dfs")
    reachable_names_dfs = {s.name for s in reachable_dfs}
    assert reachable_names_dfs == {"s0", "s1", "s2", "s3"}, f"DFS 可达状态错误: {reachable_names_dfs}"
    
    # BFS 和 DFS 结果应该相同（集合比较）
    assert reachable_bfs == reachable_dfs, "BFS 和 DFS 结果应该相同"
    
    print("  ✓ BFS 可达状态计算正确")
    print("  ✓ DFS 可达状态计算正确")
    print("  ✓ 状态去重功能正常")


def test_pre_computation():
    """测试 Pre 集合计算（为实验五 CTL 做准备）"""
    print("\n测试 4: Pre 集合计算")
    print("-" * 40)
    
    # 构建测试用例
    # s0 -> s1 -> s2
    # s3 -> s1
    ts = TransitionSystem()
    ts.add_state("s0")
    ts.add_state("s1")
    ts.add_state("s2")
    ts.add_state("s3")
    
    ts.add_transition("s0", "s1")
    ts.add_transition("s1", "s2")
    ts.add_transition("s3", "s1")
    
    s1 = ts.get_state("s1")
    s2 = ts.get_state("s2")
    
    # Pre({s1}) = {s0, s3}
    pre_s1 = ts.pre({s1})
    pre_names = {s.name for s in pre_s1}
    assert pre_names == {"s0", "s3"}, f"Pre 计算错误: {pre_names}"
    
    # Pre({s2}) = {s1}
    pre_s2 = ts.pre({s2})
    pre_names_s2 = {s.name for s in pre_s2}
    assert pre_names_s2 == {"s1"}, f"Pre 计算错误: {pre_names_s2}"
    
    print("  ✓ Pre 集合计算正确")


def test_path_finding():
    """测试路径查找（为实验二反例生成做准备）"""
    print("\n测试 5: 路径查找")
    print("-" * 40)
    
    ts = TransitionSystem()
    ts.add_state("s0")
    ts.add_state("s1")
    ts.add_state("s2")
    ts.add_state("s3")
    
    ts.add_transition("s0", "s1")
    ts.add_transition("s1", "s2")
    ts.add_transition("s2", "s3")
    ts.add_transition("s0", "s3")  # 直接路径
    
    s0 = ts.get_state("s0")
    s3 = ts.get_state("s3")
    
    # 查找路径
    path = ts.find_path(s0, s3)
    assert path is not None, "应该存在路径"
    assert path[0] == s0, "路径应从 s0 开始"
    assert path[-1] == s3, "路径应在 s3 结束"
    
    # 最短路径应该是 s0 -> s3
    assert len(path) == 2, f"最短路径长度应为 2: {[s.name for s in path]}"
    
    print("  ✓ 路径查找功能正常")
    print("  ✓ 最短路径计算正确")


def test_peterson_simplified():
    """测试简化版 Peterson 模型"""
    print("\n测试 6: 简化版 Peterson 模型")
    print("-" * 40)
    
    ts = create_simplified_peterson()
    
    # 验证可达状态数
    reachable = ts.compute_reachable_states()
    
    # 分析可达状态：
    # s0 (初始) -> s1, s2
    # s1 -> s6, s4
    # s2 -> s5, s4
    # s4 -> s7
    # s5 -> s0
    # s6 -> s0
    # s7 -> s1
    # 所以可达状态为: s0, s1, s2, s4, s5, s6, s7 = 7 个状态
    # s3 和 s8 不可达（需要从 s1->s3 或 s3->s8 的迁移，但当前模型没有）
    expected_reachable = 7
    actual_reachable = len(reachable)
    
    print(f"  期望可达状态数: {expected_reachable}")
    print(f"  实际可达状态数: {actual_reachable}")
    
    assert actual_reachable == expected_reachable, \
        f"可达状态数不匹配: 期望 {expected_reachable}, 实际 {actual_reachable}"
    
    # 验证互斥性质
    result = verify_mutual_exclusion(ts)
    assert result, "简化版 Peterson 算法应满足互斥性质"
    
    # 生成可视化文件
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ts.save_dot(OUTPUT_DIR / "test_peterson_simplified.dot")
    ts.visualize_html(OUTPUT_DIR / "test_peterson_simplified.html")
    print(f"  可视化文件已保存到 {OUTPUT_DIR}")
    
    print("  ✓ 可达状态数与手工计算一致")
    print("  ✓ 互斥性质验证通过")


def test_peterson_full():
    """测试完整版 Peterson 模型"""
    print("\n测试 7: 完整版 Peterson 模型")
    print("-" * 40)
    
    peterson = PetersonTS()
    ts = peterson.get_ts()
    
    stats = ts.get_statistics()
    
    print(f"  总状态数: {stats['total_states']}")
    print(f"  可达状态数: {stats['reachable_states']}")
    print(f"  可达迁移数: {stats['reachable_transitions']}")
    
    # 验证互斥性质
    result = verify_mutual_exclusion(ts)
    assert result, "完整版 Peterson 算法应满足互斥性质"
    
    # 生成可视化文件
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ts.save_dot(OUTPUT_DIR / "test_peterson_full.dot")
    ts.visualize_html(OUTPUT_DIR / "test_peterson_full.html")
    print(f"  可视化文件已保存到 {OUTPUT_DIR}")
    
    print("  ✓ 完整模型构建成功")
    print("  ✓ 互斥性质验证通过")


def test_statistics():
    """测试统计信息功能"""
    print("\n测试 8: 统计信息")
    print("-" * 40)
    
    ts = create_simplified_peterson()
    stats = ts.get_statistics()
    
    required_keys = [
        "total_states", "reachable_states", "initial_states",
        "total_transitions", "reachable_transitions", "actions"
    ]
    
    for key in required_keys:
        assert key in stats, f"统计信息缺少键: {key}"
        assert isinstance(stats[key], int), f"{key} 应该是整数"
    
    print(f"  总状态数: {stats['total_states']}")
    print(f"  可达状态数: {stats['reachable_states']}")
    print(f"  初始状态数: {stats['initial_states']}")
    print(f"  总迁移数: {stats['total_transitions']}")
    print(f"  可达迁移数: {stats['reachable_transitions']}")
    print(f"  动作数: {stats['actions']}")
    
    print("  ✓ 统计信息完整")


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("实验一测试套件")
    print("=" * 60)
    
    tests = [
        test_basic_state_management,
        test_transition_management,
        test_reachable_states,
        test_pre_computation,
        test_path_finding,
        test_peterson_simplified,
        test_peterson_full,
        test_statistics,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"  ✗ 失败: {e}")
            failed += 1
        except Exception as e:
            print(f"  ✗ 错误: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
