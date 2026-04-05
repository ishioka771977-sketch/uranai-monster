"""
開運アドバイスエンジン（core/kaiyun.py）
日運・月運・年運・大運を算出し、開運アドバイスを生成する
"""
import calendar
import math
from datetime import date, timedelta

from lunardate import LunarDate

from .sanmei import (
    KANSHI_60, JIKKAN, JUNISHI,
    JIKKAN_GOGYO, JIKKAN_INYO, JUNISHI_GOGYO,
    TENCHUSATSU_JUNISHI,
    _calc_hi_kanshi, _calc_nen_kanshi, _calc_tsuki_kanshi, _calc_jd,
)

# ============================================================
# 定数・データテーブル
# ============================================================

# 六曜
ROKUYO = ["大安", "赤口", "先勝", "友引", "先負", "仏滅"]

# 十二直
JUNICHOKU = ["建", "除", "満", "平", "定", "執", "破", "危", "成", "納", "開", "閉"]

# 相生（SOJO）: 生む側 → 生まれる側
SOJO = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}

# 相剋（SOKOKU）: 剋す側 → 剋される側
SOKOKU = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}

# 干合ペア
KANGO_PAIRS = {
    frozenset(["甲", "己"]),
    frozenset(["乙", "庚"]),
    frozenset(["丙", "辛"]),
    frozenset(["丁", "壬"]),
    frozenset(["戊", "癸"]),
}

# 節入り日（近似）
SETSU_DATES_APPROX = {1: 6, 2: 4, 3: 6, 4: 5, 5: 6, 6: 6, 7: 7, 8: 8, 9: 8, 10: 8, 11: 7, 12: 7}

# 六曜詳細
ROKUYO_DETAIL = {
    "大安": {"luck": "大吉", "advice": "万事に吉。新しいことを始めるのに最適な日。"},
    "赤口": {"luck": "凶", "advice": "正午のみ吉。午前・午後は控えめに過ごすのが吉。"},
    "先勝": {"luck": "小吉", "advice": "午前中が吉。急ぎの用事は早めに片付けると良い。"},
    "友引": {"luck": "吉", "advice": "友を引く日。祝い事に良い。朝晩は吉、昼は凶。"},
    "先負": {"luck": "小凶", "advice": "午後が吉。午前中は静かに過ごし、急がず焦らず。"},
    "仏滅": {"luck": "凶", "advice": "万事に凶。新規事業や契約は避け、静養の日に。"},
}

# 十二直詳細
JUNICHOKU_DETAIL = {
    "建": {"luck": "大吉", "advice": "万事に吉。新しいことを始めるのに良い日。"},
    "除": {"luck": "吉", "advice": "障害を除く日。掃除・片付け・治療に良い。"},
    "満": {"luck": "大吉", "advice": "満ちる日。新規事業・婚礼・引越しに大吉。"},
    "平": {"luck": "吉", "advice": "平穏な日。地固め・穏やかな交渉に良い。"},
    "定": {"luck": "吉", "advice": "物事が定まる日。契約・結納に良い。"},
    "執": {"luck": "小吉", "advice": "執り行う日。祭事・種まきに良い。"},
    "破": {"luck": "凶", "advice": "破れる日。契約・約束事は避けるのが賢明。"},
    "危": {"luck": "凶", "advice": "危うい日。高所作業・旅行は慎重に。"},
    "成": {"luck": "大吉", "advice": "物事が成就する日。商談・開業に大吉。"},
    "納": {"luck": "吉", "advice": "納める日。収穫・収納・買い物に良い。"},
    "開": {"luck": "大吉", "advice": "開く日。開業・建築着工に大吉。"},
    "閉": {"luck": "凶", "advice": "閉じる日。内向きの作業に良いが、新規は避ける。"},
}

# 日干同士の通変星関係（五行ベース簡易版）→ テーマ・アドバイス
DAILY_KANSEI = {
    "比劫": {
        "theme": "自分らしさの日",
        "do": "自分のペースで行動する。仲間との交流が吉。",
        "dont": "我を通しすぎると摩擦を生む。協調も大切に。",
    },
    "食傷": {
        "theme": "表現・発信の日",
        "do": "アイデアを形にする。プレゼン・SNS発信に好機。",
        "dont": "言い過ぎ・出しゃばりに注意。一歩引く余裕を。",
    },
    "財星": {
        "theme": "行動・獲得の日",
        "do": "営業・商談・買い物に吉。積極的に動くと良い。",
        "dont": "散財・衝動買いに注意。予算を決めてから動く。",
    },
    "官星": {
        "theme": "試練・成長の日",
        "do": "規律を守り、上司・目上を立てる。自己研鑽に最適。",
        "dont": "無理な挑戦は逆効果。慎重さが身を守る。",
    },
    "印星": {
        "theme": "学び・受容の日",
        "do": "読書・学習・資格取得に最適。年長者の助言を聞く。",
        "dont": "考えすぎて動けなくなりがち。適度に行動も。",
    },
}


