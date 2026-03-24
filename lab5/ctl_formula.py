"""
实验五：CTL 公式表示与解析

本模块实现 CTL (Computation Tree Logic) 公式的表示和解析：
- CTL 支持分支时间属性
- 基本算子：EX, EU, EG
- 导出算子：EF, AF, AG, AX, AU 等（通过 De Morgan 律）

CTL 语法：
φ ::= true | false | p | ¬φ | φ ∧ φ | φ ∨ φ | φ → φ
    | EX φ | AX φ
    | EF φ | AF φ
    | EG φ | AG φ
    | E[φ U φ] | A[φ U φ]
"""

from typing import Set, Optional
from dataclasses import dataclass
from enum import Enum, auto


class CTLOp(Enum):
    """CTL 操作符类型"""
    TRUE = auto()
    FALSE = auto()
    ATOM = auto()       # 原子命题
    NOT = auto()        # ¬
    AND = auto()        # ∧
    OR = auto()         # ∨
    IMPLIES = auto()    # →
    
    # 路径量词 + 时序算子
    EX = auto()         # ∃○ (存在下一个)
    AX = auto()         # ∀○ (全称下一个)
    EF = auto()         # ∃◇ (存在最终)
    AF = auto()         # ∀◇ (全称最终)
    EG = auto()         # ∃□ (存在总是)
    AG = auto()         # ∀□ (全称总是)
    EU = auto()         # ∃U (存在直到)
    AU = auto()         # ∀U (全称直到)


@dataclass
class CTLFormula:
    """
    CTL 公式类
    
    使用树形结构表示 CTL 公式
    """
    op: CTLOp
    atom: Optional[str] = None      # 原子命题名称（仅 ATOM 使用）
    left: Optional['CTLFormula'] = None   # 左子公式
    right: Optional['CTLFormula'] = None  # 右子公式（二元操作符使用）
    
    def __repr__(self) -> str:
        """字符串表示"""
        if self.op == CTLOp.TRUE:
            return "true"
        elif self.op == CTLOp.FALSE:
            return "false"
        elif self.op == CTLOp.ATOM:
            return self.atom or ""
        elif self.op == CTLOp.NOT:
            return f"¬{self.left}"
        elif self.op == CTLOp.AND:
            return f"({self.left} ∧ {self.right})"
        elif self.op == CTLOp.OR:
            return f"({self.left} ∨ {self.right})"
        elif self.op == CTLOp.IMPLIES:
            return f"({self.left} → {self.right})"
        elif self.op == CTLOp.EX:
            return f"∃○{self.left}"
        elif self.op == CTLOp.AX:
            return f"∀○{self.left}"
        elif self.op == CTLOp.EF:
            return f"∃◇{self.left}"
        elif self.op == CTLOp.AF:
            return f"∀◇{self.left}"
        elif self.op == CTLOp.EG:
            return f"∃□{self.left}"
        elif self.op == CTLOp.AG:
            return f"∀□{self.left}"
        elif self.op == CTLOp.EU:
            return f"∃[{self.left} U {self.right}]"
        elif self.op == CTLOp.AU:
            return f"∀[{self.left} U {self.right}]"
        return "unknown"
    
    def __str__(self) -> str:
        return self.__repr__()
    
    def get_atoms(self) -> Set[str]:
        """获取公式中所有原子命题"""
        atoms = set()
        if self.op == CTLOp.ATOM and self.atom:
            atoms.add(self.atom)
        if self.left:
            atoms.update(self.left.get_atoms())
        if self.right:
            atoms.update(self.right.get_atoms())
        return atoms


# ==================== 便捷构造函数 ====================

def ctl_true() -> CTLFormula:
    """true"""
    return CTLFormula(CTLOp.TRUE)


def ctl_false() -> CTLFormula:
    """false"""
    return CTLFormula(CTLOp.FALSE)


def atom(p: str) -> CTLFormula:
    """原子命题"""
    return CTLFormula(CTLOp.ATOM, atom=p)


def neg(phi: CTLFormula) -> CTLFormula:
    """¬φ"""
    return CTLFormula(CTLOp.NOT, left=phi)


def conj(phi1: CTLFormula, phi2: CTLFormula) -> CTLFormula:
    """φ1 ∧ φ2"""
    return CTLFormula(CTLOp.AND, left=phi1, right=phi2)


