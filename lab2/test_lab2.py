"""
实验二测试用例

验证不变性检查的实现正确性，包括：
1. 命题公式解析
2. 公式求值
3. 不变性检查（通过/失败）
4. 反例路径生成
"""

import sys
sys.path.insert(0, __file__.rsplit('\\', 1)[0] + '\\..\\lab1')

from transition_system import TransitionSystem
from propositional_formula import (
    PropositionalFormula, parse_formula, atom, neg, conj, disj,
    Atom, Not, And, Or
)
from invariant_checker import InvariantChecker, check_invariant
from peterson_example import create_simplified_peterson


def test_atom_parsing():
    """测试原子命题解析"""
    print("\n测试 1: 原子命题解析")
    print("-" * 40)
    
    f = parse_formula("crit0")
    assert isinstance(f.formula, Atom)
    assert f.formula.name == "crit0"
    
    print("  ✓ 原子命题解析正确")


def test_not_parsing():
    """测试非运算解析"""
    print("\n测试 2: 非运算解析")
    print("-" * 40)
    
    # 测试不同否定符号
    for symbol in ["¬", "!", "~"]:
        f = parse_formula(f"{symbol}crit0")
        assert isinstance(f.formula, Not)
        assert isinstance(f.formula.operand, Atom)
        assert f.formula.operand.name == "crit0"
    
    print("  ✓ 非运算解析正确（支持 ¬, !, ~）")


def test_and_parsing():
    """测试与运算解析"""
    print("\n测试 3: 与运算解析")
    print("-" * 40)
    
    # 测试不同与符号
    for symbol in ["∧", "&&", "&"]:
        f = parse_formula(f"crit0 {symbol} crit1")
        assert isinstance(f.formula, And)
        assert f.formula.left.name == "crit0"
        assert f.formula.right.name == "crit1"
    
    print("  ✓ 与运算解析正确（支持 ∧, &&, &）")


def test_or_parsing():
    """测试或运算解析"""
    print("\n测试 4: 或运算解析")
    print("-" * 40)
    
    # 测试不同或符号
    for symbol in ["∨", "||", "|"]:
        f = parse_formula(f"crit0 {symbol} crit1")
        assert isinstance(f.formula, Or)
        assert f.formula.left.name == "crit0"
        assert f.formula.right.name == "crit1"
    
    print("  ✓ 或运算解析正确（支持 ∨, ||, |）")


def test_parentheses():
    """测试括号分组"""
    print("\n测试 5: 括号分组")
    print("-" * 40)
    
    f = parse_formula("¬(crit0 ∧ crit1)")
    assert isinstance(f.formula, Not)
    assert isinstance(f.formula.operand, And)
    
    print("  ✓ 括号分组解析正确")


def test_precedence():
    """测试运算符优先级"""
    print("\n测试 6: 运算符优先级")
    print("-" * 40)
    
    # 非 > 与 > 或
    f = parse_formula("a ∧ b ∨ c")
    # 应该解析为 (a ∧ b) ∨ c，而不是 a ∧ (b ∨ c)
    assert isinstance(f.formula, Or)
    assert isinstance(f.formula.left, And)
    
    f = parse_formula("¬a ∧ b")
    # 应该解析为 (¬a) ∧ b
    assert isinstance(f.formula, And)
    assert isinstance(f.formula.left, Not)
    
    print("  ✓ 运算符优先级正确（非 > 与 > 或）")


def test_formula_evaluation():
    """测试公式求值"""
    print("\n测试 7: 公式求值")
    print("-" * 40)
    
    # 原子命题
    f = parse_formula("crit0")
    assert f.evaluate({"crit0"}) == True
    assert f.evaluate({"crit1"}) == False
    assert f.evaluate(set()) == False
    
    # 非运算
    f = parse_formula("¬crit0")
    assert f.evaluate({"crit0"}) == False
    assert f.evaluate({"crit1"}) == True
    
    # 与运算
    f = parse_formula("crit0 ∧ crit1")
    assert f.evaluate({"crit0", "crit1"}) == True
    assert f.evaluate({"crit0"}) == False
    assert f.evaluate({"crit1"}) == False
    assert f.evaluate(set()) == False
    
    # 或运算
    f = parse_formula("crit0 ∨ crit1")
    assert f.evaluate({"crit0", "crit1"}) == True
    assert f.evaluate({"crit0"}) == True
    assert f.evaluate({"crit1"}) == True
    assert f.evaluate(set()) == False
    
    # 复合公式
    f = parse_formula("¬(crit0 ∧ crit1)")
    assert f.evaluate({"crit0", "crit1"}) == False  # 违反互斥
    assert f.evaluate({"crit0"}) == True
    assert f.evaluate({"crit1"}) == True
    assert f.evaluate(set()) == True
    
    print("  ✓ 原子命题求值正确")
    print("  ✓ 非运算求值正确")
    print("  ✓ 与运算求值正确")
    print("  ✓ 或运算求值正确")
    print("  ✓ 复合公式求值正确")