# ============================================================
# 1. 日干支の取得
# ============================================================

def get_day_kanshi(target_date: date) -> str:
    """指定日の干支を返す（sanmei.pyのJD法を利用）"""
    return _calc_hi_kanshi(target_date)


# ============================================================
# 2. 六曜の計算
# ============================================================

def get_rokuyo(target_date: date) -> str:
    """指定日の六曜を返す（旧暦の月+日から算出）"""
    lunar = LunarDate.fromSolarDate(target_date.year, target_date.month, target_date.day)
    idx = (lunar.month + lunar.day) % 6
    return ROKUYO[idx]


# ============================================================
# 3. 十二直の計算
# ============================================================

def get_junichoku(target_date: date) -> str:
    """指定日の十二直を返す（日支と月支のオフセットから算出）"""
    # 日干支を取得し、日支を抽出
    day_kanshi = get_day_kanshi(target_date)
    day_shi = day_kanshi[1]
    day_shi_idx = JUNISHI.index(day_shi)

    # 月支を取得（節入り補正付き）
    # 節入り日で月を判定
    month = target_date.month
    day = target_date.day
    sekki_day = SETSU_DATES_APPROX.get(month, 6)
    if day < sekki_day:
        month = month - 1 if month > 1 else 12

    # 月支: 2月=寅(idx=2), 3月=卯(idx=3), ...
    MONTH_TO_SHI_IDX = {
        2: 2, 3: 3, 4: 4, 5: 5, 6: 6, 7: 7,
        8: 8, 9: 9, 10: 10, 11: 11, 12: 0, 1: 1,
    }
    month_shi_idx = MONTH_TO_SHI_IDX[month]

    # 十二直: (日支 - 月支) % 12 でインデックスを算出
    junichoku_idx = (day_shi_idx - month_shi_idx) % 12
    return JUNICHOKU[junichoku_idx]


# ============================================================
# 4. 通変星関係（日干同士）
# ============================================================

def get_daily_kansei(person_kan: str, day_kan: str) -> str:
    """本人の日干と対象日の日干の五行関係から通変星カテゴリを返す"""
    p_gogyo = JIKKAN_GOGYO[person_kan]
    d_gogyo = JIKKAN_GOGYO[day_kan]

    if p_gogyo == d_gogyo:
        return "比劫"
    elif SOJO[p_gogyo] == d_gogyo:
        # 本人が生む → 食傷
        return "食傷"
    elif SOJO[d_gogyo] == p_gogyo:
        # 相手が生む → 印星
        return "印星"
    elif SOKOKU[p_gogyo] == d_gogyo:
        # 本人が剋す → 財星
        return "財星"
    else:
        # 相手が剋す → 官星
        return "官星"


# ============================================================
# 5. 日運スコア計算
# ============================================================

def calc_lucky_score(target_date: date, person_data: dict) -> dict:
    """
    日運ラッキースコア（0〜10）を計算する。

    person_data:
        day_kan: str - 本人の日干（例: "辛"）
        tenchusatsu: list[str] - 天中殺の地支2つ（例: ["申","酉"]）
        special_kaku: str|None - 特殊格局名（例: "三巳格"）
    """
    person_kan = person_data["day_kan"]
    tcs_shi = person_data.get("tenchusatsu", [])
    special_kaku = person_data.get("special_kaku")

    # 各要素を計算
    day_kanshi = get_day_kanshi(target_date)
    day_kan = day_kanshi[0]
    day_shi = day_kanshi[1]
    rokuyo = get_rokuyo(target_date)
    junichoku = get_junichoku(target_date)
    kansei = get_daily_kansei(person_kan, day_kan)

    # 天中殺判定
    is_tcs = day_shi in tcs_shi

    # スコア計算（基本5点）
    score = 5

    # 五行関係
    if kansei == "比劫":
        score += 1   # 比和
    elif kansei == "印星":
        score += 1   # 日が本人を生む
    elif kansei == "官星":
        score -= 1   # 日が本人を剋す

    # 干合
    if frozenset([person_kan, day_kan]) in KANGO_PAIRS:
        score += 2

    # 特殊格局 × 火の日（巳/午）
    if special_kaku and day_shi in ("巳", "午"):
        score += 2

    # 特殊格局 × 水の日（亥/子）
    if special_kaku and day_shi in ("亥", "子"):
        score -= 2

    # 六曜
    if rokuyo in ("大安", "友引"):
        score += 1
    elif rokuyo == "仏滅":
        score -= 1

    # 十二直
    if junichoku in ("建", "満", "成", "開"):
        score += 1
    elif junichoku in ("破", "危", "閉"):
        score -= 1

    # 天中殺日
    if is_tcs:
        score -= 3

    # 0〜10にクランプ
    score = max(0, min(10, score))

    # アドバイス生成
    advice = generate_daily_advice(score, kansei, is_tcs, rokuyo, junichoku)

    return {
        "score": score,
        "day_kanshi": day_kanshi,
        "rokuyo": rokuyo,
        "junichoku": junichoku,
        "tenchusatsu": is_tcs,
        "kansei": kansei,
        "advice": advice,
    }


