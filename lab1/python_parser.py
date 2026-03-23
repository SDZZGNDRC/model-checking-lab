"""
Python 程序解析器

将 Python 源代码解析为程序图 (Program Graph)。

支持的语法:
- 变量赋值: x = 0, x = x + 1
- 布尔变量: flag = True/False
- 条件语句: if/else
- 循环语句: while
- 共享变量标记: # @shared 注释

取值范围自动推断:
- 布尔变量: {True, False}
- 整数变量: 从赋值和条件表达式中收集
"""

import ast
import re
from typing import Set, Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field

from program_graph import ProgramGraph, Location, Action


@dataclass
class VariableInfo:
    """变量信息"""
    name: str
    domain: Set[Any] = field(default_factory=set)
    initial_value: Any = None
    is_shared: bool = False
    is_boolean: bool = False


class PythonToProgramGraph:
    """
    Python 代码到程序图的转换器
    
    使用 Python AST 模块解析源代码，构建程序图。
    """
    
    def __init__(self):
        self._variables: Dict[str, VariableInfo] = {}
        self._shared_vars: Set[str] = set()
        self._location_counter = 0
        self._pg: Optional[ProgramGraph] = None
    
    def parse(self, source_code: str, name: str = "P") -> ProgramGraph:
        """
        解析 Python 源代码，返回程序图
        
        Args:
            source_code: Python 源代码字符串
            name: 程序图名称
            
        Returns:
            构建好的 ProgramGraph 对象
        """
        self._variables = {}
        self._shared_vars = set()
        self._location_counter = 0
        self._pg = ProgramGraph(name)
        
        # 1. 提取共享变量标记
        self._extract_shared_vars(source_code)
        
        # 2. 解析 AST
        try:
            tree = ast.parse(source_code)
        except SyntaxError as e:
            raise ValueError(f"Python 语法错误: {e}")
        
        # 3. 第一遍：收集变量信息和推断取值域
        self._collect_variables(tree)
        
        # 4. 第二遍：构建控制流图
        self._build_cfg(tree)
        
        # 5. 声明变量到程序图
        for var_name, var_info in self._variables.items():
            self._pg.declare_variable(
                var_name,
                var_info.domain,
                var_info.initial_value,
                var_info.is_shared
            )
        
        return self._pg
    
    def _extract_shared_vars(self, source: str) -> Set[str]:
        """
        从注释中提取共享变量
        
        支持格式:
        - x = 0  # @shared
        - # @shared: x, y, z
        """
        shared = set()
        
        # 匹配行尾的 # @shared 注释
        pattern1 = r'(\w+)\s*=.*#\s*@shared'
        for match in re.finditer(pattern1, source):
            var_name = match.group(1)
            shared.add(var_name)
        
        # 匹配独立的 # @shared: var1, var2 注释
        pattern2 = r'#\s*@shared\s*:\s*([\w\s,]+?)(?:\n|$)'
        for match in re.finditer(pattern2, source):
            vars_str = match.group(1)
            for var in vars_str.split(','):
                var = var.strip()
                # 过滤掉非变量名的内容
                if var and var.isidentifier():
                    shared.add(var)
        
        self._shared_vars = shared
        return shared
    
    def _collect_variables(self, tree: ast.AST):
        """收集变量信息并推断取值域"""
        
        class VariableCollector(ast.NodeVisitor):
            def __init__(self, parser: 'PythonToProgramGraph'):
                self.parser = parser
            
            def visit_Assign(self, node: ast.Assign):
                """处理赋值语句"""
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        var_name = target.id
                        value = self._extract_value(node.value)
                        
                        if var_name not in self.parser._variables:
                            self.parser._variables[var_name] = VariableInfo(
                                name=var_name,
                                is_shared=var_name in self.parser._shared_vars
                            )
                        
                        var_info = self.parser._variables[var_name]
                        
                        # 设置初始值（第一次赋值）
                        if var_info.initial_value is None and value is not None:
                            var_info.initial_value = value
                        
                        # 更新取值域
                        if value is not None:
                            var_info.domain.add(value)
                        
                        # 检查是否为布尔变量
                        if isinstance(value, bool):
                            var_info.is_boolean = True
                            var_info.domain = {True, False}
                
                self.generic_visit(node)
            
            def visit_AugAssign(self, node: ast.AugAssign):
                """处理增量赋值: x += 1"""
                if isinstance(node.target, ast.Name):
                    var_name = node.target.id
                    
                    if var_name not in self.parser._variables:
                        self.parser._variables[var_name] = VariableInfo(
                            name=var_name,
                            is_shared=var_name in self.parser._shared_vars
                        )
                    
                    # 如果是 x += constant 或 x -= constant，扩展域
                    var_info = self.parser._variables[var_name]
                    if isinstance(node.op, ast.Add) and isinstance(node.value, ast.Constant):
                        delta = node.value.value
                        if isinstance(delta, int):
                            # 扩展域：假设从当前值开始增加
                            new_values = set()
                            for v in list(var_info.domain):
                                if isinstance(v, int):
                                    new_values.add(v + delta)
                            var_info.domain.update(new_values)
                    elif isinstance(node.op, ast.Sub) and isinstance(node.value, ast.Constant):
                        delta = node.value.value
                        if isinstance(delta, int):
                            new_values = set()
                            for v in list(var_info.domain):
                                if isinstance(v, int):
                                    new_values.add(v - delta)
                            var_info.domain.update(new_values)
                
                self.generic_visit(node)
            
            def visit_Compare(self, node: ast.Compare):
                """处理比较表达式，收集比较值"""
                # 收集比较中的常量值
                for comp in node.comparators:
                    if isinstance(comp, ast.Constant):
                        value = comp.value
                        # 如果左侧是变量，将比较值加入其域
                        if isinstance(node.left, ast.Name):
                            var_name = node.left.id
                            if var_name in self.parser._variables:
                                var_info = self.parser._variables[var_name]
                                if isinstance(value, (int, bool)):
                                    var_info.domain.add(value)
                
                self.generic_visit(node)
            
            def _extract_value(self, node: ast.expr) -> Optional[Any]:
                """从 AST 节点提取常量值"""
                if isinstance(node, ast.Constant):
                    return node.value
                elif isinstance(node, ast.NameConstant):  # Python 3.7 兼容
                    return node.value
                elif isinstance(node, ast.Num):  # Python 3.7 兼容
                    return node.n
                return None
        
        collector = VariableCollector(self)
        collector.visit(tree)
        
        # 确保布尔变量有完整的域
        for var_info in self._variables.values():
            if var_info.is_boolean:
                var_info.domain = {True, False}
            # 确保初始值在域中
            if var_info.initial_value is not None:
                var_info.domain.add(var_info.initial_value)
    
    def _new_location(self, prefix: str = "L") -> str:
        """生成新的位置名称"""
        self._location_counter += 1
        return f"{prefix}{self._location_counter}"
    
    def _build_cfg(self, tree: ast.AST):
        """构建控制流图"""
        # 创建入口和出口位置
        entry = self._new_location("entry")
        exit_loc = self._new_location("exit")
        
        self._pg.set_initial_location(entry)
        self._pg.add_location(exit_loc)
        
        # 处理语句序列
        if isinstance(tree, ast.Module):
            self._process_statements(tree.body, entry, exit_loc)
    
    def _process_statements(self, stmts: List[ast.stmt], 
                           entry: str, exit_loc: str) -> str:
        """
        处理语句序列
        
        Args:
            stmts: 语句列表
            entry: 入口位置
            exit_loc: 出口位置
            
        Returns:
            最后一个位置
        """
        if not stmts:
            # 空语句序列，直接连接
            action = Action("skip", {})
            self._pg.add_transition(entry, exit_loc, action, "True")
            return exit_loc
        
        current = entry
        
        for i, stmt in enumerate(stmts):
            is_last = (i == len(stmts) - 1)
            next_loc = exit_loc if is_last else self._new_location()
            
            self._process_statement(stmt, current, next_loc)
            current = next_loc
        
        return current
    
    def _process_statement(self, stmt: ast.stmt, entry: str, exit_loc: str):
        """处理单条语句"""
        if isinstance(stmt, ast.Assign):
            self._process_assign(stmt, entry, exit_loc)
        elif isinstance(stmt, ast.AugAssign):
            self._process_aug_assign(stmt, entry, exit_loc)
        elif isinstance(stmt, ast.If):
            self._process_if(stmt, entry, exit_loc)
        elif isinstance(stmt, ast.While):
            self._process_while(stmt, entry, exit_loc)
        elif isinstance(stmt, ast.Pass):
            self._process_pass(stmt, entry, exit_loc)
        elif isinstance(stmt, ast.Expr):
            # 表达式语句（如函数调用），作为 skip 处理
            self._process_pass(stmt, entry, exit_loc)
        else:
            # 不支持的语句类型，作为 skip
            action = Action(f"skip_{type(stmt).__name__}", {})
            self._pg.add_transition(entry, exit_loc, action, "True")
    
    def _process_assign(self, stmt: ast.Assign, entry: str, exit_loc: str):
        """处理赋值语句"""
        for target in stmt.targets:
            if isinstance(target, ast.Name):
                var_name = target.id
                expr_str = self._ast_to_expr(stmt.value)
                
                action = Action(
                    name=f"{var_name}={expr_str}",
                    effect={var_name: expr_str}
                )
                self._pg.add_transition(entry, exit_loc, action, "True")
    
    def _process_aug_assign(self, stmt: ast.AugAssign, entry: str, exit_loc: str):
        """处理增量赋值语句"""
        if isinstance(stmt.target, ast.Name):
            var_name = stmt.target.id
            op_str = self._op_to_str(stmt.op)
            val_str = self._ast_to_expr(stmt.value)
            expr_str = f"{var_name} {op_str} {val_str}"
            
            action = Action(
                name=f"{var_name}{op_str}={val_str}",
                effect={var_name: expr_str}
            )
            self._pg.add_transition(entry, exit_loc, action, "True")
    
    def _process_if(self, stmt: ast.If, entry: str, exit_loc: str):
        """处理条件语句"""
        condition = self._ast_to_expr(stmt.test)
        neg_condition = f"not ({condition})"
        
        # 处理 then 分支
        then_entry = self._new_location("then")
        action_then = Action(f"if_{condition}", {})
        self._pg.add_transition(entry, then_entry, action_then, condition)
        self._process_statements(stmt.body, then_entry, exit_loc)
        
        # 处理 else 分支
        if stmt.orelse:
            else_entry = self._new_location("else")
            action_else = Action(f"else_{condition}", {})
            self._pg.add_transition(entry, else_entry, action_else, neg_condition)
            self._process_statements(stmt.orelse, else_entry, exit_loc)
        else:
            # 没有 else 分支，直接跳转到出口
            action_skip = Action("skip", {})
            self._pg.add_transition(entry, exit_loc, action_skip, neg_condition)
    
    def _process_while(self, stmt: ast.While, entry: str, exit_loc: str):
        """处理 while 循环"""
        condition = self._ast_to_expr(stmt.test)
        neg_condition = f"not ({condition})"
        
        # 循环体入口
        body_entry = self._new_location("loop_body")
        
        # 进入循环体
        action_enter = Action(f"while_{condition}", {})
        self._pg.add_transition(entry, body_entry, action_enter, condition)
        
        # 处理循环体，回到循环入口
        self._process_statements(stmt.body, body_entry, entry)
        
        # 退出循环
        action_exit = Action(f"exit_while", {})
        self._pg.add_transition(entry, exit_loc, action_exit, neg_condition)
    
    def _process_pass(self, stmt: ast.stmt, entry: str, exit_loc: str):
        """处理 pass 语句"""
        action = Action("skip", {})
        self._pg.add_transition(entry, exit_loc, action, "True")
    
    def _ast_to_expr(self, node: ast.expr) -> str:
        """将 AST 表达式节点转换为字符串"""
        if isinstance(node, ast.Constant):
            return repr(node.value)
        elif isinstance(node, ast.NameConstant):  # Python 3.7 兼容
            return repr(node.value)
        elif isinstance(node, ast.Num):  # Python 3.7 兼容
            return repr(node.n)
        elif isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.BinOp):
            left = self._ast_to_expr(node.left)
            right = self._ast_to_expr(node.right)
            op = self._op_to_str(node.op)
            return f"({left} {op} {right})"
        elif isinstance(node, ast.UnaryOp):
            operand = self._ast_to_expr(node.operand)
            op = self._unary_op_to_str(node.op)
            return f"({op}{operand})"
        elif isinstance(node, ast.Compare):
            left = self._ast_to_expr(node.left)
            parts = [left]
            for op, comp in zip(node.ops, node.comparators):
                op_str = self._cmp_op_to_str(op)
                comp_str = self._ast_to_expr(comp)
                parts.append(op_str)
                parts.append(comp_str)
            return " ".join(parts)
        elif isinstance(node, ast.BoolOp):
            op_str = " and " if isinstance(node.op, ast.And) else " or "
            values = [self._ast_to_expr(v) for v in node.values]
            return f"({op_str.join(values)})"
        else:
            return "?"
    
    def _op_to_str(self, op: ast.operator) -> str:
        """二元运算符转字符串"""
        ops = {
            ast.Add: "+",
            ast.Sub: "-",
            ast.Mult: "*",
            ast.Div: "/",
            ast.Mod: "%",
            ast.FloorDiv: "//",
        }
        return ops.get(type(op), "?")
    
    def _unary_op_to_str(self, op: ast.unaryop) -> str:
        """一元运算符转字符串"""
        ops = {
            ast.Not: "not ",
            ast.USub: "-",
            ast.UAdd: "+",
        }
        return ops.get(type(op), "?")
    
    def _cmp_op_to_str(self, op: ast.cmpop) -> str:
        """比较运算符转字符串"""
        ops = {
            ast.Eq: "==",
            ast.NotEq: "!=",
            ast.Lt: "<",
            ast.LtE: "<=",
            ast.Gt: ">",
            ast.GtE: ">=",
            ast.Is: "is",
            ast.IsNot: "is not",
            ast.In: "in",
            ast.NotIn: "not in",
        }
        return ops.get(type(op), "?")


