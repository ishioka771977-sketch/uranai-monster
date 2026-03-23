"""
紫微斗数（紫微斗數）命盤計算エンジン
農暦変換 → 命宮/身宮 → 五行局 → 十四主星 → 副星 → 四化 → 大限
"""
from datetime import date
from typing import Optional
from lunardate import LunarDate
from .models import PersonInput, ZiweiResult, ZiweiPalace

# ========== 定数 ==========
BRANCHES = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥']
STEMS = ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸']

HOUR_NAMES = ['子時', '丑時', '寅時', '卯時', '辰時', '巳時',
              '午時', '未時', '申時', '酉時', '戌時', '亥時']

# 十二宮名（命宮から逆時計回り）
PALACE_NAMES = ['命宮', '兄弟宮', '夫妻宮', '子女宮', '財帛宮', '疾厄宮',
                '遷移宮', '交友宮', '事業宮', '田宅宮', '福徳宮', '父母宮']

# ========== 五行局（納音五行）テーブル ==========
# 干支ペアのインデックス（60甲子中の序数 // 2）→ 五行局数
# 60甲子の順番で2つずつ同じ納音
NAYIN_TABLE = {
    '甲子': 4, '乙丑': 4,  # 海中金→金四局
    '丙寅': 6, '丁卯': 6,  # 爐中火→火六局
    '戊辰': 3, '己巳': 3,  # 大林木→木三局
    '庚午': 5, '辛未': 5,  # 路旁土→土五局
    '壬申': 4, '癸酉': 4,  # 劍鋒金→金四局
    '甲戌': 6, '乙亥': 6,  # 山頭火→火六局
    '丙子': 2, '丁丑': 2,  # 澗下水→水二局
    '戊寅': 5, '己卯': 5,  # 城頭土→土五局
    '庚辰': 4, '辛巳': 4,  # 白蠟金→金四局
    '壬午': 3, '癸未': 3,  # 楊柳木→木三局
    '甲申': 2, '乙酉': 2,  # 泉中水→水二局
    '丙戌': 5, '丁亥': 5,  # 屋上土→土五局
    '戊子': 6, '己丑': 6,  # 霹靂火→火六局
    '庚寅': 3, '辛卯': 3,  # 松柏木→木三局
    '壬辰': 2, '癸巳': 2,  # 長流水→水二局
    '甲午': 4, '乙未': 4,  # 沙中金→金四局
    '丙申': 6, '丁酉': 6,  # 山下火→火六局
    '戊戌': 3, '己亥': 3,  # 平地木→木三局
    '庚子': 5, '辛丑': 5,  # 壁上土→土五局
    '壬寅': 4, '癸卯': 4,  # 金箔金→金四局
    '甲辰': 6, '乙巳': 6,  # 覆燈火→火六局
    '丙午': 2, '丁未': 2,  # 天河水→水二局
    '戊申': 5, '己酉': 5,  # 大駅土→土五局
    '庚戌': 4, '辛亥': 4,  # 釵釧金→金四局
    '壬子': 3, '癸丑': 3,  # 桑柘木→木三局
    '甲寅': 2, '乙卯': 2,  # 大溪水→水二局
    '丙辰': 5, '丁巳': 5,  # 沙中土→土五局
    '戊午': 6, '己未': 6,  # 天上火→火六局
    '庚申': 3, '辛酉': 3,  # 石榴木→木三局
    '壬戌': 2, '癸亥': 2,  # 大海水→水二局
}

FIVE_ELEMENT_NAMES = {2: '水二局', 3: '木三局', 4: '金四局', 5: '土五局', 6: '火六局'}

# ========== 紫微星基点テーブル（旧・不使用）==========
# 正しい安星法: ceil(日/局数)=商, 局数*商-日=余り, 寅から商格順行, 余り奇数逆行/偶数順行

# ========== 天府星対応テーブル ==========
TIANFU_MAP = {0: 4, 1: 3, 2: 2, 3: 1, 4: 0, 5: 11, 6: 10, 7: 9, 8: 8, 9: 7, 10: 6, 11: 5}

