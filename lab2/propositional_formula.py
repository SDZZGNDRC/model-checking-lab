"""
实验二：命题公式解析器与求值器

本模块实现命题逻辑的公式解析和求值，支持：
- 原子命题（如：crit0, wait1）
- 逻辑运算符：非（¬, !, ~）、与（∧, &&, &）、或（∨, ||, |）
- 括号分组

为实验二的不变性检查提供基础支持。
"""

from typing import Set, Optional, Dict, Callable
from dataclasses import dataclass
from enum import Enum, auto
import re


class TokenType(Enum):
    """词法单元类型"""
    ATOM = auto()       # 原子命题
    NOT = auto()        # 非 (¬, !, ~)
    AND = auto()        # 与 (∧, &&, &)
    OR = auto()         # 或 (∨, ||, |)
    LPAREN = auto()     # 左括号
    RPAREN = auto()     # 右括号
    EOF = auto()        # 结束符


@dataclass
class Token:
    """词法单元"""
    type: TokenType
    value: str
    
    def __repr__(self) -> str:
        return f"Token({self.type.name}, '{self.value}')"


class Lexer:
    """
    词法分析器
    
    将输入字符串转换为词法单元序列
    """
    
    # 运算符映射
    OP_MAP = {
        '¬': TokenType.NOT,
        '!': TokenType.NOT,
        '~': TokenType.NOT,
        '∧': TokenType.AND,
        '&&': TokenType.AND,
        '&': TokenType.AND,
        '∨': TokenType.OR,
        '||': TokenType.OR,
        '|': TokenType.OR,
        '(': TokenType.LPAREN,
        ')': TokenType.RPAREN,
    }
    
    def __init__(self, text: str):
        self.text = text.strip()
        self.pos = 0
        self.length = len(self.text)
    
    def tokenize(self) -> list[Token]:
        """将输入字符串转换为词法单元列表"""
        tokens = []
        
        while self.pos < self.length:
            char = self.text[self.pos]
            
            # 跳过空白字符
            if char.isspace():
                self.pos += 1
                continue
            
            # 检查双字符运算符 (&&, ||)
            if self.pos + 1 < self.length:
                two_char = self.text[self.pos:self.pos + 2]
                if two_char in self.OP_MAP:
                    tokens.append(Token(self.OP_MAP[two_char], two_char))
                    self.pos += 2
                    continue
            
            # 检查单字符运算符
            if char in self.OP_MAP:
                tokens.append(Token(self.OP_MAP[char], char))
                self.pos += 1
                continue
            
            # 解析原子命题（标识符）
            if char.isalpha() or char == '_':
                atom = self._read_atom()
                tokens.append(Token(TokenType.ATOM, atom))
                continue
            
            raise ValueError(f"非法字符: '{char}' 在位置 {self.pos}")
        
        tokens.append(Token(TokenType.EOF, ''))
        return tokens
    
    def _read_atom(self) -> str:
        """读取原子命题标识符"""
        start = self.pos
        while self.pos < self.length and (self.text[self.pos].isalnum() or self.text[self.pos] == '_'):
            self.pos += 1
        return self.text[start:self.pos]


class Formula:
    """
    命题公式基类
    
    所有公式类型的抽象基类，定义求值接口
    """
    
    def evaluate(self, labels: Set[str]) -> bool:
        """
        在给定标签集合下求值
        
        Args:
            labels: 状态的原子命题标签集合
            
        Returns:
            公式真值
        """
        raise NotImplementedError
    
    def get_atoms(self) -> Set[str]:
        """获取公式中所有原子命题"""
        raise NotImplementedError
    
    def __repr__(self) -> str:
        raise NotImplementedError
    
    def __str__(self) -> str:
        return self.__repr__()


class Atom(Formula):
    """原子命题"""
    
    def __init__(self, name: str):
        self.name = name
    
    def evaluate(self, labels: Set[str]) -> bool:
        return self.name in labels
    
    def get_atoms(self) -> Set[str]:
        return {self.name}
    
    def __repr__(self) -> str:
        return self.name


class Not(Formula):
    """非运算"""
    
    def __init__(self, operand: Formula):
        self.operand = operand
    
    def evaluate(self, labels: Set[str]) -> bool:
        return not self.operand.evaluate(labels)
    
    def get_atoms(self) -> Set[str]:
        return self.operand.get_atoms()
    
    def __repr__(self) -> str:
        return f"¬({self.operand})"


class And(Formula):
    """与运算"""
    
    def __init__(self, left: Formula, right: Formula):
        self.left = left
        self.right = right
    
    def evaluate(self, labels: Set[str]) -> bool:
        return self.left.evaluate(labels) and self.right.evaluate(labels)
    
    def get_atoms(self) -> Set[str]:
        return self.left.get_atoms() | self.right.get_atoms()
    
    def __repr__(self) -> str:
        return f"({self.left} ∧ {self.right})"


