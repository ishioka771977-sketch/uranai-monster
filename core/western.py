"""
西洋占星術エンジン（core/western.py）
生年月日 → 太陽星座（+ 出生時刻あれば全天体・ASC・MC・ハウス・アスペクト）
"""
import math
from datetime import date, datetime, timedelta
from typing import Optional, List

try:
    import ephem
    EPHEM_AVAILABLE = True
except ImportError:
    EPHEM_AVAILABLE = False

from .models import PersonInput, WesternResult, PlanetPosition, AspectInfo


# 12星座定義
SIGNS = ["牡羊座", "牡牛座", "双子座", "蟹座", "獅子座", "乙女座",
         "天秤座", "蠍座", "射手座", "山羊座", "水瓶座", "魚座"]
SYMBOLS = ["♈", "♉", "♊", "♋", "♌", "♍", "♎", "♏", "♐", "♑", "♒", "♓"]
ELEMENTS = ["火", "地", "風", "水", "火", "地", "風", "水", "火", "地", "風", "水"]
QUALITIES = ["活動宮", "不動宮", "柔軟宮", "活動宮", "不動宮", "柔軟宮",
             "活動宮", "不動宮", "柔軟宮", "活動宮", "不動宮", "柔軟宮"]

# 太陽星座テーブル（ephem不使用時のフォールバック）
SUN_SIGN_TABLE = [
    (3, 21, 4, 19, "牡羊座", "♈", "火", "活動宮"),
    (4, 20, 5, 20, "牡牛座", "♉", "地", "不動宮"),
    (5, 21, 6, 21, "双子座", "♊", "風", "柔軟宮"),
    (6, 22, 7, 22, "蟹座", "♋", "水", "活動宮"),
    (7, 23, 8, 22, "獅子座", "♌", "火", "不動宮"),
    (8, 23, 9, 22, "乙女座", "♍", "地", "柔軟宮"),
    (9, 23, 10, 23, "天秤座", "♎", "風", "活動宮"),
    (10, 24, 11, 22, "蠍座", "♏", "水", "不動宮"),
    (11, 23, 12, 21, "射手座", "♐", "火", "柔軟宮"),
    (12, 22, 1, 19, "山羊座", "♑", "地", "活動宮"),
    (1, 20, 2, 18, "水瓶座", "♒", "風", "不動宮"),
    (2, 19, 3, 20, "魚座", "♓", "水", "柔軟宮"),
]

SUN_SIGN_KEYWORDS = {
    "牡羊座": ["情熱的", "行動力がある", "リーダーシップ", "直感的", "勇敢"],
    "牡牛座": ["安定を愛する", "五感が鋭い", "粘り強い", "美的センスがある", "信頼できる"],
    "双子座": ["知的好奇心旺盛", "コミュニケーション上手", "多才", "機転が利く", "話し上手"],
    "蟹座": ["感受性が豊か", "家族・仲間思い", "直感が鋭い", "守護本能がある", "包容力がある"],
    "獅子座": ["自己表現が得意", "カリスマ性がある", "情熱的", "心が広い", "目立つ存在"],
    "乙女座": ["完璧主義", "分析力がある", "細かいことに気が付く", "誠実", "実用的"],
    "天秤座": ["バランス感覚がある", "審美眼がある", "協調性がある", "正義感が強い", "エレガント"],
    "蠍座": ["洞察力が鋭い", "情熱的", "神秘的", "集中力が高い", "変容の力がある"],
    "射手座": ["自由を愛する", "楽観的", "哲学的思考", "冒険心がある", "正直"],
    "山羊座": ["責任感が強い", "粘り強い", "現実的", "向上心がある", "信頼できる"],
    "水瓶座": ["独創的", "人道主義", "革新的", "客観的", "自由な発想"],
    "魚座": ["感受性が豊か", "共感力が高い", "直感的", "芸術的センス", "スピリチュアル"],
}


