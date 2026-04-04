"""
万象学 宿命エネルギー指数 計算エンジン（core/bansho_energy.py）
出典: 菊池桂子『万象学入門 あなたの人生はエネルギー指数で決まる』（宙出版・1997年）
"""
from typing import Dict, List, Tuple

# ── エネルギー指数表（書籍61ページ） ──
ENERGY_TABLE = {
    "甲": {"子":7, "丑":10,"寅":11,"卯":12,"辰":8, "巳":4, "午":2, "未":5, "申":1, "酉":3, "戌":6, "亥":9},
    "乙": {"子":4, "丑":8, "寅":12,"卯":11,"辰":10,"巳":7, "午":9, "未":6, "申":3, "酉":1, "戌":5, "亥":2},
    "丙": {"子":3, "丑":6, "寅":9, "卯":7, "辰":10,"巳":11,"午":12,"未":8, "申":4, "酉":2, "戌":5, "亥":1},
    "丁": {"子":1, "丑":5, "寅":2, "卯":4, "辰":8, "巳":12,"午":11,"未":10,"申":7, "酉":9, "戌":6, "亥":3},
    "戊": {"子":3, "丑":6, "寅":9, "卯":7, "辰":10,"巳":11,"午":12,"未":8, "申":4, "酉":2, "戌":5, "亥":1},
    "己": {"子":1, "丑":5, "寅":2, "卯":4, "辰":8, "巳":12,"午":11,"未":10,"申":7, "酉":9, "戌":6, "亥":3},
    "庚": {"子":2, "丑":5, "寅":1, "卯":3, "辰":6, "巳":9, "午":7, "未":10,"申":11,"酉":12,"戌":8, "亥":4},
    "辛": {"子":9, "丑":6, "寅":3, "卯":1, "辰":5, "巳":2, "午":4, "未":8, "申":12,"酉":11,"戌":10,"亥":7},
    "壬": {"子":12,"丑":8, "寅":4, "卯":2, "辰":5, "巳":1, "午":3, "未":6, "申":9, "酉":7, "戌":10,"亥":11},
    "癸": {"子":11,"丑":10,"寅":7, "卯":9, "辰":6, "巳":3, "午":1, "未":5, "申":2, "酉":4, "戌":8, "亥":12},
}

GOGYO_MAP = {
    "甲":"木","乙":"木","丙":"火","丁":"火","戊":"土",
    "己":"土","庚":"金","辛":"金","壬":"水","癸":"水",
}

YIN_YANG_MAP = {
    "甲":"陽","乙":"陰","丙":"陽","丁":"陰","戊":"陽",
    "己":"陰","庚":"陽","辛":"陰","壬":"陽","癸":"陰",
}

HONNOU_MAP = {"木":"守備","火":"表現","土":"魅力","金":"攻撃","水":"学習"}
GOGYO_TO_HONNOU = HONNOU_MAP  # alias

# ── 蔵干（支に含まれる全天干） ──
ZOUKAN = {
    "子": ["癸"],
    "丑": ["己","癸","辛"],
    "寅": ["甲","丙","戊"],
    "卯": ["乙"],
    "辰": ["戊","乙","癸"],
    "巳": ["丙","庚","戊"],
    "午": ["丁","己"],
    "未": ["己","丁","乙"],
    "申": ["庚","壬","戊"],
    "酉": ["辛"],
    "戌": ["戊","辛","丁"],
    "亥": ["壬","甲"],
}

# ── エネルギータイプ解釈テーブル ──
ENERGY_INTERPRETATION = [
    (0,   160, "集中特化型",   "少ないエネルギーを一点に集中させる専門家タイプ",
     "一つのことに絞って深掘りするのが正解。広く浅くは不向き。"),
    (161, 180, "自営業向き型", "組織より自分のペースで動く方が力を発揮する",
     "フリーランス・自営業・少人数の会社が最適。"),
    (181, 230, "組織適応型",   "バランスの良いエネルギー。組織内で着実に成長できる",
     "会社員・管理職コースが最も自然。"),
    (231, 300, "超活動型",     "仕事だけではエネルギーが余る。常に動き続けないと暴走する",
     "仕事＋趣味＋社会活動の三本柱。経営者・複数事業が自然な生き方。"),
    (301, 999, "規格外型",     "歴史的人物クラスのエネルギー。波乱万丈が「普通」",
     "国や業界を動かすレベルの活動量が必要。"),
]

