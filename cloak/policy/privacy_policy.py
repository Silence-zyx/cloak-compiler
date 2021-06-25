import json
from typing import Any, OrderedDict
from cloak.type_check import type_pure
from cloak.cloak_ast import ast

FUNC_INPUTS = "inputs"
FUNC_READ = "read"
FUNC_MUTATE = "mutate"
FUNC_OUTPUTS = "outputs"


class FunctionPolicy():

    def __init__(self, function_name: str = "", privacy_type = None):
        """
        init function info
        """
        self.__ppv = ast.CodeVisitor()  # for privacy policy
        self.fpolicy = {}
        self.fpolicy["type"] = "function"
        self.fpolicy["name"] = function_name
        self.fpolicy["privacy"] = privacy_type if privacy_type else ast.FunctionPrivacyType.PUB
        self.read_values = []
        self.mutate_values = []

    @property
    def name(self):
        return self.fpolicy["name"]

    @property
    def read(self):
        return self.fpolicy[FUNC_INPUTS]

    @property
    def read(self):
        return self.fpolicy[FUNC_READ]

    @property
    def read(self):
        return self.fpolicy[FUNC_MUTATE]

    @property
    def read(self):
        return self.fpolicy[FUNC_OUTPUTS]

    def get_item(self, clss, var):
        """
        Return the element if it's same with the var, else return None
        """
        if not clss in [FUNC_INPUTS, FUNC_READ, FUNC_MUTATE, FUNC_OUTPUTS]:
            raise ValueError(f"'{clss}' not support now!")

        if not clss in self.fpolicy:
            return None
        if not var.idf:
            return None

        for e in self.fpolicy[clss]:
            if e["name"] == var.idf.name:
                return e

        return None

    def add_item(self, clss, var, key=""):
        if not clss in [FUNC_INPUTS, FUNC_READ, FUNC_MUTATE, FUNC_OUTPUTS]:
            raise ValueError(f"'{clss}' not support now!")
        if not clss in self.fpolicy:
            self.fpolicy[clss] = []

        is_new = False
        elem = self.get_item(clss, var)
        if not elem:
            n_elem = {}
            if var.idf:
                n_elem["name"] = var.idf.name

            if not isinstance(var, ast.StateVariableDeclaration):
                # Ignore the 'type' and 'owner' of state variables to avoid duplication
                n_elem["type"] = type_pure.delete_cloak_annotation(
                    self.__ppv.visit(var.annotated_type.type_name))

                if isinstance(var.annotated_type.type_name, (ast.Mapping, ast.Array)):
                    n_elem["owner"] = self.__ppv.visit(var.annotated_type.type_name)
                else:
                    n_elem["owner"] = self.__ppv.visit(
                        var.annotated_type.privacy_annotation)

            self.fpolicy[clss].append(n_elem)
            elem = n_elem            
            is_new = True

        if isinstance(var, ast.StateVariableDeclaration) \
            and isinstance(var.annotated_type.type_name, (ast.Mapping, ast.Array)):
            if not "keys" in elem:
                elem["keys"] = []
            _key = type_pure.delete_cloak_annotation(key)
            if not _key in elem["keys"]:
                elem["keys"].append(_key)
                is_new = True

        return is_new

class PrivacyPolicyEncoder(json.JSONEncoder):

    def default(self, o: Any) -> Any:
        try:
            if isinstance(o, FunctionPolicy):
                return o.fpolicy
            return o.policy
        except TypeError:
            pass
        # Let the base class default method raise the TypeError
        return json.JSONEncoder.default(self, o)


class PrivacyPolicy(json.JSONEncoder):

    def __init__(self, contract_name: str = ""):
        """
        init contract info
        """
        self.__ppv = ast.CodeVisitor() 

        self.policy = {}
        self.policy["contract"] = contract_name
        self.policy["states"] = []
        self.policy["functions"] = []

    @property
    def function_policies(self):
        return self.policy['functions']

    def add_state(self, var):
        item = "states"
        if not item in ["states"]:
            raise ValueError(f"'{item}' not support now!")
        if not item in self.policy:
            self.policy[item] = []
        n_elem = {}
        if var.idf:
            n_elem["name"] = var.idf.name
        n_elem["type"] = type_pure.delete_cloak_annotation(
            self.__ppv.visit(var.annotated_type.type_name))
        # TODO: renqian - handle array
        if isinstance(var.annotated_type.type_name, ast.Mapping):
            n_elem["owner"] = self.__ppv.visit(var.annotated_type.type_name)
        elif isinstance(var.annotated_type.type_name, ast.Array):
            n_elem["owner"] = self.__ppv.visit(var.annotated_type)
        else:
            n_elem["owner"] = self.__ppv.visit(var.annotated_type.privacy_annotation)

        self.policy[item].append(n_elem)

    def add_function(self, func_policy: FunctionPolicy):
        """
        add function privacy policy
        """
        item = "functions"
        if not item in self.policy:
            self.policy[item] = []

        self.policy[item].append(func_policy)

    def get_function_policy(self, f_name: str):
        for ffp in self.function_policies:
            if ffp.name == f_name:
                return ffp
        return None 

    def get_visited_map_and_key(self, idx_expr):
        assert isinstance(idx_expr, ast.IndexExpr)
        while isinstance(idx_expr.parent, ast.IndexExpr):
            idx_expr = idx_expr.parent
        
        top_idx, target_idx = idx_expr, idx_expr
        map_key = ""
        while isinstance(target_idx, ast.IndexExpr):
            map_key = f'{self.__ppv.visit(target_idx.key)}:{map_key}' if map_key else self.__ppv.visit(target_idx.key)
            target_idx = target_idx.arr

        return top_idx, target_idx, map_key

if __name__ == "__main__":
    pp = PrivacyPolicy("newContract")
    print(json.dumps(pp, cls=PrivacyPolicyEncoder))