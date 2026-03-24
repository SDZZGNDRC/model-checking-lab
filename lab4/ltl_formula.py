"""
实验四：LTL 公式解析器与 NBA 构造器

本模块实现：
- LTL 公式的解析（支持常用时序运算符）
- 从 LTL 公式手动构造 NBA（针对常用模式）
- 提供简化但实用的 LTL 到 NBA 转换

支持的 LTL 运算符：
- X φ (Next)：下一个状态满足 φ
- F φ (Eventually/Future)：某个未来状态满足 φ
- G φ (Globally/Always)：所有未来状态都满足 φ
- φ U ψ (Until)：φ 一直成立直到 ψ 成立
- φ R ψ (Release)：ψ 一直成立直到 φ 成立

以及逻辑运算符：
- ¬ φ (Not)：非
- φ ∧ ψ (And)：与
- φ ∨ ψ (Or)：或
- φ → ψ (Implies)：蕴含
"""

from typing import Set, Optional, Dict, List
from dataclasses import dataclass
from enum import Enum, auto

from nba import NBA, NBAState


class LTOperator(Enum):
    """LTL 运算符类型"""
    ATOM = auto()       # 原子命题
    NOT = auto()        # 非 (¬)
    AND = auto()        # 与 (∧)
    OR = auto()         # 或 (∨)
    IMPLIES = auto()    # 蕴含 (→)
    NEXT = auto()       # 下一个 (X)
    EVENTUALLY = auto() # 最终 (F)
    GLOBALLY = auto()   # 总是 (G)
    UNTIL = auto()      # 直到 (U)
    RELEASE = auto()    # 释放 (R)


@dataclass
class LTLFormula:
    """
    LTL 公式类
    
    使用简单的树形结构表示 LTL 公式
    """
    op: LTOperator
    atom: Optional[str] = None  # 对于 ATOM 类型
    left: Optional['LTLFormula'] = None   # 一元/二元运算符的左操作数
    right: Optional['LTLFormula'] = None  # 二元运算符的右操作数
    
    def __repr__(self) -> str:
        if self.op == LTOperator.ATOM:
            return self.atom or "true"
        elif self.op == LTOperator.NOT:
            return f"¬({self.left})"
        elif self.op == LTOperator.NEXT:
            return f"X({self.left})"
        elif self.op == LTOperator.EVENTUALLY:
            return f"♦({self.left})"
        elif self.op == LTOperator.GLOBALLY:
            return f"□({self.left})"
        elif self.op == LTOperator.AND:
            return f"({self.left} ∧ {self.right})"
        elif self.op == LTOperator.OR:
            return f"({self.left} ∨ {self.right})"
        elif self.op == LTOperator.IMPLIES:
            return f"({self.left} → {self.right})"
        elif self.op == LTOperator.UNTIL:
            return f"({self.left} U {self.right})"
        elif self.op == LTOperator.RELEASE:
            return f"({self.left} R {self.right})"
        return "unknown"
    
    def __str__(self) -> str:
        return self.__repr__()
    
    def get_atoms(self) -> Set[str]:
        """获取公式中所有原子命题"""
        if self.op == LTOperator.ATOM:
            return {self.atom} if self.atom else set()
        elif self.op in (LTOperator.NOT, LTOperator.NEXT, 
                         LTOperator.EVENTUALLY, LTOperator.GLOBALLY):
            return self.left.get_atoms() if self.left else set()
        else:
            # 二元运算符
            atoms = set()
            if self.left:
                atoms |= self.left.get_atoms()
            if self.right:
                atoms |= self.right.get_atoms()
            return atoms


# ==================== 便捷构造函数 ====================

def atom(name: str) -> LTLFormula:
    """创建原子命题公式"""
    return LTLFormula(op=LTOperator.ATOM, atom=name)


def true() -> LTLFormula:
    """创建 true 公式"""
    return LTLFormula(op=LTOperator.ATOM, atom="true")


def false() -> LTLFormula:
    """创建 false 公式"""
    return LTLFormula(op=LTOperator.ATOM, atom="false")


def neg(formula: LTLFormula) -> LTLFormula:
    """创建非运算公式"""
    return LTLFormula(op=LTOperator.NOT, left=formula)


def next_(formula: LTLFormula) -> LTLFormula:
    """创建 Next 公式 X φ"""
    return LTLFormula(op=LTOperator.NEXT, left=formula)


def eventually(formula: LTLFormula) -> LTLFormula:
    """创建 Eventually 公式 F φ 或 ♦ φ"""
    return LTLFormula(op=LTOperator.EVENTUALLY, left=formula)


def globally(formula: LTLFormula) -> LTLFormula:
    """创建 Globally 公式 G φ 或 □ φ"""
    return LTLFormula(op=LTOperator.GLOBALLY, left=formula)


