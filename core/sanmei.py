"""
算命学エンジン（core/sanmei.py）
生年月日 → 四柱（年月日時）干支・中央星・天中殺 を計算
"""
import json
import math
from datetime import date, timedelta
from pathlib import Path

from .models import PersonInput, SanmeiResult, BanshoEnergyResult
from .bansho_energy import calc_energy_index

# データファイルのパス
_DATA_DIR = Path(__file__).parent.parent / "data"


def _load_tables():
    with open(_DATA_DIR / "kanshi_table.json", encoding="utf-8") as f:
        kanshi = json.load(f)
    with open(_DATA_DIR / "star_table.json", encoding="utf-8") as f:
        star = json.load(f)
    return kanshi, star


# 六十干支（正しい60個）
KANSHI_60 = [
    "甲子","乙丑","丙寅","丁卯","戊辰","己巳","庚午","辛未","壬申","癸酉",
    "甲戌","乙亥","丙子","丁丑","戊寅","己卯","庚辰","辛巳","壬午","癸未",
    "甲申","乙酉","丙戌","丁亥","戊子","己丑","庚寅","辛卯","壬辰","癸巳",
    "甲午","乙未","丙申","丁酉","戊戌","己亥","庚子","辛丑","壬寅","癸卯",
    "甲辰","乙巳","丙午","丁未","戊申","己酉","庚戌","辛亥","壬子","癸丑",
    "甲寅","乙卯","丙辰","丁巳","戊午","己未","庚申","辛酉","壬戌","癸亥",
]

JIKKAN = ["甲","乙","丙","丁","戊","己","庚","辛","壬","癸"]
JUNISHI = ["子","丑","寅","卯","辰","巳","午","未","申","酉","戌","亥"]

JIKKAN_GOGYO = {
    "甲":"木","乙":"木","丙":"火","丁":"火","戊":"土",
    "己":"土","庚":"金","辛":"金","壬":"水","癸":"水"
}
JIKKAN_INYO = {
    "甲":"陽","乙":"陰","丙":"陽","丁":"陰","戊":"陽",
    "己":"陰","庚":"陽","辛":"陰","壬":"陽","癸":"陰"
}

# 月支（寅月=1月(旧暦)スタート）
TSUKI_SHI = ["寅","卯","辰","巳","午","未","申","酉","戌","亥","子","丑"]

# 五虎遁法（年干→1月の月干）
GOKO_TOCHU = {
    "甲":"丙","己":"丙",
    "乙":"戊","庚":"戊",
    "丙":"庚","辛":"庚",
    "丁":"壬","壬":"壬",
    "戊":"甲","癸":"甲",
}

# 日支の蔵干（主気）
JUNISHI_ZOKAN = {
    "子":"癸","丑":"己","寅":"甲","卯":"乙",
    "辰":"戊","巳":"丙","午":"丁","未":"己",
    "申":"庚","酉":"辛","戌":"戊","亥":"壬"
}

# 通変星→十大主星変換
TSUHENSEI_TO_JUDA = {
    "比肩":"貫索星","劫財":"石門星","食神":"鳳閣星","傷官":"調舒星",
    "偏財":"禄存星","正財":"司禄星","偏官":"車騎星","正官":"牽牛星",
    "偏印":"龍高星","印綬":"玉堂星"
}