def _lon_to_sign(lon_deg: float) -> tuple:
    """黄経度数 → 星座情報"""
    sign_idx = int(lon_deg // 30) % 12
    return SIGNS[sign_idx], SYMBOLS[sign_idx], ELEMENTS[sign_idx], QUALITIES[sign_idx]


def _get_sun_sign(birth_date: date) -> tuple:
    """太陽星座を日付テーブルで判定（フォールバック用）"""
    m, d = birth_date.month, birth_date.day
    for sm, sd, em, ed, name, symbol, element, quality in SUN_SIGN_TABLE:
        if sm > em:
            if (m == sm and d >= sd) or (m == em and d <= ed):
                return name, symbol, element, quality
        else:
            if (m == sm and d >= sd) or (m == em and d <= ed) or (sm < m < em):
                return name, symbol, element, quality
    return "山羊座", "♑", "地", "活動宮"


# ============================================================
# 出生地 → 緯度経度マッピング
# ============================================================
CITY_COORDS = {
    "東京": ("35.6762", "139.6503"),
    "函館": ("41.7688", "140.7290"),
    "函館市": ("41.7688", "140.7290"),
    "札幌": ("43.0621", "141.3544"),
    "大阪": ("34.6937", "135.5023"),
    "名古屋": ("35.1815", "136.9066"),
    "福岡": ("33.5904", "130.4017"),
    "仙台": ("38.2682", "140.8694"),
    "広島": ("34.3853", "132.4553"),
    "京都": ("35.0116", "135.7681"),
    "横浜": ("35.4437", "139.6380"),
    "神戸": ("34.6901", "135.1956"),
    "北九州": ("33.8834", "130.8752"),
    "新潟": ("37.9026", "139.0236"),
    "松前": ("41.4306", "140.1097"),
    "福島町": ("41.4828", "140.2508"),
}


def _resolve_coords(birth_place: Optional[str]) -> tuple:
    """出生地名から緯度経度を解決。不明なら東京デフォルト。"""
    if not birth_place:
        return "35.6762", "139.6503"
    for city, coords in CITY_COORDS.items():
        if city in birth_place:
            return coords
    return "35.6762", "139.6503"


# ============================================================
# ephem を使った天体計算
# ============================================================
def _create_observer(birth_date: date, birth_time: Optional[str] = None,
                     lat: str = "35.6762", lon: str = "139.6503") -> 'ephem.Observer':
    """ephem Observer を作成（JST→UTC変換込み）"""
    obs = ephem.Observer()
    obs.lat = lat
    obs.lon = lon
    obs.pressure = 0

    if birth_time:
        # 全角コロン・全角数字にも対応
        bt = birth_time.replace("：", ":").replace("　", " ").strip()
        # 全角数字→半角数字
        bt = bt.translate(str.maketrans("０１２３４５６７８９", "0123456789"))
        h, mi = map(int, bt.split(":"))
        jst_dt = datetime(birth_date.year, birth_date.month, birth_date.day, h, mi)
        utc_dt = jst_dt - timedelta(hours=9)
    else:
        # 出生時刻なし → 正午UTC（日本時間21時）で近似
        utc_dt = datetime(birth_date.year, birth_date.month, birth_date.day, 12, 0)

    obs.date = f"{utc_dt.year}/{utc_dt.month}/{utc_dt.day} {utc_dt.hour:02d}:{utc_dt.minute:02d}:00"
    return obs


def _calc_planet_position(body, obs, name: str) -> PlanetPosition:
    """天体の黄経位置を計算"""
    body.compute(obs)
    ecl = ephem.Ecliptic(body, epoch=obs.date)
    lon_deg = math.degrees(ecl.lon) % 360
    sign, symbol, element, quality = _lon_to_sign(lon_deg)

    # 逆行チェック（火星〜冥王星のみ）
    is_retro = False
    if hasattr(body, 'earth_distance'):
        # 簡易逆行チェック: 前日と比較して黄経が減少していれば逆行
        try:
            obs_prev = ephem.Observer()
            obs_prev.lat = obs.lat
            obs_prev.lon = obs.lon
            obs_prev.pressure = 0
            obs_prev.date = obs.date - 1
            body.compute(obs_prev)
            ecl_prev = ephem.Ecliptic(body, epoch=obs_prev.date)
            lon_prev = math.degrees(ecl_prev.lon) % 360
            # 黄経が減少（逆行）: ただし360°→0°の境界を考慮
            diff = lon_deg - lon_prev
            if diff < -180:
                diff += 360
            elif diff > 180:
                diff -= 360
            is_retro = diff < 0
        except Exception:
            pass

    return PlanetPosition(
        name=name,
        sign=sign,
        sign_symbol=symbol,
        degree=round(lon_deg, 2),
        is_retrograde=is_retro,
    )


def _calc_all_planets(obs) -> List[PlanetPosition]:
    """全天体の位置を計算"""
    planet_bodies = [
        (ephem.Sun(), "太陽"),
        (ephem.Moon(), "月"),
        (ephem.Mercury(), "水星"),
        (ephem.Venus(), "金星"),
        (ephem.Mars(), "火星"),
        (ephem.Jupiter(), "木星"),
        (ephem.Saturn(), "土星"),
        (ephem.Uranus(), "天王星"),
        (ephem.Neptune(), "海王星"),
        (ephem.Pluto(), "冥王星"),
    ]

    planets = []
    for body, name in planet_bodies:
        try:
            pos = _calc_planet_position(body, obs, name)
            planets.append(pos)
        except Exception as e:
            print(f"[西洋占星術] {name} 計算エラー: {e}")

    return planets


def _calc_asc_mc(obs) -> tuple:
    """
    ASC（上昇点）とMC（天頂）を正確に計算
    ephem の黄道座標変換を使用し、地平線と黄道の交点を精密検索
    """
    try:
        lst = float(obs.sidereal_time())  # ラジアン（ローカル恒星時）
        lat = float(obs.lat)

        # MC: RAMC（=LST）を赤道座標→黄道座標に変換
        mc_eq = ephem.Equatorial(obs.sidereal_time(), 0, epoch=obs.date)
        mc_ecl = ephem.Ecliptic(mc_eq, epoch=obs.date)
        mc_lon = math.degrees(float(mc_ecl.lon)) % 360

        # ASC: 黄道上で東の地平線（高度=0、東側）にある点を精密検索
        # ステップ1: 粗い検索（1°刻み）
        best_lon = 0.0
        best_alt = 999.0
        for deg in range(360):
            test_lon = float(deg)
            ecl = ephem.Ecliptic(math.radians(test_lon), 0, epoch=obs.date)
            eq = ephem.Equatorial(ecl, epoch=obs.date)
            ha = lst - float(eq.ra)
            alt = math.degrees(math.asin(
                math.sin(float(eq.dec)) * math.sin(lat) +
                math.cos(float(eq.dec)) * math.cos(lat) * math.cos(ha)
            ))
            # 東側（ha < 0 → 昇っている天体）かつ高度が0に最も近い点
            if math.sin(ha) < 0 and abs(alt) < abs(best_alt):
                best_alt = alt
                best_lon = test_lon

        # ステップ2: 精密検索（0.01°刻み、±2°範囲）
        search_start = best_lon - 2.0
        search_end = best_lon + 2.0
        best_alt = 999.0
        for deg100 in range(int(search_start * 100), int(search_end * 100)):
            test_lon = deg100 * 0.01
            ecl = ephem.Ecliptic(math.radians(test_lon), 0, epoch=obs.date)
            eq = ephem.Equatorial(ecl, epoch=obs.date)
            ha = lst - float(eq.ra)
            alt = math.degrees(math.asin(
                math.sin(float(eq.dec)) * math.sin(lat) +
                math.cos(float(eq.dec)) * math.cos(lat) * math.cos(ha)
            ))
            if math.sin(ha) < 0 and abs(alt) < abs(best_alt):
                best_alt = alt
                best_lon = test_lon % 360

        asc_lon = best_lon % 360

        asc_sign, _, _, _ = _lon_to_sign(asc_lon)
        mc_sign, _, _, _ = _lon_to_sign(mc_lon)

        return asc_sign, mc_sign, asc_lon, mc_lon
    except Exception as e:
        print(f"[西洋占星術] ASC/MC計算エラー: {e}")
        return None, None, None, None


def _calc_sda(dec: float, lat: float) -> float:
    """半日弧（Semi-Diurnal Arc）を計算"""
    x = -math.tan(lat) * math.tan(dec)
    if x < -1:
        return math.pi  # 沈まない（白夜）
    if x > 1:
        return 0.0      # 昇らない（極夜）
    return math.acos(x)


def _find_placidus_cusp(ramc: float, lat: float, epsilon: float, cusp_num: int) -> float:
    """
    プラシーダス・ハウスカスプを反復法で計算
    cusp_num: 2, 3, 11, 12 のいずれか
    時角(H)と半日弧(SDA)/半夜弧(SNA)の比で黄経を求める
    """
    # 初期推定値
    offsets = {11: 0.3, 12: 0.7, 2: 1.5, 3: 2.0}
    lon = ramc + offsets.get(cusp_num, 1.0)

    for _ in range(100):
        # 黄経→赤緯
        dec = math.asin(math.sin(epsilon) * math.sin(lon))
        sda = _calc_sda(dec, lat)
        sna = math.pi - sda

        # 各カスプの目標赤経
        if cusp_num == 11:
            target_ra = ramc + sda / 3
        elif cusp_num == 12:
            target_ra = ramc + 2 * sda / 3
        elif cusp_num == 2:
            target_ra = ramc + sda + sna / 3
        elif cusp_num == 3:
            target_ra = ramc + sda + 2 * sna / 3
        else:
            return 0.0

        # 目標赤経→黄経に変換
        new_lon = math.atan2(math.sin(target_ra),
                             math.cos(target_ra) * math.cos(epsilon))
        if new_lon < 0:
            new_lon += 2 * math.pi

        # 象限補正
        target_norm = target_ra % (2 * math.pi)
        if (target_norm > math.pi / 2 and target_norm < 3 * math.pi / 2):
            if new_lon < math.pi / 2 or new_lon > 3 * math.pi / 2:
                new_lon = (new_lon + math.pi) % (2 * math.pi)
        else:
            if new_lon > math.pi / 2 and new_lon < 3 * math.pi / 2:
                new_lon = (new_lon + math.pi) % (2 * math.pi)

        if abs(new_lon - lon) < 1e-10:
            break
        lon = new_lon

    return math.degrees(lon) % 360


def _calc_placidus_cusps(obs, asc_lon: float, mc_lon: float) -> List[float]:
    """
    プラシーダス・ハウスカスプを計算（全12ハウス）
    Astro.com（Swiss Ephemeris）と一致する精度
    """
    cusps = [0.0] * 13  # cusps[1]〜cusps[12]
    cusps[1] = asc_lon
    cusps[4] = (mc_lon + 180) % 360  # IC
    cusps[7] = (asc_lon + 180) % 360  # DSC
    cusps[10] = mc_lon

    ramc = float(obs.sidereal_time())
    lat = float(obs.lat)
    epsilon = math.radians(23.4393)

    # 中間カスプ（2, 3, 11, 12）を反復法で計算
    cusps[11] = _find_placidus_cusp(ramc, lat, epsilon, 11)
    cusps[12] = _find_placidus_cusp(ramc, lat, epsilon, 12)
    cusps[2] = _find_placidus_cusp(ramc, lat, epsilon, 2)
    cusps[3] = _find_placidus_cusp(ramc, lat, epsilon, 3)

    # 対向ハウス（+180°）
    cusps[5] = (cusps[11] + 180) % 360
    cusps[6] = (cusps[12] + 180) % 360
    cusps[8] = (cusps[2] + 180) % 360
    cusps[9] = (cusps[3] + 180) % 360

    return cusps


def _assign_houses(planets: List[PlanetPosition], cusps: List[float]) -> List[PlanetPosition]:
    """天体にハウスを割り当て（プラシーダス・ハウスカスプ基準）"""
    if not cusps or len(cusps) < 13:
        return planets

    for p in planets:
        # 各天体がどのハウスカスプ間にあるかを判定
        assigned = False
        for h in range(1, 13):
            next_h = h + 1 if h < 12 else 1
            cusp_start = cusps[h]
            cusp_end = cusps[next_h]

            # 黄経の循環を考慮
            if cusp_start <= cusp_end:
                if cusp_start <= p.degree < cusp_end:
                    p.house = h
                    assigned = True
                    break
            else:  # 360°をまたぐ場合
                if p.degree >= cusp_start or p.degree < cusp_end:
                    p.house = h
                    assigned = True
                    break

        if not assigned:
            # フォールバック: 等分ハウス
            house_offset = (p.degree - cusps[1]) % 360
            p.house = int(house_offset // 30) + 1

    return planets


# ============================================================
# アスペクト計算
# ============================================================
ASPECT_TYPES = [
    ("合", 0, 8),
    ("オポジション", 180, 8),
    ("スクエア", 90, 7),
    ("トライン", 120, 8),
    ("セクスタイル", 60, 6),
]


def _calc_aspects(planets: List[PlanetPosition]) -> List[AspectInfo]:
    """天体間のアスペクトを検出"""
    aspects = []

    for i in range(len(planets)):
        for j in range(i + 1, len(planets)):
            p1 = planets[i]
            p2 = planets[j]

            # 角度差
            diff = abs(p1.degree - p2.degree)
            if diff > 180:
                diff = 360 - diff

            for aspect_name, target_angle, max_orb in ASPECT_TYPES:
                orb = abs(diff - target_angle)
                # 太陽・月が絡む場合はオーブを広めに（+2°）
                effective_orb = max_orb
                if p1.name in ("太陽", "月") or p2.name in ("太陽", "月"):
                    effective_orb = max_orb + 2

                if orb <= effective_orb:
                    aspects.append(AspectInfo(
                        planet1=p1.name,
                        planet2=p2.name,
                        aspect_type=aspect_name,
                        orb=round(orb, 1),
                    ))
                    break  # 一つのペアに対して最も正確なアスペクトのみ

    return aspects


# ============================================================
# メイン計算関数
# ============================================================
def calculate_western(person: PersonInput) -> WesternResult:
    """
    生年月日 → 西洋占星術の全データを計算
    出生時刻あり → 全天体・ASC・MC・ハウス・アスペクト
    出生時刻なし → 全天体・アスペクト（ハウスなし、月は近似）
    """
    d = person.birth_date

    if not EPHEM_AVAILABLE:
        # ephem なし → テーブルベースの太陽星座のみ
        sun_sign, symbol, element, quality = _get_sun_sign(d)
        keywords = SUN_SIGN_KEYWORDS.get(sun_sign, [])
        return WesternResult(
            sun_sign=sun_sign,
            sun_sign_symbol=symbol,
            sun_element=element,
            sun_quality=quality,
            keywords=keywords[:5],
        )

    # ephem あり → 全天体計算
    has_time = person.birth_time is not None
    lat, lon = _resolve_coords(person.birth_place)
    obs = _create_observer(d, person.birth_time, lat=lat, lon=lon)

    # 全天体の位置
    planets = _calc_all_planets(obs)

    # 太陽星座（planetsから取得）
    sun_planet = next((p for p in planets if p.name == "太陽"), None)
    if sun_planet:
        sun_sign = sun_planet.sign
        sun_symbol = sun_planet.sign_symbol
        sun_element = ELEMENTS[SIGNS.index(sun_sign)]
        sun_quality = QUALITIES[SIGNS.index(sun_sign)]
    else:
        sun_sign, sun_symbol, sun_element, sun_quality = _get_sun_sign(d)

    # 月星座
    moon_planet = next((p for p in planets if p.name == "月"), None)
    moon_sign = moon_planet.sign if moon_planet else None

    # ASC/MC（出生時刻ありの場合のみ）
    asc_sign = None
    mc_sign = None
    if has_time:
        asc_sign, mc_sign, asc_lon, mc_lon = _calc_asc_mc(obs)
        cusps = _calc_placidus_cusps(obs, asc_lon, mc_lon)
        planets = _assign_houses(planets, cusps)

    # アスペクト
    aspects = _calc_aspects(planets)

    keywords = SUN_SIGN_KEYWORDS.get(sun_sign, [])

    return WesternResult(
        sun_sign=sun_sign,
        sun_sign_symbol=sun_symbol,
        sun_element=sun_element,
        sun_quality=sun_quality,
        moon_sign=moon_sign,
        asc_sign=asc_sign,
        mc_sign=mc_sign,
        keywords=keywords[:5],
        planets=planets,
        aspects=aspects,
        has_full_chart=has_time,
    )
