from __future__ import annotations

from cloak.cloak_ast import ast
from cloak.cloak_ast.ast import *
from cloak.cloak_ast.visitor.transformer_visitor import AstTransformerVisitor
from cloak.compiler.privacy.transformation.cloak_contract_transformer import CloakTransformer
from cloak.policy.privacy_policy import PrivacyPolicy
from cloak.utils.helpers import m_plus
from cloak.config import cfg

class PrivateContractTransformer(AstTransformerVisitor):
    """
    1. TODO: remove the @owner annotations.
    2. add get_states/set_states function for tee
    """

    def __init__(self, pp: PrivacyPolicy, log=False):
        self.pp = pp
        super().__init__(log)

    def visitSourceUnit(self, su: SourceUnit):
        su.pragma_directive = f"pragma solidity {cfg.cloak_solc_version_compatibility.expression};";
        su.privacy_policy = self.pp
        for cd in su.contracts:
            cd.function_definitions.append(CloakTransformer.get_states(su, cd, False))
            cd.function_definitions.append(CloakTransformer.set_states(su, cd, False))
