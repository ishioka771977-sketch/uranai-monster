"""
四柱推命エンジン（core/shichusuimei.py）
生年月日＋出生時刻 → 四柱（年月日時）・蔵干・通変星・十二運・空亡・神殺・大運を計算

sanmei.py と以下を共有:
- KANSHI_60, JIKKAN, JUNISHI, JIKKAN_GOGYO, JIKKAN_INYO, JUNISHI_ZOKAN
- NICHIKAN_TSUHEN（10×10通変星マトリクス）
- TSUHENSEI_TO_JUDA（通変星→十大主星）
- _calc_nen_kanshi, _calc_tsuki_kanshi, _calc_hi_kanshi, _calc_tenchusatsu
"""
from __future__ import annotations
from datetime import date, datetime, timedelta
from typing import Optional, List, Dict, Tuple

from .models import PersonInput, ShichusuimeiResult, Pillar, TaiunEntry
from .sanmei import (
    KANSHI_60, JIKKAN, JUNISHI,
    JIKKAN_GOGYO, JIKKAN_INYO, JUNISHI_ZOKAN,
    NICHIKAN_TSUHEN, TSUHENSEI_TO_JUDA,
    TENCHUSATSU_JUNISHI,
    _calc_nen_kanshi, _calc_tsuki_kanshi, _calc_hi_kanshi,
    _calc_tenchusatsu,
)


# =============================================================================
# 算命学との対応マッピング（公開）
# =============================================================================
# 四柱推命と算命学は基盤が共通で、通変星と十大主星は1:1対応。
# 統合鑑定で「四柱推命では偏官、算命学では車騎星」と両方の言葉で語れるよう、
# このモジュール直下に明示的に定数として配置する。

# 通変星（四柱推命）→ 十大主星（算命学）
TSUHENSEI_TO_JUDA_SEI = {
    "比肩": "貫索星", "劫財": "石門星",
    "食神": "鳳閣星", "傷官": "調舒星",
    "偏財": "禄存星", "正財": "司禄星",
    "偏官": "車騎星", "正官": "牽牛星",
    "偏印": "龍高星", "印綬": "玉堂星",
}
# 逆引き: 十大主星 → 通変星
JUDA_SEI_TO_TSUHENSEI = {v: k for k, v in TSUHENSEI_TO_JUDA_SEI.items()}

# 十二運星（四柱推命）→ 十二大従星（算命学）
# 両者は完全に1:1ではなく、並びは同じだが名称体系が異なる
JUNI_UNSEI_TO_JUDA_JUSEI = {
    "長生": "天貴星", "沐浴": "天恍星", "冠帯": "天南星", "臨官": "天禄星",
    "帝旺": "天将星", "衰":   "天堂星", "病":   "天胡星", "死":   "天極星",
    "墓":   "天庫星", "絶":   "天馳星", "胎":   "天報星", "養":   "天印星",
}


# =============================================================================
# 定数テーブル
# =============================================================================

# 五鼠遁（日干→子時(23-01時)の時干）
GOSO_TOCHU = {
    "甲": "甲", "己": "甲",  # 甲子時起
    "乙": "丙", "庚": "丙",  # 丙子時起
    "丙": "戊", "辛": "戊",  # 戊子時起
    "丁": "庚", "壬": "庚",  # 庚子時起
    "戊": "壬", "癸": "壬",  # 壬子時起
}

# 時刻 → 時支のインデックス（JUNISHI上の）
# 子=0, 丑=1, 寅=2, 卯=3, 辰=4, 巳=5, 午=6, 未=7, 申=8, 酉=9, 戌=10, 亥=11
# 子の刻は23時〜01時（跨日）
def _hour_to_toki_shi_idx(hour: int, minute: int = 0) -> int:
    """時刻(0-23時)から時支インデックスを返す"""
    # 分を含めて時刻を少し精密化（境界は切り上げ側で子刻23:00〜翌01:00を0にする）
    if hour == 23 or hour == 0:
        return 0  # 子
    if hour < 0 or hour > 23:
        raise ValueError(f"invalid hour: {hour}")
    # 1時〜22時のケース
    # 丑(1-3), 寅(3-5), ..., 亥(21-23)
    # インデックス: (hour + 1) // 2
    # hour=1→1(丑), hour=2→1(丑), hour=3→2(寅), hour=4→2(寅), ..., hour=22→11(亥)
    return (hour + 1) // 2


