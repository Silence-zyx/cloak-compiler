from __future__ import annotations

from cloak.cloak_ast import ast
from cloak.cloak_ast.ast import *
from cloak.cloak_ast.visitor.transformer_visitor import AstTransformerVisitor
from cloak.policy.privacy_policy import PrivacyPolicy

class PrivateContractTransformer(AstTransformerVisitor):
    """
    1. TODO: remove the @owner annotations.
    2. add get_states/set_states function for tee
    """

    def __init__(self, pp: PrivacyPolicy, log=False):
        self.pp = pp
        super().__init__(log)

    def visitContractDefinition(self, c: ast.ContractDefinition):
        """
        add get_states/set_states function for tee
        """
        self.append_get_states(c)
        self.append_set_states(c)
        return c

    def append_get_states(self, c: ContractDefinition):
        # TODO: Array
        uint256_array_type = AnnotatedTypeName(Array(UintTypeName("uint256")))
        parameters = [
                Parameter([], UintTypeName("uint"), Identifier("return_len"), "memory"),
                Parameter([], uint256_array_type, Identifier("read"), "memory")]
        returns = [Parameter([], uint256_array_type, Identifier("oldStates"), "memory")]
        old_states_var = VariableDeclarationStatement(
                VariableDeclaration([], uint256_array_type, Identifier("oldStates"), "memory"), 
                NewExpr(uint256_array_type, [IdentifierExpr("return_len")]))
        statements = [old_states_var]
        idx = 0
        for i in range(0, len(self.pp.policy["states"])):
            state = self.pp.policy["states"][i]
            if not self.is_mamping(state["type"]):
                statements.append(ast.AssignmentStatement(
                    IndexExpr(IdentifierExpr("oldStates"), Identifier(f"{idx}")), 
                    NumberLiteralExpr(i)))
                statements.append(ast.AssignmentStatement(
                    IndexExpr(IdentifierExpr("oldStates"), Identifier(f"{idx+1}")), 
                    IdentifierExpr(state["name"])))
                idx += 2

        statements.append(VariableDeclarationStatement(
                VariableDeclaration([], UintTypeName("uint"), Identifier("m_idx")), 
                NumberLiteralExpr(0)))
        key_size_expr = IndexExpr(IdentifierExpr("read"), IdentifierExpr("m_idx").binop("+", NumberLiteralExpr(1)))
        key_expr = IndexExpr(IdentifierExpr("read"), self.m_plus("m_idx", 2, "i"))
        for state in self.pp.policy["states"]:
            if self.is_mamping(state["type"]):
                init = VariableDeclarationStatement(
                        VariableDeclaration([], UintTypeName("uint"), Identifier("i")), 
                        NumberLiteralExpr(0))
                cond = IdentifierExpr("i").binop("<", key_size_expr)
                update = AssignmentStatement(IdentifierExpr("i"), IdentifierExpr("i").binop("+", NumberLiteralExpr(1)))
                body_stmts = [
                    AssignmentStatement(
                        IndexExpr(IdentifierExpr("oldStates"), self.m_plus(idx, "m_idx", 2, "i")),
                        IndexExpr(IdentifierExpr(state["name"]), key_expr))
                ]
                statements.append(ForStatement(init, cond, update, Block(body_stmts)))
                statements.append(AssignmentStatement(
                    IdentifierExpr("m_idx"),
                    self.m_plus("m_idx", 2, key_size_expr)))

        statements.pop()
        get_states = ConstructorOrFunctionDefinition(Identifier("get_states"), parameters, [], returns, Block(statements))
        c.function_definitions.append(get_states)

    def append_set_states(self, c: ContractDefinition):
        # TODO: Array
        uint256_array_type = AnnotatedTypeName(Array(UintTypeName("uint256")))
        parameters = [Parameter([], uint256_array_type, Identifier("data"), "memory")]
        statements = []
        idx = 0
        for state in self.pp.policy["states"]:
            if not self.is_mamping(state["type"]):
                statements.append(ast.AssignmentStatement(
                    IdentifierExpr(state["name"]),
                    IndexExpr(IdentifierExpr("data"), Identifier(f"{idx+1}"))))
                idx += 2

        statements.append(VariableDeclarationStatement(
                VariableDeclaration([], UintTypeName("uint"), Identifier("m_idx")), 
                NumberLiteralExpr(idx)))
        key_size_expr = IndexExpr(IdentifierExpr("read"), self.m_plus("m_idx", 1))
        im2_exp = IdentifierExpr("i").binop("*", NumberLiteralExpr(2))
        key_expr = IndexExpr(IdentifierExpr("read"), self.m_plus("m_idx", 2, im2_exp))
        val_expr = IndexExpr(IdentifierExpr("read"), self.m_plus("m_idx", 3, im2_exp))
        for state in self.pp.policy["states"]:
            if self.is_mamping(state["type"]):
                init = VariableDeclarationStatement(
                        VariableDeclaration([], UintTypeName("uint"), Identifier("i")), 
                        NumberLiteralExpr(0))
                cond = IdentifierExpr("i").binop("<", key_size_expr)
                update = AssignmentStatement(IdentifierExpr("i"), self.m_plus("i", 1))
                body_stmts = [
                    AssignmentStatement(
                        IndexExpr(IdentifierExpr(state["name"]), key_expr),
                        IndexExpr(IdentifierExpr("data"), val_expr))
                ]
                statements.append(ForStatement(init, cond, update, Block(body_stmts)))
                statements.append(AssignmentStatement(
                    IdentifierExpr("m_idx"), 
                    self.m_plus("m_idx", 2, key_size_expr.binop("*", NumberLiteralExpr(2)))))

        statements.pop()
        set_states = ConstructorOrFunctionDefinition(Identifier("set_states"), parameters, [], [], Block(statements))
        c.function_definitions.append(set_states)

    def m_plus(self, *lst: List[Any]) -> Expression:
        res = None
        for x in lst:
            if isinstance(x, str):
                val = IdentifierExpr(x)
            elif isinstance(x, Expression):
                val = x
            else:
                val = NumberLiteralExpr(x)
            if res:
                res = res.binop("+", val)
            else:
                res = val
        return res

    def is_mamping(self, name: str) -> bool:
        return name.find("mapping") != -1