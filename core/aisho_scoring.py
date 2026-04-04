"""
相性スコアリングエンジン（core/aisho_scoring.py）
2人の命式データと関係性カテゴリに基づき、0〜100点で相性を算出する。
点数は忖度しない。低い＝悪いではなく「違いが大きい」。
"""
from typing import Dict, Tuple

# ── 関係性カテゴリ定義 ──
RELATIONSHIP_CATEGORIES = {
    'love': {
        'label': '恋愛・パートナー',
        'icon': '💕',
        'description': '恋愛相性・出会いのタイミング・相性のツボ',
    },
    'marriage': {
        'label': '夫婦・結婚',
        'icon': '💒',
        'description': '長期的な相性・役割分担・すれ違いの原因と対策',
    },
    'boss_subordinate': {
        'label': '上司と部下',
        'icon': '🏢',
        'description': '指導スタイル・期待値の調整・活かし方',
    },
    'business': {
        'label': '仕事のパートナー',
        'icon': '🤝',
        'description': 'ビジネスの相性・協業の強み・注意点',
    },
    'parent_child': {
        'label': '親子・家族',
        'icon': '👨‍👧',
        'description': '理解し合うためのヒント・教育方針・距離感',
    },
    'friend': {
        'label': '友人・仲間',
        'icon': '🍻',
        'description': '気が合う理由・長く続くコツ・一緒にやると良いこと',
    },
}

# ── 干合テーブル ──
KANGO_PAIRS = {
    frozenset(("甲", "己")), frozenset(("乙", "庚")),
    frozenset(("丙", "辛")), frozenset(("丁", "壬")),
    frozenset(("戊", "癸")),
}

# ── 五行の相生・相剋 ──
GOGYO_MAP = {
    "甲": "木", "乙": "木", "丙": "火", "丁": "火", "戊": "土",
    "己": "土", "庚": "金", "辛": "金", "壬": "水", "癸": "水",
}

SOJO = {("木", "火"), ("火", "土"), ("土", "金"), ("金", "水"), ("水", "木")}
SOKOKU = {("木", "土"), ("土", "水"), ("水", "火"), ("火", "金"), ("金", "木")}

# ── 星座エレメント ──
SIGN_ELEMENT = {
    "牡羊座": "火", "牡牛座": "土", "双子座": "風", "蟹座": "水",
    "獅子座": "火", "乙女座": "土", "天秤座": "風", "蠍座": "水",
    "射手座": "火", "山羊座": "土", "水瓶座": "風", "魚座": "水",
}

# 星座エレメント相性（火×風、土×水が相性良い）
ELEMENT_GOOD = {frozenset(("火", "風")), frozenset(("土", "水"))}
ELEMENT_SAME = True  # 同エレメントは良い
ELEMENT_BAD = {frozenset(("火", "水")), frozenset(("土", "風"))}

# ── 天中殺グループ ──
TENCHUSATSU_JUNISHI = {
    "戌亥天中殺": ["戌", "亥"],
    "申酉天中殺": ["申", "酉"],
    "午未天中殺": ["午", "未"],
    "辰巳天中殺": ["辰", "巳"],
    "寅卯天中殺": ["寅", "卯"],
    "子丑天中殺": ["子", "丑"],
}

# ── 五本能の相生マップ ──
HONNOU_SOJO = {
    ("守備", "表現"), ("表現", "魅力"), ("魅力", "攻撃"),
    ("攻撃", "学習"), ("学習", "守備"),
}

# ── 各項目の関係性別ウェイト ──
SCORING_WEIGHTS = {
    'kan_relationship': {
        'love': 3.0, 'marriage': 2.0, 'boss_subordinate': 1.0,
        'business': 1.5, 'parent_child': 1.5, 'friend': 1.0,
    },
    'energy_compatibility': {
        'love': 1.5, 'marriage': 2.5, 'boss_subordinate': 3.0,
        'business': 2.0, 'parent_child': 3.0, 'friend': 1.5,
    },
    'honnou_complementary': {
        'love': 1.0, 'marriage': 2.0, 'boss_subordinate': 2.5,
        'business': 3.0, 'parent_child': 2.0, 'friend': 2.0,
    },
    'tenchusatsu_compatibility': {
        'love': 2.5, 'marriage': 2.5, 'boss_subordinate': 0.5,
        'business': 1.5, 'parent_child': 1.0, 'friend': 0.5,
    },
    'star_sign_compatibility': {
        'love': 2.0, 'marriage': 1.5, 'boss_subordinate': 0.5,
        'business': 0.5, 'parent_child': 1.0, 'friend': 2.0,
    },
}

