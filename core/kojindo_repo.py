"""
古神道占い v2 - データリポジトリ層
core/kojindo_repo.py

物語ストック（StoryRepo）と神社DB（ShrineRepo）を data/kojindo/ から読み込み、
タグ一致・祭神検索・方位検索などの API を提供する。

設計: くろたん「古神道v2 3層構造設計相談」(2026-05-10)
実装: コドたん「実装側意見」(2026-05-10)・Q1=JSON採用、Q2=タグ一致+AI仕上げ
"""
from __future__ import annotations
import json
import os
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional


# ============================================================
# データ構造
# ============================================================
@dataclass
class Story:
    """物語エピソード（古事記・日本書紀・宮下文書・竹内文書・神社縁起・漫画 等）"""
    id: str
    title: str
    source: str                      # 出典の具体名
    source_type: str                 # 古事記/日本書紀/宮下文書/竹内文書/風土記/神社縁起/漫画/映画
    trust_level: str                 # 正史/古史古伝/現代物語
    god: str                         # 主役の神
    story_summary: str               # 1-3文の要約
    story_one_line: str              # CMプランナー型1行
    tags: list[str] = field(default_factory=list)              # 説明タグ（自由）
    applicable_traits: list[str] = field(default_factory=list) # ★マッチング用タグ（tag_dictionary準拠）
    shrine_id: Optional[str] = None  # 紐づく神社ID

    @classmethod
    def from_dict(cls, d: dict) -> "Story":
        return cls(
            id=d["id"],
            title=d["title"],
            source=d.get("source", ""),
            source_type=d.get("source_type", ""),
            trust_level=d.get("trust_level", "正史"),
            god=d.get("god", ""),
            story_summary=d.get("story_summary", ""),
            story_one_line=d.get("story_one_line", ""),
            tags=d.get("tags", []),
            applicable_traits=d.get("applicable_traits", []),
            shrine_id=d.get("shrine_id"),
        )


@dataclass
class Shrine:
    """神社"""
    id: str
    name: str
    parent_shrine: Optional[str] = None
    location: dict = field(default_factory=dict)         # {"pref","city","lat","lng"}
    main_deity: list[str] = field(default_factory=list)
    sub_deities: list[str] = field(default_factory=list)
    benefits: list[str] = field(default_factory=list)
    atmosphere: str = ""
    access: str = ""
    episode_ids: list[str] = field(default_factory=list)
    five_element: Optional[str] = None                   # 木/火/土/金/水

    @classmethod
    def from_dict(cls, d: dict) -> "Shrine":
        return cls(
            id=d["id"],
            name=d["name"],
            parent_shrine=d.get("parent_shrine"),
            location=d.get("location", {}),
            main_deity=d.get("main_deity", []),
            sub_deities=d.get("sub_deities", []),
            benefits=d.get("benefits", []),
            atmosphere=d.get("atmosphere", ""),
            access=d.get("access", ""),
            episode_ids=d.get("episode_ids", []),
            five_element=d.get("five_element"),
        )


# ============================================================
# データディレクトリ解決
# ============================================================
_BASE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "kojindo",
)
_STORIES_DIR = os.path.join(_BASE_DIR, "stories")
_SHRINES_DIR = os.path.join(_BASE_DIR, "shrines")
_TAGS_DIR = os.path.join(_BASE_DIR, "tags")
_GODS_DIR = os.path.join(_BASE_DIR, "gods")


# ============================================================
# 守護神データ（v2.5 深掘り型）
# 1柱の神の全データ（9エピソード＋光影対＋関係者＋神社＋フェーズ）を
# data/kojindo/gods/{god_id}.json から読む。設計: 古神道v2.5 (2026-05-24)
# ============================================================
_god_cache: dict[str, dict] = {}


def load_god(god_id: str) -> Optional[dict]:
    """守護神JSONを読み込む（キャッシュあり）。未登録ならNone。

    god_id: "ninigi" 等。data/kojindo/gods/{god_id}.json を読む。
    Phase1では ninigi のみ。今後 okuninushi 等を順次追加。
    """
    if god_id in _god_cache:
        return _god_cache[god_id]
    path = os.path.join(_GODS_DIR, f"{god_id}.json")
    if not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        _god_cache[god_id] = data
        return data
    except Exception as e:
        print(f"[kojindo_repo] failed to load god {god_id}: {e}")
        return None


# 神名 → god_id マッピング（god_name と JSON の god_id を結ぶ）
# v3（2026-07-04 指令書）: 十干10柱に世代交代。god_id は core/kojindo.py の
# GOD_ID_BY_JIKKAN 凍結表が正（表記ゆれ禁止・くろたん承認 2026-07-04）。
# 深掘りJSONは現状 ninigi.json のみ実在。他の9柱は系統A/B完了後に順次追加。
GOD_NAME_TO_ID = {
    "大山津見神": "oyamatsumi",
    "木花咲耶姫": "konohanasakuya",
    "天照大神": "amaterasu",
    "月読命": "tsukuyomi",
    "伊邪那岐命": "izanagi",
    "大国主命": "okuninushi",
    "須佐之男命": "susanoo",
    "瓊瓊杵尊": "ninigi",
    "綿津見神": "watatsumi",
    "瀬織津姫": "seoritsuhime",
    # v1退役組（アーカイブ・眷属レイヤー等での再登板に備え予約）:
    # "建御雷神": "takemikazuchi",
    # "天宇受賣命": "uzume",
    # "猿田彦神": "sarutahiko",
    # "思金神": "omoikane",
    # "建御名方神": "takeminakata",
    # "玉依姫": "tamayori",
}


