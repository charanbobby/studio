from reel_gen.tracing.langfuse_client import get_langfuse, with_span


def test_get_langfuse_returns_singleton(monkeypatch):
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-test")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-test")
    a = get_langfuse()
    b = get_langfuse()
    assert a is b


def test_with_span_decorator_runs_function(monkeypatch):
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-test")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-test")

    @with_span(name="unit_test_span")
    def add(a: int, b: int) -> int:
        return a + b

    assert add(2, 3) == 5