# 日干→蔵干の通変星変換テーブル
NICHIKAN_TSUHEN = {
    "甲": {"甲":"比肩","乙":"劫財","丙":"食神","丁":"傷官","戊":"偏財","己":"正財","庚":"偏官","辛":"正官","壬":"偏印","癸":"印綬"},
    "乙": {"乙":"比肩","甲":"劫財","丁":"食神","丙":"傷官","己":"偏財","戊":"正財","辛":"偏官","庚":"正官","癸":"偏印","壬":"印綬"},
    "丙": {"丙":"比肩","丁":"劫財","戊":"食神","己":"傷官","庚":"偏財","辛":"正財","壬":"偏官","癸":"正官","甲":"偏印","乙":"印綬"},
    "丁": {"丁":"比肩","丙":"劫財","己":"食神","戊":"傷官","辛":"偏財","庚":"正財","癸":"偏官","壬":"正官","乙":"偏印","甲":"印綬"},
    "戊": {"戊":"比肩","己":"劫財","庚":"食神","辛":"傷官","壬":"偏財","癸":"正財","甲":"偏官","乙":"正官","丙":"偏印","丁":"印綬"},
    "己": {"己":"比肩","戊":"劫財","辛":"食神","庚":"傷官","癸":"偏財","壬":"正財","乙":"偏官","甲":"正官","丁":"偏印","丙":"印綬"},
    "庚": {"庚":"比肩","辛":"劫財","壬":"食神","癸":"傷官","甲":"偏財","乙":"正財","丙":"偏官","丁":"正官","戊":"偏印","己":"印綬"},
    "辛": {"辛":"比肩","庚":"劫財","癸":"食神","壬":"傷官","乙":"偏財","甲":"正財","丁":"偏官","丙":"正官","己":"偏印","戊":"印綬"},
    "壬": {"壬":"比肩","癸":"劫財","甲":"食神","乙":"傷官","丙":"偏財","丁":"正財","戊":"偏官","己":"正官","庚":"偏印","辛":"印綬"},
    "癸": {"癸":"比肩","壬":"劫財","乙":"食神","甲":"傷官","丁":"偏財","丙":"正財","己":"偏官","戊":"正官","辛":"偏印","庚":"印綬"},
}

# 天中殺グループ（旬番号→天中殺名）
TENCHUSATSU_MAP = {
    0: "戌亥天中殺",
    1: "申酉天中殺",
    2: "午未天中殺",
    3: "辰巳天中殺",
    4: "寅卯天中殺",
    5: "子丑天中殺",
}

# 天中殺年（直近）の年支マッピング
TENCHUSATSU_JUNISHI = {
    "戌亥天中殺": ["戌","亥"],
    "申酉天中殺": ["申","酉"],
    "午未天中殺": ["午","未"],
    "辰巳天中殺": ["辰","巳"],
    "寅卯天中殺": ["寅","卯"],
    "子丑天中殺": ["子","丑"],
}


def _calc_risshun(year: int) -> date:
    """立春の日付を近似計算（2月3〜5日）"""
    # 簡易計算: 1900年以降は2月3〜4日が多い
    # より正確には天文計算が必要だが、ここでは2月4日で近似
    return date(year, 2, 4)


def _adjust_year_for_risshun(d: date) -> int:
    """立春補正: 立春前の生まれは前年扱い"""
    risshun = _calc_risshun(d.year)
    if d < risshun:
        return d.year - 1
    return d.year


def _calc_nen_kanshi(birth_date: date) -> str:
    """年柱干支を計算"""
    year = _adjust_year_for_risshun(birth_date)
    idx = (year - 4) % 60
    return KANSHI_60[idx]


def _calc_tsuki_kanshi(birth_date: date, nen_kan: str) -> str:
    """月柱干支を計算（五虎遁法）"""
    # 節入り日（簡易: 各月3〜9日頃を節入りとする）
    # 正確には節気計算が必要だが、近似として月初めを使用
    # より正確な節入り日テーブル
    SEKKI_DAYS = {1:6, 2:4, 3:6, 4:5, 5:6, 6:6, 7:7, 8:7, 9:8, 10:8, 11:7, 12:7}

    month = birth_date.month
    day = birth_date.day
    sekki_day = SEKKI_DAYS.get(month, 6)

    # 節入り前は前月扱い
    if day < sekki_day:
        month -= 1
        if month == 0:
            month = 12

    # 月支インデックス（寅月=1月(旧暦), 実際の月→旧暦月への変換）
    # 実際の月: 1月→寅(month_idx=0が旧1月の寅), 2月→卯 ...
    # 実際の月1〜12を月支インデックスに変換
    # 寅月(旧1月)=新暦2月節, 卯月=3月節...
    # 月支: 月-1を0オリジンで寅スタートに変換
    tsuki_shi_idx = (month - 1) % 12  # 0=寅(2月節), 1=卯(3月節)...
    # 実際: 1月節=丑(12支idx=1), 2月節=寅(idx=2)... ずれているので修正
    # 正確な対応: 2月=寅, 3月=卯, 4月=辰, 5月=巳, 6月=午, 7月=未,
    #             8月=申, 9月=酉, 10月=戌, 11月=亥, 12月=子, 1月=丑
    MONTH_TO_SHI = {
        2:"寅", 3:"卯", 4:"辰", 5:"巳", 6:"午", 7:"未",
        8:"申", 9:"酉", 10:"戌", 11:"亥", 12:"子", 1:"丑"
    }
    tsuki_shi = MONTH_TO_SHI[month]
    tsuki_shi_idx = JUNISHI.index(tsuki_shi)

    # 五虎遁法: 年干から寅月（2月節=旧暦1月）の月干を決定
    start_kan = GOKO_TOCHU[nen_kan]
    start_kan_idx = JIKKAN.index(start_kan)

    # 月干の計算: 寅月(2月節)をoffset=0として月数を加算
    # 寅=2月, 卯=3月, 辰=4月, 巳=5月, ...
    MONTH_ORDER = {"寅":0,"卯":1,"辰":2,"巳":3,"午":4,"未":5,"申":6,"酉":7,"戌":8,"亥":9,"子":10,"丑":11}
    month_offset = MONTH_ORDER[tsuki_shi]

    tsuki_kan_idx = (start_kan_idx + month_offset) % 10
    tsuki_kan = JIKKAN[tsuki_kan_idx]

    return tsuki_kan + tsuki_shi


