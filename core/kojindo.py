"""
古神道占い（最上位レイヤー）エンジン
core/kojindo.py

7流派の鑑定結果を「古事記の神の物語」として再構成する最上位レイヤー。
- 6龍タイプ（=算命学6天中殺グループに対応）
- 守護神（中心星から導出）
- メタ軸（天つ神/国つ神）
- 人生フェーズ（年齢×神話エピソード）

くろたん『こどたんへ_古神道占い_実装指示書_Step3.md』(2026-05-06) 準拠。
方針: まず動かす。使いながら育てる。完成しない。
"""
from __future__ import annotations
from datetime import date
from typing import Optional

from .models import KojinDoResult, SanmeiResult, PersonInput
from .sanmei import _calc_tenchusatsu


# ============================================================
# 6龍判定テーブル（天中殺グループ → 6龍）
# 北極流の6龍法 = 算命学の6天中殺グループに完全1対1対応
# ============================================================
ROKURYU_TABLE = {
    "戌亥": {"name": "月龍", "element": "月", "keyword": "静かな直感"},
    "子丑": {"name": "空龍", "element": "空", "keyword": "独創の信念"},
    "寅卯": {"name": "風龍", "element": "風", "keyword": "自由な発想"},
    "辰巳": {"name": "火龍", "element": "火", "keyword": "情熱の行動"},
    "午未": {"name": "水龍", "element": "水", "keyword": "柔軟な知性"},
    "申酉": {"name": "地龍", "element": "地", "keyword": "堅実な基盤"},
}


# ============================================================
# 守護神判定テーブル（中心星 → 古事記の神）
# 占いモンスター独自構築（北極流の口伝に閉じる領域を独自タクソノミーで再構築）
# ============================================================
GUARDIAN_GOD_TABLE = {
    "貫索星": {
        "god": "建御名方神",
        "reading": "たけみなかたのかみ",
        "type": "国つ神",
        "shrine": "諏訪大社",
        "story_type": "不動の自我",
        "headline": "八度頼まれても応じず、九度目の朝に旗を立てる",
        "template": "諏訪の湖は凍り、足跡は一つ。動かぬことが、あなたの最大の戦い",
    },
    "石門星": {
        "god": "大国主命",
        "reading": "おおくにぬしのみこと",
        "type": "国つ神",
        "shrine": "出雲大社",
        "story_type": "連合の柱",
        "headline": "傷ついた兎に布を巻く手、十七人の弟を率いる肩",
        "template": "守るのは国ではなく、輪。あなたの真ん中に、人が集まる",
    },
    "鳳閣星": {
        "god": "天宇受賣命",
        "reading": "あめのうずめのみこと",
        "type": "天つ神",
        "shrine": "椿大神社",
        "story_type": "笑いと自然体",
        "headline": "桶を踏む音が三回、笑い声が八百万",
        "template": "深刻を笑いに変えるたび、世界が一センチ明るくなる",
    },
    "調舒星": {
        "god": "須佐之男命",
        "reading": "すさのおのみこと",
        "type": "天つ神→国つ神",
        "shrine": "八坂神社・氷川神社",
        "story_type": "葛藤の詩人",
        "headline": "机を叩いた拳、湖一つ分の涙、書き直した詩が三十一文字",
        "template": "壊した分だけ、誰も書けなかった一行が、あなたの指から出る",
    },
    "禄存星": {
        "god": "木花咲耶姫",
        "reading": "このはなさくやひめ",
        "type": "国つ神",
        "shrine": "富士山本宮浅間大社",
        "story_type": "華やかな儚さ",
        "headline": "火の中で産み落とす。疑われた夜に証明した命が三つ",
        "template": "咲いた花は短い。だからその一日が、見た者の一生に残る",
    },
    "司禄星": {
        "god": "玉依姫",
        "reading": "たまよりひめ",
        "type": "国つ神",
        "shrine": "賀茂御祖神社（下鴨神社）",
        "story_type": "静かな継承",
        "headline": "米を量る三合、子の額に当てる手のひら",
        "template": "派手さはない。けれど、あなたが居なければ次の朝は来ない",
    },
    "車騎星": {
        "god": "建御雷神",
        "reading": "たけみかづちのかみ",
        "type": "天つ神",
        "shrine": "鹿島神宮",
        "story_type": "単騎の剣",
        "headline": "波打ち際に剣を逆さに刺し、切先の上に座る",
        "template": "考える前に手が出て、振り返る前に勝っている。傷は勲章より早く来る",
    },
    "牽牛星": {
        "god": "瓊瓊杵尊",
        "reading": "ににぎのみこと",
        "type": "天つ神",
        "shrine": "霧島神宮・高千穂神社",
        "story_type": "天孫の長征",
        "headline": "三つの神器を抱えて雲を降りた者",
        "template": "背に日を負わぬ進路を選ぶ。名は遅れて届く。だが必ず届く",
    },
    "龍高星": {
        "god": "猿田彦神",
        "reading": "さるたひこのかみ",
        "type": "国つ神",
        "shrine": "椿大神社・猿田彦神社",
        "story_type": "先導者の道",
        "headline": "鼻が七咫。目が八咫鏡のように赤い",
        "template": "知らない道だけが道。先を歩く者の背中には、日焼けの跡しか残らない",
    },
    "玉堂星": {
        "god": "思金神",
        "reading": "おもいかねのかみ",
        "type": "天つ神",
        "shrine": "戸隠神社・秩父神社",
        "story_type": "参謀の灯",
        "headline": "岩戸の前で議事録を読み返す",
        "template": "誰かが動く前に、あなたが地図を描いている",
    },
}