# ── 五本能の解釈テーブル ──
HONNOU_DETAIL = {
    "守備": {
        "gogyo": "木", "keyword": "守る・支える・コツコツ",
        "personality": "平和主義者。コツコツ積み重ね。闘争を好まない。一つのことを粘り強くやり遂げる。",
        "career": "既存組織の維持・管理・公務員・事務職。縁の下の力持ち",
        "strong": "忍耐力・継続力・環境順応力",
        "weak": "自己主張が苦手・変化に弱い・目立たない",
        "yang": "大樹のようにどっしりとした存在。リーダー的な守備",
        "yin": "草や蔓のようにしなやか。踏まれても立ち上がる柔軟な守備",
    },
    "表現": {
        "gogyo": "火", "keyword": "伝える・表現する・感性",
        "personality": "個性的で自己主張力がある。直感・洞察力に優れる。抜群の味覚を持つ人も。",
        "career": "音楽・芸術・料理・創作活動・セミナー講師・作家・コンテンツクリエイター",
        "strong": "発信力・感性・直感。人前で話す・書く・教えるが天職",
        "weak": "気分屋・飽きっぽい・現実離れしやすい",
        "yang": "太陽のように周囲を照らす表現。ダイナミック",
        "yin": "ろうそくの炎のように繊細な表現。芸術的",
    },
    "魅力": {
        "gogyo": "土", "keyword": "惹きつける・リーダー・カリスマ",
        "personality": "人を惹きつけるカリスマ性。自分の考えは簡単には変えられない。良く言えばポリシー、悪く言えば頑固。",
        "career": "経営者・政治家・教室運営・コミュニティ運営。人が自然に集まってくる",
        "strong": "人望・包容力・安定感。自然とリーダーになる",
        "weak": "頑固・変化を嫌う・保守的すぎる",
        "yang": "山のようにどっしりとした魅力",
        "yin": "田畑のように人を育てる魅力",
    },
    "攻撃": {
        "gogyo": "金", "keyword": "切り拓く・即行動・結果主義",
        "personality": "自分から物怖じせずにどんどんアタックしていける人。結果オーライの結果主義者。持久力がないので根気を求められることは不得手。",
        "career": "複数事業の展開・新規プロジェクト・営業・スポーツ。創業者タイプ",
        "strong": "行動力・決断力・突破力。即断即決で動ける",
        "weak": "持久力不足・独断専行になりやすい・短気",
        "yang": "剣のように鋭く切り込む攻撃",
        "yin": "宝石のように磨かれた攻撃。完璧主義的な攻撃",
    },
    "学習": {
        "gogyo": "水", "keyword": "学ぶ・分析する・知的",
        "personality": "理論派・理屈屋。感情にあまり左右されないクール。何かを作り上げる創造力。",
        "career": "研究者・学者・プログラマー・戦略家・水商売の才能も（水の気）",
        "strong": "分析力・知性・創造力。一つのことを深掘りする集中力",
        "weak": "感情表現が苦手・理屈っぽい・孤立しがち",
        "yang": "大河のようにダイナミックな知性",
        "yin": "雨や霧のように静かな知性。繊細な感受性",
    },
}


# ── 五本能の組み合わせ解釈（第1×第2本能） ──
HONNOU_COMBINATION = {
    ('表現', '魅力'): {
        'talent': '人を惹きつける情報発信者',
        'description': '表現力でカリスマ性を発揮。セミナー講師・教育者に最適。',
    },
    ('表現', '攻撃'): {
        'talent': '切り拓く表現者',
        'description': '表現力と行動力の掛け算。起業家×コンテンツクリエイター。',
    },
    ('攻撃', '表現'): {
        'talent': '行動する表現者',
        'description': 'まず動いてから発信する。実践→発信のサイクルが強い。',
    },
    ('攻撃', '魅力'): {
        'talent': 'カリスマ的リーダー',
        'description': '行動力と人望の掛け算。経営者・組織トップに最適。',
    },
    ('守備', '学習'): {
        'talent': '堅実な研究者',
        'description': 'コツコツ学び続ける力。学者・専門職・職人に最適。',
    },
    ('学習', '守備'): {
        'talent': '実務的な知識人',
        'description': '知識を実務に活かす力。管理系専門職・士業に最適。',
    },
    ('魅力', '守備'): {
        'talent': '安定したリーダー',
        'description': '人望と堅実さの掛け算。組織のまとめ役・管理職に最適。',
    },
    ('魅力', '表現'): {
        'talent': '教育者・メンター',
        'description': '人を惹きつけて教える力。塾長・師匠タイプ。',
    },
    ('学習', '表現'): {
        'talent': '知的クリエイター',
        'description': '深い知識を分かりやすく伝える力。解説者・ライターに最適。',
    },
    ('攻撃', '学習'): {
        'talent': '戦略的行動者',
        'description': '分析してから一気に動く。投資家・経営コンサルに最適。',
    },
}