# 十二運（長生→養の順）
JUNI_UNSEI_ORDER = [
    "長生", "沐浴", "冠帯", "臨官", "帝旺",
    "衰", "病", "死", "墓", "絶", "胎", "養",
]

# 各日干の「長生」がある地支
CHOSEI_BRANCH = {
    "甲": "亥", "乙": "午", "丙": "寅", "丁": "酉", "戊": "寅",
    "己": "酉", "庚": "巳", "辛": "子", "壬": "申", "癸": "卯",
}

# 月律分野蔵干テーブル（地支 → [(天干, 日数), ...] 余気→中気→本気）
# 日数の合計が各支の日数（30日）に対応
ZOUKAN_DETAIL = {
    "子": [("壬", 10), ("癸", 20)],
    "丑": [("癸", 9), ("辛", 3), ("己", 18)],
    "寅": [("戊", 7), ("丙", 7), ("甲", 16)],
    "卯": [("甲", 10), ("乙", 20)],
    "辰": [("乙", 9), ("癸", 3), ("戊", 18)],
    "巳": [("戊", 7), ("庚", 7), ("丙", 16)],
    "午": [("丙", 10), ("己", 10), ("丁", 10)],  # 流派により2つの場合も
    "未": [("丁", 9), ("乙", 3), ("己", 18)],
    "申": [("戊", 7), ("壬", 7), ("庚", 16)],
    "酉": [("庚", 10), ("辛", 20)],
    "戌": [("辛", 9), ("丁", 3), ("戊", 18)],
    "亥": [("戊", 7), ("甲", 7), ("壬", 16)],
}

# 節入り日の近似（sanmei.pyの SEKKI_DAYS と整合、月→節入り日）
SEKKI_DAYS = {1: 6, 2: 4, 3: 6, 4: 5, 5: 6, 6: 6, 7: 7, 8: 7, 9: 8, 10: 8, 11: 7, 12: 7}

# 月支→対応する月の節入りを持つ月（新暦）
# 節入り: 立春(2月)=寅, 啓蟄(3月)=卯, 清明(4月)=辰, 立夏(5月)=巳, 芒種(6月)=午,
#         小暑(7月)=未, 立秋(8月)=申, 白露(9月)=酉, 寒露(10月)=戌, 立冬(11月)=亥,
#         大雪(12月)=子, 小寒(1月)=丑
SHI_TO_MONTH = {
    "寅": 2, "卯": 3, "辰": 4, "巳": 5, "午": 6, "未": 7,
    "申": 8, "酉": 9, "戌": 10, "亥": 11, "子": 12, "丑": 1,
}


# =============================================================================
# 神殺テーブル
# =============================================================================

# 日干基準
SHINSATSU_BY_NICHIKAN = {
    "天乙貴人":  {"甲":["丑","未"], "乙":["子","申"], "丙":["酉","亥"], "丁":["酉","亥"],
                "戊":["丑","未"], "己":["子","申"], "庚":["丑","未"], "辛":["寅","午"],
                "壬":["卯","巳"], "癸":["卯","巳"]},
    "文昌貴人":  {"甲":["巳"], "乙":["午"], "丙":["申"], "丁":["酉"], "戊":["申"],
                "己":["酉"], "庚":["亥"], "辛":["子"], "壬":["寅"], "癸":["卯"]},
    "羊刃":      {"甲":["卯"], "乙":["辰"], "丙":["午"], "丁":["未"], "戊":["午"],
                "己":["未"], "庚":["酉"], "辛":["戌"], "壬":["子"], "癸":["丑"]},
    "大極貴人":  {"甲":["子","午"], "乙":["子","午"], "丙":["卯","酉"], "丁":["卯","酉"],
                "戊":["丑","辰","未","戌"], "己":["丑","辰","未","戌"],
                "庚":["寅","亥"], "辛":["寅","亥"], "壬":["巳","申"], "癸":["巳","申"]},
    "福星貴人":  {"甲":["寅"], "乙":["丑","亥"], "丙":["子","戌"], "丁":["酉"], "戊":["申"],
                "己":["未"], "庚":["午"], "辛":["巳"], "壬":["辰"], "癸":["卯"]},
}

