# Extending BigBro — your capabilities directory

BigBro loads **every** `.py` file in this folder at startup, so adding a new
capability takes one file:

```python
from bigbro.capabilities.base import Capability


class MyThing(Capability):
    name = "my_thing"            # what the LLM calls
    description = "What it does, written for the LLM."
    parameters = {
        "type": "object",
        "properties": {
            "x": {"type": "string", "description": "what x is"},
        },
        "required": ["x"],
    }

    def execute(self, x: str) -> str:
        # do the work (self.workspace = where your projects live)
        return f"did it with {x}"


CAPABILITIES = [MyThing]   # ← the loader looks for this list
```

Rules of the road:

- `execute` must return a **string** (that's what the LLM sees).
- Confine file access to `self.workspace` (use `self.safe_path()`).
- Raise exceptions on failure — BigBro turns them into `ERROR:` text the LLM can recover from.
- Name clashes: if a capability name duplicates an earlier-loaded one, the later one is skipped.
- Files starting with `_` are ignored (safe for scratch work).
- Restart the CLI/web server after adding a file (no hot reload).

`example_custom.py` in this folder is a working example (`save_note`).