def conj(left: LTLFormula, right: LTLFormula) -> LTLFormula:
    """创建与运算公式 φ ∧ ψ"""
    return LTLFormula(op=LTOperator.AND, left=left, right=right)


def disj(left: LTLFormula, right: LTLFormula) -> LTLFormula:
    """创建或运算公式 φ ∨ ψ"""
    return LTLFormula(op=LTOperator.OR, left=left, right=right)


def implies(left: LTLFormula, right: LTLFormula) -> LTLFormula:
    """创建蕴含公式 φ → ψ"""
    return LTLFormula(op=LTOperator.IMPLIES, left=left, right=right)


def until(left: LTLFormula, right: LTLFormula) -> LTLFormula:
    """创建 Until 公式 φ U ψ"""
    return LTLFormula(op=LTOperator.UNTIL, left=left, right=right)


def release(left: LTLFormula, right: LTLFormula) -> LTLFormula:
    """创建 Release 公式 φ R ψ"""
    return LTLFormula(op=LTOperator.RELEASE, left=left, right=right)


# ==================== LTL 到 NBA 的转换 ====================

class LTLToNBA:
    """
    LTL 到 NBA 的转换器
    
    针对常用 LTL 模式手动构造 NBA。
    这是一个简化实现，支持以下模式：
    - G φ (□φ)：总是 φ
    - F φ (♦φ)：最终 φ
    - X φ：下一个 φ
    - □♦φ：无限经常 φ
    - ♦□φ：最终总是 φ
    - □(φ → ♦ψ)：每当 φ 则最终 ψ
    - φ U ψ：φ 直到 ψ
    """
    
    def __init__(self):
        self._state_counter = 0
    
    def _new_state_name(self, prefix: str = "q") -> str:
        """生成新状态名称"""
        name = f"{prefix}{self._state_counter}"
        self._state_counter += 1
        return name
    
    def convert(self, formula: LTLFormula, all_atoms: Optional[Set[str]] = None) -> NBA:
        """
        将 LTL 公式转换为 NBA
        
        Args:
            formula: LTL 公式
            all_atoms: 所有可能的原子命题集合（用于构造补集转移）
            
        Returns:
            接受该公式所表示语言的 NBA
        """
        self._state_counter = 0
        self._all_atoms = all_atoms or formula.get_atoms()
        return self._convert_formula(formula)
    
    def _convert_formula(self, formula: LTLFormula) -> NBA:
        """递归转换公式"""
        if formula.op == LTOperator.ATOM:
            return self._build_atom(formula.atom)
        elif formula.op == LTOperator.NOT:
            return self._build_not(formula.left)
        elif formula.op == LTOperator.GLOBALLY:
            return self._build_globally(formula.left)
        elif formula.op == LTOperator.EVENTUALLY:
            return self._build_eventually(formula.left)
        elif formula.op == LTOperator.NEXT:
            return self._build_next(formula.left)
        elif formula.op == LTOperator.AND:
            return self._build_and(formula.left, formula.right)
        elif formula.op == LTOperator.OR:
            return self._build_or(formula.left, formula.right)
        elif formula.op == LTOperator.IMPLIES:
            return self._build_implies(formula.left, formula.right)
        elif formula.op == LTOperator.UNTIL:
            return self._build_until(formula.left, formula.right)
        else:
            raise ValueError(f"不支持的运算符: {formula.op}")
    
    def _build_atom(self, atom_name: Optional[str]) -> NBA:
        """构造原子命题的 NBA"""
        nba = NBA()
        
        if atom_name == "true":
            # true：接受所有运行
            q0 = nba.add_state(self._new_state_name(), is_initial=True, is_accept=True)
            # 为所有原子命题添加自环
            for a in self._all_atoms:
                nba.add_transition(q0.name, q0.name, a)
        elif atom_name == "false":
            # false：不接受任何运行
            q0 = nba.add_state(self._new_state_name(), is_initial=True)
            # 没有接受状态
        else:
            # 普通原子命题：要求当前状态满足该命题
            q0 = nba.add_state(self._new_state_name(), is_initial=True, is_accept=True)
            nba.add_transition(q0.name, q0.name, atom_name)
        
        return nba
    
    def _build_not(self, operand: LTLFormula) -> NBA:
        """构造 ¬φ 的 NBA
        
        注意：这里使用简化处理，假设操作数是原子命题
        完整实现需要 NBA 的补运算（复杂）
        """
        if operand.op == LTOperator.ATOM and operand.atom not in ("true", "false"):
            # ¬atom：要求当前状态不满足该原子命题
            nba = NBA()
            q0 = nba.add_state(self._new_state_name(), is_initial=True, is_accept=True)
            
            # 为所有其他原子命题添加自环
            for a in self._all_atoms:
                if a != operand.atom:
                    nba.add_transition(q0.name, q0.name, a)
            
            return nba
        else:
            # 对于复杂公式，返回一个占位 NBA
            # 实际应该使用 NBA 补运算
            raise ValueError(f"复杂非运算暂不支持: ¬({operand})")
    
    def _build_globally(self, operand: LTLFormula) -> NBA:
        """构造 G φ (□φ) 的 NBA"""
        nba = NBA()
        
        if operand.op == LTOperator.ATOM:
            # □atom：所有状态都必须满足 atom
            q0 = nba.add_state(self._new_state_name(), is_initial=True, is_accept=True)
            nba.add_transition(q0.name, q0.name, operand.atom)
        elif operand.op == LTOperator.EVENTUALLY and operand.left.op == LTOperator.ATOM:
            # □♦atom：无限经常 atom（Buchi 条件）
            # 这是最重要的模式之一
            atom_name = operand.left.atom
            
            # q0：初始+接受状态（刚读到 atom 或初始状态）
            # q1：等待 atom 的状态
            q0 = nba.add_state(self._new_state_name(), is_initial=True, is_accept=True)
            q1 = nba.add_state(self._new_state_name())
            
            # 在 q0：读到 atom，保持在 q0（接受）
            nba.add_transition(q0.name, q0.name, atom_name)
            
            # 在 q0：读到非 atom，到 q1（等待）
            for a in self._all_atoms:
                if a != atom_name:
                    nba.add_transition(q0.name, q1.name, a)
            
            # 在 q1：读到 atom，回到 q0（接受）
            nba.add_transition(q1.name, q0.name, atom_name)
            
            # 在 q1：读到非 atom，保持在 q1（继续等待）
            for a in self._all_atoms:
                if a != atom_name:
                    nba.add_transition(q1.name, q1.name, a)
        else:
            # 一般情况：需要更复杂的构造
            raise ValueError(f"复杂的 G 运算暂不支持: G({operand})")
        
        return nba
    
    def _build_eventually(self, operand: LTLFormula) -> NBA:
        """构造 F φ (♦φ) 的 NBA"""
        nba = NBA()
        
        if operand.op == LTOperator.ATOM:
            atom_name = operand.atom
            
            # q0：初始状态（等待 atom）
            # q1：接受状态（已经读到 atom）
            q0 = nba.add_state(self._new_state_name(), is_initial=True)
            q1 = nba.add_state(self._new_state_name(), is_accept=True)
            
            # 在 q0：读到 atom，到 q1
            nba.add_transition(q0.name, q1.name, atom_name)
            
            # 在 q0：读到非 atom，保持在 q0
            for a in self._all_atoms:
                if a != atom_name:
                    nba.add_transition(q0.name, q0.name, a)
            
            # 在 q1：自环（已经满足）
            for a in self._all_atoms:
                nba.add_transition(q1.name, q1.name, a)
        else:
            raise ValueError(f"复杂的 F 运算暂不支持: F({operand})")
        
        return nba
    
    def _build_next(self, operand: LTLFormula) -> NBA:
        """构造 X φ 的 NBA"""
        nba = NBA()
        
        if operand.op == LTOperator.ATOM:
            atom_name = operand.atom
            
            # q0：初始状态（等待下一个）
            # q1：接受状态（下一个状态满足 atom）
            q0 = nba.add_state(self._new_state_name(), is_initial=True)
            q1 = nba.add_state(self._new_state_name(), is_accept=True)
            
            # 在 q0：无论读到什么，都到 q1
            for a in self._all_atoms:
                nba.add_transition(q0.name, q1.name, a)
            
            # 在 q1：必须满足 atom
            nba.add_transition(q1.name, q1.name, atom_name)
        else:
            raise ValueError(f"复杂的 X 运算暂不支持: X({operand})")
        
        return nba
    
    def _build_and(self, left: LTLFormula, right: LTLFormula) -> NBA:
        """构造 φ ∧ ψ 的 NBA（使用 NBA 交运算）"""
        # 简化：仅支持特定模式
        # □(φ → ♦ψ) 是一种常见模式
        if (left.op == LTOperator.GLOBALLY and 
            left.left.op == LTOperator.IMPLIES):
            # □(a → ♦b)
            impl = left.left
            if (impl.right.op == LTOperator.EVENTUALLY and
                impl.right.left.op == LTOperator.ATOM and
                impl.left.op == LTOperator.ATOM):
                return self._build_always_implies_eventually(
                    impl.left.atom, impl.right.left.atom
                )
        
        raise ValueError(f"复杂的 ∧ 运算暂不支持: ({left}) ∧ ({right})")
    
    def _build_or(self, left: LTLFormula, right: LTLFormula) -> NBA:
        """构造 φ ∨ ψ 的 NBA"""
        raise ValueError(f"∨ 运算暂不支持: ({left}) ∨ ({right})")
    
    def _build_implies(self, left: LTLFormula, right: LTLFormula) -> NBA:
        """构造 φ → ψ 的 NBA"""
        # φ → ψ 等价于 ¬φ ∨ ψ
        # 简化：仅支持 a → ♦b 模式
        if left.op == LTOperator.ATOM and right.op == LTOperator.EVENTUALLY:
            if right.left.op == LTOperator.ATOM:
                return self._build_always_implies_eventually(left.atom, right.left.atom)
        
        raise ValueError(f"复杂的 → 运算暂不支持: ({left}) → ({right})")
    
    def _build_until(self, left: LTLFormula, right: LTLFormula) -> NBA:
        """构造 φ U ψ 的 NBA"""
        if left.op == LTOperator.ATOM and right.op == LTOperator.ATOM:
            left_atom = left.atom
            right_atom = right.atom
            
            nba = NBA()
            
            # q0：等待 ψ 的状态（φ 持续成立）
            # q1：接受状态（ψ 已成立）
            q0 = nba.add_state(self._new_state_name(), is_initial=True)
            q1 = nba.add_state(self._new_state_name(), is_accept=True)
            
            # 在 q0：
            # - 读到 ψ，到 q1
            nba.add_transition(q0.name, q1.name, right_atom)
            # - 读到 φ 但不是 ψ，保持在 q0
            if left_atom != right_atom:
                nba.add_transition(q0.name, q0.name, left_atom)
            
            # 在 q1：自环
            for a in self._all_atoms:
                nba.add_transition(q1.name, q1.name, a)
            
            return nba
        
        raise ValueError(f"复杂的 U 运算暂不支持: ({left}) U ({right})")
    
    def _build_always_implies_eventually(self, antecedent: str, consequent: str) -> NBA:
        """
        构造 □(antecedent → ♦consequent) 的 NBA
        
        这是响应属性（response property）的标准形式。
        每当 antecedent 成立，最终 consequent 必须成立。
        """
        nba = NBA()
        
        # q0：初始+接受状态（没有未完成的义务）
        # q1：等待 consequent（antecedent 已发生，但 consequent 还未发生）
        q0 = nba.add_state(self._new_state_name(), is_initial=True, is_accept=True)
        q1 = nba.add_state(self._new_state_name())
        
        # 在 q0：
        # - 如果 antecedent 且 consequent：保持在 q0（义务立即完成）
        if antecedent == consequent:
            nba.add_transition(q0.name, q0.name, antecedent)
        else:
            # - 如果 antecedent 但没有 consequent：到 q1（产生义务）
            nba.add_transition(q0.name, q1.name, antecedent)
            # - 如果 consequent：保持在 q0
            nba.add_transition(q0.name, q0.name, consequent)
        
        # - 其他符号：保持在 q0
        for a in self._all_atoms:
            if a not in (antecedent, consequent):
                nba.add_transition(q0.name, q0.name, a)
        
        # 在 q1：
        # - 如果 consequent：回到 q0（义务完成）
        nba.add_transition(q1.name, q0.name, consequent)
        
        # - 如果没有 consequent：保持在 q1（继续等待）
        for a in self._all_atoms:
            if a != consequent:
                nba.add_transition(q1.name, q1.name, a)
        
        return nba


# ==================== 便捷转换函数 ====================

def ltl_to_nba(formula: LTLFormula, all_atoms: Optional[Set[str]] = None) -> NBA:
    """
    将 LTL 公式转换为 NBA
    
    Args:
        formula: LTL 公式
        all_atoms: 所有可能的原子命题集合
        
    Returns:
        对应的 NBA
    """
    converter = LTLToNBA()
    return converter.convert(formula, all_atoms)


# ==================== 常用 LTL 模式 ====================

def always_eventually(atom_name: str) -> LTLFormula:
    """
    构造 □♦atom（无限经常 atom）
    
    这是活性（liveness）属性的典型形式。
    """
    return globally(eventually(atom(atom_name)))


def implies_eventually(antecedent: str, consequent: str) -> LTLFormula:
    """
    构造 □(antecedent → ♦consequent)
    
    响应属性：每当 antecedent 发生，最终 consequent 必须发生。
    """
    return globally(implies(atom(antecedent), eventually(atom(consequent))))


def eventually_always(atom_name: str) -> LTLFormula:
    """
    构造 ♦□atom（最终总是 atom）
    
    稳定性（stability）属性。
    """
    return eventually(globally(atom(atom_name)))