# 年支 or 日支 基準（三合局ベース）
# グループ: 寅午戌 / 巳酉丑 / 申子辰 / 亥卯未
SANGO_GROUPS = {
    "寅": "寅午戌", "午": "寅午戌", "戌": "寅午戌",
    "巳": "巳酉丑", "酉": "巳酉丑", "丑": "巳酉丑",
    "申": "申子辰", "子": "申子辰", "辰": "申子辰",
    "亥": "亥卯未", "卯": "亥卯未", "未": "亥卯未",
}

SHINSATSU_BY_SANGO_BRANCH = {
    "駅馬":    {"寅午戌":"申", "巳酉丑":"亥", "申子辰":"寅", "亥卯未":"巳"},
    "桃花殺":  {"寅午戌":"卯", "巳酉丑":"午", "申子辰":"酉", "亥卯未":"子"},
    "華蓋":    {"寅午戌":"戌", "巳酉丑":"丑", "申子辰":"辰", "亥卯未":"未"},
    "劫殺":    {"寅午戌":"亥", "巳酉丑":"寅", "申子辰":"巳", "亥卯未":"申"},
    "亡神":    {"寅午戌":"巳", "巳酉丑":"申", "申子辰":"亥", "亥卯未":"寅"},
}

# 月支基準
# 天徳貴人は「干」または「支」で指定（辞書の値が天干か地支か）
TENTOKU_TABLE = {
    "子":("支","巳"), "丑":("干","庚"), "寅":("干","丁"), "卯":("支","申"),
    "辰":("干","壬"), "巳":("干","辛"), "午":("支","亥"), "未":("干","甲"),
    "申":("干","癸"), "酉":("支","寅"), "戌":("干","丙"), "亥":("干","乙"),
}

# 月徳貴人（月支の三合局 → 天干）
GETTOKU_TABLE = {
    "寅午戌":"丙", "申子辰":"壬", "巳酉丑":"庚", "亥卯未":"甲",
}

# 血刃（年支 or 日支 基準 → 他柱の地支）
KETSUJIN_TABLE = {
    "子":"戌", "丑":"酉", "寅":"申", "卯":"未",
    "辰":"午", "巳":"巳", "午":"辰", "未":"卯",
    "申":"寅", "酉":"丑", "戌":"子", "亥":"亥",
}

# 月徳合（月支 → 天干）
GETTOKU_GOU_TABLE = {
    "寅":"辛", "卯":"己", "辰":"丁", "巳":"乙",
    "午":"辛", "未":"己", "申":"丁", "酉":"乙",
    "戌":"辛", "亥":"己", "子":"丁", "丑":"乙",
}

# 節度貴人（日干 → 地支）
SETSUDO_KIJIN_TABLE = {
    "甲":"巳", "乙":"未", "丙":"巳", "丁":"未", "戊":"巳",
    "己":"未", "庚":"亥", "辛":"丑", "壬":"亥", "癸":"丑",
}


# =============================================================================
# 内部関数
# =============================================================================

def _parse_time(birth_time: str) -> Tuple[int, int]:
    """'HH:MM' を (hour, minute) にパース"""
    h, m = birth_time.split(":")
    return int(h), int(m)