class Or(Formula):
    """或运算"""
    
    def __init__(self, left: Formula, right: Formula):
        self.left = left
        self.right = right
    
    def evaluate(self, labels: Set[str]) -> bool:
        return self.left.evaluate(labels) or self.right.evaluate(labels)
    
    def get_atoms(self) -> Set[str]:
        return self.left.get_atoms() | self.right.get_atoms()
    
    def __repr__(self) -> str:
        return f"({self.left} ∨ {self.right})"


class Parser:
    """
    递归下降解析器
    
    语法规则（优先级从低到高）：
    - expr    := or_expr
    - or_expr := and_expr ( '∨' and_expr )*
    - and_expr:= not_expr ( '∧' not_expr )*
    - not_expr:= '¬' not_expr | primary
    - primary := ATOM | '(' expr ')'
    """
    
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.pos = 0
    
    def parse(self) -> Formula:
        """解析公式"""
        result = self._parse_or()
        if self._current().type != TokenType.EOF:
            raise ValueError(f"意外的词法单元: {self._current()}")
        return result
    
    def _current(self) -> Token:
        """获取当前词法单元"""
        return self.tokens[self.pos]
    
    def _advance(self) -> Token:
        """前进到下一个词法单元"""
        token = self._current()
        if self.pos < len(self.tokens) - 1:
            self.pos += 1
        return token
    
    def _expect(self, token_type: TokenType) -> Token:
        """期望特定类型的词法单元"""
        if self._current().type != token_type:
            raise ValueError(f"期望 {token_type.name}，但得到 {self._current().type.name}")
        return self._advance()
    
    def _parse_or(self) -> Formula:
        """解析或表达式"""
        left = self._parse_and()
        
        while self._current().type == TokenType.OR:
            self._advance()
            right = self._parse_and()
            left = Or(left, right)
        
        return left
    
    def _parse_and(self) -> Formula:
        """解析与表达式"""
        left = self._parse_not()
        
        while self._current().type == TokenType.AND:
            self._advance()
            right = self._parse_not()
            left = And(left, right)
        
        return left
    
    def _parse_not(self) -> Formula:
        """解析非表达式"""
        if self._current().type == TokenType.NOT:
            self._advance()
            operand = self._parse_not()
            return Not(operand)
        
        return self._parse_primary()
    
    def _parse_primary(self) -> Formula:
        """解析基本表达式（原子或括号组）"""
        token = self._current()
        
        if token.type == TokenType.ATOM:
            self._advance()
            return Atom(token.value)
        
        if token.type == TokenType.LPAREN:
            self._advance()
            expr = self._parse_or()
            self._expect(TokenType.RPAREN)
            return expr
        
        raise ValueError(f"意外的词法单元: {token}")


class PropositionalFormula:
    """
    命题公式包装类
    
    提供便捷的公式解析和求值接口
    """
    
    def __init__(self, formula: Formula):
        self.formula = formula
    
    @staticmethod
    def parse(text: str) -> 'PropositionalFormula':
        """
        从字符串解析公式
        
        Args:
            text: 公式字符串，如 "¬(crit0 ∧ crit1)"
            
        Returns:
            PropositionalFormula 对象
            
        Examples:
            >>> f = PropositionalFormula.parse("¬(crit0 ∧ crit1)")
            >>> f.evaluate({"crit0"})  # True
            >>> f.evaluate({"crit0", "crit1"})  # False
        """
        lexer = Lexer(text)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        formula = parser.parse()
        return PropositionalFormula(formula)
    
    def evaluate(self, labels: Set[str]) -> bool:
        """
        在给定标签集合下求值
        
        Args:
            labels: 状态的原子命题标签集合
            
        Returns:
            公式真值
        """
        return self.formula.evaluate(labels)
    
    def get_atoms(self) -> Set[str]:
        """获取公式中所有原子命题"""
        return self.formula.get_atoms()
    
    def __repr__(self) -> str:
        return repr(self.formula)
    
    def __str__(self) -> str:
        return str(self.formula)


def parse_formula(text: str) -> PropositionalFormula:
    """
    便捷函数：解析公式字符串
    
    Args:
        text: 公式字符串
        
    Returns:
        PropositionalFormula 对象
    """
    return PropositionalFormula.parse(text)


# 常用公式构造函数
def atom(name: str) -> PropositionalFormula:
    """创建原子命题公式"""
    return PropositionalFormula(Atom(name))


def neg(formula: PropositionalFormula) -> PropositionalFormula:
    """创建非运算公式"""
    return PropositionalFormula(Not(formula.formula))


def conj(left: PropositionalFormula, right: PropositionalFormula) -> PropositionalFormula:
    """创建与运算公式"""
    return PropositionalFormula(And(left.formula, right.formula))


def disj(left: PropositionalFormula, right: PropositionalFormula) -> PropositionalFormula:
    """创建或运算公式"""
    return PropositionalFormula(Or(left.formula, right.formula))