def _calc_jd(d: date) -> float:
    """ユリウス日を計算"""
    y, m, day = d.year, d.month, d.day
    if m <= 2:
        y -= 1
        m += 12
    A = int(y / 100)
    B = 2 - A + int(A / 4)
    jd = int(365.25 * (y + 4716)) + int(30.6001 * (m + 1)) + day + B - 1524.5
    return jd


def _calc_hi_kanshi(birth_date: date) -> str:
    """日柱干支を計算（JD法）

    基準: JDの floor値に+50してmod60すると干支インデックスが得られる
    （1899/12/22 = 甲子(index 0) に対応）
    検証: 1977/5/24 → JD=2443287.5 → floor=2443287 → +50=2443337 → %60=17 → 辛巳 ✓
    """
    birth_jd = _calc_jd(birth_date)
    idx = (int(birth_jd) + 50) % 60
    return KANSHI_60[idx]


def _calc_tenchusatsu(hi_kanshi: str) -> str:
    """天中殺グループを判定"""
    idx = KANSHI_60.index(hi_kanshi)
    jun_num = idx // 10  # 旬番号（0〜5）
    return TENCHUSATSU_MAP[jun_num]


def _calc_star_from_kan(nichikan: str, target_kan: str, star_table: dict) -> tuple:
    """日干と対象天干の関係から十大主星を導出"""
    tsuhen = NICHIKAN_TSUHEN[nichikan].get(target_kan, "比肩")
    sei = TSUHENSEI_TO_JUDA[tsuhen]
    sei_data = star_table["juudaishusei"][sei]
    return sei, sei_data["honno"]


def _calc_chuo_sei(nichikan: str, hi_shi: str, star_table: dict) -> tuple:
    """中央星（日支の蔵干と日干の関係から）を計算"""
    zokan = JUNISHI_ZOKAN[hi_shi]
    tsuhen = NICHIKAN_TSUHEN[nichikan].get(zokan, "比肩")
    chuo_sei = TSUHENSEI_TO_JUDA[tsuhen]

    sei_data = star_table["juudaishusei"][chuo_sei]
    return chuo_sei, sei_data["honno"], sei_data["keywords"], sei_data["charm_words"]


