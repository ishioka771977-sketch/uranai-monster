"""エネルギー差100超の減点緩和(2026-09-25・選択肢2)のテスト"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.aisho_scoring import _score_energy_compatibility


def test_tiers_unchanged_within_100():
    assert _score_energy_compatibility(200, 220, "守備") == 10
    assert _score_energy_compatibility(200, 250, "守備") == 8
    assert _score_energy_compatibility(200, 290, "守備") == 6


def test_over_100_default_is_4():
    assert _score_energy_compatibility(342, 207) == 4
    assert _score_energy_compatibility(342, 207, "守備") == 4
    assert _score_energy_compatibility(342, 207, "学習") == 4


def test_over_100_outward_high_side_is_6():
    for h in ("表現", "攻撃", "魅力"):
        assert _score_energy_compatibility(342, 207, h) == 6
        assert _score_energy_compatibility(207, 342, h) == 6
