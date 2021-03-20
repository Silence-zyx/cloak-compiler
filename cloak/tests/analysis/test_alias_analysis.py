import re

from parameterized import parameterized_class

from cloak.ast.visitor.transformer_visitor import AstTransformerVisitor
from cloak.examples.examples import analysis, all_examples
from cloak.tests.utils.test_examples import TestExamples
from cloak.tests.zkay_unit_test import ZkayTestCase
from cloak.ast.analysis.alias_analysis import alias_analysis
from cloak.ast.ast import Statement, Comment, BlankLine
from cloak.ast.build_ast import build_ast
from cloak.ast.pointers.parent_setter import set_parents
from cloak.ast.pointers.symbol_table import link_identifiers


class TestAliasAnalysisDetail(ZkayTestCase):

    def test_alias_analysis(self):
        # perform analysis
        ast = build_ast(analysis.code())
        set_parents(ast)
        link_identifiers(ast)
        alias_analysis(ast)

        # generate string, including analysis results
        v = AnalysisCodeVisitor()
        s = v.visit(ast)
        # next statement can be enabled to determine the computed output
        # print(s)

        # check output
        self.maxDiff = None
        self.assertMultiLineEqual(analysis.code(), re.sub(" +\n", "\n", s.code()))


@parameterized_class(('name', 'example'), all_examples)
class TestAliasAnalysis(TestExamples):

    def test_alias_analysis(self):
        # perform analysis
        ast = build_ast(self.example.code())
        set_parents(ast)
        link_identifiers(ast)
        alias_analysis(ast)


class AnalysisCodeVisitor(AstTransformerVisitor):
    def visitStatement(self, ast: Statement):
        return [BlankLine(), Comment(str(ast.before_analysis)), self.visit_children(ast), Comment(str(ast.after_analysis)), BlankLine()]

    def visitBlock(self, ast: Statement):
        return [BlankLine(), Comment(str(ast.before_analysis)), self.visit_children(ast), Comment(str(ast.after_analysis))]