# ── 即答アドバイス（エネルギー帯別） ──
INSTANT_ENERGY_ADVICE = {
    'very_low': {  # 〜160
        'one_liner': '一点集中型。余計なこと全部捨てて、これだと思ったことに全力を。',
        'drink_talk': '「あなた{value}。少ないからダメじゃない。F1のエンジンじゃなくてスナイパーライフル。一発の精度がすごい人。」',
    },
    'low': {  # 161〜180
        'one_liner': '自分のペースで勝負する人。組織より個人プレーが正解。',
        'drink_talk': '「{value}か。会社勤めよりフリーランスの方が輝くタイプ。自分のリズムを大事にして。」',
    },
    'average': {  # 181〜230
        'one_liner': 'バランス型。組織の中で着実にキャリアを積める人。',
        'drink_talk': '「{value}。一番生きやすいゾーン。会社の中でコツコツ信頼を積み上げるのが最強の開運法。」',
    },
    'high': {  # 231〜300
        'one_liner': '仕事だけじゃ足りない人。趣味・社会活動で意識的にエネルギーを燃やせ。',
        'drink_talk': '「{value}！仕事だけじゃエネルギー余るでしょ？ゴルフとかスポーツとかやってる？やってないならすぐ始めて。イライラの原因それだから。」',
    },
    'very_high': {  # 301〜
        'one_liner': '規格外。普通の枠じゃ収まらない。複数の事業・活動を同時に走らせろ。',
        'drink_talk': '「{value}！！歴史的人物クラス。仕事3つ4つ掛け持ちして、やっとちょうどいい。止まったら死ぬマグロと同じ。」',
    },
}