# ============================================================
# 人生フェーズテーブル（年齢 × 神話エピソード）
# E リサーチ集計の高一致結果を反映
# ============================================================
LIFE_PHASE_TABLE = [
    {"age_range": (0, 12),  "phase": "母の庇護",   "episode": "神産み",          "line": "庭に守られた根を持つ時期"},
    {"age_range": (12, 24), "phase": "反抗と試練", "episode": "須佐之男の追放",  "line": "火傷から立ち上がる季節"},
    {"age_range": (24, 36), "phase": "修行期",     "episode": "根の国訪問",      "line": "眠れぬ部屋を女神が通す"},
    {"age_range": (36, 48), "phase": "国造り",     "episode": "少彦名との協働",  "line": "半身を得て土地を耕す"},
    {"age_range": (48, 56), "phase": "収穫と完成", "episode": "複合フェーズ",    "line": "建てた城の窓から、次の主が見える"},
    {"age_range": (56, 66), "phase": "国譲り",     "episode": "国譲り",          "line": "明け渡してこそ残る"},
    {"age_range": (66, 200),"phase": "神上がり",   "episode": "幽冥主宰",        "line": "見えぬところの王になる"},
]


# ============================================================
# メタ軸の自動判定（守護神の type フィールドから決定）
# ============================================================
def _resolve_meta_axis(god_type: str) -> str:
    """守護神の type → "天つ神" / "国つ神" / "両方" """
    if god_type == "天つ神":
        return "天つ神"
    if god_type == "国つ神":
        return "国つ神"
    if god_type == "天つ神→国つ神":
        return "両方"  # 須佐之男のように両方を経た神
    return "国つ神"  # デフォルト（地に降りた人）


# ============================================================
# 年齢計算
# ============================================================
def _calc_age(birth_date: date, today: Optional[date] = None) -> int:
    """満年齢（誕生日前後考慮）"""
    today = today or date.today()
    age = today.year - birth_date.year
    if (today.month, today.day) < (birth_date.month, birth_date.day):
        age -= 1
    return max(0, age)


def _resolve_phase(age: int):
    """満年齢 → 現在のライフフェーズ"""
    for entry in LIFE_PHASE_TABLE:
        lo, hi = entry["age_range"]
        if lo <= age < hi:
            return entry
    return LIFE_PHASE_TABLE[-1]


def _resolve_next_phase(age: int):
    """満年齢 → 次のライフフェーズ"""
    current = _resolve_phase(age)
    cur_lo, _ = current["age_range"]
    for entry in LIFE_PHASE_TABLE:
        lo, _ = entry["age_range"]
        if lo > cur_lo:
            return entry
    return current  # 最終フェーズの場合は同じ


# ============================================================
# 天中殺グループから6龍を導出
# ============================================================
def _tenchusatsu_to_rokuryu_key(tenchusatsu_name: str) -> str:
    """「申酉天中殺」 → "申酉" """
    if tenchusatsu_name and tenchusatsu_name.endswith("天中殺"):
        return tenchusatsu_name.replace("天中殺", "")
    return tenchusatsu_name or ""


# ============================================================
# メイン関数: calculate_kojindo
# ============================================================
def calculate_kojindo(sanmei: SanmeiResult, person: PersonInput) -> KojinDoResult:
    """既存の算命学計算結果から古神道占いの三層を導出

    Args:
        sanmei: SanmeiResult（中央星 + 天中殺）
        person: PersonInput（生年月日 = 年齢計算用）
    """
    # === 6龍タイプ ===
    rokuryu_key = _tenchusatsu_to_rokuryu_key(sanmei.tenchusatsu)
    rokuryu = ROKURYU_TABLE.get(rokuryu_key, {
        "name": "地龍", "element": "地", "keyword": "堅実な基盤"
    })

    # === 守護神 ===
    chuo_sei = sanmei.chuo_sei or "牽牛星"
    god = GUARDIAN_GOD_TABLE.get(chuo_sei, GUARDIAN_GOD_TABLE["牽牛星"])

    # === メタ軸 ===
    meta_axis = _resolve_meta_axis(god["type"])

    # === 人生フェーズ ===
    age = _calc_age(person.birth_date)
    phase = _resolve_phase(age)
    next_phase = _resolve_next_phase(age)

    # === 144タイプID ===
    type_id = f"{rokuryu['name']}_{god['god']}_{meta_axis}"

    return KojinDoResult(
        rokuryu_name=rokuryu["name"],
        rokuryu_element=rokuryu["element"],
        rokuryu_keyword=rokuryu["keyword"],
        rokuryu_tenchusatsu=rokuryu_key,
        god_name=god["god"],
        god_reading=god["reading"],
        god_type=god["type"],
        god_shrine=god["shrine"],
        god_story_type=god["story_type"],
        god_headline=god["headline"],
        god_template=god["template"],
        meta_axis=meta_axis,
        current_age=age,
        phase_name=phase["phase"],
        phase_episode=phase["episode"],
        phase_line=phase["line"],
        next_phase_name=next_phase["phase"],
        next_phase_episode=next_phase["episode"],
        type_id=type_id,
    )