# ========== 四化テーブル ==========
SIHUA_TABLE = {
    0: {'化禄': '廉貞', '化権': '破軍', '化科': '武曲', '化忌': '太陽'},   # 甲
    1: {'化禄': '天機', '化権': '天梁', '化科': '紫微', '化忌': '太陰'},   # 乙
    2: {'化禄': '天同', '化権': '天機', '化科': '文昌', '化忌': '廉貞'},   # 丙
    3: {'化禄': '太陰', '化権': '天同', '化科': '天機', '化忌': '巨門'},   # 丁
    4: {'化禄': '貪狼', '化権': '太陰', '化科': '右弼', '化忌': '天機'},   # 戊
    5: {'化禄': '武曲', '化権': '貪狼', '化科': '天梁', '化忌': '文曲'},   # 己
    6: {'化禄': '太陽', '化権': '武曲', '化科': '天同', '化忌': '天相'},   # 庚
    7: {'化禄': '巨門', '化権': '太陽', '化科': '文曲', '化忌': '文昌'},   # 辛
    8: {'化禄': '天梁', '化権': '紫微', '化科': '左輔', '化忌': '武曲'},   # 壬
    9: {'化禄': '破軍', '化権': '巨門', '化科': '太陰', '化忌': '貪狼'},   # 癸
}

# ========== 天魁・天鉞テーブル ==========
TIANKUI_TABLE = [1, 0, 11, 11, 1, 0, 1, 6, 3, 3]
TIANYUE_TABLE = [7, 8, 9, 9, 7, 8, 7, 2, 5, 5]

# ========== 禄存テーブル ==========
LUCUN_TABLE = [2, 3, 5, 6, 5, 6, 8, 9, 11, 0]  # 甲→寅, 乙→卯, ...

# ========== 火星・鈴星 年支グループ ==========
FIRE_BELL_BASE = {
    'yin_wu_xu': (1, 3),    # 寅午戌
    'shen_zi_chen': (2, 10),  # 申子辰
    'si_you_chou': (3, 10),   # 巳酉丑
    'hai_mao_wei': (9, 10),   # 亥卯未
}

YEAR_BRANCH_GROUPS = {
    'yin_wu_xu': [2, 6, 10],
    'shen_zi_chen': [8, 0, 4],
    'si_you_chou': [5, 9, 1],
    'hai_mao_wei': [11, 3, 7],
}

# ========== 五虎遁（年干→寅月天干） ==========
TIGER_MONTH_STEM = {0: 2, 1: 4, 2: 6, 3: 8, 4: 0, 5: 2, 6: 4, 7: 6, 8: 8, 9: 0}

# ========== 十四主星の基本キーワード ==========
STAR_KEYWORDS = {
    '紫微': '帝王・リーダーシップ・尊厳',
    '天機': '知恵・変化・策略',
    '太陽': '光明・博愛・名誉',
    '武曲': '財星・決断・剛毅',
    '天同': '安楽・温和・享受',
    '廉貞': '情熱・複雑・政治力',
    '天府': '安定・財庫・包容',
    '太陰': '陰柔・芸術・母性',
    '貪狼': '欲望・多才・魅力',
    '巨門': '口才・疑念・分析',
    '天相': '補佐・礼儀・調和',
    '天梁': '庇護・長寿・清高',
    '七殺': '決断・孤高・開拓',
    '破軍': '破壊・変革・冒険',
}


# ========== 計算関数 ==========

