"""
占いモンスターマシーン Phase 1a
共通データモデル（dataclass）
"""
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Tuple
from datetime import date


@dataclass
class PersonInput:
    """入力データ（将来の2人入力に対応できる構造）"""
    birth_date: date                        # 必須
    birth_time: Optional[str] = None        # "HH:MM" 形式、任意
    birth_place: Optional[str] = None       # 都市名、任意
    blood_type: Optional[str] = None        # "A" / "B" / "O" / "AB"、任意
    name: Optional[str] = None              # 表示用、任意
    gender: Optional[str] = None            # "男性" / "女性" / "その他"、任意


@dataclass
class SanmeiResult:
    """算命学の計算結果"""
    nen_kanshi: str                         # 年柱干支（例: "丁巳"）
    tsuki_kanshi: str                       # 月柱干支（例: "乙巳"）
    hi_kanshi: str                          # 日柱干支（例: "辛巳"）
    nichikan: str                           # 日干（例: "辛"）
    nichikan_gogyo: str                     # 日干の五行（例: "金"）
    nichikan_inyo: str                      # 日干の陰陽（例: "陰"）
    chuo_sei: str                           # 中央星（例: "牽牛星"）
    chuo_honno: str                         # 中央星の本能（例: "攻撃本能"）
    tenchusatsu: str                        # 天中殺グループ（例: "申酉天中殺"）
    tenchusatsu_years: list                 # 直近の天中殺年リスト
    keywords: list                          # 性格キーワード3〜5個
    charm_words: list = field(default_factory=list)  # 飲み屋で使える褒め言葉
    # Phase 1a拡張: 人体図全5星
    kita_sei: str = ""                      # 北の星（頭）
    kita_honno: str = ""
    minami_sei: str = ""                    # 南の星（腹）
    minami_honno: str = ""
    higashi_sei: str = ""                   # 東の星（右手）
    higashi_honno: str = ""
    nishi_sei: str = ""                     # 西の星（左手）
    nishi_honno: str = ""
    # 五行バランス
    gogyo_balance: Dict[str, int] = field(default_factory=lambda: {"木": 0, "火": 0, "土": 0, "金": 0, "水": 0})
    # 特殊格局
    kakkyoku: str = ""                      # 特殊格局名（例: "三巳格"）
    # 柱の天干・地支（個別アクセス用）
    nen_kan: str = ""
    nen_shi: str = ""
    tsuki_kan: str = ""
    tsuki_shi: str = ""
    hi_kan: str = ""
    hi_shi: str = ""
    # 万象学エネルギー
    bansho_energy: Optional['BanshoEnergyResult'] = None


@dataclass
class BanshoEnergyResult:
    """万象学 宿命エネルギー指数"""
    total_energy: int                              # エネルギー指数（総合計）
    energy_type: str                               # 集中特化型/安定キャリア型/etc
    energy_description: str                        # タイプの説明
    energy_advice: str                             # アドバイス
    gogyo_scores: Dict[str, int] = field(default_factory=dict)   # {'木':15, '火':20, ...}
    honnou_ranking: List[Tuple[str, int]] = field(default_factory=list)  # [('攻撃',100), ...]
    top_honnou: str = ""                           # 第1本能
    top_score: int = 0
    second_honnou: str = ""                        # 第2本能
    second_score: int = 0
    zero_honnou: List[str] = field(default_factory=list)  # 0点の本能
    combo_talent: str = ""                         # 第1×第2本能コンボ才能
    combo_description: str = ""                    # コンボ説明
    one_liner: str = ""                            # 一言アドバイス
    drink_talk: str = ""                           # 飲み屋トーク


@dataclass
class PlanetPosition:
    """天体の位置情報"""
    name: str                               # 天体名（例: "太陽"）
    sign: str                               # 星座（例: "双子座"）
    sign_symbol: str                        # 星座記号
    degree: float                           # 黄経度数
    house: Optional[int] = None             # ハウス番号（1-12, 出生時刻ありの場合）
    is_retrograde: bool = False             # 逆行中か


@dataclass
class AspectInfo:
    """アスペクト情報"""
    planet1: str                            # 天体1（例: "太陽"）
    planet2: str                            # 天体2（例: "月"）
    aspect_type: str                        # アスペクト種類（例: "合"）
    orb: float                              # オーブ（度数差）
    description: str = ""                   # 説明


