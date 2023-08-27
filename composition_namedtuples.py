import arpeggio
from arpeggio.peg import ParserPEG, PTNodeVisitor, visit_parse_tree
from collections import namedtuple
import timeit
from textwrap import dedent
import json

Label = namedtuple("Label", ['contents'])
Part = namedtuple("Part", ['name', 'components'])
Composition = namedtuple("Composition", ['elements'])
Element = namedtuple("Element", ['material', 'proportion'])

class LabelVisitor(PTNodeVisitor):

    def visit_label(self, node, children):
        return Label(contents = children)
    
    def visit_part(self, node, children) -> {str:[{str:float}]}:
        return Part(name=children[0], components=children[1])

    def visit_composition(self, node, children) -> [{str:float}]:
        return Composition(elements=children)

    def visit_part_name(self, node, children) -> str:
        return ' '.join(children)
    
    def visit_composition_element(self, node, children) -> (float, str):
        return Element(material=children[1], proportion=children[0])

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

def stringify(v: Label|Part|Composition|Element) -> str:
    match v:
        case Label(contents=[Part(), *_]):
            return "; ".join([stringify(p) for p in v.contents])
        case Label(contents=[Composition()]):
            return stringify(v.contents[0])
        case Part(name=n, components=c):
            return f"{n}: {stringify(c)}"
        case Composition(elements=es):
            return ", ".join([stringify(e) for e in es])
        case Element(material=m, proportion=p):
            # Do I regret making this a float? Maybe
            # There's probably some odd edge-case where there is something that ends up
            # as something like 100.1% ... I want to generally have 0 DP, but I don't want
            # to have 100.0 as a result.
            #
            percentage = f"{p*100:.1f}"
            if percentage[-2:] == ".0":
                percentage = percentage[:-2]
            return f"{percentage}% {m}"
        case unknown:
            return f"BUG({unknown!r})"

def jsonify(v: Label|Part|Composition|Element) -> str:
    """Emit a JSON representation of the parsed result.
    
    If we were just using lists and dictionaries we could jump directly to
    the 'json' library and get good JSON representation. That doesn't
    work so well when you're using Named Tuples, so we need to convert it
    to a lists and dictionaries.
    """
    
    match v:
        case Label(contents=[Part(), *_]):
            parts = {}
            for part in v.contents:
                parts.update(jsonify(part))
            return parts
        case Label(contents=[Composition()]):
            return jsonify(v.contents[0])
        case Part(name=n, components=c):
            return {n: jsonify(c)}
        case Composition(elements=es):
            composition = {}
            for element in es:
                composition.update(jsonify(element))
            return composition
        case Element(material=m, proportion=p):
            return {m: p}
        case unknown:
            return f"BUG({unknown!r})"

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
    print("JSON        : ", json.dumps(jsonify(result)))
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
        stringify(
            Label(contents=[
                Part(name='Shell', components=Composition(elements=[
                    Element(material='Cotton Pile', proportion=0.9),
                    Element(material='Polyester', proportion=0.1)])),
                Part(name='Lining', components=Composition(elements=[
                    Element(material='Cotton', proportion=1.0)]))]))
        '''),
    globals={
        'stringify': stringify,
        'Label': Label, 'Composition': Composition, 'Element': Element, 'Part': Part},
    number=n)])

print("Timings for jsonifying a label: ", end="")
n=1000
print([ f"{t/n * 1_000_000:.0f}µs" for t in timeit.repeat(
    dedent('''
        jsonify(
            Label(contents=[
                Part(name='Shell', components=Composition(elements=[
                    Element(material='Cotton Pile', proportion=0.9),
                    Element(material='Polyester', proportion=0.1)])),
                Part(name='Lining', components=Composition(elements=[
                    Element(material='Cotton', proportion=1.0)]))]))
        '''),
    globals={
        'jsonify': jsonify,
        'Label': Label, 'Composition': Composition, 'Element': Element, 'Part': Part},
    number=n)])