def _birth_time_to_hour_idx(birth_time: Optional[str]) -> int:
    """出生時刻文字列 → 時辰インデックス"""
    if not birth_time:
        return 6  # デフォルト: 午時（正午）
    bt = birth_time.replace('：', ':').strip()
    bt = bt.translate(str.maketrans('０１２３４５６７８９', '0123456789'))
    try:
        h, m = map(int, bt.split(':'))
    except (ValueError, AttributeError):
        return 6
    total_min = h * 60 + m
    return ((total_min + 60) // 120) % 12


def _calc_ming_gong(lunar_month: int, birth_hour_idx: int) -> int:
    """命宮の地支インデックスを計算"""
    start_idx = (2 + lunar_month - 1) % 12
    return (start_idx - birth_hour_idx) % 12


def _calc_shen_gong(lunar_month: int, birth_hour_idx: int) -> int:
    """身宮の地支インデックスを計算"""
    start_idx = (2 + lunar_month - 1) % 12
    return (start_idx + birth_hour_idx) % 12


def _get_palace_stems(year_stem_idx: int) -> dict:
    """各宮（地支インデックス）の天干インデックスを返す"""
    tiger_stem_idx = TIGER_MONTH_STEM[year_stem_idx]
    palace_stems = {}
    for month in range(1, 13):
        branch_idx = (2 + month - 1) % 12
        stem_idx = (tiger_stem_idx + month - 1) % 10
        palace_stems[branch_idx] = stem_idx
    return palace_stems


def _get_five_element(kanshi: str) -> int:
    """干支から五行局数を取得（納音五行テーブル）"""
    return NAYIN_TABLE.get(kanshi, 4)  # デフォルト金四局


def _calc_ziwei_palace(lunar_day: int, five_element_num: int) -> int:
    """紫微星の宮インデックスを計算（正統安星法）
    1. 商 = ceil(日/局数)
    2. 余り = 局数*商 - 日
    3. 寅(idx=2)から商格順行して基準宮を決定
    4. 余り0→そのまま / 奇数→逆行 / 偶数→順行
    """
    import math
    F = five_element_num
    Q = math.ceil(lunar_day / F)
    R = F * Q - lunar_day
    # 寅(2)を1格目としてQ格目まで順行
    base = (2 + Q - 1) % 12
    if R == 0:
        return base
    elif R % 2 == 1:  # 奇数→逆行
        return (base - R) % 12
    else:  # 偶数→順行
        return (base + R) % 12


def _place_14_stars(ziwei_idx: int) -> dict:
    """十四主星の配置 → {星名: 宮インデックス}"""
    tf_idx = TIANFU_MAP[ziwei_idx]
    return {
        '紫微': ziwei_idx % 12,
        '天機': (ziwei_idx - 1) % 12,
        '太陽': (ziwei_idx - 3) % 12,
        '武曲': (ziwei_idx - 4) % 12,
        '天同': (ziwei_idx - 5) % 12,
        '廉貞': (ziwei_idx - 8) % 12,
        '天府': tf_idx % 12,
        '太陰': (tf_idx + 1) % 12,
        '貪狼': (tf_idx + 2) % 12,
        '巨門': (tf_idx + 3) % 12,
        '天相': (tf_idx + 4) % 12,
        '天梁': (tf_idx + 5) % 12,
        '七殺': (tf_idx + 6) % 12,
        '破軍': (tf_idx + 10) % 12,
    }


def _place_aux_stars(lunar_month: int, birth_hour_idx: int,
                     year_stem_idx: int, year_branch_idx: int) -> dict:
    """副星の配置 → {星名: 宮インデックス}"""
    stars = {}

    # 六吉星
    stars['左輔'] = (4 + lunar_month - 1) % 12
    stars['右弼'] = (10 - (lunar_month - 1)) % 12
    stars['文昌'] = (10 - birth_hour_idx) % 12
    stars['文曲'] = (4 + birth_hour_idx) % 12
    stars['天魁'] = TIANKUI_TABLE[year_stem_idx]
    stars['天鉞'] = TIANYUE_TABLE[year_stem_idx]

    # 禄存・擎羊・陀羅
    lucun = LUCUN_TABLE[year_stem_idx]
    stars['禄存'] = lucun
    stars['擎羊'] = (lucun + 1) % 12
    stars['陀羅'] = (lucun - 1) % 12

    # 火星・鈴星
    group = None
    for gname, indices in YEAR_BRANCH_GROUPS.items():
        if year_branch_idx in indices:
            group = gname
            break
    if group:
        fire_base, bell_base = FIRE_BELL_BASE[group]
        stars['火星'] = (fire_base + birth_hour_idx) % 12
        stars['鈴星'] = (bell_base + birth_hour_idx) % 12

    # 地空・地劫
    stars['地空'] = (11 - birth_hour_idx) % 12
    stars['地劫'] = (11 + birth_hour_idx) % 12

    return stars


def _get_sihua_assignments(year_stem_idx: int) -> dict:
    """四化の付与 → {星名: 四化名}"""
    table = SIHUA_TABLE[year_stem_idx]
    result = {}
    for hua_name, star_name in table.items():
        result[star_name] = hua_name
    return result


def _calc_da_xian(ming_gong_idx: int, year_stem_idx: int,
                  five_element_num: int, gender: str) -> tuple:
    """大限の計算 → (年齢リスト, 方向)"""
    is_yang_stem = (year_stem_idx % 2 == 0)

    if (gender == 'M' and is_yang_stem) or (gender == 'F' and not is_yang_stem):
        direction = '順行'
    else:
        direction = '逆行'

    F = five_element_num
    ages = []
    for i in range(12):
        start = F + i * 10
        end = start + 9
        ages.append((start, end))

    return ages, direction


# ========== メイン計算関数 ==========

def calculate_ziwei(person: PersonInput, gender: str = 'M') -> ZiweiResult:
    """
    紫微斗数の命盤を計算する
    person: PersonInput（birth_date必須、birth_time推奨）
    gender: 'M' or 'F'（大限の順逆に影響）
    """
    d = person.birth_date

    # Step 1: 農暦変換
    try:
        lunar = LunarDate.fromSolarDate(d.year, d.month, d.day)
        lunar_year = lunar.year
        lunar_month = lunar.month
        lunar_day = lunar.day
        is_leap = lunar.isLeapMonth
    except Exception:
        # 変換失敗時は近似値
        lunar_year = d.year
        lunar_month = d.month
        lunar_day = d.day
        is_leap = False

    # Step 2: 生時インデックス
    birth_hour_idx = _birth_time_to_hour_idx(person.birth_time)

    # Step 3: 年干支
    year_stem_idx = (d.year - 4) % 10
    year_branch_idx = (d.year - 4) % 12

    # Step 4: 命宮・身宮
    ming_gong_idx = _calc_ming_gong(lunar_month, birth_hour_idx)
    shen_gong_idx = _calc_shen_gong(lunar_month, birth_hour_idx)

    # Step 5: 宮の天干
    palace_stems = _get_palace_stems(year_stem_idx)

    # Step 6: 五行局
    ming_stem_idx = palace_stems.get(ming_gong_idx, 0)
    ming_kanshi = STEMS[ming_stem_idx] + BRANCHES[ming_gong_idx]
    five_element_num = _get_five_element(ming_kanshi)

    # Step 7: 紫微星配置
    ziwei_idx = _calc_ziwei_palace(lunar_day, five_element_num)

    # Step 8: 十四主星
    main_stars = _place_14_stars(ziwei_idx)

    # Step 9: 副星
    aux_stars = _place_aux_stars(lunar_month, birth_hour_idx,
                                year_stem_idx, year_branch_idx)

    # Step 10: 四化
    sihua = _get_sihua_assignments(year_stem_idx)

    # Step 11: 大限
    da_xian_ages, da_xian_dir = _calc_da_xian(
        ming_gong_idx, year_stem_idx, five_element_num, gender)

    # Step 12: 12宮を組み立て
    palaces = []
    for i in range(12):
        # 命宮から逆時計回り（地支インデックスを-1ずつ）
        branch_idx = (ming_gong_idx - i) % 12
        stem_idx = palace_stems.get(branch_idx, 0)

        # この宮にある主星
        p_main = [name for name, idx in main_stars.items() if idx == branch_idx]
        # この宮にある副星
        p_aux = [name for name, idx in aux_stars.items() if idx == branch_idx]
        # この宮の四化
        p_sihua = []
        for star in p_main + p_aux:
            if star in sihua:
                p_sihua.append(sihua[star])

        palaces.append(ZiweiPalace(
            branch=BRANCHES[branch_idx],
            branch_idx=branch_idx,
            stem=STEMS[stem_idx],
            palace_name=PALACE_NAMES[i],
            main_stars=p_main,
            aux_stars=p_aux,
            sihua=p_sihua,
        ))

    # 命宮の主星からキーワード生成
    ming_stars = [name for name, idx in main_stars.items() if idx == ming_gong_idx]
    keywords = []
    for star in ming_stars:
        if star in STAR_KEYWORDS:
            keywords.extend(STAR_KEYWORDS[star].split('・'))

    return ZiweiResult(
        lunar_year=lunar_year,
        lunar_month=lunar_month,
        lunar_day=lunar_day,
        is_leap_month=is_leap,
        birth_hour_name=HOUR_NAMES[birth_hour_idx],
        birth_hour_idx=birth_hour_idx,
        ming_gong_branch=BRANCHES[ming_gong_idx],
        ming_gong_idx=ming_gong_idx,
        shen_gong_branch=BRANCHES[shen_gong_idx],
        shen_gong_idx=shen_gong_idx,
        five_element_name=FIVE_ELEMENT_NAMES.get(five_element_num, f'局{five_element_num}'),
        five_element_num=five_element_num,
        year_stem=STEMS[year_stem_idx],
        year_stem_idx=year_stem_idx,
        year_branch=BRANCHES[year_branch_idx],
        year_branch_idx=year_branch_idx,
        palaces=palaces,
        sihua_assignments=sihua,
        da_xian_ages=da_xian_ages,
        da_xian_direction=da_xian_dir,
        ziwei_palace_idx=ziwei_idx,
        tianfu_palace_idx=TIANFU_MAP[ziwei_idx],
        keywords=keywords,
    )
