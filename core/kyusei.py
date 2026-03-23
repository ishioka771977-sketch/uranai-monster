"""
九星気学エンジン（core/kyusei.py）
生年月日 → 本命星・月命星・年盤位置・今年のテーマ
"""
import json
from datetime import date
from pathlib import Path

from .models import PersonInput, KyuseiResult

_DATA_DIR = Path(__file__).parent.parent / "data"

KYUSEI_NAMES = {
    1:"一白水星", 2:"二黒土星", 3:"三碧木星",
    4:"四緑木星", 5:"五黄土星", 6:"六白金星",
    7:"七赤金星", 8:"八白土星", 9:"九紫火星"
}


def _load_kyusei_table():
    with open(_DATA_DIR / "kyusei_table.json", encoding="utf-8") as f:
        return json.load(f)


def _calc_risshun(year: int) -> date:
    """立春の日付（2月4日で近似）"""
    return date(year, 2, 4)


def calc_honmei_sei(birth_year: int, birth_month: int, birth_day: int) -> int:
    """
    本命星番号を計算（各桁の和法）
    西暦の各桁を足して一桁にし、11から引く（10以上なら-9）
    ※ 立春（2月4日）前は前年扱い
    検証: 1977/5/24 → 1+9+7+7=24→2+4=6→11-6=5 → 五黄土星 ✓
    """
    year = birth_year
    risshun = _calc_risshun(year)
    if date(birth_year, birth_month, birth_day) < risshun:
        year -= 1

    # 各桁の和を一桁になるまで繰り返す
    digit_sum = sum(int(c) for c in str(year))
    while digit_sum >= 10:
        digit_sum = sum(int(c) for c in str(digit_sum))
    sei_num = 11 - digit_sum
    if sei_num > 9:
        sei_num -= 9
    return sei_num


def _calc_getsu_mei_sei(honmei_num: int, birth_month: int, birth_day: int) -> int:
    """
    月命星番号を計算
    月の節入り（各月6〜8日頃）前は前月扱い
    """
    SEKKI_DAYS = {1:6, 2:4, 3:6, 4:5, 5:6, 6:6, 7:7, 8:7, 9:8, 10:8, 11:7, 12:7}
    month = birth_month
    day = birth_day

    if day < SEKKI_DAYS.get(month, 6):
        month -= 1
        if month == 0:
            month = 12

    # 月命星テーブル: 本命星番号 → 1月(1月節)の月命星
    # グループ規則: 本命星1,4,7 → 8; 2,5,8 → 5; 3,6,9 → 2
    # 検証: 六白(6)5月生まれ → start=2, 2-(5-1)=-2→+9=7 → 七赤 ✓
    GETSU_MEI_START = {
        1: 8, 2: 5, 3: 2,
        4: 8, 5: 5, 6: 2,
        7: 8, 8: 5, 9: 2
    }
    start = GETSU_MEI_START[honmei_num]
    # 1月スタートで月が増えるごとに-1
    getsu_num = start - (month - 1)
    while getsu_num <= 0:
        getsu_num += 9
    return getsu_num


def _calc_bad_direction(honmei_num: int) -> str:
    """凶方位を計算（本命殺・本命的殺の方位）"""
    # 各本命星の凶方位（暗剣殺・五黄殺の方位 + 本命殺）
    BAD_DIRECTIONS = {
        1: "南",      # 一白の反対方向
        2: "北東",
        3: "西",
        4: "北西",
        5: "全方位注意",
        6: "南東",
        7: "東",
        8: "南西",
        9: "北",
    }
    return BAD_DIRECTIONS.get(honmei_num, "")


def calculate_kyusei(person: PersonInput, target_year: int = 2026) -> KyuseiResult:
    """
    生年月日 → 本命星・月命星・年盤位置を計算
    """
    table = _load_kyusei_table()

    d = person.birth_date
    honmei_num = calc_honmei_sei(d.year, d.month, d.day)
    honmei_sei = KYUSEI_NAMES[honmei_num]

    getsu_num = _calc_getsu_mei_sei(honmei_num, d.month, d.day)
    getsu_mei_sei = KYUSEI_NAMES[getsu_num]

    # 年盤位置と今年のテーマ
    positions_2026 = table["position_themes_2026"]["positions"]
    pos_data = positions_2026.get(honmei_sei, {
        "position": "中宮", "theme": "充実の年", "desc": "力を蓄え前進する年"
    })

    lucky_dir = table["lucky_directions_2026"].get(honmei_sei, "東・南")

    # 凶方位（本命殺・本命的殺）
    bad_dir = _calc_bad_direction(honmei_num)

    keywords = table["kyusei_keywords"].get(honmei_sei, [])

    return KyuseiResult(
        honmei_sei=honmei_sei,
        getsu_mei_sei=getsu_mei_sei,
        year_position=pos_data["position"],
        year_theme=pos_data["theme"],
        year_desc=pos_data["desc"],
        lucky_direction=lucky_dir,
        keywords=keywords[:5],
        bad_direction=bad_dir,
    )
