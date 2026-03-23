"""
数秘術エンジン（core/numerology.py）
生年月日 → ライフパスナンバー・個人年数
"""
from datetime import date

from .models import PersonInput, NumerologyResult

LIFE_PATH_MEANINGS = {
    1: {"title": "リーダー", "desc": "独立心が強く、自分の道を切り拓く開拓者"},
    2: {"title": "調和者", "desc": "繊細で協調性があり、人と人をつなぐ架け橋"},
    3: {"title": "表現者", "desc": "創造力にあふれ、喜びを生み出すエンターテイナー"},
    4: {"title": "建設者", "desc": "堅実で信頼される、土台を作る実務家"},
    5: {"title": "冒険者", "desc": "自由を愛し、変化の中で輝く挑戦者"},
    6: {"title": "愛の人", "desc": "愛情深く、家庭や美を大切にする調和の守護者"},
    7: {"title": "探求者", "desc": "深い洞察力で真実を追い求める賢者"},
    8: {"title": "達成者", "desc": "パワフルに目標を達成する、生まれながらの経営者"},
    9: {"title": "博愛者", "desc": "人類愛に溢れ、大きなビジョンで世界を変える人"},
    11: {"title": "直感のマスター", "desc": "鋭い直感で人を導く、スピリチュアルなメッセンジャー"},
    22: {"title": "建築のマスター", "desc": "壮大なビジョンを現実にする、究極の実現者"},
    33: {"title": "愛のマスター", "desc": "無条件の愛で世界を包む、究極のヒーラー"},
}

PERSONAL_YEAR_MEANINGS = {
    1: {"title": "始まりの年", "desc": "新しいサイクルのスタート。種を蒔く時"},
    2: {"title": "忍耐の年", "desc": "待つことが大切。人間関係を深める時"},
    3: {"title": "表現の年", "desc": "才能が花開く。発信・創造・楽しむ時"},
    4: {"title": "基盤の年", "desc": "地固めの時。努力が試される"},
    5: {"title": "変化の年", "desc": "自由と変化がやってくる。冒険の時"},
    6: {"title": "責任の年", "desc": "家庭・愛情・責任がテーマ。調和を作る時"},
    7: {"title": "内省の年", "desc": "自分と向き合う。学びと精神的成長の時"},
    8: {"title": "収穫の年", "desc": "努力が実る。お金・地位・パワーが動く時"},
    9: {"title": "完成の年", "desc": "サイクルの締めくくり。手放しと感謝の時"},
    11: {"title": "覚醒の年", "desc": "直感と霊感が高まる特別な年"},
    22: {"title": "実現の年", "desc": "大きなビジョンが現実になる特別な年"},
}

LP_KEYWORDS = {
    1: ["独立心が強い", "先駆者", "自分の道を行く", "リーダー気質", "情熱的"],
    2: ["協調性がある", "繊細", "平和主義", "直感が鋭い", "人の心がわかる"],
    3: ["表現力がある", "明るい", "創造的", "人を楽しませる", "話し上手"],
    4: ["コツコツ努力", "堅実", "信頼できる", "責任感がある", "地道な力"],
    5: ["自由を愛する", "変化に強い", "好奇心旺盛", "多才", "冒険心"],
    6: ["愛情深い", "面倒見がいい", "美的センスがある", "責任感", "家族思い"],
    7: ["洞察力がある", "分析的", "神秘的", "学ぶことが好き", "真実を追う"],
    8: ["強い意志", "実行力がある", "経営センス", "目標達成力", "カリスマ性"],
    9: ["博愛精神", "芸術的センス", "先見の明", "理想主義", "人類愛"],
    11: ["直感が鋭い", "スピリチュアル", "インスピレーション", "人を導く", "感受性豊か"],
    22: ["大きなビジョン", "実現力", "組織構築", "革新的", "世界を変える力"],
    33: ["無条件の愛", "ヒーラー", "奉仕の精神", "愛のマスター", "癒しの力"],
}


def _reduce_to_single(n: int, master_numbers: tuple = (11, 22, 33)) -> int:
    """数を1桁（またはマスターナンバー）に還元"""
    while n > 9 and n not in master_numbers:
        n = sum(int(d) for d in str(n))
    return n


def calc_life_path(birth_date: date) -> int:
    """
    ライフパスナンバーを計算
    例: 1977年5月24日 → 1+9+7+7+0+5+2+4 = 35 → 3+5 = 8
    """
    total = sum(int(c) for c in birth_date.strftime("%Y%m%d"))
    return _reduce_to_single(total)


def calc_personal_year(birth_month: int, birth_day: int, target_year: int = 2026) -> int:
    """
    個人年数を計算
    例: 5月24日・2026年 → 5+2+4+2+0+2+6 = 21 → 2+1 = 3
    """
    digits = f"{birth_month:02d}{birth_day:02d}{target_year}"
    total = sum(int(c) for c in digits)
    return _reduce_to_single(total)


def calc_birthday_number(birth_day: int) -> int:
    """
    誕生日数を計算（生まれた日を一桁に還元）
    例: 24日 → 2+4 = 6
    例: 11日 → 11（マスターナンバー）
    """
    return _reduce_to_single(birth_day)


def calculate_numerology(person: PersonInput, target_year: int = 2026) -> NumerologyResult:
    """
    生年月日 → ライフパスナンバー・個人年数・誕生日数を計算
    """
    d = person.birth_date

    lp = calc_life_path(d)
    py = calc_personal_year(d.month, d.day, target_year)
    bd = calc_birthday_number(d.day)

    lp_data = LIFE_PATH_MEANINGS.get(lp, {"title": "探求者", "desc": "独自の道を歩む人"})
    py_data = PERSONAL_YEAR_MEANINGS.get(py, {"title": "成長の年", "desc": "前進する年"})

    keywords = LP_KEYWORDS.get(lp, [])

    return NumerologyResult(
        life_path=lp,
        personal_year=py,
        life_path_title=lp_data["title"],
        life_path_meaning=lp_data["desc"],
        personal_year_title=py_data["title"],
        personal_year_meaning=py_data["desc"],
        keywords=keywords[:5],
        birthday_number=bd,
    )