@dataclass
class WesternResult:
    """西洋占星術の計算結果"""
    sun_sign: str                           # 太陽星座（例: "双子座"）
    sun_sign_symbol: str                    # 星座記号（例: "♊"）
    sun_element: str                        # エレメント（例: "風"）
    sun_quality: str                        # クオリティ（例: "柔軟宮"）
    moon_sign: Optional[str] = None         # 月星座（出生時刻ありの場合）
    asc_sign: Optional[str] = None          # ASC（出生時刻ありの場合）
    mc_sign: Optional[str] = None           # MC（出生時刻ありの場合）
    keywords: list = field(default_factory=list)
    # Phase 1a拡張: 全天体
    planets: List[PlanetPosition] = field(default_factory=list)
    aspects: List[AspectInfo] = field(default_factory=list)
    has_full_chart: bool = False             # 出生時刻ありでフルチャートか


@dataclass
class KyuseiResult:
    """九星気学の計算結果"""
    honmei_sei: str                         # 本命星（例: "六白金星"）
    getsu_mei_sei: str                      # 月命星（例: "七赤金星"）
    year_position: str                      # 今年の年盤位置（例: "東"）
    year_theme: str                         # 今年のテーマ（例: "発展・成長の年"）
    year_desc: str                          # 今年のテーマ詳細
    lucky_direction: str                    # 吉方位
    keywords: list = field(default_factory=list)
    # Phase 1a拡張
    bad_direction: str = ""                 # 凶方位


@dataclass
class NumerologyResult:
    """数秘術の計算結果"""
    life_path: int                          # ライフパスナンバー（1〜9, 11, 22, 33）
    personal_year: int                      # 個人年数（2026年）
    life_path_title: str                    # LP のタイトル（例: "達成者"）
    life_path_meaning: str                  # LP の意味
    personal_year_title: str                # 個人年のタイトル
    personal_year_meaning: str              # 個人年の意味
    keywords: list = field(default_factory=list)
    # Phase 1a拡張
    birthday_number: int = 0                # 誕生日数


@dataclass
class TarotResult:
    """タロット1枚ドローの結果"""
    card_name: str                          # カード名（例: "女帝"）
    card_name_en: str                       # 英語名（例: "The Empress"）
    card_number: int                        # カード番号
    is_reversed: bool                       # 逆位置かどうか
    arcana: str                             # "大アルカナ"
    keywords: list                          # キーワード3つ
    message: str                            # カードの基本メッセージ
    image_key: str                          # カード画像のキー（UI用）


@dataclass
class ZiweiPalace:
    """紫微斗数の一宮の情報"""
    branch: str                             # 地支（例: "寅"）
    branch_idx: int                         # 地支インデックス（0〜11）
    stem: str                               # 天干（例: "甲"）
    palace_name: str                        # 宮名（例: "命宮"）
    main_stars: List[str] = field(default_factory=list)    # 主星リスト
    aux_stars: List[str] = field(default_factory=list)     # 副星リスト
    sihua: List[str] = field(default_factory=list)         # 四化（例: ["化禄"]）


@dataclass
class ZiweiResult:
    """紫微斗数の計算結果"""
    lunar_year: int                         # 農暦年
    lunar_month: int                        # 農暦月
    lunar_day: int                          # 農暦日
    is_leap_month: bool                     # 閏月か
    birth_hour_name: str                    # 時辰名（例: "丑時"）
    birth_hour_idx: int                     # 時辰インデックス（0〜11）
    ming_gong_branch: str                   # 命宮の地支（例: "戌"）
    ming_gong_idx: int                      # 命宮インデックス
    shen_gong_branch: str                   # 身宮の地支
    shen_gong_idx: int                      # 身宮インデックス
    five_element_name: str                  # 五行局名（例: "火六局"）
    five_element_num: int                   # 五行局数（2〜6）
    year_stem: str                          # 年干（例: "丁"）
    year_stem_idx: int                      # 年干インデックス
    year_branch: str                        # 年支（例: "巳"）
    year_branch_idx: int                    # 年支インデックス
    palaces: List[ZiweiPalace] = field(default_factory=list)  # 12宮リスト
    sihua_assignments: Dict[str, str] = field(default_factory=dict)  # 星名→四化
    da_xian_ages: list = field(default_factory=list)   # 大限年齢 [(start, end), ...]
    da_xian_direction: str = ""             # 大限方向（"順行" or "逆行"）
    ziwei_palace_idx: int = 0              # 紫微星の宮
    tianfu_palace_idx: int = 0             # 天府星の宮
    keywords: list = field(default_factory=list)


@dataclass
class DivinationBundle:
    """全占術の統合結果パッケージ"""
    person: PersonInput
    sanmei: SanmeiResult
    western: WesternResult
    kyusei: KyuseiResult
    numerology: NumerologyResult
    tarot: TarotResult
    ziwei: Optional['ZiweiResult'] = None   # 紫微斗数（出生時刻必須のためOptional）
    has_birth_time: bool = False            # 出生時刻の有無
    has_blood_type: bool = False            # 血液型の有無