def parse_python(source_code: str, name: str = "P") -> ProgramGraph:
    """
    便捷函数：将 Python 代码解析为程序图
    
    Args:
        source_code: Python 源代码
        name: 程序图名称
        
    Returns:
        ProgramGraph 对象
    """
    parser = PythonToProgramGraph()
    return parser.parse(source_code, name)


# ==================== 示例程序 ====================

# 简单计数器程序
COUNTER_PROGRAM = '''
x = 0
while x < 3:
    x = x + 1
'''

# Peterson 算法 - 进程 0
PETERSON_P0 = '''
flag0 = False  # @shared
flag1 = False  # @shared
turn = 0       # @shared
pc0 = 0        # 程序计数器: 0=noncrit, 1=set_flag, 2=set_turn, 3=wait, 4=crit, 5=reset
'''

# Peterson 算法 - 进程 1
PETERSON_P1 = '''
flag0 = False  # @shared
flag1 = False  # @shared
turn = 0       # @shared
pc1 = 0        # 程序计数器
'''


if __name__ == "__main__":
    print("=" * 60)
    print("Python 程序解析器测试")
    print("=" * 60)
    
    # 测试简单计数器程序
    print("\n【计数器程序】")
    print(COUNTER_PROGRAM)
    
    pg = parse_python(COUNTER_PROGRAM, "Counter")
    pg.print_info()
    
    print("\n展开为 Transition System:")
    ts = pg.unfold_to_ts()
    ts.print_reachable_graph()