def test_get_atoms():
    """测试获取原子命题"""
    print("\n测试 8: 获取原子命题")
    print("-" * 40)
    
    f = parse_formula("crit0")
    assert f.get_atoms() == {"crit0"}
    
    f = parse_formula("crit0 ∧ crit1")
    assert f.get_atoms() == {"crit0", "crit1"}
    
    f = parse_formula("¬(crit0 ∧ crit1) ∨ wait0")
    assert f.get_atoms() == {"crit0", "crit1", "wait0"}
    
    print("  ✓ 获取原子命题正确")


def test_programmatic_formula():
    """测试程序化创建公式"""
    print("\n测试 9: 程序化创建公式")
    print("-" * 40)
    
    # 使用便捷函数创建公式
    f = neg(conj(atom("crit0"), atom("crit1")))
    assert f.evaluate({"crit0", "crit1"}) == False
    assert f.evaluate({"crit0"}) == True
    
    # 等价于 ¬(crit0 ∧ crit1)
    f2 = parse_formula("¬(crit0 ∧ crit1)")
    assert f.evaluate({"crit0", "crit1"}) == f2.evaluate({"crit0", "crit1"})
    
    print("  ✓ 程序化创建公式正确")


def test_invariant_checker_pass():
    """测试不变性检查通过的情况"""
    print("\n测试 10: 不变性检查通过")
    print("-" * 40)
    
    ts = create_simplified_peterson()
    
    checker = InvariantChecker(ts)
    result = checker.check_string("¬(crit0 ∧ crit1)", method="bfs")
    
    assert result.holds == True
    assert result.violated_state is None
    assert result.counterexample is None
    assert result.checked_states > 0
    
    print(f"  ✓ 不变性检查通过")
    print(f"  ✓ 检查了 {result.checked_states} 个状态")


def test_invariant_checker_fail():
    """测试不变性检查失败的情况"""
    print("\n测试 11: 不变性检查失败")
    print("-" * 40)
    
    # 创建一个简单的 TS，其中有一个状态同时有 crit0 和 crit1
    ts = TransitionSystem()
    ts.add_state("s0", set())
    ts.add_state("s1", {"crit0"})
    ts.add_state("s2", {"crit1"})
    ts.add_state("s3", {"crit0", "crit1"})  # 违反状态
    
    ts.add_initial_state("s0")
    ts.add_transition("s0", "s1")
    ts.add_transition("s1", "s2")
    ts.add_transition("s2", "s3")
    
    checker = InvariantChecker(ts)
    result = checker.check_string("¬(crit0 ∧ crit1)", method="bfs")
    
    assert result.holds == False
    assert result.violated_state is not None
    assert result.counterexample is not None
    assert len(result.counterexample) > 0
    
    # 验证反例路径正确
    assert result.counterexample[0].name == "s0"
    assert result.counterexample[-1].name == "s3"
    
    print(f"  ✓ 不变性检查正确检测到违反")
    print(f"  ✓ 反例路径: {' -> '.join(s.name for s in result.counterexample)}")


def test_counterexample_path():
    """测试反例路径生成"""
    print("\n测试 12: 反例路径生成")
    print("-" * 40)
    
    # 创建一个有明确路径的 TS
    ts = TransitionSystem()
    ts.add_state("start", set())
    ts.add_state("middle", {"wait0"})
    ts.add_state("bad", {"crit0", "crit1"})
    
    ts.add_initial_state("start")
    ts.add_transition("start", "middle")
    ts.add_transition("middle", "bad")
    
    result = check_invariant(ts, "¬(crit0 ∧ crit1)")
    
    assert not result.holds
    assert result.counterexample is not None
    
    # 验证路径
    path_names = [s.name for s in result.counterexample]
    assert path_names == ["start", "middle", "bad"]
    
    print(f"  ✓ 反例路径正确")
    print(f"  ✓ 路径: {' -> '.join(path_names)}")