def _calc_jintaizu(nichikan: str, nen_kan: str, tsuki_kan: str,
                   hi_shi: str, nen_shi: str, star_table: dict) -> dict:
    """
    人体図（十大主星の配置）を計算
    - 中央: 日干 vs 日支蔵干（月支蔵干の流派もあるが、日支蔵干を採用）
    - 北（頭）: 日干 vs 年干
    - 南（腹）: 日干 vs 月干
    - 東（右手）: 日干 vs 日支蔵干 → 中央と同じなので月支蔵干を使用
    - 西（左手）: 日干 vs 年支蔵干
    """
    # 中央星は別途計算済みなので、残り4つを計算
    kita_sei, kita_honno = _calc_star_from_kan(nichikan, nen_kan, star_table)
    minami_sei, minami_honno = _calc_star_from_kan(nichikan, tsuki_kan, star_table)

    # 東: 日支蔵干（本気）
    hi_zokan = JUNISHI_ZOKAN[hi_shi]
    higashi_sei, higashi_honno = _calc_star_from_kan(nichikan, hi_zokan, star_table)

    # 西: 年支蔵干（本気）
    nen_zokan = JUNISHI_ZOKAN[nen_shi]
    nishi_sei, nishi_honno = _calc_star_from_kan(nichikan, nen_zokan, star_table)

    return {
        "kita_sei": kita_sei, "kita_honno": kita_honno,
        "minami_sei": minami_sei, "minami_honno": minami_honno,
        "higashi_sei": higashi_sei, "higashi_honno": higashi_honno,
        "nishi_sei": nishi_sei, "nishi_honno": nishi_honno,
    }


# 地支の五行（蔵干の本気五行）
JUNISHI_GOGYO = {
    "子": "水", "丑": "土", "寅": "木", "卯": "木",
    "辰": "土", "巳": "火", "午": "火", "未": "土",
    "申": "金", "酉": "金", "戌": "土", "亥": "水",
}


def _calc_gogyo_balance(nen_kanshi: str, tsuki_kanshi: str, hi_kanshi: str) -> dict:
    """
    五行バランスを計算（天干3つ + 地支3つ = 6要素）
    """
    balance = {"木": 0, "火": 0, "土": 0, "金": 0, "水": 0}

    # 天干の五行
    for kan in [nen_kanshi[0], tsuki_kanshi[0], hi_kanshi[0]]:
        g = JIKKAN_GOGYO.get(kan)
        if g:
            balance[g] += 1

    # 地支の五行
    for shi in [nen_kanshi[1], tsuki_kanshi[1], hi_kanshi[1]]:
        g = JUNISHI_GOGYO.get(shi)
        if g:
            balance[g] += 1

    return balance


def _detect_kakkyoku(nen_kanshi: str, tsuki_kanshi: str, hi_kanshi: str) -> str:
    """
    特殊格局を検出
    - 三位一体格（三巳格、三酉格など）: 3柱の地支が同じ
    - 一気格: 3柱の地支が同じ五行
    """
    nen_shi = nen_kanshi[1]
    tsuki_shi = tsuki_kanshi[1]
    hi_shi = hi_kanshi[1]

    # 三位一体格（地支が3つとも同じ）
    if nen_shi == tsuki_shi == hi_shi:
        shi_names = {
            "子": "三子格", "丑": "三丑格", "寅": "三寅格", "卯": "三卯格",
            "辰": "三辰格", "巳": "三巳格", "午": "三午格", "未": "三未格",
            "申": "三申格", "酉": "三酉格", "戌": "三戌格", "亥": "三亥格",
        }
        return shi_names.get(nen_shi, "")

    # 方合（三合会局）チェック
    SANKAGO = [
        ({"申", "子", "辰"}, "水局三合"),
        ({"寅", "午", "戌"}, "火局三合"),
        ({"巳", "酉", "丑"}, "金局三合"),
        ({"亥", "卯", "未"}, "木局三合"),
    ]
    shi_set = {nen_shi, tsuki_shi, hi_shi}
    for pattern, name in SANKAGO:
        if shi_set == pattern:
            return name

    # 一気格（地支が同じ五行）
    gogyo_set = {JUNISHI_GOGYO[nen_shi], JUNISHI_GOGYO[tsuki_shi], JUNISHI_GOGYO[hi_shi]}
    if len(gogyo_set) == 1:
        element = gogyo_set.pop()
        return f"{element}性地支一気格"

    return ""


def _calc_tenchusatsu_years(tenchusatsu: str, base_year: int = None) -> list:
    if base_year is None:
        from datetime import date
        base_year = date.today().year
    """直近の天中殺年を計算"""
    missing_shi = TENCHUSATSU_JUNISHI[tenchusatsu]
    years = []
    for y in range(base_year - 2, base_year + 12):
        y_shi_idx = (y - 4) % 12
        y_shi = JUNISHI[y_shi_idx]
        if y_shi in missing_shi:
            years.append(y)
    return sorted(years)[:4]  # 直近4年分


