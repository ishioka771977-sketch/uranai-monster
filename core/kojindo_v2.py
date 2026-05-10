"""
古神道占い v2 - 動的マッチングエンジン
core/kojindo_v2.py

7流派の鑑定結果から特徴タグを抽出し、物語ストックから最適な3-5本を
タグ一致でフィルタリングし、神社推薦も組み立てる。

設計: くろたん「古神道v2 3層構造設計相談」(2026-05-10)
実装: コドたん「実装側意見」(2026-05-10)
方針: Q3回答 = フィルタリングは Python、AI 呼び出しは1回（後で2回化検討）

v1.5 段階の方針（くろたん回答 Q5）:
- 「守護神」セクションは v1 の固定マッピングを背骨として残す
- 「重なる物語」セクションで動的マッチした 2-3本を提案的に語る
- エピソード20-30で開始、増えるほど動的比率を上げる
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional

from .models import DivinationBundle
from .kojindo_repo import StoryRepo, ShrineRepo, Story, Shrine, get_story_repo, get_shrine_repo
from .kojindo import calculate_kojindo, KojinDoResult  # v1 計算結果（背骨）


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
    タグは tag_dictionary.json (v1.5 暫定版) と整合する形で出力する。
    """
    traits: set[str] = set()
    s = bundle.sanmei

    # === 中央星タグ ===
    if s.chuo_sei:
        traits.add(f"中央星={s.chuo_sei}")

    # === 五行偏りタグ（4σ的閾値: 40%以上=過多、10%未満=不足）===
    g = s.gogyo_balance or {}
    for element in ("木", "火", "土", "金", "水"):
        v = g.get(element, 0)
        if v >= 40:
            traits.add(f"{element}過多")
        elif v <= 10:
            traits.add(f"{element}不足")

    # === 万象学エネルギータグ ===
    e = s.bansho_energy
    if e:
        en = e.total_energy
        if en >= 300:
            traits.add("エネルギー超過(300+)")
        elif en >= 230:
            traits.add("エネルギー高(230-299)")
        elif en >= 180:
            traits.add("エネルギー中(180-229)")
        elif en >= 160:
            traits.add("エネルギー低(160-179)")
        else:
            traits.add("エネルギー集中特化(160未満)")

        # 本能ランキングから最高/最低本能タグ
        if e.honnou_ranking:
            top_h = e.honnou_ranking[0][0]
            bottom_h = e.honnou_ranking[-1][0]
            traits.add(f"{top_h}高")
            # 最低が0点なら「低」
            if e.honnou_ranking[-1][1] <= 5:
                traits.add(f"{bottom_h}低")

    # === 性質タグ（中央星から推測）===
    chuo = s.chuo_sei or ""
    if chuo == "牽牛星":
        traits.add("名誉型")
        traits.add("組織型")
    if chuo in ("龍高星", "調舒星"):
        traits.add("放浪型")
    if chuo == "貫索星":
        traits.add("不動")
    if chuo in ("鳳閣星", "司禄星", "玉堂星"):
        traits.add("組織型")  # 安定タイプ寄り
    if chuo == "調舒星":
        traits.add("破壊と再生")
    if chuo in ("司禄星", "玉堂星"):
        traits.add("継承の物語")

    # === 状態タグ（年齢×フェーズ）===
    # v1 計算結果の phase_name を流用
    v1 = calculate_kojindo(s, bundle.person)
    phase_to_state = {
        "母の庇護": "神産み期",
        "反抗と試練": "反抗期",
        "修行期": "修行期",
        "国造り": "国造り期",
        "収穫と完成": "収穫期",
        "国譲り": "国譲り期",
        "神上がり": "神上がり期",
    }
    state_tag = phase_to_state.get(v1.phase_name)
    if state_tag:
        traits.add(state_tag)

    # === 天中殺中フラグ ===
    from datetime import date as _date
    cur_year = _date.today().year
    if s.tenchusatsu_years and cur_year in s.tenchusatsu_years:
        traits.add("天中殺中")

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
