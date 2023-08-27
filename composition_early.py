import arpeggio
from arpeggio.peg import ParserPEG, PTNodeVisitor, visit_parse_tree

class LabelVisitor(PTNodeVisitor):

    def visit_label(self, node, children):
        return children[0]
    
    def visit_part(self, node, children) -> {str:[{str:float}]}:
        return {children[0]: children[1]}

    def visit_composition(self, node, children) -> [{str:float}]:
        return children

    def visit_part_name(self, node, children) -> str:
        return ' '.join(children)
    
    def visit_composition_element(self, node, children) -> (float, str):
        return {children[1]: children[0]}

    def visit_percentage(self, node, children) -> float:
        return float(children[0]) / 100.0
    
    def visit_fibre_type(self, node, children) -> str:
        return ' '.join(children)
    
    def visit_SP(self, node, children) -> None:
        """Don't include SP (and SP+ etc.) in the AST
        This is useful to remove and sqeeze spaces"""
        return None

with open('label.peg') as g:
    label_grammar = g.read()

try:
    label_parser = ParserPEG(label_grammar, "label", skipws=False)
except arpeggio.NoMatch as e:
    print("Failed to parse grammar: ", e) 
    exit(1)


# print(ast.tree_str())

for input_ in [
    'Shell: 90% Cotton Pile, 10% Recycled Polyester',
    'Shell Cover: 90% Cotton Pile',
    'Shell: 90% Cotton Pile, 10% Polyester; Lining: 100% Cotton',
    '90% Cotton, 5% Polyester, 5% Lycra Spandex',
    '99.5% Cotton, 0.5% Magic',
    ]:

    ast = label_parser.parse(input_)
    result = visit_parse_tree(ast, LabelVisitor())

    print(result)


