import re
import ast
import difflib

def tokenize_code(code):
    # Remove single-line comments (Python-style for now)
    code = re.sub(r'#.*', '', code)
    code = code.lower()
    tokens = re.findall(r'\b\w+\b', code)
    return set(tokens)


def jaccard_similarity(code1, code2):
    tokens1 = tokenize_code(code1)
    tokens2 = tokenize_code(code2)

    if not tokens1 or not tokens2:
        return 0

    intersection = tokens1.intersection(tokens2)
    union = tokens1.union(tokens2)

    return round(len(intersection) / len(union) * 100, 2)


def normalize_ast(code):
    """
    Parse code into AST and strip all variable/function names
    so renamed variables don't affect the similarity score.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return None

    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            node.id = "VAR"          # x, y, total → VAR
        elif isinstance(node, ast.arg):
            node.arg = "ARG"         # function arguments → ARG
        elif isinstance(node, ast.FunctionDef):
            node.name = "FUNC"       # function names → FUNC

    return ast.dump(tree)


def ast_similarity(code1, code2):
    """
    Compare the logical structure of two code snippets.
    Returns 0-100. Falls back to 0 if code has syntax errors.
    Works for Python only — other languages fall back to Jaccard.
    """
    struct1 = normalize_ast(code1)
    struct2 = normalize_ast(code2)

    if struct1 is None or struct2 is None:
        return 0

    ratio = difflib.SequenceMatcher(None, struct1, struct2).ratio()
    return round(ratio * 100, 2)


def combined_similarity(code1, code2):
    """
    Final score:
      40% Jaccard  → catches exact copy-paste
      60% AST      → catches renamed variables / same logic
    Falls back gracefully to pure Jaccard for non-Python code.
    """
    jaccard  = jaccard_similarity(code1, code2)
    ast_score = ast_similarity(code1, code2)

    # If AST returned 0 (non-Python or syntax error),
    # just use Jaccard alone so the score isn't dragged down unfairly
    if ast_score == 0:
        return jaccard

    return round((0.4 * jaccard) + (0.6 * ast_score), 2)