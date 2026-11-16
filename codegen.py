"""Pontos de implementação da geração de comandos e expressões."""

import load_previous
from ast_nodes import Assignment, BinaryOperator, Block, CallStmt, IfStmt, PrintStmt, ReturnStmt, StringLiteral, TypeName, VarDecl, WhileStmt

from catalogue import catalogue
from ir import (
    Add,
    Addi,
    Beq,
    Bge,
    Blt,
    Bne,
    Bnez,
    Call,
    Context,
    Div,
    FunctionIR,
    Jump,
    LabelInstr,
    Li,
    Move,
    Mul,
    Neg,
    Param,
    PrintBool,
    PrintInt,
    PrintString,
    ProgramIR,
    Rem,
    Return,
    Seqz,
    Slli,
    Slt,
    Snez,
    Sub,
    Xor,
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

    def _sub(self, child, result_class, table, true_label=None, false_label=None):
        # pega a escolha que o seletor ja calculou pro filho e emite ela
        choice = table.lookup(child, result_class)
        return self._emit(child, choice, table, result_class, true_label, false_label)

    def _regs(self, subproblems, table):
        # avalia os filhos na ordem do codigo e devolve os registradores
        return [self._sub(child, cls, table) for child, cls in subproblems]

    def literal_imm12(self, node, subproblems, table):
        # nao emite nada, so devolve o valor pra ser usado como imediato
        return signed_literal(node)

    def literal_pow2(self, node, subproblems, table):
        # nao emite nada, so devolve o valor pra virar o deslocamento
        return signed_literal(node)

    def emit_neg(self, node, subproblems, table):
        # calcula o operando e nega com a instrucao Neg
        (src,) = self._regs(subproblems, table)
        dst = self.context.temp()
        self.context.emit(Neg(dst, src, origin=node.span))
        return dst

    # mapeia cada operador aritmetico pra instrucao correspondente
    _ARITH = {
        BinaryOperator.ADD: Add,
        BinaryOperator.SUBTRACT: Sub,
        BinaryOperator.MULTIPLY: Mul,
        BinaryOperator.DIVIDE: Div,
        BinaryOperator.REMAINDER: Rem,
    }

    def emit_arith(self, node, subproblems, table):
        # avalia os dois lados e emite a instrucao do operador
        lhs, rhs = self._regs(subproblems, table)
        dst = self.context.temp()
        self.context.emit(self._ARITH[node.operator](dst, lhs, rhs, origin=node.span))
        return dst

    def emit_sum_imm(self, node, subproblems, table):
        # o imediato pode estar em qualquer lado, entao separa pelo tipo da classe
        src = imm = None
        for child, cls in subproblems:
            if cls == IMM12:
                imm = self._sub(child, cls, table)
            else:
                src = self._sub(child, cls, table)
        dst = self.context.temp()
        self.context.emit(Addi(dst, src, imm, origin=node.span))
        return dst

    def emit_sub_imm(self, node, subproblems, table):
        # x - n vira addi com -n
        (src,) = self._regs(subproblems, table)
        dst = self.context.temp()
        self.context.emit(Addi(dst, src, -signed_literal(node.right), origin=node.span))
        return dst

    def emit_mul_pow2(self, node, subproblems, table):
        # multiplicar por potencia de 2 vira um shift pra esquerda, com a potencia em qualquer lado
        src = shift = None
        for child, cls in subproblems:
            if cls == POW2:
                shift = self._sub(child, cls, table).bit_length() - 1
            else:
                src = self._sub(child, cls, table)
        dst = self.context.temp()
        self.context.emit(Slli(dst, src, shift, origin=node.span))
        return dst

    def emit_slt(self, node, subproblems, table):
        # a < b usa slt direto, a > b inverte os operandos
        lhs, rhs = self._regs(subproblems, table)
        if node.operator is BinaryOperator.GREATER:
            lhs, rhs = rhs, lhs
        dst = self.context.temp()
        self.context.emit(Slt(dst, lhs, rhs, origin=node.span))
        return dst

    def emit_sle(self, node, subproblems, table):
        # a <= b eh o mesmo que nao (b < a), e a >= b eh nao (a < b)
        lhs, rhs = self._regs(subproblems, table)
        if node.operator is BinaryOperator.LESS_EQUAL:
            lhs, rhs = rhs, lhs
        tmp = self.context.temp()
        self.context.emit(Slt(tmp, lhs, rhs, origin=node.span))
        dst = self.context.temp()
        self.context.emit(Seqz(dst, tmp, origin=node.span))
        return dst

    def emit_seq(self, node, subproblems, table):
        # o xor da zero quando os valores sao iguais, depois testa com seqz no == e snez no !=
        lhs, rhs = self._regs(subproblems, table)
        tmp = self.context.temp()
        self.context.emit(Xor(tmp, lhs, rhs, origin=node.span))
        test = Seqz if node.operator is BinaryOperator.EQUAL else Snez
        dst = self.context.temp()
        self.context.emit(test(dst, tmp, origin=node.span))
        return dst

    # para cada comparacao guarda o desvio usado e se precisa inverter os operandos
    _BRANCH = {
        BinaryOperator.LESS: (Blt, False),
        BinaryOperator.GREATER: (Blt, True),
        BinaryOperator.LESS_EQUAL: (Bge, True),
        BinaryOperator.GREATER_EQUAL: (Bge, False),
        BinaryOperator.EQUAL: (Beq, False),
        BinaryOperator.NOT_EQUAL: (Bne, False),
    }

    def emit_cond(self, node, subproblems, table, true_label, false_label):
        # desvia pro true se a comparacao der certo, senao pula pro false
        lhs, rhs = self._regs(subproblems, table)
        branch, swap = self._BRANCH[node.operator]
        if swap:
            lhs, rhs = rhs, lhs
        self.context.emit(branch(lhs, rhs, true_label, origin=node.span))
        self.context.emit(Jump(false_label, origin=node.span))

    def emit_not_reg(self, node, subproblems, table):
        # negacao logica em registrador usa seqz
        (src,) = self._regs(subproblems, table)
        dst = self.context.temp()
        self.context.emit(Seqz(dst, src, origin=node.span))
        return dst

    def emit_not_cond(self, node, subproblems, table, true_label, false_label):
        # em cond basta trocar os rotulos de true e false
        ((child, cls),) = subproblems
        self._sub(child, cls, table, false_label, true_label)

    def emit_and_cond(self, node, subproblems, table, true_label, false_label):
        # se o lado esquerdo for falso ja pula pro false, senao testa o direito
        (left, lcls), (right, rcls) = subproblems
        middle = self.context.label()
        self._sub(left, lcls, table, middle, false_label)
        self.context.emit(LabelInstr(middle))
        self._sub(right, rcls, table, true_label, false_label)

    def emit_or_cond(self, node, subproblems, table, true_label, false_label):
        # se o lado esquerdo for verdadeiro ja pula pro true, senao testa o direito
        (left, lcls), (right, rcls) = subproblems
        middle = self.context.label()
        self._sub(left, lcls, table, true_label, middle)
        self.context.emit(LabelInstr(middle))
        self._sub(right, rcls, table, true_label, false_label)

    def emit_logic_reg(self, node, subproblems, table):
        # gera o && ou || como cond e transforma em valor no registrador, 1 no true e 0 no false
        if node.operator is BinaryOperator.LOGICAL_AND:
            emit_cond = self.emit_and_cond
        else:
            emit_cond = self.emit_or_cond
        dst = self.context.temp()
        true_label = self.context.label()
        false_label = self.context.label()
        end_label = self.context.label()
        emit_cond(node, subproblems, table, true_label, false_label)
        self.context.emit(LabelInstr(true_label))
        self.context.emit(Li(dst, 1, origin=node.span))
        self.context.emit(Jump(end_label, origin=node.span))
        self.context.emit(LabelInstr(false_label))
        self.context.emit(Li(dst, 0, origin=node.span))
        self.context.emit(LabelInstr(end_label))
        return dst

    def emit_literal_bool_cond(self, node, subproblems, table, true_label, false_label):
        # literal booleano so pula direto pro rotulo certo
        self.context.emit(Jump(true_label if node.value else false_label, origin=node.span))

    def emit_identifier_cond(self, node, subproblems, table, true_label, false_label):
        # se a variavel for diferente de zero vai pro true, senao vai pro false
        src = self.context.variable(node.metadata["symbol"])
        self.context.emit(Bnez(src, true_label, origin=node.span))
        self.context.emit(Jump(false_label, origin=node.span))

    def _emit_call(self, node, subproblems, table, dst):
        # avalia os argumentos em ordem e emite a chamada
        args = self._regs(subproblems, table)
        self.context.emit(Call(dst, node.metadata["symbol"], args, origin=node.span))
        return dst

    def emit_call_reg(self, node, subproblems, table):
        return self._emit_call(node, subproblems, table, self.context.temp())

    def emit_call_effect(self, node, subproblems, table):
        # o resultado eh descartado entao dst fica None, que eh obrigatorio pra void
        self._emit_call(node, subproblems, table, None)

    def emit_call_cond(self, node, subproblems, table, true_label, false_label):
        # chama a funcao e desvia de acordo com o valor retornado
        value = self._emit_call(node, subproblems, table, self.context.temp())
        self.context.emit(Bnez(value, true_label, origin=node.span))
        self.context.emit(Jump(false_label, origin=node.span))
