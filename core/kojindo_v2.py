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
from .kojindo_repo import StoryRepo, ShrineRepo, Story, Shrine, get_story_repo, get_shrine_repo
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
class KojinDoV2Result:
    """v2 = v1 結果 + 動的マッチング結果"""
    v1: KojinDoResult                                    # v1 の守護神（背骨）
    traits: list[str] = field(default_factory=list)      # 抽出された特徴タグ
    candidate_stories: list[Story] = field(default_factory=list)  # マッチ候補（10-15本）
    recommended_shrines: list[Shrine] = field(default_factory=list)  # 推薦神社


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

    # === 五行偏りタグ（quality・40%以上=過多、10%以下=不足）===
    g = s.gogyo_balance or {}
    for element in ("木", "火", "土", "金", "水"):
        v = g.get(element, 0)
        if v >= 40:
            traits.add(f"{element}過多")
    # 不足は重要な「火不足」「水不足」のみ採用（タグ辞書準拠）
    if g.get("水", 0) <= 10:
        traits.add("水不足")
    if g.get("火", 0) <= 10:
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
# 統合: calculate_kojindo_v2
# ============================================================
def calculate_kojindo_v2(bundle: DivinationBundle) -> KojinDoV2Result:
    """v2 統合計算（v1 = 背骨 + 動的マッチ = 重なる物語）"""
    v1 = calculate_kojindo(bundle.sanmei, bundle.person)
    traits = extract_traits(bundle)
    stories = filter_stories(traits, limit=12)
    shrines = recommend_shrines(stories, v1)
    return KojinDoV2Result(
        v1=v1,
        traits=traits,
        candidate_stories=stories,
        recommended_shrines=shrines,
    )