# ── エネルギー帯 詳細解説（書籍準拠） ──
ENERGY_BAND_DETAIL = {
    'very_low': {
        'label': '集中特化型',
        'range': '〜160',
        'description': '組織には向いていない。サラリーマンとして長続きしにくい。無理に組織に合わせると陰転して病気になるリスクも。',
        'correct_life': '一点集中。専門職・職人・フリーランス。自分のペースで生きる。',
        'metaphor': 'F1のエンジンじゃなくてスナイパーライフル。一発の精度がすごい人。',
        'youten_actions': [
            '「これだ」と思えることに全力を注ぐ。余計なことは全部捨てる',
            '少人数の環境で深い関係を築く。広く浅くは不向き',
            '自分のペース・リズムを最優先にする生活設計',
        ],
        'inten_signs': [
            '「自分は根気がない」「いい加減だ」と自己否定が始まる',
            '組織に合わせるストレスで体調を崩す（不眠・胃腸・倦怠感）',
        ],
    },
    'low': {
        'label': '自営業向き型',
        'range': '161〜180',
        'description': '組織適応の下限ゾーン。会社勤めもできるが、自分のペースで動く方が力を発揮する。',
        'correct_life': 'フリーランス・自営業・少人数の会社。自分のリズムを大事に。',
        'metaphor': 'マイペースが武器。自分のリズムを守れる環境を選べ。',
        'youten_actions': [
            '大きな組織より小回りの利く環境を選ぶ',
            '一人の時間を確保する。充電の時間が人より多く必要',
            '得意分野に特化して「この人に頼めば間違いない」を作る',
        ],
        'inten_signs': [
            '他人のペースに巻き込まれて疲弊する',
            '「もっとがんばらないと」と自分を追い込み始める',
        ],
    },
    'average': {
        'label': '組織適応型',
        'range': '181〜230',
        'description': '現代日本社会で最も生きやすいゾーン。世の中の常識・規範に妥協しながら生きていける。組織の中で浮き彫りにされずに済む。',
        'correct_life': '会社員・管理職コースが最も自然。コツコツ信頼を積み上げるのが最強の開運法。',
        'metaphor': '一番生きやすいゾーン。安定こそが武器。',
        'youten_actions': [
            '組織の中で着実にキャリアを積む。信頼の積み重ねが最大の資産',
            '200以上なら管理職・リーダーシップを積極的に取る',
            '安定を土台にして、少しずつ挑戦の幅を広げる',
        ],
        'inten_signs': [
            '安定に甘えて成長が止まる。マンネリ感が出てくる',
            '「自分はもっとできるはず」と現状への不満が募る',
        ],
    },
    'high': {
        'label': '超活動型',
        'range': '231〜300',
        'description': '世の中の常識・社会の規範の中で生きていくにはかなり自分自身を傷つけることになる。多すぎるエネルギーのために自分を苦しめてしまう。',
        'correct_life': '仕事＋趣味＋社会活動の三本柱。本業だけではエネルギーが余る。',
        'metaphor': 'エネルギーが余って暴走する。ゴルフ・趣味・ボランティアで意識的に燃やせ。',
        'youten_actions': [
            '仕事以外のアウトレットを必ず持つ（スポーツ・趣味・社会活動）',
            '複数のプロジェクト・活動を同時に走らせる',
            'エネルギーの「はけ口」を意識的にスケジュールに組み込む',
        ],
        'inten_signs': [
            '部下や家族にエネルギーを向けてしまう（パワハラ・支配的になる）',
            '愚痴・不満が爆発する。ワンマンになり周囲と衝突する',
        ],
    },
    'very_high': {
        'label': '規格外型',
        'range': '301〜',
        'description': '歴史的人物クラスのエネルギー。普通の枠では収まらない。波乱万丈が「普通」。組織の中で生きていくかぎり、常識・規範との妥協が避けられない。',
        'correct_life': '経営者・複数事業・社会的リーダーが自然な生き方。仕事3つ4つ掛け持ちしてやっとちょうどいい。',
        'metaphor': '止まったら死ぬマグロと同じ。常に動き続けろ。',
        'youten_actions': [
            '複数の事業・活動・社会的リーダーシップを同時に走らせる',
            '国や業界を動かすレベルの大きなビジョンを持つ',
            '周囲のエネルギー差を理解し、部下や家族に合わせる意識を持つ',
        ],
        'inten_signs': [
            'エネルギーの不完全燃焼が身体に出る（重大な病気のリスク）',
            '「おれが頑張っているのだからお前たちも」と周囲を追い込む',
        ],
    },
}

# ── 0点本能別アドバイス ──
ZERO_HONNOU_ADVICE = {
    '守備': {
        'meaning': 'コツコツ守り固めるのは生まれ持った才能ではない',
        'advice': '「堅実にコツコツ」を求められると消耗する。得意な本能で攻めて、守りは仕組み（ルール・システム）に任せるのが正解。',
        'alternative': '守備は「仕組み化」で補う。マニュアル・ルーティンを作って自動化せよ。',
    },
    '表現': {
        'meaning': '自己表現・発信は生まれ持った才能ではない',
        'advice': '人前で話す・書く・発信することに苦手意識がある。無理にSNSや講演をやる必要はない。',
        'alternative': '表現は「誰かの力を借りる」で補う。ライター・デザイナー・広報を味方につけよ。',
    },
    '魅力': {
        'meaning': '人を惹きつけるカリスマ性は生まれ持った才能ではない',
        'advice': '「リーダーになれ」「人をまとめろ」は消耗する。参謀・専門家ポジションの方が輝く。',
        'alternative': '魅力は「実績」で補う。カリスマ性がなくても、結果で人はついてくる。',
    },
    '攻撃': {
        'meaning': '自分から切り拓く行動力は生まれ持った才能ではない',
        'advice': '「営業してこい」「新規開拓しろ」は消耗する。既存の仕組みを深掘りする方が向いている。',
        'alternative': '攻撃は「環境」で補う。自分から動かなくても案件が来る仕組みを作れ。',
    },
    '学習': {
        'meaning': 'じっと座って学ぶ・分析するのは生まれ持った才能ではない',
        'advice': '机上の勉強は向いていない。「動きながら学ぶ」「教えながら学ぶ」「実践から学ぶ」が合っている。',
        'alternative': '学習は「実践」で補う。本を読むより現場に出ろ。教えることで自分が一番学べる。',
    },
}


