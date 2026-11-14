"""Ponto de implementação do reconhecimento de padrões e custos mínimos."""

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
        # garante que o tipo do nó existe e bate com o tipo do padrão
        if pattern.kind is not None and not isinstance(node, pattern.kind):
            return None

        # garante que o operador do nó existe e bate com o operador do padrão
        if pattern.operator is not None:
            if not hasattr(node, 'operator'):
                return None
            if node.operator != pattern.operator:
                return None

        # garante que o predicado existe e bate com o predicado do padrão
        if pattern.predicate is not None and not pattern.predicate(node):
            return None

        # garante que os filhos do nó existem e batem com os filhos do padrão
        if len(children(node)) != len(pattern.children):
            return None
        for i, child in enumerate(children(node)):
            if not self._match_pattern(child, pattern.children[i]):
                return None
        
        return True
