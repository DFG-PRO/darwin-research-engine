from pathlib import Path
import ast


GENERATED_TEST = Path(__file__).with_name(
    "test_content_hashing_model_qualification.py"
)


def test_generated_hashing_qualification_is_semantically_nontrivial():
    assert GENERATED_TEST.exists(), "model did not create the required test file"

    source = GENERATED_TEST.read_text(encoding="utf-8")
    tree = ast.parse(source)

    functions = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name
        == "test_sha256_helpers_are_deterministic_and_equivalent_for_utf8_text"
    ]
    assert len(functions) == 1

    function = functions[0]

    assert any(isinstance(node, ast.Assert) for node in ast.walk(function))

    called_names = set()
    for node in ast.walk(function):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            called_names.add(node.func.id)

    assert "sha256_text" in called_names
    assert "sha256_bytes" in called_names

    constants = {
        node.value
        for node in ast.walk(function)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    assert any("sha256:" in value for value in constants)

    assert ".encode(" in source
