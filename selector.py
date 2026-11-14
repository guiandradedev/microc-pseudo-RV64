"""Ponto de implementação do reconhecimento de padrões e custos mínimos."""

import load_previous
from ast_nodes import CallExpr
from patterns import *

class Selector:
    """Selecione coberturas sem executar expressões ou emitir instruções."""

    def __init__(self, rules):
        self.rules = tuple(rules)

    def analyze(self, expr):
        """Calcule mínimos por nó/classe sem emitir instruções."""
        table = SelectionTable()
        self._visit_nodes(expr, table)
        return table

    def _visit_nodes(self, node, table):
        """Visite nós e calcule custos mínimos por classe."""

        # Primeiro visita recursimamente os filhos do nó atual em pos-ordem
        for child in children(node):
            self._visit_nodes(child, table)

        # dicionário temporario que guarda melhor escolha encontrada 
        best = {}
        for rule in self.rules:
            # verifica se o padrao da regra é estruturalmente igual ao nó atual
            subproblems = self._match_pattern(node, rule.pattern)
            if subproblems is None:
                continue
            
            # busca na tabela as melhores escolhas para cada subproblema
            child_choices = [table.lookup(child, cls) for child, cls in subproblems]
            # se algum subproblema nao bater com a classe exigida, nao aplica a regra
            if any(choice is None for choice in child_choices):
                continue

            # custo da cobertura = custo da propria regra + custos otimos dos subproblemas
            total = rule.cost + sum(choice.cost for choice in child_choices)
            current = best.get(rule.result)

            # registra a regra se for a primeira para a classe de resultado ou se o custo for menor
            if current is None or total < current[0]:
                best[rule.result] = (total, rule, subproblems)

        # inserindo na tabela as escolhas de custo minimo
        for result_class, (total, rule, subproblems) in best.items():
            table.put(node, result_class, Choice(total, rule, subproblems))


    def _match_pattern(self, node, pattern: Pattern):
        """Retorna os pares (filho, classe) exigidos, ou None se não combina."""
        # garante que o tipo do nó existe e bate com o tipo do padrão
        if pattern.kind is not None and not isinstance(node, pattern.kind):
            return None

        # garante que o operador do nó existe e coincide com o operador do padrão
        if pattern.operator is not None:
            if getattr(node, "operator", None) != pattern.operator:
                return None

        # garante que o predicado existe e bate com o predicado do padrão
        if pattern.predicate is not None:
            pred_result = pattern.predicate(node)
            if pred_result is False or pred_result is None:
                return None
            # padrao com predicado sem filhos reconhecendo a subarvore toda
            if not pattern.children:
                return ()

        # Args(classe) com filho unico de uma chamada, tem q ter a mesma classe para todos os args
        if len(pattern.children) == 1 and isinstance(pattern.children[0], Args):
            if not isinstance(node, CallExpr):
                return None
            arg_class = pattern.children[0].result
            return tuple((arg, arg_class) for arg in node.arguments)

        # pega filhos do no e testa a aridade com o do pattern
        node_children = children(node)
        if len(pattern.children) != len(node_children):
            return None

        # percorre os filhos do no e especificacoes dos filhos no patters
        subproblems = []
        for child, need in zip(node_children, pattern.children):
            # se pattern exige uma classe, adiciona par (filho, classe) aos subproblemas
            if isinstance(need, Need):
                subproblems.append((child, need.result))
            # se pattern tem subpattern aninhado.
            elif isinstance(need, Pattern):
                nested = self._match_pattern(child, need)
                if nested is None:
                    return None
                subproblems.extend(nested)
            else:
                return None

        return tuple(subproblems)
