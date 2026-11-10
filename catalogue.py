"""Ponto de implementação das regras declarativas do enunciado."""
from patterns import REG, ResultClass, Need, Args, Pattern, Rule, imm12, neg_imm12, pow2, IMM12, POW2, signed_literal
from previous.ast_nodes import BinaryExpr, BinaryOperator, BoolLiteral, IdentifierExpr, IntLiteral, UnaryExpr, UnaryOperator

"""
Rule: nome, onde vai salvar, padrão, custo, ação
Pattern: tipo?, operador?, filhos = (), predicado?
Args: resultado da subárvore de cada argumento
Need: resultado da subárvore que ocupa este ponto do padrão
"""

def _add_rule(rules, name, result, kind, operator = None, kids = (), predicate = None, cost = 1, action = None):
    pattern = Pattern(kind, operator, kids, predicate)
    rules.append(Rule(name, result, pattern, cost, action or name))

def catalogue():
    """Codifique o catálogo do enunciado com Rule e Pattern."""

    rules = []

    # Operações folha
    _add_rule(rules, "literal_int_reg", result=REG, kind=IntLiteral, predicate=signed_literal, cost=1, action="literal_int_reg")
    _add_rule(rules, "literal_bool_reg", result=REG, kind=BoolLiteral, cost=1, action="literal_bool_reg")
    _add_rule(rules, "identifier_reg", result=REG, kind=IdentifierExpr, cost=0, action="identifier_reg")
    _add_rule(rules, "literal_imm12", result=IMM12, kind=IntLiteral, predicate=imm12, cost=0, action="literal_imm12")
    _add_rule(rules, "literal_pow2", result=POW2, kind=IntLiteral, predicate=pow2, cost=0, action="literal_pow2")

    # Operações aritméticas
    _add_rule(rules, "neg_reg", result=REG, kind=UnaryExpr, operator=UnaryOperator.NEGATE, kids=(Need(REG),), cost=1, action="emit_neg")
    # Operações aritméticas REG p REG
    _add_rule(rules, "arith_add", result=REG, kind=BinaryExpr, operator=BinaryOperator.ADD, kids=(Need(REG), Need(REG)), cost=1, action="emit_arith")
    _add_rule(rules, "arith_sub", result=REG, kind=BinaryExpr, operator=BinaryOperator.SUBTRACT, kids=(Need(REG), Need(REG)), cost=1, action="emit_arith")
    _add_rule(rules, "arith_mul", result=REG, kind=BinaryExpr, operator=BinaryOperator.MULTIPLY, kids=(Need(REG), Need(REG)), cost=1, action="emit_arith")
    _add_rule(rules, "arith_div", result=REG, kind=BinaryExpr, operator=BinaryOperator.DIVIDE, kids=(Need(REG), Need(REG)), cost=1, action="emit_arith")
    # Operações aritméticas REG p IMM12 ou IMM12 p REG
    _add_rule(rules, "sum_imm_right", result=REG, kind=BinaryExpr, operator=BinaryOperator.ADD,kids=(Need(REG), Need(IMM12)), cost=1, action="emit_sum_imm")
    _add_rule(rules, "sum_imm_left", result=REG, kind=BinaryExpr, operator=BinaryOperator.ADD,kids=(Need(IMM12), Need(REG)), cost=1, action="emit_sum_imm")
    _add_rule(rules, "sub_imm_right", result=REG, kind=BinaryExpr, operator=BinaryOperator.SUBTRACT,kids=(Need(REG), Pattern(kind=IntLiteral, predicate=neg_imm12)), cost=1, action="emit_sub_imm") # Oposto deve caber no imediato
    # Operações aritméticas REG p POW2 ou POW2 p REG
    _add_rule(rules, "mul_pow2_right", result=REG, kind=IntLiteral, operator=BinaryOperator.MULTIPLY, kids=(Need(REG), Pattern(kind=IntLiteral, predicate=pow2)), cost=1, action="emit_mul_pow2_right")



# Regra e emissão Custo
# Literal inteiro com sinal ou bool para REG, com Li. 1
# Identificador para REG, reutilizando o VReg do símbolo. 0
# Literal elegível para IMM12 ou POW2, sem instrução. 0
# Negação aritmética de REG para REG, com Neg. 1
# Aritmética geral de dois REG para REG. 1
# Soma REG/IMM12 ou IMM12/REG, com Addi. 1
# Subtração REG menos literal cujo oposto cabe no imediato, com Addi. 1
# Multiplicação REG/POW2 ou POW2/REG, com Slli. 1
# Menor ou maior de dois REG para REG, com Slt. 1
# Menor ou igual, maior ou igual para REG, com Slt e Seqz. 2
# Igualdade/desigualdade para REG, com Xor e Seqz/Snez. 2
# Comparação de dois REG para COND, branch direto e Jump. 2
# Negação lógica de REG para REG, com Seqz. 1
# Negação lógica de COND para COND, invertendo destinos. 0
# &&/|| de dois COND para COND. 0
# &&/|| de dois COND para REG, com duas Li e um Jump. 3
# Literal bool para COND, com Jump. 1
# Identificador bool para COND, com branch e Jump. 2
# Chamada com argumentos REG para REG ou EFFECT, com Call. 1
# Chamada bool com argumentos REG para COND, com chamada e desvios. 3

    return rules