# ============================================================
# 6. 日運アドバイス生成
# ============================================================

def generate_daily_advice(score: int, kansei: str, is_tcs: bool, rokuyo: str, junichoku: str) -> str:
    """スコアと各要素に基づき、一行アドバイスを生成する"""
    if is_tcs:
        return "天中殺日。新規の決断は避け、受け身で過ごすのが吉。既存の仕事を丁寧に。"

    kansei_info = DAILY_KANSEI.get(kansei, DAILY_KANSEI["比劫"])

    if score >= 8:
        return f"最高の運気！{kansei_info['theme']}。{kansei_info['do']}"
    elif score >= 6:
        return f"好調な日。{kansei_info['theme']}。{kansei_info['do']}"
    elif score >= 4:
        rokuyo_info = ROKUYO_DETAIL.get(rokuyo, {})
        rokuyo_advice = rokuyo_info.get("advice", "")
        return f"平穏な日。{rokuyo_advice}"
    elif score >= 2:
        return f"やや低調。{kansei_info['dont']}"
    else:
        return f"要注意の日。{kansei_info['dont']}無理をせず守りの姿勢で。"


# ============================================================
# 7. 月間カレンダー生成
# ============================================================

def calc_monthly_calendar(year: int, month: int, person_data: dict) -> dict:
    """指定月の全日程の日運カレンダーを生成する"""
    # 月干支を計算
    sample_date = date(year, month, 15)  # 月中の日を使って月干支を取得
    nen_kanshi = _calc_nen_kanshi(sample_date)
    month_kanshi = _calc_tsuki_kanshi(sample_date, nen_kanshi[0])

    # 月の日数
    _, num_days = calendar.monthrange(year, month)

    days = []
    best_day = None
    worst_day = None

    for d in range(1, num_days + 1):
        target = date(year, month, d)
        result = calc_lucky_score(target, person_data)
        entry = {
            "date": target.isoformat(),
            "score": result["score"],
            "day_kanshi": result["day_kanshi"],
            "rokuyo": result["rokuyo"],
            "junichoku": result["junichoku"],
            "tenchusatsu": result["tenchusatsu"],
            "kansei": result["kansei"],
            "advice": result["advice"],
        }
        days.append(entry)

        if best_day is None or result["score"] > best_day["score"]:
            best_day = entry
        if worst_day is None or result["score"] < worst_day["score"]:
            worst_day = entry

    return {
        "year": year,
        "month": month,
        "month_kanshi": month_kanshi,
        "days": days,
        "best_day": best_day,
        "worst_day": worst_day,
    }


# ============================================================
# 8. 月運アドバイス生成
# ============================================================

def generate_monthly_advice(person_data: dict, year: int, month: int) -> dict:
    """月単位の開運アドバイスを生成する"""
    sample_date = date(year, month, 15)
    nen_kanshi = _calc_nen_kanshi(sample_date)
    month_kanshi = _calc_tsuki_kanshi(sample_date, nen_kanshi[0])
    month_kan = month_kanshi[0]
    month_shi = month_kanshi[1]

    person_kan = person_data["day_kan"]
    tcs_shi = person_data.get("tenchusatsu", [])

    kansei = get_daily_kansei(person_kan, month_kan)
    kansei_info = DAILY_KANSEI.get(kansei, DAILY_KANSEI["比劫"])

    # 月支が天中殺の地支に該当するか
    is_tcs_month = month_shi in tcs_shi

    theme = kansei_info["theme"]
    if is_tcs_month:
        theme = "天中殺月 — 守りの月"

    return {
        "month_kanshi": month_kanshi,
        "kansei": kansei,
        "theme": theme,
        "do": kansei_info["do"] if not is_tcs_month else "既存の仕事を丁寧にこなす。新規の契約・大きな決断は翌月以降に。",
        "dont": kansei_info["dont"] if not is_tcs_month else "新規事業・転職・引越しなど人生の大きな変化は避ける。",
        "tenchusatsu_month": is_tcs_month,
    }


