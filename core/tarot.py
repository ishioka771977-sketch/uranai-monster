"""
タロットエンジン（core/tarot.py）
大アルカナ22枚 + 小アルカナ56枚 = 78枚フルデッキ対応
"""
import json
import random
from pathlib import Path

from .models import TarotResult

_DATA_DIR = Path(__file__).parent.parent / "data"


def _load_tarot_data():
    with open(_DATA_DIR / "tarot_cards.json", encoding="utf-8") as f:
        return json.load(f)


def _load_all_cards():
    """大アルカナ + 小アルカナの全カードをロード"""
    data = _load_tarot_data()
    all_cards = []

    # 大アルカナ22枚
    for card in data.get("major_arcana", []):
        card["_arcana"] = "大アルカナ"
        all_cards.append(card)

    # 小アルカナ56枚
    for card in data.get("minor_arcana", []):
        card["_arcana"] = "小アルカナ"
        all_cards.append(card)

    return all_cards


def draw_tarot(n: int = 1, seed: int = None, major_only: bool = False) -> list:
    """
    タロットをランダムにn枚ドロー
    major_only=True: 大アルカナ22枚のみから引く（通常鑑定用）
    major_only=False: 78枚フルデッキから引く（対話型タロット用）
    """
    if major_only:
        data = _load_tarot_data()
        cards = data["major_arcana"]
        arcana_label = "大アルカナ"
    else:
        cards = _load_all_cards()
        arcana_label = None  # カードごとに判定

    if seed is not None:
        random.seed(seed)

    selected = random.sample(cards, min(n, len(cards)))
    results = []

    for card in selected:
        is_reversed = random.random() < 0.5
        if is_reversed:
            pos_data = card["reversed"]
        else:
            pos_data = card["upright"]

        arcana = arcana_label or card.get("_arcana", "大アルカナ")
        suit_name = card.get("suit_name", "")
        display_name = card["name"]

        results.append(TarotResult(
            card_name=display_name,
            card_name_en=card["name_en"],
            card_number=card["number"],
            is_reversed=is_reversed,
            arcana=arcana,
            keywords=pos_data["keywords"],
            message=pos_data["message"],
            image_key=card.get("image_key", ""),
        ))

    return results