def disj(phi1: CTLFormula, phi2: CTLFormula) -> CTLFormula:
    """φ1 ∨ φ2"""
    return CTLFormula(CTLOp.OR, left=phi1, right=phi2)


def implies(phi1: CTLFormula, phi2: CTLFormula) -> CTLFormula:
    """φ1 → φ2"""
    return CTLFormula(CTLOp.IMPLIES, left=phi1, right=phi2)


def ex(phi: CTLFormula) -> CTLFormula:
    """∃○φ (存在下一个)"""
    return CTLFormula(CTLOp.EX, left=phi)


def ax(phi: CTLFormula) -> CTLFormula:
    """∀○φ (全称下一个)"""
    return CTLFormula(CTLOp.AX, left=phi)


def ef(phi: CTLFormula) -> CTLFormula:
    """∃◇φ (存在最终)"""
    return CTLFormula(CTLOp.EF, left=phi)


def af(phi: CTLFormula) -> CTLFormula:
    """∀◇φ (全称最终)"""
    return CTLFormula(CTLOp.AF, left=phi)


def eg(phi: CTLFormula) -> CTLFormula:
    """∃□φ (存在总是)"""
    return CTLFormula(CTLOp.EG, left=phi)


def ag(phi: CTLFormula) -> CTLFormula:
    """∀□φ (全称总是)"""
    return CTLFormula(CTLOp.AG, left=phi)


def eu(phi1: CTLFormula, phi2: CTLFormula) -> CTLFormula:
    """∃[φ1 U φ2] (存在直到)"""
    return CTLFormula(CTLOp.EU, left=phi1, right=phi2)


def au(phi1: CTLFormula, phi2: CTLFormula) -> CTLFormula:
    """∀[φ1 U φ2] (全称直到)"""
    return CTLFormula(CTLOp.AU, left=phi1, right=phi2)


# ==================== 导出算子（通过基本算子定义）====================

def ef_via_eg(phi: CTLFormula) -> CTLFormula:
    """
    EF φ = E[true U φ]
    使用 EU 定义 EF
    """
    return eu(ctl_true(), phi)


def af_via_au(phi: CTLFormula) -> CTLFormula:
    """
    AF φ = A[true U φ]
    使用 AU 定义 AF
    """
    return au(ctl_true(), phi)


def eg_via_af(phi: CTLFormula) -> CTLFormula:
    """
    EG φ = ¬AF¬φ
    使用 AF 和否定定义 EG
    """
    return neg(af(neg(phi)))


def ag_via_ef(phi: CTLFormula) -> CTLFormula:
    """
    AG φ = ¬EF¬φ
    使用 EF 和否定定义 AG
    """
    return neg(ef(neg(phi)))


def ax_via_ex(phi: CTLFormula) -> CTLFormula:
    """
    AX φ = ¬EX¬φ
    使用 EX 和否定定义 AX
    """
    return neg(ex(neg(phi)))


def au_via_eg_eu(phi1: CTLFormula, phi2: CTLFormula) -> CTLFormula:
    """
    A[φ1 U φ2] = ¬(E[¬φ2 U (¬φ1 ∧ ¬φ2)] ∨ EG¬φ2)
    使用 EG 和 EU 定义 AU
    """
    not_phi1 = neg(phi1)
    not_phi2 = neg(phi2)
    return neg(disj(
        eu(not_phi2, conj(not_phi1, not_phi2)),
        eg(not_phi2)
    ))


# ==================== 常用 CTL 模式 ====================

def mutual_exclusion(crit1: str = "crit1", crit2: str = "crit2") -> CTLFormula:
    """
    互斥属性：∀□(¬crit1 ∨ ¬crit2)
    即：所有路径上所有状态都不满足 crit1 和 crit2 同时成立
    """
    return ag(disj(neg(atom(crit1)), neg(atom(crit2))))


def no_starvation(wait: str = "wait", crit: str = "crit") -> CTLFormula:
    """
    无饥饿属性：∀□(wait → ∀◇crit)
    即：所有路径上，如果处于 wait 状态，则最终一定能进入 crit 状态
    """
    return ag(implies(atom(wait), af(atom(crit))))


def reachability(target: str) -> CTLFormula:
    """
    可达性：∃◇target
    即：存在一条路径能到达目标状态
    """
    return ef(atom(target))


