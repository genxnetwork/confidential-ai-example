"""Exercise the installed wheel and actual chat flow against isolated staging."""

import importlib.util
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
spec = importlib.util.spec_from_file_location(
    "chat_demo", Path(__file__).resolve().parents[1] / "confai-promter.py"
)
demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)
with patch("builtins.input", return_value=""):
    client = demo.setup_client(sys.argv[1])
expected = sys.argv[2] == "true"
assert (client is not None) == expected
if client:
    result = client.chat.completions.create(
        model=demo.CHAT_MODEL,
        messages=[{"role": "user", "content": "Synthetic container admission test."}],
    )
    assert result.choices[0].message.content.startswith("Synthetic")
    client.close()
print("CONTAINER CASE PASSED:", sys.argv[1])