def _calc_toki_kanshi(birth_time: str, nichikan: str) -> str:
    """時柱干支を計算（五鼠遁）"""
    hour, minute = _parse_time(birth_time)
    shi_idx = _hour_to_toki_shi_idx(hour, minute)
    toki_shi = JUNISHI[shi_idx]
    start_kan = GOSO_TOCHU[nichikan]
    start_kan_idx = JIKKAN.index(start_kan)
    toki_kan = JIKKAN[(start_kan_idx + shi_idx) % 10]
    return toki_kan + toki_shi


def _calc_tsuhensei(nichikan: str, target_kan: str) -> str:
    """日干と対象天干から通変星を求める（sanmei.NICHIKAN_TSUHEN を流用）"""
    return NICHIKAN_TSUHEN[nichikan][target_kan]


def _calc_juni_unsei(nichikan: str, branch: str) -> str:
    """日干と地支から十二運星を求める"""
    is_yang = (JIKKAN_INYO[nichikan] == "陽")
    chosei_idx = JUNISHI.index(CHOSEI_BRANCH[nichikan])
    branch_idx = JUNISHI.index(branch)
    if is_yang:
        offset = (branch_idx - chosei_idx) % 12
    else:
        offset = (chosei_idx - branch_idx) % 12
    return JUNI_UNSEI_ORDER[offset]


def _days_from_setsuiri(birth_date: date) -> int:
    """生日がその月支の節入りから何日目か（1起点）を返す"""
    month = birth_date.month
    sekki_day = SEKKI_DAYS.get(month, 6)
    if birth_date.day < sekki_day:
        # 前月の節入りからの日数
        prev_month = month - 1 if month > 1 else 12
        prev_year = birth_date.year if month > 1 else birth_date.year - 1
        prev_sekki = SEKKI_DAYS.get(prev_month, 6)
        try:
            prev_setsu = date(prev_year, prev_month, prev_sekki)
        except ValueError:
            prev_setsu = date(prev_year, prev_month, 1)
        return (birth_date - prev_setsu).days + 1
    else:
        setsu = date(birth_date.year, month, sekki_day)
        return (birth_date - setsu).days + 1


def _calc_tsuki_zoukan(tsuki_shi: str, days_from_setsuiri: int) -> Tuple[str, str]:
    """月柱の蔵干（月律分野蔵干）を節入りからの日数で選出
    Returns: (天干, 分類名 "余気"|"中気"|"本気")
    """
    entries = ZOUKAN_DETAIL[tsuki_shi]
    labels = ["余気", "中気", "本気"] if len(entries) == 3 else ["余気", "本気"]
    cumulative = 0
    for i, (stem, days) in enumerate(entries):
        cumulative += days
        if days_from_setsuiri <= cumulative:
            return stem, labels[i]
    # 範囲外（本気）
    return entries[-1][0], labels[-1]


