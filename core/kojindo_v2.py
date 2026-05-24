"""
古神道占い v2 - 動的マッチングエンジン
core/kojindo_v2.py

7流派の鑑定結果から特徴タグを抽出し、物語ストックから最適な3-5本を
タグ一致でフィルタリングし、神社推薦も組み立てる。

設計: くろたん「古神道v2 3層構造設計相談」(2026-05-10)
       くろたん「設計修正指示_流派名非表示」(2026-05-10) — ★最重要
       くろたん「v2再設計書_動的マッチング」(2026-05-10)

設計の核心ルール:
- 鑑定文に占術名・占術用語を一切出さない（算命学・牽牛星・用神・天中殺・六龍 等）
- 7流派の特性は「行動・思考・身体感覚」に変換して AI に渡す
- 5本の物語が1人の中で重なる構造（守護神1柱に重ねない）
- 6龍タイプ・メタ軸は内部ロジックとして保持・UIには出さない
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional

from .models import DivinationBundle
from .kojindo_repo import (
    StoryRepo, ShrineRepo, Story, Shrine,
    get_story_repo, get_shrine_repo,
    load_god, GOD_NAME_TO_ID,
)
from .kojindo import calculate_kojindo, KojinDoResult  # v1 計算結果（背骨）


# ============================================================
# タグ → 体感説明マップ（くろたん『設計修正指示』TRAIT_TRANSLATIONS 準拠）
# 鑑定文に占術名を出さないため、特徴タグを「行動・思考・身体感覚」に翻訳して
# AI に渡す。AI はこの体感説明を本文に流用する。
# ============================================================
TRAIT_SENSATION_MAP = {
    # === 中央星（内部のみ・これが最も占術臭が強い） ===
    # → 行動パターンに完全変換
    "中央星=貫索星": "一人で立つことに誇りを持つ人。壁を作るのが得意だが、壁の中は温かい",
    "中央星=石門星": "人が集まる中心にいる人。チームの真ん中で呼吸する",
    "中央星=鳳閣星": "楽しむことが仕事。深刻を笑いに変える天性がある",
    "中央星=調舒星": "繊細で完璧主義。壊しながら作る。孤独な時間が創造の燃料",
    "中央星=禄存星": "与えることで存在を確認する人。人が集まる磁場を持っている",
    "中央星=司禄星": "守る人。蓄える人。派手さはないが、いなくなると全部が止まる",
    "中央星=車騎星": "考える前に手が出る人。走りながら考える。傷は勲章より早い",
    "中央星=牽牛星": "名誉とプライドで動く人。鎧を着て生きる。脱ぐ練習が人生の課題",
    "中央星=龍高星": "知らないものに出会った瞬間だけ心拍が上がる人。放浪が栄養",
    "中央星=玉堂星": "答えを知ってから動く人。遅いが正確。本棚が人生の地図",

    # === エネルギー量（万象学） ===
    "規格外エネルギー": "止まると壊れるエンジンを積んでいる。3つのチャンネルで燃やし続ける必要がある",
    "高エネルギー": "余力があるエンジン。組織の中で突出するが暴走はしない",
    "中エネルギー": "標準的な排気量。組織と相性が良い。穏やかに長く走る設計",
    "省エネ型": "少ない燃料で遠くまで行ける。無駄遣い厳禁。深く狭く掘る人",

    # === 五行偏り ===
    "火過多": "宝石に火入れしている人。輝きが増す代わりに、水で冷やさないと焦げる",
    "水過多": "感情と知性が満ちすぎている。流れを作らないと淀む",
    "木過多": "伸びる力が強すぎる。剪定しないと折れる方向に伸びる",
    "金過多": "硬すぎる。磨く・削る・研ぐを続けないと錆びる",
    "土過多": "重すぎる。動かす力（風と水）を意識的に入れないと沈む",
    "水不足": "水辺に行くと呼吸が楽になる人。学ぶこと・流れる時間が最大の充電",
    "火不足": "表現の場を作らないと冷えていく人。誰かの前で話す時間が薬",

    # === 性質・本能 ===
    "名誉型": "名前で呼ばれるより肩書きで呼ばれるほうが楽。席を立つ時は誰よりも先に立ち、座る時は最後に座る",
    "表現型": "黙っていると毒になる人。話す・書く・演じる場が必要",
    "組織型": "枠がある中で力を発揮する人。完全な自由は逆に苦手",

    # === 構造タグ ===
    "破壊と再生": "壊した分だけ建てる人。一度更地にしないと次が建たない",
    "継承の物語": "受け取って渡す役回り。自分が主役じゃないことに、本人は気づきにくい",
    "放浪の物語": "知らない道に足を伸ばすことが命の更新。同じ場所に長くいると萎む",
    "単騎の戦い": "一人で決めて一人で動く方が結果が出る人。会議より現場",
    "連合の物語": "仲間がいて初めて自分が立つ人。一人だと細る",
    "毒→薬の変換": "困難をプレゼントに変える特技がある。一度毒を喰った経験が薬に変わっている",

    # === フェーズ ===
    "修行期": "20代後半〜30代前半。社会という暗い室で、本当の道具を渡される時期",
    "国造り期": "30代後半〜40代後半。半身となる相棒を得て、土地を耕し始める時期",
    "国譲り準備期": "40代後半〜50代半ば。建てた城の窓から、次の主が見え始めている",
    "国譲り期": "50代半ば〜60代半ば。握っていたものを渡す稽古が本格化する",
    "収穫期": "実りが見え始めている。撒いた種があちこちで芽を出している",
    "反抗期": "10代後半〜20代前半。既存の秩序を壊して、自分の物差しを作る時期",
}


def traits_to_sensations(traits: list[str]) -> list[tuple[str, str]]:
    """特徴タグ → (タグ, 体感説明) のリストに変換。
    占術名を一切出さず、行動・思考・身体感覚で語る。
    """
    out = []
    seen_sensations = set()
    for t in traits:
        sense = TRAIT_SENSATION_MAP.get(t)
        if sense and sense not in seen_sensations:
            out.append((t, sense))
            seen_sensations.add(sense)
    return out


def extract_internal_traits(bundle: DivinationBundle) -> list[str]:
    """体感説明を引くための「内部用」拡張タグ。
    extract_traits() の出力（マッチング用26タグ）に、中央星等の細かいタグも追加。
    これは ai/interpreter.py の体感変換にだけ使い、StoryRepo.filter には使わない。
    """
    s = bundle.sanmei
    base_traits = extract_traits(bundle)
    extra: list[str] = []

    # 中央星タグ（内部用・体感変換のため）
    if s.chuo_sei:
        extra.append(f"中央星={s.chuo_sei}")

    # （将来: 用神・ASC・本命星等を追加可能）

    return base_traits + extra


# ============================================================
# v2 拡張結果データ
# ============================================================
@dataclass
class GodDeepDiveResult:
    """v2.5 深掘り型: 1柱の神の中から命式タグで選んだエピソード群と付帯情報"""
    god_id: str
    god_name: str
    god_reading: str
    god_summary: str
    selected_episodes: list[dict] = field(default_factory=list)   # 2-3本（user-facing fields のみ）
    light_shadows: list[dict] = field(default_factory=list)       # 選ばれたエピソードに対応する光影対
    related_gods_in_episodes: list[dict] = field(default_factory=list)  # 選ばれたエピソードに登場する関係神
    recommended_shrine: Optional[dict] = None                     # 1社（選ばれたエピソードに最も紐づく）
    life_phase_for_age: Optional[dict] = None                     # 現年齢に対応する神のフェーズ
    match_tags: list[str] = field(default_factory=list)           # 内部マッチに使った深掘り用タグ（デバッグ）


@dataclass
class KojinDoV2Result:
    """v2 = v1 結果 + 動的マッチング結果
    v2.5 (2026-05-24): god_deep を追加。1柱の神のデータが gods/{id}.json に
    あれば god_deep に深掘り結果を入れる（無ければ None で旧来の3本型）。
    """
    v1: KojinDoResult                                    # v1 の守護神（背骨）
    traits: list[str] = field(default_factory=list)      # 抽出された特徴タグ
    candidate_stories: list[Story] = field(default_factory=list)  # マッチ候補（10-15本・3本型用）
    recommended_shrines: list[Shrine] = field(default_factory=list)  # 推薦神社（3本型用）
    god_deep: Optional[GodDeepDiveResult] = None         # v2.5 深掘り結果（守護神JSONがある時のみ）


# ============================================================
# Step 1: 7流派 → 特徴タグ抽出
# ============================================================
def extract_traits(bundle: DivinationBundle) -> list[str]:
    """7流派の bundle から特徴タグを抽出する（Python ルールベース）

    Q3回答に従い、AI 呼び出しなしで純 Python ロジック。
    タグは tag_dictionary.json v1.5-final（26個）に厳密準拠する。
    """
    traits: set[str] = set()
    s = bundle.sanmei

    # === 五行偏りタグ（比率・40%以上=過多、10%以下=不足）===
    # 2026-05-17 バグ修正: s.gogyo_balance は個数（命式の五行カウント、
    # 合計6〜8程度）を返す。旧コードは「40%以上/10%以下」のパーセント前提で
    # 生値比較していたため、過多は永久に発火せず（個数は最大8）、
    # 不足は全員に発火していた（個数は常に10以下）。
    # → ひでさん命式（火=4 = 三巳格＋火4つ）で「火不足」と真逆判定。
    # 合計で正規化して比率(%)で判定する。個数辞書でもパーセント辞書でも
    # 正しく動く（パーセント辞書なら合計≒100で比率は元値とほぼ等価）。
    g = s.gogyo_balance or {}
    _total = sum(v for v in g.values() if isinstance(v, (int, float)))
    if _total > 0:
        for element in ("木", "火", "土", "金", "水"):
            pct = g.get(element, 0) / _total * 100
            if pct >= 40:
                traits.add(f"{element}過多")
        # 不足は重要な「火不足」「水不足」のみ採用（タグ辞書準拠）
        if g.get("水", 0) / _total * 100 <= 10:
            traits.add("水不足")
        if g.get("火", 0) / _total * 100 <= 10:
            traits.add("火不足")

    # === 万象学エネルギータグ（quantity・4段階）===
    e = s.bansho_energy
    if e:
        en = e.total_energy
        if en >= 300:
            traits.add("規格外エネルギー")
        elif en >= 230:
            traits.add("高エネルギー")
        elif en >= 180:
            traits.add("中エネルギー")
        else:
            traits.add("省エネ型")

    # === 構造タグ・性質タグ（中央星と本能から導出）===
    chuo = s.chuo_sei or ""
    # 名誉型: 中心星=牽牛星 or 攻撃本能（陰金）最高
    if chuo == "牽牛星":
        traits.add("名誉型")
    # 表現型: 中心星=鳳閣星/調舒星 or 表現本能最高
    if chuo in ("鳳閣星", "調舒星"):
        traits.add("表現型")
    # 組織型: 守備系・安定系
    if chuo in ("牽牛星", "鳳閣星", "司禄星", "玉堂星", "石門星"):
        traits.add("組織型")
    # 単騎の戦い: 攻撃陽金・不動
    if chuo in ("車騎星", "貫索星"):
        traits.add("単騎の戦い")
    # 破壊と再生: 調舒星
    if chuo == "調舒星":
        traits.add("破壊と再生")
    # 継承の物語: 司禄星・玉堂星
    if chuo in ("司禄星", "玉堂星"):
        traits.add("継承の物語")
    # 連合の物語: 石門星・禄存星
    if chuo in ("石門星", "禄存星"):
        traits.add("連合の物語")
    # 放浪の物語: 龍高星・調舒星
    if chuo in ("龍高星", "調舒星"):
        traits.add("放浪の物語")

    # === 万象学本能から表現型・名誉型を補完 ===
    if e and e.honnou_ranking:
        top_h = e.honnou_ranking[0][0]
        if "攻撃" in top_h:
            traits.add("名誉型")
        if "表現" in top_h:
            traits.add("表現型")
        if "守備" in top_h:
            traits.add("組織型")

    # === 状態・フェーズタグ（年齢×フェーズ）===
    v1 = calculate_kojindo(s, bundle.person)
    phase_to_state = {
        "反抗と試練": "反抗期",
        "修行期": "修行期",
        "国造り": "国造り期",
        "収穫と完成": "収穫期",
        "国譲り": "国譲り期",
    }
    # 48-56は「国譲り準備期」も併記（重要フェーズ）
    if v1.phase_name == "収穫と完成":
        traits.add("収穫期")
        traits.add("国譲り準備期")
    else:
        state_tag = phase_to_state.get(v1.phase_name)
        if state_tag:
            traits.add(state_tag)

    return sorted(traits)


# ============================================================
# Step 2-3: マッチングと神社推薦
# ============================================================
def filter_stories(traits: list[str], limit: int = 12,
                   story_repo: Optional[StoryRepo] = None) -> list[Story]:
    """タグ一致でストーリー候補を絞る（Q2回答: 案A タグ一致）"""
    repo = story_repo or get_story_repo()
    return repo.filter_by_traits(traits, limit=limit)


def recommend_shrines(stories: list[Story], v1: KojinDoResult,
                      shrine_repo: Optional[ShrineRepo] = None) -> list[Shrine]:
    """選ばれた物語に紐づく神社 + v1守護神の神社 を推薦"""
    repo = shrine_repo or get_shrine_repo()
    shrine_ids = []
    seen = set()

    # 1) 物語に紐づく神社
    for st in stories:
        if st.shrine_id and st.shrine_id not in seen:
            shrine_ids.append(st.shrine_id)
            seen.add(st.shrine_id)

    # 2) v1 守護神に紐づく神社（祭神検索）
    if v1.god_name:
        for shr in repo.find_by_deity(v1.god_name):
            if shr.id not in seen:
                shrine_ids.append(shr.id)
                seen.add(shr.id)

    return [repo.get(sid) for sid in shrine_ids if repo.get(sid) is not None]


# ============================================================
# v2.5 深掘り型: 1柱の神のJSON データから命式に合うエピソードを選ぶ
# 設計: 古神道占い_v2.5_深掘り型_再設計書_20260524.md
# ============================================================

# 中央星 (raw) と Deep Research の生語彙の両方を出して、両方向のマッチを
# 取りやすくする。extract_traits の体感寄りタグ（名誉型・組織型・規格外
# エネルギー 等）も合算する。
def extract_god_match_tags(bundle: DivinationBundle) -> list[str]:
    """v2.5 深掘り型のエピソード選定に使う、Deep Research語彙寄りのタグ群。
    extract_traits の体感タグも内側に取り込む（両方の語彙でマッチさせる）。
    """
    tags: set[str] = set(extract_traits(bundle))  # 既存の体感タグも内包
    s = bundle.sanmei

    # === 中心星（raw）===
    if s.chuo_sei:
        tags.add(s.chuo_sei)
    # 西/北/南/東の星も加える（Deep Researchで「印星過多」等は別軸だが
    # 単星マッチ用に出しておく）
    for star in (s.nishi_sei, s.kita_sei, s.minami_sei, s.higashi_sei):
        if star:
            tags.add(star)

    # === 特殊格局 ===
    if s.kakkyoku:
        tags.add(s.kakkyoku)  # 例: "三巳格"

    # === 五行 raw 名（既存の "{el}過多"/"水不足"/"火不足" に加え、
    #     "用神{el}不足" の Deep Research 表記も付ける）===
    g = s.gogyo_balance or {}
    total = sum(v for v in g.values() if isinstance(v, (int, float)))
    if total > 0:
        for el in ("木", "火", "土", "金", "水"):
            pct = g.get(el, 0) / total * 100
            if pct <= 10 and el in ("水", "火"):
                tags.add(f"用神{el}不足")

    # === 数秘 ライフパス（使命・影 両方を出して、エピソード側のどちらでも拾える）===
    lp = bundle.numerology.life_path
    if isinstance(lp, int):
        tags.add(f"LP{lp}使命")
        tags.add(f"LP{lp}の影")
        # マスター数 11/22/33 は還元数（2/4/6）でも一致させる
        reduce_map = {11: 2, 22: 4, 33: 6}
        if lp in reduce_map:
            r = reduce_map[lp]
            tags.add(f"LP{r}使命")
            tags.add(f"LP{r}の影")

    # === 紫微斗数: 化忌の宮・命宮の主星・四化付き星 ===
    z = bundle.ziwei
    if z is not None:
        # 化忌の宮 → "化忌{palace_name}"
        for pal in (z.palaces or []):
            for h in (pal.sihua or []):
                if "忌" in h and pal.palace_name:
                    tags.add(f"化忌{pal.palace_name}")
        # 命宮の主星 → 単星 ＋ 独坐タグ ＋ 即位/受領
        for pal in (z.palaces or []):
            if pal.palace_name == "命宮":
                mains = pal.main_stars or []
                for st_name in mains:
                    tags.add(st_name)  # 例: "貪狼", "紫微", "七殺"
                if len(mains) == 1:
                    tags.add(f"{mains[0]}独坐")
                if "紫微" in mains:
                    tags.add("紫微即位")
                if "天府" in mains:
                    tags.add("天府受領")
                break
        # 四化: sihua_assignments {星: 化xx}
        for star_name, hua in (z.sihua_assignments or {}).items():
            tags.add(f"{star_name}{hua}")  # 例: "巨門化忌", "天梁化禄"

    # === 西洋: 金星サイン・金星×木星合 ===
    w = bundle.western
    venus_sign = None
    jupiter_sign = None
    for p in (w.planets or []):
        if p.name == "金星":
            venus_sign = p.sign
            if p.sign:
                tags.add(f"金星{p.sign}")
        elif p.name == "木星":
            jupiter_sign = p.sign
    for a in (w.aspects or []):
        if a.aspect_type == "合" and {a.planet1, a.planet2} == {"金星", "木星"}:
            tags.add("金星木星合")

    # === 万象学: 印星過多（簡易・四柱推命の通変星から判定）===
    sh = bundle.shichusuimei
    if sh is not None:
        in_count = 0
        all_count = 0
        for pillar in (sh.nen_pillar, sh.tsuki_pillar, sh.hi_pillar, sh.toki_pillar):
            if pillar is None:
                continue
            for fld in ("tsuhensei", "zoukan_tsuhensei"):
                v = getattr(pillar, fld, "") or ""
                if v and v != "—":
                    all_count += 1
                    if v in ("印綬", "偏印"):
                        in_count += 1
        if all_count > 0 and in_count / all_count >= 0.30:
            tags.add("印星過多")

    return sorted(tags)


def _calc_current_age(bundle: DivinationBundle) -> int:
    from datetime import date as _d
    bd = bundle.person.birth_date
    today = _d.today()
    age = today.year - bd.year - ((today.month, today.day) < (bd.month, bd.day))
    return max(0, age)


def select_episodes(god_data: dict, match_tags: list[str], limit: int = 3) -> list[dict]:
    """1柱の神の episodes からタグ一致でスコアリングして上位を返す（生エピソード）"""
    tagset = set(match_tags)
    scored = []
    for ep in god_data.get("episodes", []):
        ep_tags = set(ep.get("matching_tags") or [])
        score = len(ep_tags & tagset)
        if score > 0:
            scored.append((score, ep))
    # スコア降順、タイで id 安定ソート
    scored.sort(key=lambda x: (-x[0], x[1].get("id", "")))
    return [ep for _, ep in scored[:limit]]


def _episode_user_facing(ep: dict) -> dict:
    """エピソードからプロンプト用フィールドだけを残す（matching_tags は内部のみ・占術用語漏洩防止）"""
    return {
        "id": ep.get("id"),
        "title": ep.get("title"),
        "source": ep.get("source"),
        "source_type": ep.get("source_type"),
        "summary": ep.get("summary"),
        "core_phrase": ep.get("core_phrase"),
        "light": ep.get("light"),
        "shadow": ep.get("shadow"),
        "life_phase_label": ep.get("life_phase_label"),
        "related_gods": list(ep.get("related_gods") or []),
        "related_shrines": list(ep.get("related_shrines") or []),
        "reading_example": ep.get("reading_example"),
    }


def select_light_shadows(god_data: dict, selected_eps: list[dict],
                         match_tags: list[str], limit: int = 3) -> list[dict]:
    """選ばれたエピソードのタグ群と入力タグの共通集合で、光影対をスコアリング"""
    ep_tag_pool: set[str] = set(match_tags)
    for ep in selected_eps:
        ep_tag_pool |= set(ep.get("matching_tags") or [])
    scored = []
    for pair in god_data.get("light_shadow_pairs", []):
        ptags = set(pair.get("matching_tags") or [])
        score = len(ptags & ep_tag_pool)
        if score > 0:
            scored.append((score, pair))
    scored.sort(key=lambda x: -x[0])
    out = []
    for _, p in scored[:limit]:
        out.append({"light": p.get("light"), "shadow": p.get("shadow")})
    return out


def select_related_gods_for_episodes(god_data: dict, selected_eps: list[dict]) -> list[dict]:
    """選ばれたエピソードの related_gods に名前が現れる related_gods 定義だけ返す"""
    names_in_eps: set[str] = set()
    for ep in selected_eps:
        for nm in (ep.get("related_gods") or []):
            # "豊吾田津姫=木花咲耶姫" のような別名表記から本体名を取る
            for token in str(nm).split("="):
                names_in_eps.add(token.strip())
    out = []
    seen = set()
    for rg in god_data.get("related_gods", []):
        nm = rg.get("name")
        if nm and nm in names_in_eps and nm not in seen:
            out.append({
                "name": nm,
                "reading": rg.get("reading", ""),
                "role": rg.get("role", ""),
                "divination_use": rg.get("divination_use", ""),
            })
            seen.add(nm)
    return out


def recommend_shrine_for_episodes(god_data: dict, selected_eps: list[dict]) -> Optional[dict]:
    """選ばれたエピソードに最も結びつく神社を1社推薦"""
    ep_ids = {ep.get("id") for ep in selected_eps if ep.get("id")}
    if not ep_ids:
        # フォールバック: 最初の神社
        shrines = god_data.get("shrines", [])
        return shrines[0] if shrines else None
    scored = []
    for shr in god_data.get("shrines", []):
        match_ids = set(shr.get("matching_episode_ids") or [])
        score = len(match_ids & ep_ids)
        if score > 0:
            scored.append((score, shr))
    if not scored:
        shrines = god_data.get("shrines", [])
        return shrines[0] if shrines else None
    scored.sort(key=lambda x: -x[0])
    shr = scored[0][1]
    return {
        "name": shr.get("name"),
        "location": shr.get("location", {}),
        "summary": shr.get("summary", ""),
        "season_recommendation": shr.get("season_recommendation", ""),
        "experience": shr.get("experience", ""),
    }


def pick_life_phase_for_age(god_data: dict, age: int) -> Optional[dict]:
    """現年齢に対応する神の人生フェーズを1つ返す。
    age が範囲内なら最初のヒット、範囲外なら最も近いフェーズを返す。
    """
    phases = god_data.get("life_phases") or []
    if not phases:
        return None
    # 完全一致
    for ph in phases:
        a_from = int(ph.get("age_from", 0))
        a_to = int(ph.get("age_to", 999))
        if a_from <= age <= a_to:
            return {"phase": ph.get("phase"), "title": ph.get("title"),
                    "age_label": f"{a_from}〜{a_to}歳",
                    "description": ph.get("description", "")}
    # 範囲外: 最も近いフェーズ
    nearest = min(phases, key=lambda ph: min(abs(age - int(ph.get("age_from", 0))),
                                              abs(age - int(ph.get("age_to", 0)))))
    a_from = int(nearest.get("age_from", 0))
    a_to = int(nearest.get("age_to", 0))
    return {"phase": nearest.get("phase"), "title": nearest.get("title"),
            "age_label": f"{a_from}〜{a_to}歳",
            "description": nearest.get("description", "")}


def build_god_deep(bundle: DivinationBundle, v1: KojinDoResult) -> Optional[GodDeepDiveResult]:
    """v2.5 深掘り型結果を構築。守護神が gods/{id}.json に未登録なら None。"""
    god_id = GOD_NAME_TO_ID.get(v1.god_name or "")
    if not god_id:
        return None
    god_data = load_god(god_id)
    if not god_data:
        return None
    match_tags = extract_god_match_tags(bundle)
    raw_eps = select_episodes(god_data, match_tags, limit=3)
    if not raw_eps:
        # スコア0でも最初の1本（主物語）は出す（最低限の鑑定文）
        raw_eps = list(god_data.get("episodes", []))[:1]
    selected_eps = [_episode_user_facing(ep) for ep in raw_eps]
    pairs = select_light_shadows(god_data, raw_eps, match_tags, limit=3)
    rel = select_related_gods_for_episodes(god_data, raw_eps)
    shrine = recommend_shrine_for_episodes(god_data, raw_eps)
    age = _calc_current_age(bundle)
    phase = pick_life_phase_for_age(god_data, age)
    return GodDeepDiveResult(
        god_id=god_data.get("god_id", god_id),
        god_name=god_data.get("god_name", v1.god_name),
        god_reading=god_data.get("god_reading", v1.god_reading),
        god_summary=god_data.get("god_summary", ""),
        selected_episodes=selected_eps,
        light_shadows=pairs,
        related_gods_in_episodes=rel,
        recommended_shrine=shrine,
        life_phase_for_age=phase,
        match_tags=match_tags,
    )


# ============================================================
# 統合: calculate_kojindo_v2
# ============================================================
def calculate_kojindo_v2(bundle: DivinationBundle) -> KojinDoV2Result:
    """v2 統合計算（v1 = 背骨 + 動的マッチ）。
    v2.5: 守護神JSONがあれば god_deep を併設（深掘り型へ）。
    """
    v1 = calculate_kojindo(bundle.sanmei, bundle.person)
    traits = extract_traits(bundle)
    stories = filter_stories(traits, limit=12)
    shrines = recommend_shrines(stories, v1)
    god_deep = build_god_deep(bundle, v1)
    return KojinDoV2Result(
        v1=v1,
        traits=traits,
        candidate_stories=stories,
        recommended_shrines=shrines,
        god_deep=god_deep,
    )