def safety(invariant: str) -> CTLFormula:
    """
    安全性：∀□invariant
    即：所有路径上所有状态都满足不变式
    """
    return ag(atom(invariant))


def response(trigger: str, response: str) -> CTLFormula:
    """
    响应属性：∀□(trigger → ∀◇response)
    即：所有路径上，trigger 发生后 response 最终一定会发生
    """
    return ag(implies(atom(trigger), af(atom(response))))


# ==================== 公式解析（简化版）====================

class CTLParser:
    """
    CTL 公式解析器（简化版）
    
    支持从字符串解析 CTL 公式
    """
    
    def __init__(self, text: str):
        self.text = text.replace(" ", "")
        self.pos = 0
    
    def parse(self) -> CTLFormula:
        """解析公式"""
        result = self._parse_formula()
        if self.pos < len(self.text):
            raise ValueError(f"Unexpected character at position {self.pos}: {self.text[self.pos:]}")
        return result
    
    def _parse_formula(self) -> CTLFormula:
        """解析公式（处理蕴含）"""
        left = self._parse_or()
        if self._match("->"):
            right = self._parse_formula()
            return implies(left, right)
        return left
    
    def _parse_or(self) -> CTLFormula:
        """解析或"""
        left = self._parse_and()
        while self._match("|") or self._match("||"):
            right = self._parse_and()
            left = disj(left, right)
        return left
    
    def _parse_and(self) -> CTLFormula:
        """解析与"""
        left = self._parse_unary()
        while True:
            # 先尝试匹配 &&，再匹配 &
            if self._match("&&"):
                right = self._parse_unary()
                left = conj(left, right)
            elif self._match("&"):
                right = self._parse_unary()
                left = conj(left, right)
            else:
                break
        return left
    
    def _parse_unary(self) -> CTLFormula:
        """解析一元操作"""
        # 否定
        if self._match("!") or self._match("¬"):
            return neg(self._parse_unary())
        
        # CTL 时序算子
        if self._match("EX"):
            return ex(self._parse_unary())
        if self._match("AX"):
            return ax(self._parse_unary())
        if self._match("EF"):
            return ef(self._parse_unary())
        if self._match("AF"):
            return af(self._parse_unary())
        if self._match("EG"):
            return eg(self._parse_unary())
        if self._match("AG"):
            return ag(self._parse_unary())
        
        # EU 和 AU
        if self._match("E["):
            left = self._parse_formula()
            if not self._match("U"):
                raise ValueError("Expected 'U' in EU formula")
            right = self._parse_formula()
            if not self._match("]"):
                raise ValueError("Expected ']' in EU formula")
            return eu(left, right)
        
        if self._match("A["):
            left = self._parse_formula()
            if not self._match("U"):
                raise ValueError("Expected 'U' in AU formula")
            right = self._parse_formula()
            if not self._match("]"):
                raise ValueError("Expected ']' in AU formula")
            return au(left, right)
        
        return self._parse_primary()
    
    def _parse_primary(self) -> CTLFormula:
        """解析基本元素"""
        # 括号
        if self._match("("):
            result = self._parse_formula()
            if not self._match(")"):
                raise ValueError("Expected ')'")
            return result
        
        # true/false
        if self._match("true"):
            return ctl_true()
        if self._match("false"):
            return ctl_false()
        
        # 原子命题
        return self._parse_atom()
    
    def _parse_atom(self) -> CTLFormula:
        """解析原子命题"""
        start = self.pos
        while self.pos < len(self.text) and (self.text[self.pos].isalnum() or self.text[self.pos] == "_"):
            self.pos += 1
        if start == self.pos:
            raise ValueError(f"Expected atom at position {self.pos}")
        return atom(self.text[start:self.pos])
    
    def _match(self, s: str) -> bool:
        """尝试匹配字符串"""
        if self.text[self.pos:self.pos+len(s)] == s:
            self.pos += len(s)
            return True
        return False


def parse_ctl(formula_str: str) -> CTLFormula:
    """
    从字符串解析 CTL 公式
    
    Args:
        formula_str: 公式字符串
        
    Returns:
        CTLFormula 对象
        
    Examples:
        >>> parse_ctl("AG(!crit1 | !crit2)")
        >>> parse_ctl("EF(target)")
        >>> parse_ctl("AG(wait -> AF(crit))")
    """
    parser = CTLParser(formula_str)
    return parser.parse()
