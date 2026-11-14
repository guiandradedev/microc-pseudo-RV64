"""Pontos de implementação da geração de comandos e expressões."""

import load_previous
from ast_nodes import Assignment, BinaryOperator, Block, CallStmt, IfStmt, PrintStmt, ReturnStmt, StringLiteral, TypeName, VarDecl, WhileStmt

from catalogue import catalogue
from ir import (
    Context,
    FunctionIR,
    Jump,
    LabelInstr,
    Li,
    Move,
    Param,
    PrintBool,
    PrintInt,
    PrintString,
    ProgramIR,
    Return,
)
from patterns import COND, EFFECT, IMM12, POW2, REG, ResultClass, signed_literal
from selector import Selector

class CodeGenerator:
    """Coordene comandos ad hoc e seleção de expressões com DP."""

    def __init__(self):
        self.context = None
        self.selector = Selector(tuple(catalogue()))
        self.table = None

    def generate(self, program):
        """Traduza funções e comandos. Selecione expressões com DP."""
        
        # Cria a representacao intermediaria do programa
        program_ir = ProgramIR(functions=[], strings={})

        # traduz cada declaracao de funcao na ordem de aparecimento
        for function_dcl in program.functions:
            function_id = self._generate_function(function_dcl, program_ir)
            program_ir.functions.append(function_id)

        return program_ir

    def _generate_function(self, function_dcl, program_ir):
        # cria uma FunctionIR com o símbolo da função
        function_symbol= function_dcl.metadata["symbol"]
        function_ir = FunctionIR(function=function_symbol, instructions=[])

        # cria um contexto para a função atual com a IR da função e do programa
        context = Context(function=function_ir, program=program_ir)
        self.context = context

        # para cada parâmetro da função, emitir uma instrução Param que registra seu VReg
        for i, param in enumerate(function_dcl.parameters):
            reg_dest = context.variable(param.metadata['symbol']) 
            context.emit(Param(reg_dest, i, origin=param.span))

        # percorre o corpo da func traduzindo comandos
        self.statement(function_dcl.body)

        # garantir retorno vazio no fim de funcoes void caso n tenham return explicito
        if function_dcl.return_type is TypeName.VOID:
            if not function_ir.instructions or not isinstance(function_ir.instructions[-1], Return):
                context.emit(Return(None, origin=function_dcl.span))

        return function_ir

    def expression(self, node, result_class, true_label=None, false_label=None):
        """Selecione e reconstrua uma expressão, preservando curto-circuito."""
        # calcula os custos
        table = self.selector.analyze(node)
        choice = table.lookup(node, result_class)

        # se não houver cobertura, levanta um erro com a posição do nó
        if choice is None:
            # caso n exista cobertura valida relata o erro detalhando o no a classe e a posicao 
            span = getattr(node, "span", None)
            pos = (
                f"{span.start_line}:{span.start_column}"
                if span is not None
                else "desconhecida"
            )

            raise ValueError(f"sem cobertura para {type(node).__name__} como {result_class} em {pos}")

        return self._emit(node, choice, table, result_class, true_label, false_label)

    def _emit(self, node, choice, table, result_class, true_label=None, false_label=None):
        """Emita a ação vencedora da seleção de expressão."""

        # no lugar de fazer muitos if/else para cada ação, optamos por usar mecanismos do python para localizar o método e chama-lo de forma dinamica, facilitando a leitura do código
        
        # localizar o metodo da acao emissora coresponde a regra vencedora 
        action = choice.rule.action
        method = getattr(self, action, None)

        # se não existir metodo correspondente da erro
        if not callable(method):
            raise NotImplementedError(f"ação '{action}' ainda não implementada")
        
        # se classe = cond, repassa os rotulos de desvio true e false para a acao
        if result_class == ResultClass.COND:
            return method(node, choice.subproblems, table, true_label, false_label)
        
        return method(node, choice.subproblems, table)


    def statement(self, node):
        """Traduza um comando ad hoc."""
        # se for um bloco, percorre cada comando interno de forma recursiva
        if isinstance(node, Block):
            for inner in node.statements:
                self.statement(inner)
            return

        # se for uma declaração de variavel e houver inicializador, processa a expressão e move para o registrador do símbolo
        if isinstance(node, VarDecl):
            if node.initializer is not None:
                content = self.expression(node.initializer, REG)
                destination = self.context.variable(node.metadata["symbol"])
                self.context.emit(Move(destination, content, origin=node.span))
            return

        # se for uma atribuição, processa a expressão do lado direito em REG e move para o registrador da variável alvo
        if isinstance(node, Assignment):
            content = self.expression(node.value, REG)
            destination = self.context.variable(node.target.metadata["symbol"])
            self.context.emit(Move(destination, content, origin=node.span))
            return

        # se for uma chamada de função, processa a chamada exigindo a classe EFFECT, que emite os argumentos e a chamada
        if isinstance(node, CallStmt):
            self.expression(node.call, ResultClass.EFFECT)
            return

        # se for um retorno de funcao, emite o retorno da funçao.
        # se o valor de retorno não existir (void), retorna ele, caso contrarior etorna None
        if isinstance(node, ReturnStmt):
            value = None
            if node.value is not None:
                value = self.expression(node.value, REG)

            self.context.emit(Return(value, origin=node.span))
            return

        # comandos condicionais, avalia a condicao na classe cond
        if isinstance(node, IfStmt):
            then_label = self.context.label()
            if node.else_block is not None:
                
                else_label = self.context.label()
                end_label = self.context.label()
                self.expression(
                    node.condition, ResultClass.COND, then_label, else_label
                )
                self.context.emit(LabelInstr(then_label))
                self.statement(node.then_block)
                self.context.emit(Jump(end_label, origin=node.span))
                self.context.emit(LabelInstr(else_label))
                self.statement(node.else_block)
                self.context.emit(LabelInstr(end_label))
            else:
                # sem ramo else, pula para end
                end_label = self.context.label()
                self.expression(
                    node.condition, ResultClass.COND, then_label, end_label
                )
                self.context.emit(LabelInstr(then_label))
                self.statement(node.then_block)
                self.context.emit(LabelInstr(end_label))
            return

        # while: avalia test_label para entrar em body ou end
        if isinstance(node, WhileStmt):
            test_label = self.context.label()
            body_label = self.context.label()
            end_label = self.context.label()
            self.context.emit(LabelInstr(test_label))
            self.expression(
                node.condition, ResultClass.COND, body_label, end_label
            )
            self.context.emit(LabelInstr(body_label))
            self.statement(node.body)
            self.context.emit(Jump(test_label, origin=node.span))
            self.context.emit(LabelInstr(end_label))
            return

        # print: imprime cada item e finaliza com \n
        if isinstance(node, PrintStmt):
            for item in node.items:
                if isinstance(item, StringLiteral):
                    self.context.emit(
                        PrintString(self.context.string(item.value), origin=item.span)
                    )
                else:
                    value = self.expression(item, REG)
                    if item.metadata.get("type") is TypeName.BOOL:
                        self.context.emit(PrintBool(value, origin=item.span))
                    else:
                        self.context.emit(PrintInt(value, origin=item.span))
            self.context.emit(
                PrintString(self.context.string("\n"), origin=node.span)
            )
            return

        raise NotImplementedError(f"Statement {type(node)}")


    def emit_literal_int_reg(self, node, subproblems, table):
        # aloca um registraodr temporario e carrega o valor inteiro com a instrucao Li
        dst = self.context.temp()
        self.context.emit(Li(dst, signed_literal(node), origin=node.span))
        return dst

    def emit_literal_bool_reg(self, node, subproblems, table):
        # aloca um registraodr temporario e carrega o valor booleano com a instrucao Li
        dst = self.context.temp()
        self.context.emit(Li(dst, 1 if node.value else 0, origin=node.span))
        return dst

    def identifier_reg(self, node, subproblems, table):
        # retorna o registrador associado ao simbolo da variavel sem emitir instrucao
        return self.context.variable(node.metadata["symbol"])