# ── スコア解釈 ──
SCORE_INTERPRETATION = [
    (90, 100, '運命型', '出会うべくして出会った相性。自然にうまくいく。',
     'この相性に甘えず、感謝を忘れないこと。'),
    (70, 89, '共鳴型', '響き合える部分が多い。一緒にいて心地よい。',
     '共通点を楽しみつつ、違いも探求すると深まる。'),
    (40, 69, '補完型', '違いがあるからこそ補い合える。お互いにないものを持っている。',
     '違いを「欠点」ではなく「自分にない才能」として見ること。'),
    (10, 39, '成長型', '大きな違いがある。だからこそ最も成長できる関係。',
     '理解に時間がかかる。でもこの人から学べることは計り知れない。'),
    (0, 9, '異次元型', '全く異なる世界観を持つ2人。理解するには努力が必要。',
     'この人は自分の「鏡」。理解できない部分にこそ、自分の盲点がある。'),
]

# ── エネルギー差アドバイス ──
ENERGY_DIFF_ADVICE = {
    (0, 30): {
        'label': 'ほぼ同レベル',
        'general': 'ペースが合う。自然体でいられる関係。',
        'boss_subordinate': '対等に近い関係が築ける。意見交換が活発になる。',
        'marriage': '家庭内のバランスが良い。主導権争いが少ない。',
        'parent_child': '子どもの気持ちを理解しやすい。',
    },
    (31, 60): {
        'label': '適度な差',
        'general': 'お互いを補い合える良い差。',
        'boss_subordinate': '自然なリーダーシップが成立する。',
        'marriage': '役割分担がしやすい。高い方がリードする形が安定。',
        'parent_child': '親の導きが自然に受け入れられる距離感。',
    },
    (61, 100): {
        'label': '注意が必要な差',
        'general': '意識的にペースを合わせる努力が必要。',
        'boss_subordinate': '上司は期待値を下げること。部下は自分のペースを守ること。',
        'marriage': '高い方が趣味・仕事で外でエネルギーを消費してから家に帰ると良い。',
        'parent_child': '子どもに親のペースを押し付けない。習い事の数を減らす勇気。',
    },
    (101, 999): {
        'label': '大きな差',
        'general': '互いのエネルギーレベルを知ることが第一歩。',
        'boss_subordinate': '上司は「自分の基準で測らない」を鉄則にする。',
        'marriage': '高い方がエネルギーを外で十分に消費する仕組みが必須。',
        'parent_child': '子どものペースを完全に尊重する。「がんばれ」より「そのままでいい」。',
    },
}

# ── 五本能相性テキスト ──
SAME_HONNOU_AISHO = {
    '守備': '安定感抜群。お互いの領域を侵さない穏やかな関係。ただし変化に弱い。',
    '表現': '刺激し合えるクリエイティブな関係。ただし主張がぶつかりやすい。',
    '魅力': '両方がリーダータイプで主導権争いになりやすい。役割分担が鍵。',
    '攻撃': '超アクティブなコンビ。一緒にいると加速する。ただしブレーキ役がいない。',
    '学習': '知的な対話が永遠に続く関係。ただし行動に移すのが遅い。',
}


# ============================================================
# スコア計算関数
# ============================================================

def _score_kan_relationship(kan1: str, kan2: str) -> int:
    """日干同士の五行関係をスコア化（0-10）"""
    if frozenset((kan1, kan2)) in KANGO_PAIRS:
        return 10  # 干合
    g1 = GOGYO_MAP.get(kan1, "")
    g2 = GOGYO_MAP.get(kan2, "")
    if g1 == g2:
        return 6  # 比和
    if (g1, g2) in SOJO:
        return 8  # 相生（生じる側）
    if (g2, g1) in SOJO:
        return 7  # 相生（生じられる側）
    if (g1, g2) in SOKOKU:
        return 4  # 相剋（剋す側）
    if (g2, g1) in SOKOKU:
        return 3  # 相剋（剋される側）
    return 5  # その他

def _score_energy_compatibility(energy1: int, energy2: int) -> int:
    """エネルギー差をスコア化（0-10）"""
    diff = abs(energy1 - energy2)
    if diff <= 30:
        return 10
    elif diff <= 60:
        return 8
    elif diff <= 100:
        return 5
    elif diff <= 150:
        return 3
    else:
        return 1

def _score_honnou_complementary(top1_a: str, top1_b: str) -> int:
    """第1本能同士の相性をスコア化（0-10）"""
    if top1_a == top1_b:
        return 7  # 同じ本能（共感型）
    if (top1_a, top1_b) in HONNOU_SOJO or (top1_b, top1_a) in HONNOU_SOJO:
        return 10  # 相生
    # 相剋チェック（五行変換は不要、本能名で直接チェック）
    return 5

def _score_tenchusatsu(tc1: str, tc2: str, year1: int, year2: int) -> int:
    """天中殺の相性をスコア化（0-10）"""
    JUNISHI = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]

    # 天中殺縁チェック（相手の生年の支が自分の天中殺支に含まれるか）
    def _year_shi(y: int) -> str:
        return JUNISHI[(y - 4) % 12]

    y1_shi = _year_shi(year1)
    y2_shi = _year_shi(year2)

    tc1_shis = TENCHUSATSU_JUNISHI.get(tc1, [])
    tc2_shis = TENCHUSATSU_JUNISHI.get(tc2, [])

    # 天中殺縁: 相手の年支が自分の天中殺支
    is_tc_en = (y2_shi in tc1_shis) or (y1_shi in tc2_shis)

    if is_tc_en:
        return 3  # 天中殺縁
    if tc1 == tc2:
        return 7  # 同じ天中殺グループ（同志型）
    return 8  # 異なるグループ（無関係）

