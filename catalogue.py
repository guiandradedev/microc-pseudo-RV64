"""Ponto de implementação das regras declarativas do enunciado."""
from patterns import REG, ResultClass, Need, Args, Pattern, Rule, imm12, neg_imm12, pow2, IMM12, POW2, signed_literal
from previous.ast_nodes import BinaryExpr, BinaryOperator, BoolLiteral, CallExpr, IdentifierExpr, UnaryExpr, UnaryOperator

"""
Rule: nome, onde vai salvar, padrão (pattern), custo, ação
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
    _add_rule(rules, "literal_int_reg", result=REG, kind=None, predicate=lambda n: signed_literal(n) is not None, cost=1, action="literal_int_reg")
    _add_rule(rules, "literal_bool_reg", result=REG, kind=BoolLiteral, cost=1, action="literal_bool_reg")
    _add_rule(rules, "identifier_reg", result=REG, kind=IdentifierExpr, cost=0, action="identifier_reg")
    _add_rule(rules, "literal_imm12", result=IMM12, kind=None, predicate=imm12, cost=0, action="literal_imm12")
    _add_rule(rules, "literal_pow2", result=POW2, kind=None, predicate=pow2, cost=0, action="literal_pow2")

    # Operações aritméticas
    _add_rule(rules, "neg_reg", result=REG, kind=UnaryExpr, operator=UnaryOperator.NEGATE, kids=(Need(REG),), cost=1, action="emit_neg")
    
    # Operações aritméticas REG p REG
    _add_rule(rules, "arith_add", result=REG, kind=BinaryExpr, operator=BinaryOperator.ADD, kids=(Need(REG), Need(REG)), cost=1, action="emit_arith")
    _add_rule(rules, "arith_sub", result=REG, kind=BinaryExpr, operator=BinaryOperator.SUBTRACT, kids=(Need(REG), Need(REG)), cost=1, action="emit_arith")
    _add_rule(rules, "arith_mul", result=REG, kind=BinaryExpr, operator=BinaryOperator.MULTIPLY, kids=(Need(REG), Need(REG)), cost=1, action="emit_arith")
    _add_rule(rules, "arith_div", result=REG, kind=BinaryExpr, operator=BinaryOperator.DIVIDE, kids=(Need(REG), Need(REG)), cost=1, action="emit_arith")
    _add_rule(rules, "arith_rem", result=REG, kind=BinaryExpr, operator=BinaryOperator.REMAINDER, kids=(Need(REG), Need(REG)), cost=1, action="emit_arith")

    # Operações aritméticas REG p IMM12 ou IMM12 p REG
    _add_rule(rules, "sum_imm_right", result=REG, kind=BinaryExpr, operator=BinaryOperator.ADD,kids=(Need(REG), Need(IMM12)), cost=1, action="emit_sum_imm")
    _add_rule(rules, "sum_imm_left", result=REG, kind=BinaryExpr, operator=BinaryOperator.ADD,kids=(Need(IMM12), Need(REG)), cost=1, action="emit_sum_imm")
    _add_rule(rules, "sub_imm_right", result=REG, kind=BinaryExpr, operator=BinaryOperator.SUBTRACT,kids=(Need(REG), Pattern(predicate=neg_imm12)), cost=1, action="emit_sub_imm") # Oposto deve caber no imediato

    # Operações aritméticas REG p POW2 ou POW2 p REG
    _add_rule(rules, "mul_pow2_right", result=REG, kind=BinaryExpr, operator=BinaryOperator.MULTIPLY, kids=(Need(REG), Need(POW2)), cost=1, action="emit_mul_pow2_right")
    _add_rule(rules, "mul_pow2_left", result=REG, kind=BinaryExpr, operator=BinaryOperator.MULTIPLY, kids=(Need(POW2), Need(REG)), cost=1, action="emit_mul_pow2_left")

    # Menor ou maior de dois REG para REG 
    _add_rule(rules, "slt_reg", result=REG, kind=BinaryExpr, operator=BinaryOperator.LESS, kids=(Need(REG), Need(REG)), cost=1, action="emit_slt")
    _add_rule(rules, "sgt_reg", result=REG, kind=BinaryExpr, operator=BinaryOperator.GREATER, kids=(Need(REG), Need(REG)), cost=1, action="emit_slt")

    # Menor ou igual, maior ou igual para REG, com Slt e Seqz
    _add_rule(rules, "sle_reg", result=REG, kind=BinaryExpr, operator=BinaryOperator.LESS_EQUAL, kids=(Need(REG), Need(REG)), cost=2, action="emit_sle")
    _add_rule(rules, "sge_reg", result=REG, kind=BinaryExpr, operator=BinaryOperator.GREATER_EQUAL, kids=(Need(REG), Need(REG)), cost=2, action="emit_sle")

    # Igualdade/desigualdade para REG, com Xor e Seqz/Snez
    _add_rule(rules, "seq_reg", result=REG, kind=BinaryExpr, operator=BinaryOperator.EQUAL, kids=(Need(REG), Need(REG)), cost=2, action="emit_seq")
    _add_rule(rules, "sne_reg", result=REG, kind=BinaryExpr, operator=BinaryOperator.NOT_EQUAL, kids=(Need(REG), Need(REG)), cost=2, action="emit_sne")

    # Comparação de dois REG para COND, branch direto e Jump
    _add_rule(rules, "cond_less", result=ResultClass.COND, kind=BinaryExpr, operator=BinaryOperator.LESS, kids=(Need(REG), Need(REG)), cost=2, action="emit_cond")
    _add_rule(rules, "cond_greater", result=ResultClass.COND, kind=BinaryExpr, operator=BinaryOperator.GREATER, kids=(Need(REG), Need(REG)), cost=2, action="emit_cond")
    _add_rule(rules, "cond_less_equal", result=ResultClass.COND, kind=BinaryExpr, operator=BinaryOperator.LESS_EQUAL, kids=(Need(REG), Need(REG)), cost=2, action="emit_cond")
    _add_rule(rules, "cond_greater_equal", result=ResultClass.COND, kind=BinaryExpr, operator=BinaryOperator.GREATER_EQUAL, kids=(Need(REG), Need(REG)), cost=2, action="emit_cond")
    _add_rule(rules, "cond_equal", result=ResultClass.COND, kind=BinaryExpr, operator=BinaryOperator.EQUAL, kids=(Need(REG), Need(REG)), cost=2, action="emit_cond")
    _add_rule(rules, "cond_not_equal", result=ResultClass.COND, kind=BinaryExpr, operator=BinaryOperator.NOT_EQUAL, kids=(Need(REG), Need(REG)), cost=2, action="emit_cond")

    # Negação lógica de REG para REG, com Seqz
    _add_rule(rules, "not_reg", result=REG, kind=UnaryExpr, operator=UnaryOperator.NOT, kids=(Need(REG),), cost=1, action="emit_not_reg")

    # Negação lógica de COND para COND, invertendo destino
    _add_rule(rules, "not_cond", result=ResultClass.COND, kind=UnaryExpr, operator=UnaryOperator.NOT, kids=(Need(ResultClass.COND),), cost=0, action="emit_not_cond")

    # &&/|| de dois COND para COND
    _add_rule(rules, "and_cond", result=ResultClass.COND, kind=BinaryExpr, operator=BinaryOperator.LOGICAL_AND, kids=(Need(ResultClass.COND), Need(ResultClass.COND)), cost=0, action="emit_and_cond")
    _add_rule(rules, "or_cond", result=ResultClass.COND, kind=BinaryExpr, operator=BinaryOperator.LOGICAL_OR, kids=(Need(ResultClass.COND), Need(ResultClass.COND)), cost=0, action="emit_or_cond")

    # &&/|| de dois COND para REG, com duas Li e um Jump
    _add_rule(rules, "and_cond_reg", result=REG, kind=BinaryExpr, operator=BinaryOperator.LOGICAL_AND, kids=(Need(ResultClass.COND), Need(ResultClass.COND)), cost=3, action="emit_and_cond_reg")
    _add_rule(rules, "or_cond_reg", result=REG, kind=BinaryExpr, operator=BinaryOperator.LOGICAL_OR, kids=(Need(ResultClass.COND), Need(ResultClass.COND)), cost=3, action="emit_or_cond_reg")

    # Literal bool para COND, com Jump
    _add_rule(rules, "literal_bool_cond", result=ResultClass.COND, kind=BoolLiteral, cost=1, action="emit_literal_bool_cond")
    # Identificador bool para COND, com branch e Jump
    _add_rule(rules, "identifier_cond", result=ResultClass.COND, kind=IdentifierExpr, cost=2, action="emit_identifier_cond")

    # Chamada com argumentos REG para REG ou EFFECT, com Call
    _add_rule(rules, "call_reg", result=REG, kind=CallExpr, kids=(Args(REG),), cost=1, action="emit_call_reg")
    _add_rule(rules, "call_effect", result=ResultClass.EFFECT, kind=CallExpr, kids=(Args(REG),), cost=1, action="emit_call_effect")

    # Chamada bool com argumentos REG para COND, com chamada e desvios
    _add_rule(rules, "call_cond", result=ResultClass.COND, kind=CallExpr, kids=(Args(REG),), cost=3, action="emit_call_cond")


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