def _calc_shinsatsu(
    nichikan: str,
    nen_shi: str, tsuki_shi: str, hi_shi: str, toki_shi: Optional[str],
    nen_kan: str, tsuki_kan: str, toki_kan: Optional[str],
) -> List[Dict]:
    """神殺12種を判定。位置情報つきで返す"""
    result = []
    position_labels = [
        ("年支", nen_shi), ("月支", tsuki_shi), ("日支", hi_shi),
    ]
    if toki_shi:
        position_labels.append(("時支", toki_shi))
    kan_labels = [("年干", nen_kan), ("月干", tsuki_kan)]
    if toki_kan:
        kan_labels.append(("時干", toki_kan))

    # 1-5, 11-12. 日干基準 → 命式中の地支
    for name, table in SHINSATSU_BY_NICHIKAN.items():
        candidates = table.get(nichikan, [])
        for pos, branch in position_labels:
            if branch in candidates:
                # 日干基準の神殺で日干自身の柱は含める
                result.append({"name": name, "position": pos, "element": branch})

    # 4-8. 年支/日支基準の三合局系
    # 同一の (name, position, element) は基準が違っても1回だけ登録する
    seen_sango = set()
    for base_pos, base_shi in [("年支", nen_shi), ("日支", hi_shi)]:
        group = SANGO_GROUPS.get(base_shi)
        if not group:
            continue
        for name, table in SHINSATSU_BY_SANGO_BRANCH.items():
            target = table[group]
            for pos, branch in position_labels:
                if branch == target:
                    key = (name, pos, branch)
                    if key in seen_sango:
                        continue
                    seen_sango.add(key)
                    result.append({"name": name, "position": pos, "element": branch, "basis": base_pos})

    # 9. 天徳貴人（月支基準 → 他の柱の干 or 支）
    kind, target = TENTOKU_TABLE[tsuki_shi]
    if kind == "干":
        for pos, k in kan_labels:
            if k == target:
                result.append({"name": "天徳貴人", "position": pos, "element": k})
        # 日干も判定対象
        if nichikan == target:
            result.append({"name": "天徳貴人", "position": "日干", "element": nichikan})
    else:  # kind == "支"
        for pos, b in position_labels:
            if b == target:
                result.append({"name": "天徳貴人", "position": pos, "element": b})

    # 10. 月徳貴人（月支三合局 → 天干）
    group = SANGO_GROUPS.get(tsuki_shi)
    if group:
        target_kan = GETTOKU_TABLE[group]
        for pos, k in kan_labels:
            if k == target_kan:
                result.append({"name": "月徳貴人", "position": pos, "element": k})
        if nichikan == target_kan:
            result.append({"name": "月徳貴人", "position": "日干", "element": nichikan})

    # 13. 血刃（年支 or 日支 → 他柱の地支）
    seen_ketsu = set()
    for base_pos, base_shi in [("年支", nen_shi), ("日支", hi_shi)]:
        target = KETSUJIN_TABLE.get(base_shi)
        if not target:
            continue
        for pos, branch in position_labels:
            if branch == target:
                key = ("血刃", pos, branch)
                if key in seen_ketsu:
                    continue
                seen_ketsu.add(key)
                result.append({"name": "血刃", "position": pos, "element": branch, "basis": base_pos})

    # 14. 月徳合（月支 → 他柱の天干）
    target_kan = GETTOKU_GOU_TABLE.get(tsuki_shi)
    if target_kan:
        for pos, k in kan_labels:
            if k == target_kan:
                result.append({"name": "月徳合", "position": pos, "element": k})
        if nichikan == target_kan:
            result.append({"name": "月徳合", "position": "日干", "element": nichikan})

    # 15. 節度貴人（日干 → 命式中の地支）
    target_shi = SETSUDO_KIJIN_TABLE.get(nichikan)
    if target_shi:
        for pos, branch in position_labels:
            if branch == target_shi:
                result.append({"name": "節度貴人", "position": pos, "element": branch})

    return result