# ============================================================
# 9. 年運アドバイス生成
# ============================================================

def generate_yearly_advice(person_data: dict, year: int) -> dict:
    """年単位の開運アドバイスを生成する"""
    year_kanshi = _calc_nen_kanshi(date(year, 6, 15))
    year_kan = year_kanshi[0]
    year_shi = year_kanshi[1]

    person_kan = person_data["day_kan"]
    tcs_shi = person_data.get("tenchusatsu", [])

    kansei = get_daily_kansei(person_kan, year_kan)
    kansei_info = DAILY_KANSEI.get(kansei, DAILY_KANSEI["比劫"])

    is_tcs_year = year_shi in tcs_shi

    # 年干の五行
    year_gogyo = JIKKAN_GOGYO[year_kan]

    # テーマ
    if is_tcs_year:
        theme = "天中殺年 — 守りと内省の年"
        keywords = ["受容", "整理", "準備", "内省", "手放す"]
        energy_advice = "天中殺年は「空」のエネルギー。欲を手放し、人の役に立つことに集中すると吉。"
    else:
        theme = kansei_info["theme"].replace("の日", "の年")
        keywords_map = {
            "比劫": ["自立", "独立", "仲間", "原点回帰", "基盤づくり"],
            "食傷": ["表現", "創造", "発信", "技術", "アウトプット"],
            "財星": ["行動", "獲得", "営業", "拡大", "実利"],
            "官星": ["試練", "成長", "責任", "規律", "昇進"],
            "印星": ["学び", "研究", "受容", "資格", "知恵"],
        }
        keywords = keywords_map.get(kansei, keywords_map["比劫"])
        energy_advice = f"{year_gogyo}のエネルギーが支配する年。{kansei_info['do']}"

    return {
        "year_kanshi": year_kanshi,
        "kansei": kansei,
        "theme": theme,
        "keywords": keywords,
        "do": kansei_info["do"] if not is_tcs_year else "受け身の姿勢で、人への奉仕を意識する。来年への準備期間。",
        "dont": kansei_info["dont"] if not is_tcs_year else "新規事業・結婚・不動産購入など大きな決断は極力避ける。",
        "tenchusatsu_year": is_tcs_year,
        "energy_advice": energy_advice,
    }


# ============================================================
# 10. 大運（10年運）計算
# ============================================================