def _load_json_files(directory: str) -> list[dict]:
    """ディレクトリ内の全 JSON ファイルを読み込み、各 'stories' or 'shrines' リストを連結"""
    if not os.path.isdir(directory):
        return []
    items = []
    for fname in sorted(os.listdir(directory)):
        if not fname.endswith(".json") or fname.startswith("_"):
            continue
        path = os.path.join(directory, fname)
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            # スキーマ: {"stories": [...]} or {"shrines": [...]}
            for key in ("stories", "shrines"):
                if key in data and isinstance(data[key], list):
                    items.extend(data[key])
        except Exception as e:
            print(f"[kojindo_repo] failed to load {path}: {e}")
    return items


# ============================================================
# StoryRepo（物語ストック）
# ============================================================
class StoryRepo:
    """物語エピソードのリポジトリ。起動時に全件メモリ読み込み"""

    def __init__(self):
        raw = _load_json_files(_STORIES_DIR)
        self._stories: list[Story] = [Story.from_dict(d) for d in raw]
        self._by_id: dict[str, Story] = {s.id: s for s in self._stories}
        # タグ → エピソードID の逆引きインデックス
        self._by_trait: dict[str, list[str]] = defaultdict(list)
        for s in self._stories:
            for trait in s.applicable_traits:
                self._by_trait[trait].append(s.id)

    def all(self) -> list[Story]:
        return list(self._stories)

    def get(self, story_id: str) -> Optional[Story]:
        return self._by_id.get(story_id)

    def filter_by_traits(self, traits: list[str], limit: int = 15) -> list[Story]:
        """タグ一致でストーリー候補を絞る（Q2回答: 案A タグ一致）

        スコア = applicable_traits と入力 traits の積集合のサイズ。
        スコア降順で limit 件返す。スコア0は除外。
        """
        if not traits:
            return []
        traits_set = set(traits)
        scored = []
        for s in self._stories:
            score = len(set(s.applicable_traits) & traits_set)
            if score > 0:
                scored.append((score, s))
        # スコア降順、タイで id 安定ソート
        scored.sort(key=lambda x: (-x[0], x[1].id))
        return [s for _, s in scored[:limit]]

    def count(self) -> int:
        return len(self._stories)


# ============================================================
# ShrineRepo（神社DB・古神道+開運習慣L3-L5で共有）
# ============================================================
class ShrineRepo:
    """神社のリポジトリ。古神道占いと開運習慣L3-L5で共通利用"""

    def __init__(self):
        raw = _load_json_files(_SHRINES_DIR)
        self._shrines: list[Shrine] = [Shrine.from_dict(d) for d in raw]
        self._by_id: dict[str, Shrine] = {s.id: s for s in self._shrines}
        # 祭神 → 神社ID の逆引きインデックス
        self._by_deity: dict[str, list[str]] = defaultdict(list)
        for shr in self._shrines:
            for deity in (shr.main_deity + shr.sub_deities):
                self._by_deity[deity].append(shr.id)

    def all(self) -> list[Shrine]:
        return list(self._shrines)

    def get(self, shrine_id: str) -> Optional[Shrine]:
        return self._by_id.get(shrine_id)

    def find_by_deity(self, deity_name: str) -> list[Shrine]:
        ids = self._by_deity.get(deity_name, [])
        return [self._by_id[i] for i in ids if i in self._by_id]

    def find_by_pref(self, pref: str) -> list[Shrine]:
        return [s for s in self._shrines if s.location.get("pref") == pref]

    def find_by_element(self, element: str) -> list[Shrine]:
        return [s for s in self._shrines if s.five_element == element]

    def find_by_benefit(self, keyword: str) -> list[Shrine]:
        return [s for s in self._shrines if any(keyword in b for b in s.benefits)]

    def count(self) -> int:
        return len(self._shrines)


# ============================================================
# TagDictionary（タグ辞書）
# ============================================================
class TagDictionary:
    """許容タグの辞書。エピソード作成時のバリデーションに使う"""

    def __init__(self):
        path = os.path.join(_TAGS_DIR, "tag_dictionary.json")
        self._all_tags: set[str] = set()
        self._by_category: dict[str, list[str]] = {}
        self._version: str = "unknown"
        if os.path.isfile(path):
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                self._version = data.get("_version", "unknown")
                self._by_category = data.get("categories", {})
                self._all_tags = set(data.get("all_tags", []))
            except Exception as e:
                print(f"[kojindo_repo] failed to load tag_dictionary: {e}")

    def all(self) -> set[str]:
        return set(self._all_tags)

    def is_valid(self, tag: str) -> bool:
        return tag in self._all_tags

    def validate_traits(self, traits: list[str]) -> tuple[list[str], list[str]]:
        """入力タグを (valid, invalid) に分類"""
        valid = [t for t in traits if t in self._all_tags]
        invalid = [t for t in traits if t not in self._all_tags]
        return valid, invalid

    def version(self) -> str:
        return self._version


# ============================================================
# シングルトンインスタンス（Streamlit 等から再利用）
# ============================================================
_story_repo_instance: Optional[StoryRepo] = None
_shrine_repo_instance: Optional[ShrineRepo] = None
_tag_dict_instance: Optional[TagDictionary] = None


def get_story_repo() -> StoryRepo:
    global _story_repo_instance
    if _story_repo_instance is None:
        _story_repo_instance = StoryRepo()
    return _story_repo_instance


def get_shrine_repo() -> ShrineRepo:
    global _shrine_repo_instance
    if _shrine_repo_instance is None:
        _shrine_repo_instance = ShrineRepo()
    return _shrine_repo_instance


def get_tag_dictionary() -> TagDictionary:
    global _tag_dict_instance
    if _tag_dict_instance is None:
        _tag_dict_instance = TagDictionary()
    return _tag_dict_instance
