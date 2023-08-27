import arpeggio
from arpeggio.peg import ParserPEG, PTNodeVisitor, visit_parse_tree
import json
from textwrap import dedent
import timeit

class LabelVisitor(PTNodeVisitor):

    def visit_label(self, node, children):
        # We either have a single child (a single composition, which is a dictionary)
        # Or we have a list of parts (a list of dictionaries)
        # We need to combine them into one dictionary
        #
        res = {}
        for child in children:
            res.update(child)
        return res
    
    def visit_part(self, node, children) -> {str:[{str:float}]}:
        return {children[0]: children[1]}

    def visit_composition(self, node, children) -> [{str:float}]:
        res = {}
        for child in children:
            res.update(child)
        return res

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

def stringify(v: any) -> str:
    """Reconstruct the label"""

    # How can we tell if we're looking at a single composition, or
    # a list of parts (with their composition)? We don't have any
    # type distinction between parts and compositions; they are
    # both dictionaries... so we need to to try and see how deep
    # these dictionaries are.

    # Structural pattern matching in Python doesn't seem to allow
    # us to match any dictionary of dictionaries, so we'll just
    # look at the 'first' (random) element of the dictionary; if
    # it's value is a dict, then we know we're dealing with parts,
    # rather than just simple compositions.
    #
    # This is probabaly the biggest indication that we need something
    # that has carries abstract types in the AST, such as Named Tuples
    # or Dataclasses

    def pct(f) -> str:
        s = f"{f*100:.1f}".replace(".0", "")
        return f"{s}%"
    
    if isinstance(v[list(v)[0]], dict):
        return "; ".join([f"{part}: {stringify(composition)}" for part, composition in v.items()])
    else:
        return ", ".join([f"{pct(proportion)} {material}" for material, proportion in v.items()])


with open('label.peg') as g:
    label_grammar = g.read()

try:
    label_parser = ParserPEG(label_grammar, "label", skipws=False)
except arpeggio.NoMatch as e:
    print("Failed to parse grammar: ", e) 
    exit(1)


# print(ast.tree_str())

for input_ in [
    'Shell: 90% Cotton, 10% Recycled Polyester',
    'Shell Cover: 90% Cotton',
    'Shell: 90% Cotton, 10% Polyester; Lining: 100% Cotton',
    '90% Cotton, 5% Polyester, 5% Lycra',
    '100% Unbleached Organic Hemp',
    '99.5% Cotton, 0.5% Magic',
    
    # Some failure cases
    '90% Cotton 10% Polyester',
    ]:

    print("Input label : ", input_)
    try:
        ast = label_parser.parse(input_)
    except arpeggio.NoMatch as e:
        print("Error       : ", e)
        print("---")
        continue
    result = visit_parse_tree(ast, LabelVisitor())

    print("Parsed      : ", result)
    print("JSON        : ", json.dumps(result))
    print("Cleaned     : ", stringify(result))
    print("---")

# exit(0)

# Performance

print("Timings (µs) for creating the parser: ", end="")
n=100
print([ f"{t/n * 1_000_000:.0f}µs" for t in timeit.repeat(
    '''ParserPEG(label_grammar, "label", skipws=False)''',
    globals={'ParserPEG': ParserPEG, 'label_grammar': label_grammar}, number=n)])

print("Timings for parsing an input: ", end="")
n=1000
print([ f"{t/n * 1_000_000:.0f}µs" for t in timeit.repeat(
    '''label_parser.parse('Shell: 90% Cotton Pile, 10% Polyester; Lining: 100% Cotton')''',
    globals={'label_parser': label_parser}, number=n)])

print("Timings for stringifying a label: ", end="")
n=1000
print([ f"{t/n * 1_000_000:.0f}µs" for t in timeit.repeat(
    dedent('''
        stringify({'Shell': {'Cotton Pile': 0.9, 'Polyester': 0.1}, 'Lining': {'Cotton': 1.0}})
        '''),
    globals={'stringify': stringify},
    number=n)])