def calculate_sanmei(person: PersonInput) -> SanmeiResult:
    """
    生年月日 → 算命学の命式を計算（人体図全5星・五行バランス・特殊格局込み）
    """
    _, star_table = _load_tables()

    d = person.birth_date

    # 年柱
    nen_kanshi = _calc_nen_kanshi(d)
    nen_kan = nen_kanshi[0]
    nen_shi = nen_kanshi[1]

    # 月柱
    tsuki_kanshi = _calc_tsuki_kanshi(d, nen_kan)
    tsuki_kan = tsuki_kanshi[0]
    tsuki_shi = tsuki_kanshi[1]

    # 日柱
    hi_kanshi = _calc_hi_kanshi(d)
    nichikan = hi_kanshi[0]   # 日干
    hi_shi = hi_kanshi[1]     # 日支
    nichikan_gogyo = JIKKAN_GOGYO[nichikan]
    nichikan_inyo = JIKKAN_INYO[nichikan]

    # 天中殺
    tenchusatsu = _calc_tenchusatsu(hi_kanshi)
    tenchusatsu_years = _calc_tenchusatsu_years(tenchusatsu)

    # 中央星
    chuo_sei, chuo_honno, keywords, charm_words = _calc_chuo_sei(nichikan, hi_shi, star_table)

    # 人体図全5星
    jintaizu = _calc_jintaizu(nichikan, nen_kan, tsuki_kan, hi_shi, nen_shi, star_table)

    # 五行バランス
    gogyo_balance = _calc_gogyo_balance(nen_kanshi, tsuki_kanshi, hi_kanshi)

    # 特殊格局
    kakkyoku = _detect_kakkyoku(nen_kanshi, tsuki_kanshi, hi_kanshi)

    # 万象学エネルギー
    energy = calc_energy_index(nen_kan, nen_shi, tsuki_kan, tsuki_shi, nichikan, hi_shi)
    bansho = BanshoEnergyResult(
        total_energy=energy["total_energy"],
        energy_type=energy["energy_type"],
        energy_description=energy["energy_description"],
        energy_advice=energy["energy_advice"],
        gogyo_scores={g: d["総合計"] for g, d in energy["gogyo_detail"].items()},
        honnou_ranking=energy["honnou_ranking"],
        top_honnou=energy["top_honnou"],
        top_score=energy["top_score"],
        second_honnou=energy["second_honnou"],
        second_score=energy["second_score"],
        zero_honnou=energy["zero_honnou"],
        combo_talent=energy["combo_talent"],
        combo_description=energy["combo_description"],
        one_liner=energy["one_liner"],
        drink_talk=energy["drink_talk"],
    )

    return SanmeiResult(
        nen_kanshi=nen_kanshi,
        tsuki_kanshi=tsuki_kanshi,
        hi_kanshi=hi_kanshi,
        nichikan=nichikan,
        nichikan_gogyo=nichikan_gogyo,
        nichikan_inyo=nichikan_inyo,
        chuo_sei=chuo_sei,
        chuo_honno=chuo_honno,
        tenchusatsu=tenchusatsu,
        tenchusatsu_years=tenchusatsu_years,
        keywords=keywords[:5],
        charm_words=charm_words,
        kita_sei=jintaizu["kita_sei"],
        kita_honno=jintaizu["kita_honno"],
        minami_sei=jintaizu["minami_sei"],
        minami_honno=jintaizu["minami_honno"],
        higashi_sei=jintaizu["higashi_sei"],
        higashi_honno=jintaizu["higashi_honno"],
        nishi_sei=jintaizu["nishi_sei"],
        nishi_honno=jintaizu["nishi_honno"],
        gogyo_balance=gogyo_balance,
        kakkyoku=kakkyoku,
        bansho_energy=bansho,
        nen_kan=nen_kan,
        nen_shi=nen_shi,
        tsuki_kan=tsuki_kan,
        tsuki_shi=tsuki_shi,
        hi_kan=nichikan,
        hi_shi=hi_shi,
    )