def calc_taiun(person_data: dict, birth_date: date, gender: str) -> list:
    """
    大運（10年周期の運勢サイクル）を計算する。

    person_data:
        day_kan: str - 本人の日干
        tenchusatsu: list[str] - 天中殺の地支2つ
    gender: "男" or "女"
    """
    person_kan = person_data["day_kan"]
    tcs_shi = person_data.get("tenchusatsu", [])

    # 年干支を取得
    nen_kanshi = _calc_nen_kanshi(birth_date)
    nen_kan = nen_kanshi[0]
    nen_inyo = JIKKAN_INYO[nen_kan]

    # 月干支を取得
    tsuki_kanshi = _calc_tsuki_kanshi(birth_date, nen_kan)
    tsuki_idx = KANSHI_60.index(tsuki_kanshi)

    # 順行/逆行の判定
    # 男性×陽年干 = 順行, 男性×陰年干 = 逆行
    # 女性×陽年干 = 逆行, 女性×陰年干 = 順行
    is_male = gender in ("男", "男性")
    if is_male:
        forward = (nen_inyo == "陽")
    else:
        forward = (nen_inyo == "陰")

    # 立運（大運開始年齢）の計算
    # 順行: 生年月日から次の節入りまでの日数
    # 逆行: 生年月日から前の節入りまでの日数
    birth_month = birth_date.month
    birth_day = birth_date.day
    sekki_day = SETSU_DATES_APPROX.get(birth_month, 6)

    if forward:
        # 次の節入り日まで
        if birth_day < sekki_day:
            # 当月の節入り日が未来
            next_setsu = date(birth_date.year, birth_month, sekki_day)
        else:
            # 翌月の節入り日
            if birth_month == 12:
                next_month = 1
                next_year = birth_date.year + 1
            else:
                next_month = birth_month + 1
                next_year = birth_date.year
            next_sekki_day = SETSU_DATES_APPROX.get(next_month, 6)
            next_setsu = date(next_year, next_month, next_sekki_day)
        days_diff = (next_setsu - birth_date).days
    else:
        # 前の節入り日まで
        if birth_day >= sekki_day:
            # 当月の節入り日が過去
            prev_setsu = date(birth_date.year, birth_month, sekki_day)
        else:
            # 前月の節入り日
            if birth_month == 1:
                prev_month = 12
                prev_year = birth_date.year - 1
            else:
                prev_month = birth_month - 1
                prev_year = birth_date.year
            prev_sekki_day = SETSU_DATES_APPROX.get(prev_month, 6)
            prev_setsu = date(prev_year, prev_month, prev_sekki_day)
        days_diff = (birth_date - prev_setsu).days

    # 日数 ÷ 3 = 立運年齢（四捨五入）
    start_age = round(days_diff / 3)

    # 大運リスト（10個生成）
    taiun_list = []
    for i in range(10):
        if forward:
            idx = (tsuki_idx + (i + 1)) % 60
        else:
            idx = (tsuki_idx - (i + 1)) % 60

        kanshi = KANSHI_60[idx]
        kan = kanshi[0]
        shi = kanshi[1]
        gogyo = JIKKAN_GOGYO[kan]
        kansei = get_daily_kansei(person_kan, kan)

        # 大運天中殺判定（大運の地支が天中殺の地支に含まれるか）
        is_taiun_tcs = shi in tcs_shi

        # 天中殺が発動する年の範囲（大運期間内で地支が天中殺に該当する年）
        period_start_age = start_age + (i * 10)
        period_end_age = period_start_age + 9
        tcs_years = []
        if is_taiun_tcs:
            # この大運期間中は全体的に天中殺の影響
            birth_year = birth_date.year
            for age in range(period_start_age, period_end_age + 1):
                y = birth_year + age
                y_shi_idx = (y - 4) % 12
                y_shi = JUNISHI[y_shi_idx]
                if y_shi in tcs_shi:
                    tcs_years.append(y)

        # 五行→本能マッピング
        HONNOU_MAP = {"木": "守備", "火": "表現", "土": "魅力", "金": "攻撃", "水": "学習"}
        honnou = HONNOU_MAP.get(gogyo, "")
        taiun_list.append({
            "start_age": period_start_age,
            "end_age": period_end_age,
            "kan": kan,
            "shi": shi,
            "kanshi": kanshi,
            "gogyo": gogyo,
            "honnou": honnou,
            "kansei": kansei,
            "is_taiun_tenchusatsu": is_taiun_tcs,
            "tenchusatsu_years": tcs_years,
        })

    return taiun_list


# ============================================================
# 11. 現在の大運を取得
# ============================================================

def get_current_taiun(taiun_list: list, birth_year: int, current_year: int) -> dict:
    """現在どの大運期間にいるかを返す"""
    current_age = current_year - birth_year
    for entry in taiun_list:
        if entry["start_age"] <= current_age <= entry["end_age"]:
            return entry
    # 見つからない場合は最後の大運を返す
    return taiun_list[-1] if taiun_list else {}


# ============================================================
# 検証コメント: ひでさん（石岡秀貴）の大運
# ============================================================
#
# 入力:
#   birth_date = date(1977, 5, 24)
#   gender = "男"
#   person_data = {
#       "day_kan": "辛",         # 日干: 辛（辛巳）
#       "tenchusatsu": ["申", "酉"],  # 申酉天中殺
#       "special_kaku": "三巳格",
#   }
#
# 計算過程:
#   年干支: 丁巳（(1977-4)%60=53 → KANSHI_60[53]="丁巳"）
#   年干: 丁 → 陰
#   月干支: 乙巳（GOKO_TOCHU["丁"]="壬", 巳月offset=3, (8+3)%10=1→"乙", 乙巳）
#   月干支のKANSHI_60 index: 41
#
#   方向: 男性 × 陰年干(丁) = 逆行
#   節入り: 5月の節入り=6日, 生日=24日 → 当月の節入りが過去 → 24-6=18日
#   立運年齢: round(18/3) = 6歳
#
#   大運シーケンス（逆行: index 41から-1ずつ）:
#     i=0: idx=40 → 甲辰（ 6〜15歳）
#     i=1: idx=39 → 癸卯（16〜25歳）
#     i=2: idx=38 → 壬寅（26〜35歳）
#     i=3: idx=37 → 辛丑（36〜45歳）
#     i=4: idx=36 → 庚子（46〜55歳）
#     i=5: idx=35 → 己亥（56〜65歳）
#     i=6: idx=34 → 戊戌（66〜75歳）
#     i=7: idx=33 → 丁酉（76〜85歳）
#
# 期待値: 甲辰→癸卯→壬寅→辛丑→庚子→己亥→戊戌→丁酉 ✓
