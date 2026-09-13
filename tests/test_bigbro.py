"""End-to-end tests for BigBro using the deterministic mock LLM (no network, no API keys)."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from bigbro.capabilities import load_capabilities  # noqa: E402
from bigbro.config import Config  # noqa: E402
from bigbro.core import BigBro  # noqa: E402
from bigbro.llm.mock import MockProvider  # noqa: E402


def make_bb(tmp_path):
    cfg = Config(provider="mock", workspace=tmp_path / "ws")
    bb = BigBro(cfg)
    return bb


def test_run_with_mock_and_file_tools(tmp_path):
    bb = make_bb(tmp_path)
    bb.provider = MockProvider(script=[
        ("tool", "write_file", {"path": "projects/demo/hello.txt", "content": "hi bigbro"}),
        ("tool", "read_file", {"path": "projects/demo/hello.txt"}),
        ("final", "All done."),
    ])
    history, reply, events = bb.run("create a hello file")
    assert (bb.cfg.workspace / "projects/demo/hello.txt").read_text() == "hi bigbro"
    assert reply == "All done."
    assert [e.name for e in events] == ["write_file", "read_file"]
    assert any(m["role"] == "tool" and m.get("name") == "read_file" for m in history)


def test_scaffold_capability(tmp_path):
    bb = make_bb(tmp_path)
    out = bb._by_name["scaffold_project"].execute(kind="website-react", name="demo-site")
    assert "Scaffolded" in out
    assert (bb.cfg.workspace / "projects/demo-site/package.json").exists()
    out2 = bb._by_name["scaffold_project"].execute(kind="mobile-flutter", name="demo-app")
    assert "Scaffolded" in out2
    assert (bb.cfg.workspace / "projects/demo-app/pubspec.yaml").exists()
    out3 = bb._by_name["list_templates"].execute()
    assert "website-react" in out3 and "backend-express" in out3


def test_path_guard_blocks_workspace_escape(tmp_path):
    bb = make_bb(tmp_path)
    with pytest.raises(PermissionError):
        bb._by_name["read_file"].execute(path="/etc/passwd")
    with pytest.raises(PermissionError):
        bb._by_name["write_file"].execute(path="../outside.txt", content="x")
    with pytest.raises(PermissionError):
        bb._by_name["run_command"].execute(command="ls", cwd="../../etc")


def test_bad_capability_arguments_return_error_not_crash(tmp_path):
    bb = make_bb(tmp_path)
    from bigbro.llm.base import ToolCall
    result, ok = bb._execute(ToolCall(id="1", name="read_file", arguments={}))
    assert not ok and result.startswith("ERROR")
    result, ok = bb._execute(ToolCall(id="2", name="does_not_exist", arguments={}))
    assert not ok and "unknown capability" in result


def test_user_capability_discovery(tmp_path):
    user_dir = tmp_path / "usercaps"
    user_dir.mkdir()
    (user_dir / "mycap.py").write_text(
        "from bigbro.capabilities.base import Capability\n"
        "class Hello(Capability):\n"
        "    name = 'hello_test'\n"
        "    description = 'test cap'\n"
        '    parameters = {"type": "object", "properties": {}}\n'
        "    def execute(self):\n"
        '        return "hello from user cap"\n'
        "CAPABILITIES = [Hello]\n"
    )
    caps = load_capabilities(tmp_path / "ws", user_dir=user_dir)
    names = {c.name for c in caps}
    assert "hello_test" in names            # user capability loaded
    assert "write_file" in names            # builtins still there
    cap = next(c for c in caps if c.name == "hello_test")
    assert cap.execute() == "hello from user cap"


def test_example_custom_capability_loaded_by_default(tmp_path):
    bb = make_bb(tmp_path)
    assert "save_note" in {c.name for c in bb.caps}


FAKE_MODEL_LIST = {
    "data": [
        {"id": "old/free-old:free", "created": 1000,
         "pricing": {"prompt": "0", "completion": "0"}, "supported_parameters": ["tools"]},
        {"id": "paid/latest-paid", "created": 9999,
         "pricing": {"prompt": "0.000001", "completion": "0.000002"}, "supported_parameters": ["tools"]},
        {"id": "newest/free-with-tools:free", "created": 9000,
         "pricing": {"prompt": "0", "completion": "0"}, "supported_parameters": ["tools", "max_tokens"]},
        {"id": "free-but-no-tools:free", "created": 9500,
         "pricing": {"prompt": "0", "completion": "0"}, "supported_parameters": []},
    ]
}


class _FakeResp:
    def raise_for_status(self):
        pass

    def json(self):
        return FAKE_MODEL_LIST


def test_pick_latest_free_model_selects_newest_free_with_tools(monkeypatch):
    from bigbro.llm import free_model

    monkeypatch.setattr(free_model.requests, "get", lambda *a, **k: _FakeResp())
    assert free_model.pick_latest_free_model() == "newest/free-with-tools:free"


def test_resolve_free_model_cache_and_fallback(tmp_path, monkeypatch):
    import json as _json
    import time as _time

    from bigbro.llm import free_model

    cache = tmp_path / "cache.json"

    # 1) fresh cache → used without any network
    def boom(*a, **k):
        raise AssertionError("fresh cache must not hit the network")

    monkeypatch.setattr(free_model.requests, "get", boom)
    cache.write_text(_json.dumps({"ts": _time.time(), "model": "cached/model:free"}))
    model, source = free_model.resolve_free_model(cache_file=cache)
    assert model == "cached/model:free" and source == "cache"

    # 2) stale cache + offline → fallback constant
    cache.write_text(_json.dumps({"ts": _time.time() - 10**7, "model": "cached/model:free"}))
    model, source = free_model.resolve_free_model(cache_file=cache)
    assert source == "fallback" and model == free_model.FALLBACK_FREE_MODEL

    # 3) stale cache + live list → picks newest free+tools and refreshes cache
    monkeypatch.setattr(free_model.requests, "get", lambda *a, **k: _FakeResp())
    model, source = free_model.resolve_free_model(cache_file=cache)
    assert source == "live" and model == "newest/free-with-tools:free"
    assert _json.loads(cache.read_text())["model"] == "newest/free-with-tools:free"


def test_free_provider_requires_key(monkeypatch):
    from bigbro.config import Config
    from bigbro.llm import make_provider

    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="OPENROUTER_API_KEY"):
        make_provider(Config(provider="free"))


def test_default_provider_is_free():
    from bigbro.config import Config
    assert Config().provider == "free"