def test_bfs_vs_dfs():
    """测试 BFS 和 DFS 结果一致性"""
    print("\n测试 13: BFS 和 DFS 结果一致性")
    print("-" * 40)
    
    ts = create_simplified_peterson()
    
    checker = InvariantChecker(ts)
    result_bfs = checker.check_string("¬(crit0 ∧ crit1)", method="bfs")
    result_dfs = checker.check_string("¬(crit0 ∧ crit1)", method="dfs")
    
    # 两种方法应该得到相同的结果
    assert result_bfs.holds == result_dfs.holds
    assert result_bfs.checked_states == result_dfs.checked_states
    
    print(f"  ✓ BFS 和 DFS 结果一致")
    print(f"  ✓ BFS 检查状态数: {result_bfs.checked_states}")
    print(f"  ✓ DFS 检查状态数: {result_dfs.checked_states}")


def test_multiple_atoms():
    """测试多个原子命题的公式"""
    print("\n测试 14: 多个原子命题的公式")
    print("-" * 40)
    
    ts = create_simplified_peterson()
    
    # 测试包含多个原子命题的公式
    formulas = [
        "¬wait0 ∨ ¬crit1",  # 等价于 wait0 → ¬crit1
        "(wait0 ∨ wait1) ∧ ¬(crit0 ∧ crit1)",
        "¬crit0 ∨ ¬crit1 ∨ (wait0 ∧ wait1)",
    ]
    
    for formula_str in formulas:
        try:
            result = check_invariant(ts, formula_str)
            print(f"  ✓ 公式 '{formula_str}' 检查完成")
        except Exception as e:
            print(f"  ✗ 公式 '{formula_str}' 检查失败: {e}")
            raise


def test_empty_ts():
    """测试空 Transition System"""
    print("\n测试 15: 空 Transition System")
    print("-" * 40)
    
    ts = TransitionSystem()
    
    result = check_invariant(ts, "crit0")
    
    assert result.holds == True
    assert result.checked_states == 0
    
    print("  ✓ 空 TS 处理正确")


def test_initial_violation():
    """测试初始状态就违反不变式的情况"""
    print("\n测试 16: 初始状态违反")
    print("-" * 40)
    
    ts = TransitionSystem()
    ts.add_state("bad", {"crit0", "crit1"})
    ts.add_initial_state("bad")
    
    result = check_invariant(ts, "¬(crit0 ∧ crit1)")
    
    assert not result.holds
    assert result.violated_state.name == "bad"
    assert len(result.counterexample) == 1
    assert result.counterexample[0].name == "bad"
    
    print("  ✓ 初始状态违反检测正确")
    print(f"  ✓ 反例路径: {result.counterexample[0].name}")


def test_complex_formula():
    """测试复杂嵌套公式"""
    print("\n测试 17: 复杂嵌套公式")
    print("-" * 40)
    
    # 复杂嵌套公式
    formula_str = "((a ∧ b) ∨ (c ∧ d)) ∧ ¬e"
    f = parse_formula(formula_str)
    
    # 测试各种标签组合
    assert f.evaluate({"a", "b", "c", "d"}) == True
    assert f.evaluate({"a", "b", "e"}) == False
    assert f.evaluate({"c", "d"}) == True
    assert f.evaluate({"a", "c"}) == False
    
    print("  ✓ 复杂嵌套公式求值正确")


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("实验二测试套件")
    print("=" * 60)
    
    tests = [
        test_atom_parsing,
        test_not_parsing,
        test_and_parsing,
        test_or_parsing,
        test_parentheses,
        test_precedence,
        test_formula_evaluation,
        test_get_atoms,
        test_programmatic_formula,
        test_invariant_checker_pass,
        test_invariant_checker_fail,
        test_counterexample_path,
        test_bfs_vs_dfs,
        test_multiple_atoms,
        test_empty_ts,
        test_initial_violation,
        test_complex_formula,
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
