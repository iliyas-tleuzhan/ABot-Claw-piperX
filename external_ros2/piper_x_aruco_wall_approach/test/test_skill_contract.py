import pathlib


def test_abot_skill_exists_with_required_contract():
    root = pathlib.Path(__file__).resolve().parents[3]
    skill = root / "openclaw-workspace/skills/piper-touch-marker/SKILL.md"
    assert skill.is_file()
    text = skill.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    assert "name: piper-touch-marker" in text
    assert "touch the marker" in text
    assert "/health" in text
    assert "127.0.0.1:8893" in text
    assert "/tools/touch-marker" in text
    assert "/tools/search-marker" in text
    assert "/tools/go-manipulation-pose" in text
    assert "/tools/go-nav-pose" in text
    assert "/manipulation_task/finished" in text
    assert "rear PiPER-X is intentionally disabled" in text
    assert "Never publish raw joint states" in text
