import importlib.util
from pathlib import Path


spec = importlib.util.spec_from_file_location(
    "win_min_cmd",
    Path(__file__).resolve().parents[1] / "scripts" / "win_min_cmd.py",
)
win_min_cmd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(win_min_cmd)


def test_parse_args_accepts_exception_switch():
    parser = win_min_cmd.build_parser()
    args = parser.parse_args(["-x", "putty", "mintty"])

    assert args.class_names == []
    assert args.exception_classes == ["putty", "mintty"]