def _calc_taiun(
    birth_date: date,
    gender: Optional[str],
    nen_kan: str,
    tsuki_kanshi: str,
    nichikan: str,
) -> Tuple[int, int, int, str, List[TaiunEntry]]:
    """大運を算出。
    Returns: (days_to_setsu, ritsuun_mansai, ritsuun_kazoe, direction, taiun_list)
    """
    is_yang_year = (JIKKAN_INYO[nen_kan] == "陽")
    is_male = (gender in ("男性", "男", "male", "M", "m"))
    forward = (is_yang_year and is_male) or ((not is_yang_year) and (not is_male))

    # 節入りまでの日数
    month = birth_date.month
    sekki_day = SEKKI_DAYS.get(month, 6)
    current_setsu = date(birth_date.year, month, sekki_day)

    if forward:
        # 次の節入りまで
        next_month = month + 1 if month < 12 else 1
        next_year = birth_date.year if month < 12 else birth_date.year + 1
        next_sekki_day = SEKKI_DAYS.get(next_month, 6)
        next_setsu = date(next_year, next_month, next_sekki_day)
        if birth_date < current_setsu:
            # 節入り前に生まれた場合、次の節入り=current_setsu
            days_to_setsu = (current_setsu - birth_date).days
        else:
            days_to_setsu = (next_setsu - birth_date).days
    else:
        # 前の節入りまで
        if birth_date >= current_setsu:
            prev_setsu = current_setsu
        else:
            prev_month = month - 1 if month > 1 else 12
            prev_year = birth_date.year if month > 1 else birth_date.year - 1
            prev_sekki_day = SEKKI_DAYS.get(prev_month, 6)
            prev_setsu = date(prev_year, prev_month, prev_sekki_day)
        days_to_setsu = (birth_date - prev_setsu).days

    mansai = days_to_setsu // 3
    kazoe = mansai + 1  # 数え年：満年齢+1（簡易）

    # 大運8柱（月柱を起点に進行/逆行）
    gan_idx = JIKKAN.index(tsuki_kanshi[0])
    shi_idx = JUNISHI.index(tsuki_kanshi[1])
    taiun_list: List[TaiunEntry] = []
    for i in range(1, 9):
        if forward:
            g = JIKKAN[(gan_idx + i) % 10]
            z = JUNISHI[(shi_idx + i) % 12]
        else:
            g = JIKKAN[(gan_idx - i) % 10]
            z = JUNISHI[(shi_idx - i) % 12]
        tsu = _calc_tsuhensei(nichikan, g)
        entry = TaiunEntry(
            index=i,
            start_age_mansai=mansai + (i - 1) * 10,
            start_age_kazoe=kazoe + (i - 1) * 10,
            kanshi=g + z,
            kan=g,
            shi=z,
            tsuhensei=tsu,
            juda=TSUHENSEI_TO_JUDA.get(tsu, ""),
            juni_unsei=_calc_juni_unsei(nichikan, z),
        )
        taiun_list.append(entry)

    direction = "順行" if forward else "逆行"
    return days_to_setsu, mansai, kazoe, direction, taiun_list


def _calc_gogyo_balance_shichu(
    pillars_kan: List[str], pillars_shi: List[str]
) -> Dict[str, int]:
    """四柱（天干・地支・蔵干本気）を使って五行バランスを%で算出"""
    counts = {"木": 0, "火": 0, "土": 0, "金": 0, "水": 0}
    # 天干
    for k in pillars_kan:
        if k:
            counts[JIKKAN_GOGYO[k]] += 2  # 天干は重み2
    # 地支の本気
    for s in pillars_shi:
        if s:
            honki = JUNISHI_ZOKAN[s]
            counts[JIKKAN_GOGYO[honki]] += 3  # 地支本気は重み3
    total = sum(counts.values()) or 1
    return {g: round(v * 100 / total) for g, v in counts.items()}


def _build_pillar(
    kanshi: str,
    zoukan: str,
    zoukan_type: str,
    nichikan: str,
    is_hi_pillar: bool = False,
) -> Pillar:
    """Pillar dataclass を構築"""
    kan = kanshi[0]
    shi = kanshi[1]
    if is_hi_pillar:
        tsu = "—"
        juda = "—"
    else:
        tsu = _calc_tsuhensei(nichikan, kan)
        juda = TSUHENSEI_TO_JUDA.get(tsu, "")
    zoukan_tsu = _calc_tsuhensei(nichikan, zoukan)
    return Pillar(
        kanshi=kanshi, kan=kan, shi=shi,
        zoukan=zoukan, zoukan_type=zoukan_type,
        tsuhensei=tsu, juda=juda,
        zoukan_tsuhensei=zoukan_tsu,
        juni_unsei=_calc_juni_unsei(nichikan, shi),
    )


# =============================================================================
# トップレベル API
# =============================================================================

