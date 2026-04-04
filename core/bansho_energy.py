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
    (181, 230, "安定キャリア型","バランスの良いエネルギー。組織内で着実に成長できる",
     "会社員・管理職コースが最も自然。"),
    (231, 250, "複数活動型",   "仕事だけではエネルギーが余る。複数のアウトレットが必要",
     "本業＋趣味＋社会活動の三本柱。"),
    (251, 300, "超活動型",     "常に動き続けないとエネルギーが暴走する帝王級",
     "経営者・複数事業・社会的リーダーが自然な生き方。"),
    (301, 999, "規格外型",     "歴史的人物クラスのエネルギー。波乱万丈が「普通」",
     "国や業界を動かすレベルの活動量が必要。"),
]

# ── 五本能の解釈テーブル ──
HONNOU_DETAIL = {
    "守備": {
        "gogyo": "木", "keyword": "守る・支える・コツコツ",
        "personality": "平和主義者。コツコツ積み重ね。奉仕の人。競争は苦手。",
        "career": "既存組織の維持・管理・公務員・事務職",
        "strong": "忍耐力・継続力・縁の下の力持ち",
        "weak": "変化に弱い・自己主張が苦手",
    },
    "表現": {
        "gogyo": "火", "keyword": "伝える・表現する・感性",
        "personality": "個性的で自己主張力がある。直感・洞察力に優れる。",
        "career": "音楽・芸術・料理・創作活動・講師・作家",
        "strong": "発信力・感性・直感",
        "weak": "気分屋・飽きっぽい・現実離れ",
    },
    "魅力": {
        "gogyo": "土", "keyword": "惹きつける・リーダー・カリスマ",
        "personality": "人を惹きつけるカリスマ性。自然とリーダーになる。",
        "career": "経営者・政治家・教室運営・コミュニティ運営",
        "strong": "人望・包容力・安定感",
        "weak": "頑固・変化を嫌う・保守的すぎる",
    },
    "攻撃": {
        "gogyo": "金", "keyword": "切り拓く・即行動・結果主義",
        "personality": "創業者タイプ。即行動。ダイナミック。じっとしていられない。",
        "career": "複数事業の展開・新規プロジェクト・営業・スポーツ",
        "strong": "行動力・決断力・突破力",
        "weak": "持久力不足・独断専行・短気",
    },
    "学習": {
        "gogyo": "水", "keyword": "学ぶ・分析する・知的",
        "personality": "学者肌。クールで知的。何かを作り上げる力。",
        "career": "研究者・学者・プログラマー・戦略家",
        "strong": "分析力・知性・創造力",
        "weak": "感情表現が苦手・理屈っぽい・孤立しがち",
    },
}


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
    }


def get_energy_percent(total: int) -> int:
    """エネルギー指数をパーセントに変換（範囲: 89〜401）"""
    lo, hi = 89, 401
    return max(0, min(100, int((total - lo) / (hi - lo) * 100)))
