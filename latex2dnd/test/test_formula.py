from latex2dnd.formula import import_from_string


def test_import_from_string_executes_code_in_named_module():
    module = import_from_string("value = 6 * 7", name="answer")

    assert module.__name__ == "answer"
    assert module.__file__ == "codestr"
    assert module.value == 42