def calculate_shichusuimei(person: PersonInput) -> ShichusuimeiResult:
    """四柱推命の完全命式を計算する"""
    d = person.birth_date

    # 四柱
    nen_kanshi = _calc_nen_kanshi(d)
    nen_kan, nen_shi = nen_kanshi[0], nen_kanshi[1]

    tsuki_kanshi = _calc_tsuki_kanshi(d, nen_kan)
    tsuki_kan, tsuki_shi = tsuki_kanshi[0], tsuki_kanshi[1]

    hi_kanshi = _calc_hi_kanshi(d)
    nichikan = hi_kanshi[0]
    hi_shi = hi_kanshi[1]

    # 時柱（出生時刻があれば）
    has_toki = bool(person.birth_time)
    toki_kanshi = None
    toki_kan = None
    toki_shi = None
    if has_toki:
        toki_kanshi = _calc_toki_kanshi(person.birth_time, nichikan)
        toki_kan, toki_shi = toki_kanshi[0], toki_kanshi[1]

    # 蔵干
    # 年・日・時柱は本気、月柱は月律分野蔵干（節入り日数で選出）
    nen_zoukan = JUNISHI_ZOKAN[nen_shi]
    nen_zoukan_type = "本気"

    days_from_setsu = _days_from_setsuiri(d)
    tsuki_zoukan, tsuki_zoukan_type = _calc_tsuki_zoukan(tsuki_shi, days_from_setsu)

    hi_zoukan = JUNISHI_ZOKAN[hi_shi]
    hi_zoukan_type = "本気"

    toki_zoukan = None
    toki_zoukan_type = None
    if toki_shi:
        toki_zoukan = JUNISHI_ZOKAN[toki_shi]
        toki_zoukan_type = "本気"

    # Pillar 構築
    nen_pillar = _build_pillar(nen_kanshi, nen_zoukan, nen_zoukan_type, nichikan)
    tsuki_pillar = _build_pillar(tsuki_kanshi, tsuki_zoukan, tsuki_zoukan_type, nichikan)
    hi_pillar = _build_pillar(hi_kanshi, hi_zoukan, hi_zoukan_type, nichikan, is_hi_pillar=True)
    toki_pillar = None
    if toki_kanshi:
        toki_pillar = _build_pillar(toki_kanshi, toki_zoukan, toki_zoukan_type, nichikan)

    # 空亡（＝算命学の天中殺と同一ロジック）
    tenchusatsu_name = _calc_tenchusatsu(hi_kanshi)  # "申酉天中殺"
    kuubou_branches = TENCHUSATSU_JUNISHI[tenchusatsu_name]
    kuubou_name = "".join(kuubou_branches) + "空亡"

    # 神殺
    shinsatsu_list = _calc_shinsatsu(
        nichikan, nen_shi, tsuki_shi, hi_shi, toki_shi,
        nen_kan, tsuki_kan, toki_kan,
    )

    # 大運
    days_to_setsu, mansai, kazoe, direction, taiun_list = _calc_taiun(
        d, person.gender, nen_kan, tsuki_kanshi, nichikan,
    )

    # 五行バランス
    pillars_kan = [nen_kan, tsuki_kan, nichikan] + ([toki_kan] if toki_kan else [])
    pillars_shi = [nen_shi, tsuki_shi, hi_shi] + ([toki_shi] if toki_shi else [])
    gogyo_balance = _calc_gogyo_balance_shichu(pillars_kan, pillars_shi)

    return ShichusuimeiResult(
        nen_pillar=nen_pillar,
        tsuki_pillar=tsuki_pillar,
        hi_pillar=hi_pillar,
        toki_pillar=toki_pillar,
        has_toki=has_toki,
        nichikan=nichikan,
        nichikan_gogyo=JIKKAN_GOGYO[nichikan],
        nichikan_inyo=JIKKAN_INYO[nichikan],
        kuubou=kuubou_branches,
        kuubou_name=kuubou_name,
        shinsatsu=shinsatsu_list,
        taiun_ritsuun_days=days_to_setsu,
        taiun_ritsuun_age_mansai=mansai,
        taiun_ritsuun_age_kazoe=kazoe,
        taiun_direction=direction,
        taiun_list=taiun_list,
        gogyo_balance=gogyo_balance,
    )