def _score_star_sign(sign1: str, sign2: str) -> int:
    """太陽星座の相性をスコア化（0-10）"""
    e1 = SIGN_ELEMENT.get(sign1, "")
    e2 = SIGN_ELEMENT.get(sign2, "")
    if not e1 or not e2:
        return 5
    if e1 == e2:
        return 9  # 同エレメント
    if frozenset((e1, e2)) in ELEMENT_GOOD:
        return 8  # 相性良い
    if frozenset((e1, e2)) in ELEMENT_BAD:
        return 3  # 相性要注意
    return 5  # 中立


def calc_aisho_score(bundle1, bundle2, relationship: str) -> dict:
    """
    2人の相性スコアを計算する。

    Args:
        bundle1, bundle2: DivinationBundle
        relationship: 'love'|'marriage'|'boss_subordinate'|'business'|'parent_child'|'friend'

    Returns:
        {
            'score': int (0-100),
            'label': str,
            'meaning': str,
            'advice': str,
            'detail': {item_key: raw_score},
            'energy_diff': int,
            'energy_advice': dict,
            'honnou_text': str,
        }
    """
    s1 = bundle1.sanmei
    s2 = bundle2.sanmei

    # 各項目を採点
    raw_scores = {}

    # 1. 日干関係
    raw_scores['kan_relationship'] = _score_kan_relationship(s1.nichikan, s2.nichikan)

    # 2. エネルギー差
    e1 = s1.bansho_energy.total_energy if s1.bansho_energy else 200
    e2 = s2.bansho_energy.total_energy if s2.bansho_energy else 200
    raw_scores['energy_compatibility'] = _score_energy_compatibility(e1, e2)

    # 3. 五本能の補完
    h1 = s1.bansho_energy.top_honnou if s1.bansho_energy else ""
    h2 = s2.bansho_energy.top_honnou if s2.bansho_energy else ""
    raw_scores['honnou_complementary'] = _score_honnou_complementary(h1, h2)

    # 4. 天中殺
    y1 = bundle1.person.birth_date.year
    y2 = bundle2.person.birth_date.year
    raw_scores['tenchusatsu_compatibility'] = _score_tenchusatsu(
        s1.tenchusatsu, s2.tenchusatsu, y1, y2
    )

    # 5. 太陽星座
    sign1 = bundle1.western.sun_sign if bundle1.western else ""
    sign2 = bundle2.western.sun_sign if bundle2.western else ""
    raw_scores['star_sign_compatibility'] = _score_star_sign(sign1, sign2)

    # 加重平均
    weighted_sum = 0.0
    weight_total = 0.0
    for item_key, raw in raw_scores.items():
        w = SCORING_WEIGHTS.get(item_key, {}).get(relationship, 1.0)
        weighted_sum += raw * w
        weight_total += w

    raw_avg = weighted_sum / weight_total if weight_total > 0 else 5
    final_score = int(raw_avg * 10)
    final_score = min(100, max(0, final_score))

    # スコア解釈
    label, meaning, advice = '補完型', '', ''
    for lo, hi, lbl, mng, adv in SCORE_INTERPRETATION:
        if lo <= final_score <= hi:
            label, meaning, advice = lbl, mng, adv
            break

    # エネルギー差アドバイス
    energy_diff = abs(e1 - e2)
    energy_adv = {}
    for (lo, hi), adv_dict in ENERGY_DIFF_ADVICE.items():
        if lo <= energy_diff <= hi:
            energy_adv = adv_dict
            break

    # 五本能テキスト
    honnou_text = ""
    if h1 and h2:
        if h1 == h2:
            honnou_text = SAME_HONNOU_AISHO.get(h1, "")
        elif (h1, h2) in HONNOU_SOJO:
            honnou_text = f"{h1}→{h2}（相生）: {h1}が{h2}を助ける関係。最高のサポート。"
        elif (h2, h1) in HONNOU_SOJO:
            honnou_text = f"{h2}→{h1}（相生）: {h2}が{h1}を助ける関係。最高のサポート。"
        else:
            honnou_text = f"{h1}×{h2}: 異なるタイプ同士。違いを活かせば補完し合える。"

    return {
        'score': final_score,
        'label': label,
        'meaning': meaning,
        'advice': advice,
        'detail': raw_scores,
        'energy1': e1,
        'energy2': e2,
        'energy_diff': energy_diff,
        'energy_advice': energy_adv,
        'honnou1': h1,
        'honnou2': h2,
        'honnou_text': honnou_text,
    }


def get_energy_diff_advice(diff: int, relationship: str) -> str:
    """エネルギー差に応じた関係性別アドバイスを返す"""
    for (lo, hi), adv_dict in ENERGY_DIFF_ADVICE.items():
        if lo <= diff <= hi:
            return adv_dict.get(relationship, adv_dict.get('general', ''))
    return ''