def get_energy_band(total: int) -> str:
    """エネルギー指数からバンドキーを返す"""
    if total <= 160:
        return 'very_low'
    elif total <= 180:
        return 'low'
    elif total <= 230:
        return 'average'
    elif total <= 300:
        return 'high'
    else:
        return 'very_high'


def energy_compatibility_reading(person_a_energy: int, person_b_energy: int) -> str:
    """2人のエネルギー値から相性コメントを生成"""
    diff = abs(person_a_energy - person_b_energy)
    higher = max(person_a_energy, person_b_energy)
    lower = min(person_a_energy, person_b_energy)

    if diff <= 30:
        return f'エネルギー差{diff}。ペースがぴったり合う。自然体でいられる関係。'
    elif diff <= 60:
        return f'エネルギー差{diff}。適度な差がお互いを補い合う。良い関係。'
    elif diff <= 100:
        return f'エネルギー差{diff}。{higher}の方が{lower}の方のペースに合わせる意識が必要。'
    else:
        return (
            f'エネルギー差{diff}。生活リズムが大きく異なる。'
            f'{higher}の方は余ったエネルギーを別のアウトレット（趣味・仕事）で消費すること。'
            f'{lower}の方は無理に合わせず、自分のペースを守ること。'
        )


def calc_energy_index(
    year_kan: str, year_shi: str,
    month_kan: str, month_shi: str,
    day_kan: str, day_shi: str,
) -> Dict:
    """
    万象学の宿命エネルギー指数を計算する。

    手順（書籍59〜72ページ準拠）：
    ① 命式から全ての干（天干＋蔵干）を抽出し出現回数を数える
    ② 各干について年支・月支・日支のエネルギー値を合計
    ③ 合計 × 干の個数 = 最終値
    ④ 五行ごとに集計 → 総合計 = エネルギー指数
    """
    supports = [year_shi, month_shi, day_shi]

    # STEP 1: 命式中の全ての干を収集し出現回数を数える
    all_kans = [year_kan, month_kan, day_kan]
    for shi in supports:
        all_kans.extend(ZOUKAN.get(shi, []))

    kan_count = {}
    for k in all_kans:
        kan_count[k] = kan_count.get(k, 0) + 1

    # STEP 2-3: 各干のエネルギー計算
    kan_energy = {}
    for kan in ENERGY_TABLE:
        shi_sum = sum(ENERGY_TABLE[kan][shi] for shi in supports)
        count = kan_count.get(kan, 0)
        kan_energy[kan] = {
            "year": ENERGY_TABLE[kan][supports[0]],
            "month": ENERGY_TABLE[kan][supports[1]],
            "day": ENERGY_TABLE[kan][supports[2]],
            "sum": shi_sum,
            "count": count,
            "total": shi_sum * count,
        }

    # STEP 4: 五行ごとに集計
    gogyo_detail = {}
    for gogyo in ["木", "火", "土", "金", "水"]:
        yang_kan = [k for k, g in GOGYO_MAP.items() if g == gogyo and YIN_YANG_MAP[k] == "陽"][0]
        yin_kan  = [k for k, g in GOGYO_MAP.items() if g == gogyo and YIN_YANG_MAP[k] == "陰"][0]
        yang_total = kan_energy[yang_kan]["total"]
        yin_total  = kan_energy[yin_kan]["total"]
        gogyo_detail[gogyo] = {
            "陽干": yang_kan, "陽": yang_total,
            "陰干": yin_kan,  "陰": yin_total,
            "総合計": yang_total + yin_total,
            "本能": HONNOU_MAP[gogyo],
        }

    total_energy = sum(g["総合計"] for g in gogyo_detail.values())

    # 五本能ランキング
    honnou_ranking = sorted(
        [(g["本能"], g["総合計"]) for g in gogyo_detail.values()],
        key=lambda x: x[1], reverse=True,
    )

    # エネルギータイプ判定
    energy_type = "標準型"
    energy_description = ""
    energy_advice = ""
    for lo, hi, typ, desc, adv in ENERGY_INTERPRETATION:
        if lo <= total_energy <= hi:
            energy_type = typ
            energy_description = desc
            energy_advice = adv
            break

    # ゼロ本能
    zero_honnou = [h for h, s in honnou_ranking if s == 0]

    # 第1×第2本能コンボ
    top1 = honnou_ranking[0][0] if honnou_ranking else ""
    top2 = honnou_ranking[1][0] if len(honnou_ranking) > 1 else ""
    combo = HONNOU_COMBINATION.get((top1, top2), {})
    combo_talent = combo.get('talent', '')
    combo_description = combo.get('description', '')

    # 即答アドバイス
    band = get_energy_band(total_energy)
    instant = INSTANT_ENERGY_ADVICE.get(band, {})
    one_liner = instant.get('one_liner', '')
    drink_talk = instant.get('drink_talk', '').format(value=total_energy)

    # エネルギー帯詳細
    band_detail = ENERGY_BAND_DETAIL.get(band, {})

    # 五行バランス比率（%）
    gogyo_balance = {}
    for gogyo_name in ["木", "火", "土", "金", "水"]:
        score = gogyo_detail[gogyo_name]["総合計"]
        gogyo_balance[gogyo_name] = {
            "score": score,
            "percent": round(score / total_energy * 100, 1) if total_energy > 0 else 0,
            "honnou": HONNOU_MAP[gogyo_name],
        }

    # 第1本能の陰陽干キャラクター
    top1_gogyo = honnou_ranking[0][0] if honnou_ranking else ""
    top1_gogyo_key = {v: k for k, v in HONNOU_MAP.items()}.get(top1_gogyo, "")
    top1_yang_detail = ""
    top1_yin_detail = ""
    if top1_gogyo_key:
        gd = gogyo_detail[top1_gogyo_key]
        yang_score = gd["陽"]
        yin_score = gd["陰"]
        top_h_detail = HONNOU_DETAIL.get(top1_gogyo, {})
        if yang_score >= yin_score:
            top1_yang_detail = top_h_detail.get("yang", "")
            dominant_yinyang = "陽"
        else:
            top1_yin_detail = top_h_detail.get("yin", "")
            dominant_yinyang = "陰"
    else:
        dominant_yinyang = ""

    # 0点本能の詳細アドバイス
    zero_honnou_details = []
    for zh in zero_honnou:
        adv = ZERO_HONNOU_ADVICE.get(zh, {})
        zero_honnou_details.append({
            "name": zh,
            "meaning": adv.get("meaning", ""),
            "advice": adv.get("advice", ""),
            "alternative": adv.get("alternative", ""),
        })

    return {
        "total_energy": total_energy,
        "energy_type": energy_type,
        "energy_description": energy_description,
        "energy_advice": energy_advice,
        "gogyo_detail": gogyo_detail,
        "kan_energy": kan_energy,
        "honnou_ranking": honnou_ranking,
        "top_honnou": honnou_ranking[0][0] if honnou_ranking else "",
        "top_score": honnou_ranking[0][1] if honnou_ranking else 0,
        "second_honnou": honnou_ranking[1][0] if len(honnou_ranking) > 1 else "",
        "second_score": honnou_ranking[1][1] if len(honnou_ranking) > 1 else 0,
        "zero_honnou": zero_honnou,
        "combo_talent": combo_talent,
        "combo_description": combo_description,
        "one_liner": one_liner,
        "drink_talk": drink_talk,
        "band": band,
        "band_detail": band_detail,
        "gogyo_balance": gogyo_balance,
        "dominant_yinyang": dominant_yinyang,
        "top1_yang_detail": top1_yang_detail,
        "top1_yin_detail": top1_yin_detail,
        "zero_honnou_details": zero_honnou_details,
    }


def get_energy_percent(total: int) -> int:
    """エネルギー指数をパーセントに変換（範囲: 89〜401）"""
    lo, hi = 89, 401
    return max(0, min(100, int((total - lo) / (hi - lo) * 100)))
