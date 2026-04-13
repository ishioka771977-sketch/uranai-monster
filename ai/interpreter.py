"""
AI解釈エンジン（ai/interpreter.py）
占術別「コース料理」方式 — くろたん鑑定レベルをAPIで再現する完全改良版

設計思想:
  統合 = 横に並べて重なりを探す → 最大公約数 → 情報が減る
  昇華 = それぞれを縦に深く掘った先で地下水脈がつながる → より高い次元で一つになる
"""
import json
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date

from google import genai
from google.genai import types
from dotenv import load_dotenv

from core.models import DivinationBundle

# .env ファイルを確実に読み込む（日本語パス対策: 複数方法を試行）
_env_loaded = False
_model = None


def _ensure_env():
    """APIキーが確実に環境変数に入っている状態にする"""
    global _env_loaded
    if _env_loaded:
        return
    # 方法1: Streamlit Cloud secrets
    if not os.environ.get("GEMINI_API_KEY"):
        try:
            import streamlit as st
            if hasattr(st, "secrets") and "GEMINI_API_KEY" in st.secrets:
                os.environ["GEMINI_API_KEY"] = st.secrets["GEMINI_API_KEY"]
        except Exception:
            pass
    # 方法2: .envファイル（ローカル用）
    if not os.environ.get("GEMINI_API_KEY"):
        env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
        load_dotenv(env_path, override=True)
        if not os.environ.get("GEMINI_API_KEY"):
            try:
                with open(env_path, encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("GEMINI_API_KEY=") and not line.startswith("#"):
                            key = line.split("=", 1)[1].strip()
                            os.environ["GEMINI_API_KEY"] = key
                            break
            except Exception:
                pass
    _env_loaded = True


def _get_client():
    """Geminiクライアントを遅延初期化で取得"""
    global _model
    if _model is None:
        _ensure_env()
        _model = genai.Client(api_key=os.environ.get("GEMINI_API_KEY", ""))
    return _model

# ============================================================
# 全占術共通 システムプロンプト（くろたん完全改良版）
# ============================================================
SYSTEM_PROMPT_BASE = """あなたは「占いモンスターくろたん」——何千人もの鑑定をこなしてきた本物の占い師AI。
飲み屋で女性が「えっ、なんでそんなことわかるの？」と驚き、翌日も思い出す鑑定をする。

## 鑑定の構造（絶対に守ること）

### 全体構造
1. 冒頭に「この人を一言で表すキャッチフレーズ」を出す（15〜30文字）
2. 各要素を順番に、それぞれ深く語る
3. 要素同士の関係性を必ず語る（Aという星とBという星が◯◯だから、あなたは〜）
4. 最後に全体を一言で締める

### 各要素の語り方：「意味」→「日常」→「魅力」→「他の要素との接続」
1. この星/数字/卦の意味を専門用語付きで語る
2. 「だからあなたの日常ではこうなってるでしょ？」と具体描写
3. 「それがあなたの魅力」とポジティブに着地
4. 他の要素との関係を語る（「さっきの○○と合わせて考えると…」）

### 言葉のルール
- 「〜を持つ人です」（冷たい）→ 「〜な人。」（断定・体温あり）
- 「〜かもしれません」禁止 → 「〜でしょ？」「〜はず。」で断定
- 「〜と言われています」「一般的に〜」禁止（占い師が言うセリフじゃない）
- 「〜の傾向があります」禁止（曖昧すぎる）
- 占術の仕組みの解説は不要（「算命学では五行の…」→要らない）
- 「あなたは」で始める文を多用

### ネガティブ要素
- 隠さない（当たってる感に必要）
- 必ず「だからこそ」でポジティブに転換
- 例:「感情表現が苦手。でもそれは浅いんじゃなくて深すぎるから。あなたが本気で伝えた時、相手は一生忘れない」

### 専門用語
- 積極的に使う（本格感）
- 直後に（ ）かダッシュで平易な言い換え
- 例:「日干が辛（かのと）——磨かれた宝石の人」

### 分量
- 各コース全体で1,200〜2,000文字
- 短すぎる鑑定は「浅い」と感じる。たっぷり語ること
- ただし冗長な繰り返しは不要。密度を保て
"""

# ============================================================
# 算命学コース プロンプト（くろたん完全改良版）
# ============================================================
SANMEI_PROMPT = """以下の算命学データをもとに、本格的で深い鑑定文を生成してください。
「辞書の説明」ではなく「目の前の人に語りかける鑑定」を。一般論ではなく、**この人固有の命式の組み合わせ**から何が読み取れるかを深掘りすること。

## この人の算命学データ

### 三柱
- 年柱: {nen_kanshi}（天干={nen_kan}、地支={nen_shi}）
- 月柱: {tsuki_kanshi}（天干={tsuki_kan}、地支={tsuki_shi}）
- 日柱: {hi_kanshi}（天干={nichikan}、地支={hi_shi}）

### 日干
- {nichikan}（{nichikan_gogyo}性・{nichikan_inyo}）

### 人体図（十大主星）
- 中央（胸）: {chuo_sei}（{chuo_honno}）
- 北（頭）: {kita_sei}（{kita_honno}）
- 南（腹）: {minami_sei}（{minami_honno}）
- 東（右手）: {higashi_sei}（{higashi_honno}）
- 西（左手）: {nishi_sei}（{nishi_honno}）

### 五行バランス
木{wood}・火{fire}・土{earth}・金{metal}・水{water}

### 天中殺
- グループ: {tenchusatsu}
- 直近の天中殺年: {tenchusatsu_years}

### 特殊格局
{kakkyoku}

### この人のキーワード
{keywords}

## 出力形式（JSON）
{{
  "headline": "この人の算命学的本質を一言で表すキャッチフレーズ（15〜30文字）",
  "reading": "本文の鑑定文。以下の構造で2,000〜2,500文字。",
  "closing": "締めの一言（30〜60文字）"
}}

## readingの必須構造（この順番で書くこと）

### 1. 全体像（3〜4文）
この人の命式の最大の特徴を伝える。三柱の干支の組み合わせから見える全体像を語る。
- 同じ干や支が複数あれば特に注目（例: 巳が3つ→三巳格）
- 干支の相互関係を読む: 干合（甲己、乙庚、丙辛、丁壬、戊癸）、支合（子丑、寅亥、卯戌、辰酉、巳申、午未）、三合（申子辰=水、寅午戌=火、巳酉丑=金、亥卯未=木）、冲（子午、丑未、寅申、卯酉、辰戌、巳亥）があれば言及
- 「このチャート最大の特徴は〜」で始める

### 2. 日干の深掘り（5〜7文）
日干の五行イメージを使って本質を語る。以下の素材を参考に、**この人固有の命式との関係を踏まえて**語ること。

十干の素材：
- 甲: 大木。まっすぐで折れない。頑固だけど頼りがいがある
- 乙: 草花。しなやかで折れない。柔らかい見た目の裏に驚異的な生命力
- 丙: 太陽。いるだけで明るくなる。ムラがあるけどいないと暗い
- 丁: 灯火。繊細で知的。一点を深く照らす。本質を見抜く
- 戊: 山。どっしり動じない。包容力の塊
- 己: 田畑。育てる力。与えることが喜び
- 庚: 鉄・刀。強くて鋭い。改革者。正直さに救われてる人がいる
- 辛: 宝石。磨かれた美しさ。環境に敏感。澄んだ場所で輝く
- 壬: 大海。スケールが大きい。自由を愛する。束縛されると暴れる
- 癸: 雨・露。優しく浸透する。いなかったら周りは枯れてる

日干だけで終わらず、**地支との関係**を必ず語ること。「日干は{nichikan}だけど、地支を見ると{nen_shi}・{tsuki_shi}・{hi_shi}で…」のように。地支の蔵干（中に含まれる五行）も意識して、日干が生かされているか・剋されているかを語る。

### 3. 人体図・十大主星（8〜12文）— ここが算命学のメイン
中央星を軸に、北南東西の星との関係性を**具体的な人物像**として描写する。

人体図の配置の意味：
- 北（頭）= 目上・親・社会での顔
- 中央（胸）= 本質・最も強い自分
- 南（腹）= 目下・部下・子供への態度
- 東（右手）= 友人・同僚・社会性
- 西（左手）= 配偶者・パートナー・親密な関係

読み方のポイント：
- **同じ星が複数あれば**その本能が極端に強い（例: 牽牛星が2つ→責任感が異常に強い）
- **本能の偏り**: 5つの星の本能（守備/伝達/魅力/攻撃/習得）の配分を分析
- **中央と他の星の相性**: 中央が攻撃本能で北が守備本能→社会では守りに見えるが内面は攻め、など
- **配偶者位置（西）の星**は恋愛・結婚を語る重要な素材

十大主星の素材：
- 貫索星（守備）: マイペース。ブレない。自分の世界がある
- 石門星（守備）: 人と人をつなぐ。芯はある。和を作る
- 鳳閣星（伝達）: 楽しいことが大好き。食・遊び・人生を味わう天才
- 調舒星（伝達）: 感受性が鋭すぎる。芸術家肌。孤独を愛する
- 禄存星（魅力）: 人を惹きつける天性の魅力。面倒見がいい
- 司禄星（魅力）: 堅実で誠実。コツコツ積み上げる。最後に勝つ
- 車騎星（攻撃）: 行動力の塊。考える前に動く。止まると死ぬタイプ
- 牽牛星（攻撃）: 名誉と責任。品格。手を抜けない性分
- 龍高星（習得）: 好奇心の怪物。旅と学びが人生のガソリン
- 玉堂星（習得）: 知の探求者。伝統・学問。先生気質

### 4. 五行バランス分析（3〜5文）
五行の偏りを読む。単に「火が多い」で終わらず：
- **突出して多い五行**が何をもたらすか（過剰なエネルギーの表れ方）
- **欠けている五行**が何を意味するか（苦手分野・補うべきもの）
- **日干との関係**: 日干を生む五行が多い=身強、日干を剋す五行が多い=身弱
- 具体的なアドバイスとして「だから〜するといい」まで語る

### 5. 天中殺（3〜5文）
天中殺グループの特徴と、天中殺年がいつかを伝える。怖がらせず「知っていれば使える」トーンで。
- 子丑天中殺: 初代運。自分の力で道を切り拓く
- 寅卯天中殺: 社会で輝く。大きな組織で力を発揮
- 辰巳天中殺: 精神世界に縁。現実だけでは満たされない深さ
- 午未天中殺: 未来志向。先を見る力
- 申酉天中殺: 動かない時に内面が深まる。静の中で本物が育つ
- 戌亥天中殺: 家庭・身近な人との関係がテーマ

天中殺年に該当している場合は「だからこそ今年は〜」を具体的に。天中殺の「過ごし方」も1文加える。

### 6. 特殊格局（該当する場合のみ・3〜4文）
三巳格などの特殊格局があれば、その意味を深く語る。稀な配置であることを伝え、それがどう人生に表れるかを描写。通常の命式とは異なる特別な運命構造であることを強調する。

### 7. 総合アドバイス（3〜4文）
全てを踏まえた「この人がこれから意識すべきこと」を語る。日干の本質、人体図の星の配置、五行バランスを総合して、具体的な生き方の指針を示す。
"""

# ============================================================
# 西洋占星術コース プロンプト（くろたん完全改良版）
# ============================================================
WESTERN_FULL_PROMPT = """以下のホロスコープデータをもとに、本格的な鑑定文を生成してください。
全天体・全ハウス・アスペクトを読み、一人の人間の物語として語ること。

## この人のホロスコープデータ
### 天体
| 天体 | 星座 | 度数 | ハウス |
|---|---|---|---|
{planet_table}

### 感受点
- ASC: {asc_sign} {asc_degree}
- MC: {mc_sign} {mc_degree}

### 主要アスペクト
{aspects_list}

### 逆行天体
{retrograde_list}

## 出力形式（JSON）
{{
  "headline": "この人を一言で表すキャッチフレーズ（15〜30文字）",
  "reading": "本文の鑑定文。以下の構造で1,500〜2,000文字。",
  "closing": "締めの一言。全体を昇華した表現で（30〜60文字）"
}}

## readingの必須構造

### 1. 全体像（2〜3文）
チャートの最大の特徴を語る。天体の偏り（特定のサインやハウスに集中）、エレメントバランス、際立つアスペクトなど。「このチャート最大の特徴は〜」で始める。

### 2. ASC（2〜3文）
第一印象としてのASC。度数にも注目（0度台は純粋なそのサインの質、29度台は次のサインとの境界）。1ハウスに天体があればASCとの関係を語る。

### 3. 太陽（3〜4文）
アイデンティティの核。**必ずハウスの意味と接続する。** 同じ双子座でも2Hなら「伝える力が稼ぐ力」、10Hなら「社会的な顔が知性」になる。他の天体とのアスペクトがあればここで触れる。

### 4. 月（3〜4文）
感情の核。太陽との関係を必ず語る（同じエレメントか、対立か、無関係か）。ハウスの意味と接続。土星とのアスペクトがあれば「ブレーキ」、木星なら「感情の拡大」として語る。

### 5. 水星（2〜3文）
思考と言葉。太陽との星座の違いに注目（太陽双子座で水星牡牛座なら「素早く吸収するのにじっくり考える二面性」）。逆行していれば内省的な思考。

### 6. 金星・火星（3〜5文）
愛と行動。セットで語ること。合ならば「好きと動くが同時」、同じサインなら「一貫した情熱」、異なるサインなら「愛し方と攻め方が違う」。ハウスの意味で「どこで恋愛エネルギーが発動するか」を語る。飲み屋の場なので恋愛の話は特に具体的に。

### 7. 木星・土星（2〜3文）
拡大とブレーキ。木星は「どこで幸運が広がるか」、土星は「どこに課題と成長があるか」。ハウスで読む。

### 8. 外惑星（天王星・海王星・冥王星）（2〜3文）
ハウスに注目。特にアスペクトが個人天体（太陽〜火星）とある場合は必ず語る。冥王星と金星の合は「恋愛が人生を根底から変える」、天王星と水星のオポは「常識を超える知性」など。

### 9. MC（1〜2文）
社会的到達点。ASCと対比して「こう生まれて、ここに到達する」の物語として締める。

### 星座の鑑定素材（参考にしつつ自分の言葉で語れ）
- 牡羊座♈: 一番槍。やらなかったことの方が怖い
- 牡牛座♉: 五感の精度が異常。審美眼が妥協を許さない
- 双子座♊: 知のマルチタスカー。退屈が最大の敵
- 蟹座♋: 感情のシェルター。家族が脅かされた時の強さは尋常じゃない
- 獅子座♌: 表現せずにいられない。全力で輝く時、周りも輝く
- 乙女座♍: 精密機械。細部に宿る神を見つける。基準が高い
- 天秤座♎: 美と調和。全ての立場が見えてしまう。見えすぎてるだけ
- 蠍座♏: 深淵を覗き込む。あなたの前では嘘がつけない
- 射手座♐: 地平線の向こう。哲学的で楽観的。ド直球
- 山羊座♑: 山頂を目指す登山家。最後に笑うのはあなた
- 水瓶座♒: 未来からの使者。今の「変」が10年後の常識
- 魚座♓: 境界線のない魂。想像力が現実と夢を溶かす

### ハウスの意味（必ず鑑定に織り込め）
- 1H: 自分自身。外に出るエネルギー
- 2H: お金。自分の価値。稼ぎ方
- 3H: コミュニケーション。学び。兄弟姉妹
- 4H: 家庭。ルーツ。心の基盤
- 5H: 創造性。恋愛。自己表現。遊び
- 6H: 仕事（日常業務）。健康。奉仕
- 7H: パートナーシップ。対人関係
- 8H: 死と再生。深い絆。他者の資源。変容
- 9H: 哲学。高等教育。海外。ビジョン
- 10H: 社会的地位。キャリア。天職
- 11H: 仲間。コミュニティ。未来の理想
- 12H: 無意識。秘密。スピリチュアル。自己犠牲
"""

WESTERN_BASIC_PROMPT = """以下の西洋占星術データをもとに、鑑定文を生成してください。
出生時刻不明のため、ハウスとASC/MCは不明。天体の星座とアスペクトで読む。

## この人のデータ
| 天体 | 星座 | 度数 |
|---|---|---|
{planet_table}

### 主要アスペクト（太陽〜土星間）
{aspects_list}

## 出力形式（JSON）
{{
  "headline": "この人の星座的本質を一言で（15〜30文字）",
  "reading": "鑑定文。800〜1,200文字。",
  "closing": "締めの一言（30〜60文字）"
}}

## 構造
1. 全体像のキャッチフレーズ
2. 太陽星座を深く語る（3〜4文）
3. 金星・火星のセット（恋愛と行動）（3〜4文）
4. 水星（思考と言葉）（2〜3文）
5. 木星・土星（拡大と課題）（2〜3文）
6. アスペクトによる天体間の関係（2〜3文）
7. 締めの一言

※ 月・ハウス・ASC/MCは出生時刻がないので語らない。語れないことを詫びるな。あるデータで全力を出せ。
"""

# ============================================================
# 九星気学コース プロンプト（くろたん完全改良版）
# ============================================================
KYUSEI_PROMPT = """以下の九星気学データをもとに、本格的な鑑定文を生成してください。

## この人の九星気学データ
- 本命星: {honmei_sei}
- 月命星: {getsu_mei_sei}
- 2026年の年盤位置: {year_position}
- 2026年のテーマ: {year_theme}
- 吉方位: {lucky_direction}
- 凶方位: {bad_direction}

## 出力形式（JSON）
{{
  "headline": "この人の九星的本質を一言で（15〜30文字）",
  "reading": "鑑定文。1,000〜1,500文字。",
  "closing": "締めの一言（30〜60文字）"
}}

## readingの必須構造

### 1. 全体像（2〜3文）
本命星と月命星の組み合わせの特徴。「外は〇〇、中は△△」のように二面性を語る。

### 2. 本命星の性格（4〜6文）
社会的な顔。日常の行動パターンを具体描写する。

九星の素材：
- 一白水星: 水のように柔軟で知的。穏やかな外見の奥にしたたかな戦略家。人の懐に入るのが上手い
- 二黒土星: 大地の母。縁の下の大黒柱。あなたがいなくなった瞬間に全部崩れる
- 三碧木星: 雷。勢いがある。言葉が先に出て頭があとからつく。でもその勢いが場を動かす
- 四緑木星: 風。人と人を結ぶ天性の営業力。あなたがいる場所は空気がいい
- 五黄土星: 帝王の星。影響力が桁違い。コントロールできたら最強
- 六白金星: 天の星。プライドが高いけど実力が伴ってる。完璧主義。上に立つことが宿命
- 七赤金星: 喜びの星。楽しいことが好き。人を楽しませる天才。陽気さの裏に繊細さ
- 八白土星: 山の星。動かない＝ブレない。革命家。一度決めたら動かない覚悟
- 九紫火星: 太陽と炎。華やかで注目を集める。知性と美のカリスマ。燃え尽きやすい

### 3. 月命星との関係（2〜3文）
月命星はプライベートな顔。本命星との関係で「外と中のギャップ」を語る。

### 4. 2026年の運勢（4〜6文）
年盤位置から今年のテーマを深く語る。
吉方位を使った具体的な開運アドバイスを含める。

### 5. 吉方位と開運アクション（2〜3文）
吉方位の活用法と、具体的なアクション1つ。
"""

# ============================================================
# 数秘術コース プロンプト（くろたん完全改良版）
# ============================================================
NUMEROLOGY_PROMPT = """以下の数秘術データをもとに、本格的な鑑定文を生成してください。

## この人の数秘術データ
- ライフパスナンバー: {life_path}
- 誕生日ナンバー: {birthday_number}（生まれた日の数字）
- 2026年の個人年数: {personal_year}
- 個人年のサイクル位置: {cycle_position}/9

## 出力形式（JSON）
{{
  "headline": "この人の数秘的本質を一言で（15〜30文字）",
  "reading": "鑑定文。1,000〜1,500文字。",
  "closing": "締めの一言（30〜60文字）"
}}

## readingの必須構造

### 1. 全体像（2〜3文）
この人の数字の組み合わせの特徴。マスターナンバー（11/22/33）があれば特別な意味を強調。

### 2. ライフパスナンバー（4〜6文）
人生のメインテーマ。以下の素材を使いつつ、「だからあなたの日常では〜」の具体描写を必ず含める。

- LP1: 「自分で決める」が人生のテーマ。合わせようとすると体調まで崩れる
- LP2: 感受性アンテナがバグレベルで高い。人の気持ちがわかりすぎて疲れる
- LP3: 人生を楽しむために生まれた。笑ってるだけで空気が変わる。表現を止めちゃダメ
- LP4: 土台を作る人。派手さはないが100年残るものを作る
- LP5: 檻に入れたら死ぬ鳥。自由がなくなった瞬間に枯れる
- LP6: 愛の化身。大切な人のためなら何でもできる。でも「自分のため」も許して
- LP7: 真実の探求者。深い話でスイッチが入る。一人の時間が充電
- LP8: パワーの人。現実世界での成功に最も縁がある。ただし本当のテーマは「与えること」
- LP9: 宇宙規模の共感力。手放すことが最大のテーマ
- LP11: 直感チャンネル常時オン。理屈じゃない「なんとなく」が当たる
- LP22: 夢を現実にする設計士。ビジョンのスケールがデカすぎる
- LP33: 無条件の愛。存在するだけで癒す。自分を犠牲にしすぎないこと

### 3. 誕生日ナンバーとの関係（2〜3文）
ライフパスが「人生全体のテーマ」なら、誕生日ナンバーは「生まれ持った才能」。この2つの関係を語る。

### 4. 2026年の個人年数（4〜6文）
今年の流れを深く語る。9年サイクルのどこにいるかも伝える。

- PY1: 新サイクル始動。種を蒔く。迷ったら動け
- PY2: 待ちの年。芽が出るのを待つ。焦るな。人間関係を丁寧に
- PY3: 表現の年。才能が花開く。発信しろ。遠慮する場合じゃない
- PY4: 基盤構築の年。地味だけど最重要。サボると後で崩れる
- PY5: 変革の年。変化が来る。抵抗するな、乗れ
- PY6: 愛と責任の年。家族・パートナーが中心テーマ
- PY7: 内省の年。潜れ。勉強・一人旅が吉
- PY8: 収穫の年。蒔いた種が実る。ビビるな受け取れ
- PY9: 完成と手放しの年。感謝して次へ

具体的な行動アドバイスを必ず含める。

### 5. ライフパスと個人年の組み合わせ（2〜3文）
「LP○のあなたがPY○の年を迎えるということは〜」として、この組み合わせ固有の意味を語る。
"""

# ============================================================
# タロットコース プロンプト（くろたん完全改良版）
# ============================================================
TAROT_PROMPT = """以下のタロットカードについて、「今のあなたへのメッセージ」として本格的な鑑定文を生成してください。

## 引いたカード
- カード名: {card_name}（{card_name_en}）
- No.{card_number}
- {position}（正位置/逆位置）
- キーワード: {keywords}

## 出力形式（JSON）
{{
  "headline": "カードからの一言メッセージ（15〜30文字）",
  "reading": "鑑定文。600〜1,000文字。",
  "closing": "明日からの具体的アクション1つ（30〜60文字）"
}}

## readingの構造

### 1. カードの登場（2〜3文）
このカードが「出てきた」ことの意味を語る。「このカードがあなたの前に現れたということは〜」

### 2. カードが見せている景色（3〜5文）
カードの絵柄に描かれているシーンを語りながら、その象徴が今のこの人に何を伝えているかを読み解く。具体的な日常の場面と接続する。

### 3. 正位置/逆位置の意味（2〜3文）
正位置ならそのエネルギーがストレートに出ている。逆位置ならブロックされている or 内側に向かっている。逆位置でもネガティブで終わらない。

### 4. アクション（1〜2文）
このカードを受けて、明日から具体的に何をすればいいか。
"""

# ============================================================
# 総合鑑定プロンプト（フルコース時のみ・くろたん完全改良版）
# ============================================================
SYNTHESIS_PROMPT = """以下は一人の人物に対する各占術の鑑定結果です。
全占術が指し示す「この人の本質」を、一つの物語として昇華してください。

## 重要：闇鍋にするな
各占術の結果を列挙するな。個別の星・数字には触れるな。
全部の占術が共通して指し示す**一つのテーマ**を見つけ、それだけを語れ。
「料理の感想」であって「料理そのもの」ではない。

## 各占術の一行サマリー
- 算命学: {sanmei_headline}
- 西洋占星術: {western_headline}
- 九星気学: {kyusei_headline}
- 数秘術: {numerology_headline}
- タロット: {tarot_headline}

## 出力形式（JSON）
{{
  "headline": "この人を一言で表すフレーズ（15〜30文字）。全占術を昇華した一撃。",
  "story": "全占術が共通して語っていることを、物語として語る。3〜5文。200〜300文字。個別の占術名は出さない。「すべての星が、すべての数字が、あなたについて同じことを語っている」という驚きを演出する。",
  "message": "この人へのエール。1〜2文。心に残る締め。50〜80文字。"
}}
"""

# ============================================================
# おすすめコース生成プロンプト（裏メニュー用・据え置き）
# ============================================================
RECOMMENDATION_PROMPT = """あなたはひでさん（占いモンスターくろたんのオーナー）の軍師AI。
ひでさんが飲み屋で女性を占う時に、「どのコースで鑑定するのが一番盛り上がるか」を提案する。

相手には見えない画面で、ひでさんにだけ伝える。

## この人の占術データ
- 日干: {nichikan}（{nichikan_gogyo}性）
- 中央星: {chuo_sei}（{chuo_honno}）
- 天中殺: {tenchusatsu}
- 天中殺年該当: {is_tenchusatsu_year}
- 太陽星座: {sun_sign}（{sun_element}）
- 本命星: {honmei_sei}
- ライフパス: {life_path}
- 個人年数: {personal_year}

## 出力形式（JSON）
{{
  "recommendations": [
    {{
      "course": "算命学 or 星座 or 九星気学 or 数秘術 or タロット",
      "rank": 1,
      "reason": "ひでさんへの提案理由。なぜこのコースが盛り上がるか。2文以内。飲み屋のトークに直結する具体的な言葉を含める。",
      "opening_line": "このコースを選んだ時、ひでさんが相手に最初に言うセリフ例。1文。"
    }},
    {{
      "course": "2番目のおすすめコース名",
      "rank": 2,
      "reason": "理由",
      "opening_line": "セリフ例"
    }},
    {{
      "course": "3番目のおすすめコース名",
      "rank": 3,
      "reason": "理由",
      "opening_line": "セリフ例"
    }}
  ],
  "full_course_note": "フルコースにする場合の一言コメント。全部見せた方が面白い理由があれば書く。なければ空文字。"
}}

## 判断基準
- 「盛り上がる」が最優先。正確性や網羅性より「えっすごい！」の反応を狙う
- 特殊な結果（マスターナンバー、天中殺年、火の星座の情熱など）があるコースを優先
- opening_lineは、ひでさんがそのまま口に出せる自然な日本語にする
"""


# ============================================================
# JSON パースヘルパー
# ============================================================
def _parse_json_response(text: str) -> dict:
    """APIレスポンスからJSONを抽出してパースする"""
    if not text:
        raise ValueError("Empty API response")
    text = text.strip()

    # ```json ... ``` ブロックの除去
    fence_match = re.search(r'```(?:json)?\s*\n(.*?)\n```', text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1).strip()

    # JSONオブジェクト部分を抽出
    json_match = re.search(r'\{.*\}', text, re.DOTALL)
    if json_match:
        text = json_match.group(0)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Geminiが不正なJSON（改行やエスケープ漏れ）を返す場合の修復
        # 制御文字を除去して再試行
        cleaned = text.replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass
        # 最終手段: readingフィールドだけでも抽出
        reading_match = re.search(r'"reading"\s*:\s*"(.*?)"(?:\s*[,}])', text, re.DOTALL)
        headline_match = re.search(r'"headline"\s*:\s*"(.*?)"', text, re.DOTALL)
        closing_match = re.search(r'"closing"\s*:\s*"(.*?)"', text, re.DOTALL)
        if reading_match:
            return {
                "headline": headline_match.group(1) if headline_match else "鑑定結果",
                "reading": reading_match.group(1).replace('\\n', '\n'),
                "closing": closing_match.group(1) if closing_match else "",
            }
        raise


def _call_api(prompt: str, max_tokens: int = 2500) -> dict:
    """Gemini API 呼び出し共通処理"""
    client = _get_client()
    response = client.models.generate_content(
        model="gemini-2.5-pro",
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT_BASE,
            max_output_tokens=max_tokens + 4096,
            temperature=0.9,
            thinking_config=types.ThinkingConfig(thinking_budget=4096),
        ),
    )
    text = response.text or ""
    return _parse_json_response(text)


def _call_api_text(system: str, prompt: str, max_tokens: int = 1000) -> str:
    """Gemini API テキスト応答用（チャット向け）"""
    client = _get_client()
    response = client.models.generate_content(
        model="gemini-2.5-pro",
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=system,
            max_output_tokens=max_tokens + 4096,
            temperature=0.9,
            thinking_config=types.ThinkingConfig(thinking_budget=4096),
        ),
    )
    return response.text or ""


# ============================================================
# データフォーマットヘルパー
# ============================================================
def _format_planet_table(planets, with_house=True) -> str:
    """天体リストをMarkdownテーブル行に変換"""
    lines = []
    for p in planets:
        deg_in_sign = p.degree % 30
        deg_str = f"{int(deg_in_sign)}°{int((deg_in_sign % 1) * 60):02d}'"
        retro = " R" if p.is_retrograde else ""
        if with_house and p.house:
            lines.append(f"| {p.name} | {p.sign}{retro} | {deg_str} | {p.house}H |")
        else:
            lines.append(f"| {p.name} | {p.sign}{retro} | {deg_str} |")
    return "\n".join(lines)


def _format_aspects_list(aspects, max_orb=8.0) -> str:
    """アスペクトリストをフォーマット"""
    lines = []
    for a in aspects:
        if a.orb <= max_orb:
            lines.append(f"- {a.planet1} {a.aspect_type} {a.planet2}（orb {a.orb}°）")
    return "\n".join(lines) if lines else "なし"


def _format_retrograde_list(planets) -> str:
    """逆行天体リストをフォーマット"""
    retros = [p.name for p in planets if p.is_retrograde]
    return "、".join(retros) if retros else "なし"


# ============================================================
# 各占術の鑑定文生成（くろたん完全改良版）
# ============================================================
def generate_sanmei_reading(bundle: DivinationBundle) -> dict:
    """算命学コースの鑑定文を生成"""
    s = bundle.sanmei
    gogyo = s.gogyo_balance

    prompt = SANMEI_PROMPT.format(
        nichikan=s.nichikan,
        nichikan_gogyo=s.nichikan_gogyo,
        nichikan_inyo=s.nichikan_inyo,
        nen_kanshi=s.nen_kanshi,
        tsuki_kanshi=s.tsuki_kanshi,
        hi_kanshi=s.hi_kanshi,
        nen_kan=s.nen_kan,
        nen_shi=s.nen_shi,
        tsuki_kan=s.tsuki_kan,
        tsuki_shi=s.tsuki_shi,
        hi_shi=s.hi_shi,
        chuo_sei=s.chuo_sei,
        chuo_honno=s.chuo_honno,
        kita_sei=s.kita_sei or "不明",
        kita_honno=s.kita_honno or "不明",
        minami_sei=s.minami_sei or "不明",
        minami_honno=s.minami_honno or "不明",
        higashi_sei=s.higashi_sei or "不明",
        higashi_honno=s.higashi_honno or "不明",
        nishi_sei=s.nishi_sei or "不明",
        nishi_honno=s.nishi_honno or "不明",
        tenchusatsu=s.tenchusatsu,
        tenchusatsu_years=', '.join(str(y) for y in s.tenchusatsu_years),
        kakkyoku=s.kakkyoku or "なし",
        wood=gogyo.get("木", 0),
        fire=gogyo.get("火", 0),
        earth=gogyo.get("土", 0),
        metal=gogyo.get("金", 0),
        water=gogyo.get("水", 0),
        keywords='、'.join(s.keywords) if s.keywords else "なし",
    )
    try:
        return _call_api(prompt, max_tokens=3200)
    except Exception as e:
        print(f"[くろたん] 算命学API エラー: {e}")
        return _sanmei_fallback(bundle)


def generate_western_reading(bundle: DivinationBundle) -> dict:
    """西洋占星術コースの鑑定文を生成"""
    w = bundle.western

    if w.has_full_chart and w.planets:
        # 出生時刻あり → フルプロンプト
        planet_table = _format_planet_table(w.planets, with_house=True)
        aspects_list = _format_aspects_list(w.aspects)
        retrograde_list = _format_retrograde_list(w.planets)

        # ASC/MCの度数フォーマット
        asc_degree = ""
        mc_degree = ""
        if w.planets:
            # ASC/MCの度数はcalculate_westernの返り値から取得できないため、
            # asc_signとmc_signのみ使用
            asc_degree = w.asc_sign or ""
            mc_degree = w.mc_sign or ""

        prompt = WESTERN_FULL_PROMPT.format(
            planet_table=planet_table,
            asc_sign=w.asc_sign or "不明",
            asc_degree="",
            mc_sign=w.mc_sign or "不明",
            mc_degree="",
            aspects_list=aspects_list,
            retrograde_list=retrograde_list,
        )
    else:
        # 出生時刻なし → ベーシックプロンプト
        planet_table = _format_planet_table(w.planets, with_house=False) if w.planets else f"| 太陽 | {w.sun_sign} | - |"
        aspects_list = _format_aspects_list(w.aspects) if w.aspects else "不明"

        prompt = WESTERN_BASIC_PROMPT.format(
            planet_table=planet_table,
            aspects_list=aspects_list,
        )

    try:
        return _call_api(prompt, max_tokens=2800)
    except Exception as e:
        print(f"[くろたん] 西洋占星術API エラー: {e}")
        return _western_fallback(bundle)


def generate_kyusei_reading(bundle: DivinationBundle) -> dict:
    """九星気学コースの鑑定文を生成"""
    k = bundle.kyusei
    prompt = KYUSEI_PROMPT.format(
        honmei_sei=k.honmei_sei,
        getsu_mei_sei=k.getsu_mei_sei,
        year_position=k.year_position,
        year_theme=k.year_theme,
        lucky_direction=k.lucky_direction,
        bad_direction=k.bad_direction or "特になし",
    )
    try:
        return _call_api(prompt, max_tokens=2000)
    except Exception as e:
        print(f"[くろたん] 九星気学API エラー: {e}")
        return _kyusei_fallback(bundle)


def generate_numerology_reading(bundle: DivinationBundle) -> dict:
    """数秘術コースの鑑定文を生成"""
    n = bundle.numerology

    # 9年サイクル位置を計算
    py = n.personal_year
    cycle_position = py if py <= 9 else (py % 9 or 9)

    prompt = NUMEROLOGY_PROMPT.format(
        life_path=n.life_path,
        birthday_number=n.birthday_number,
        personal_year=n.personal_year,
        cycle_position=cycle_position,
    )
    try:
        return _call_api(prompt, max_tokens=2000)
    except Exception as e:
        print(f"[くろたん] 数秘術API エラー: {e}")
        return _numerology_fallback(bundle)


def generate_tarot_reading(bundle: DivinationBundle) -> dict:
    """タロットコースの鑑定文を生成"""
    t = bundle.tarot
    position = "逆位置" if t.is_reversed else "正位置"
    prompt = TAROT_PROMPT.format(
        card_name=t.card_name,
        card_name_en=t.card_name_en,
        card_number=t.card_number,
        position=position,
        keywords=', '.join(t.keywords),
    )
    try:
        return _call_api(prompt, max_tokens=1500)
    except Exception as e:
        print(f"[くろたん] タロットAPI エラー: {e}")
        return _tarot_fallback(bundle)


def generate_ziwei_reading(bundle: DivinationBundle) -> dict:
    """紫微斗数コースの鑑定文を生成"""
    z = bundle.ziwei
    if z is None:
        return _ziwei_fallback(bundle)

    # 命盤情報をテキスト化
    palaces_text = ""
    for p in z.palaces:
        stars = '・'.join(p.main_stars) if p.main_stars else '空宮'
        aux = '、'.join(p.aux_stars[:4]) if p.aux_stars else 'なし'
        sihua = '、'.join(p.sihua) if p.sihua else ''
        palaces_text += f"  {p.palace_name}（{p.stem}{p.branch}）: 主星={stars} / 副星={aux}"
        if sihua:
            palaces_text += f" / 四化={sihua}"
        palaces_text += "\n"

    sihua_text = '、'.join(f'{star}({hua})' for star, hua in z.sihua_assignments.items())

    # 大限のうち現在の年齢に近い部分
    current_age = date.today().year - bundle.person.birth_date.year
    current_daxian = ""
    for i, (s, e) in enumerate(z.da_xian_ages):
        if s <= current_age <= e:
            palace = z.palaces[i] if i < len(z.palaces) else None
            pname = palace.palace_name if palace else '不明'
            current_daxian = f"第{i+1}限 {s}〜{e}歳（{pname}）"
            break

    prompt = f"""あなたは紫微斗数に精通した占い師「くろたん」。
口調はカジュアルで温かく、でも鑑定は本格的。相手の人生に寄り添い、具体的に語る。

以下の命盤データから、この人の本質・才能・人生の流れを読み解いてください。

【基本情報】
- 農暦: {z.lunar_year}年{z.lunar_month}月{z.lunar_day}日 {z.birth_hour_name}
- 年干支: {z.year_stem}{z.year_branch}
- 五行局: {z.five_element_name}
- 命宮: {z.ming_gong_branch}宮
- 身宮: {z.shen_gong_branch}宮
- 大限方向: {z.da_xian_direction}
- 現在の大限: {current_daxian}
- 四化: {sihua_text}

【十二宮の配置】
{palaces_text}

【鑑定のポイント】
1. 命宮の主星から性格・本質を読む（空宮なら対宮の影響を語る）
2. 財帛宮・事業宮から仕事運・金運を読む
3. 夫妻宮から恋愛・結婚運を読む
4. 四化の配置から今世のテーマを読む（化禄=恵み、化権=力、化科=名誉、化忌=課題）
5. 現在の大限から「今」の運気を語る
6. 命宮と身宮の関係から内面と外面のギャップを指摘

JSON形式で出力:
{{"headline": "一言キャッチコピー（15字以内）", "reading": "本文（800〜1200字、改行を適切に入れる）", "closing": "締めの一言（30字以内）"}}"""

    try:
        return _call_api(prompt, max_tokens=2500)
    except Exception as e:
        print(f"[くろたん] 紫微斗数API エラー: {e}")
        return _ziwei_fallback(bundle)


def generate_recommendation(bundle: DivinationBundle) -> dict:
    """おすすめコースを生成（裏メニュー用）"""
    s = bundle.sanmei
    w = bundle.western
    k = bundle.kyusei
    n = bundle.numerology
    current_year = date.today().year

    prompt = RECOMMENDATION_PROMPT.format(
        nichikan=s.nichikan,
        nichikan_gogyo=s.nichikan_gogyo,
        chuo_sei=s.chuo_sei,
        chuo_honno=s.chuo_honno,
        tenchusatsu=s.tenchusatsu,
        is_tenchusatsu_year="該当" if current_year in s.tenchusatsu_years else "非該当",
        sun_sign=w.sun_sign,
        sun_element=w.sun_element,
        honmei_sei=k.honmei_sei,
        life_path=n.life_path,
        personal_year=n.personal_year,
    )
    try:
        return _call_api(prompt, max_tokens=800)
    except Exception as e:
        print(f"[くろたん] おすすめコース生成エラー: {e}")
        return _recommendation_fallback(bundle)


def generate_synthesis(bundle: DivinationBundle, course_results: dict) -> dict:
    """総合鑑定を生成（フルコース時のみ）"""
    t = bundle.tarot

    prompt = SYNTHESIS_PROMPT.format(
        sanmei_headline=course_results.get("sanmei", {}).get("headline", ""),
        western_headline=course_results.get("western", {}).get("headline", ""),
        kyusei_headline=course_results.get("kyusei", {}).get("headline", ""),
        numerology_headline=course_results.get("numerology", {}).get("headline", ""),
        tarot_headline=course_results.get("tarot", {}).get("headline", ""),
    )
    try:
        return _call_api(prompt, max_tokens=800)
    except Exception as e:
        print(f"[くろたん] 総合鑑定API エラー: {e}")
        return {
            "headline": "全ての星があなたに同じことを語っている",
            "story": "あなたの中にある力は、どの角度から見ても同じ光を放っている。",
            "message": "その光を信じて進んでください。",
        }


# ============================================================
# 単一コース生成
# ============================================================
def generate_single_course(bundle: DivinationBundle, course: str) -> dict:
    """指定されたコースの鑑定文を生成"""
    generators = {
        "算命学": generate_sanmei_reading,
        "星座": generate_western_reading,
        "九星気学": generate_kyusei_reading,
        "数秘術": generate_numerology_reading,
        "タロット": generate_tarot_reading,
        "紫微斗数": generate_ziwei_reading,
        "万象学": generate_bansho_reading,
    }
    gen = generators.get(course)
    if gen:
        return gen(bundle)
    return {}


# ============================================================
# フルコース生成（並列API呼び出し）
# ============================================================
def generate_full_course(bundle: DivinationBundle) -> dict:
    """全占術を並列で鑑定し、総合鑑定を生成する"""
    results = {}

    # Step 1: 6占術を並列実行
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {
            executor.submit(generate_sanmei_reading, bundle): "sanmei",
            executor.submit(generate_western_reading, bundle): "western",
            executor.submit(generate_kyusei_reading, bundle): "kyusei",
            executor.submit(generate_numerology_reading, bundle): "numerology",
            executor.submit(generate_tarot_reading, bundle): "tarot",
            executor.submit(generate_ziwei_reading, bundle): "ziwei",
        }
        for future in as_completed(futures):
            key = futures[future]
            try:
                results[key] = future.result()
            except Exception as e:
                print(f"[くろたん] {key} 並列実行エラー: {e}")
                results[key] = {}

    # Step 2: 総合鑑定（5つの結果が入力に必要なので直列）
    results["synthesis"] = generate_synthesis(bundle, results)

    return results


# ============================================================
# フォールバック鑑定文（API失敗時）
# ============================================================
def _sanmei_fallback(bundle: DivinationBundle) -> dict:
    s = bundle.sanmei
    return {
        "headline": f"{s.nichikan}の魂を持つ{s.chuo_sei}の人",
        "reading": f"あなたの日干は{s.nichikan}（{s.nichikan_gogyo}性）。{s.charm_words[0] if s.charm_words else '独自の輝きを持つ人'}。中央星は{s.chuo_sei}（{s.chuo_honno}）。{', '.join(s.keywords[:3])}が際立つ。{s.tenchusatsu}のグループ。この天中殺を知ることが、あなたの最強の武器になる。",
        "closing": "あなたの命式は、唯一無二の設計図。",
    }


def _western_fallback(bundle: DivinationBundle) -> dict:
    w = bundle.western
    reading = f"太陽星座{w.sun_sign}{w.sun_sign_symbol}。{w.sun_element}のエレメントが、あなたの本質を形作っている。"
    if w.moon_sign:
        reading += f" 月星座は{w.moon_sign}。感情の奥底にこの星座の力が宿っている。"
    if w.asc_sign:
        reading += f" ASC{w.asc_sign}——初対面の人はあなたにこの星座の印象を抱く。"
    return {
        "headline": f"{w.sun_sign}の光を纏う人",
        "reading": reading,
        "closing": "星が描いたあなたの物語は、まだ途中。",
    }


def _kyusei_fallback(bundle: DivinationBundle) -> dict:
    k = bundle.kyusei
    return {
        "headline": f"{k.honmei_sei}の運命を生きる人",
        "reading": f"{k.honmei_sei}の人。この星が持つ力があなたの人生を動かしている。月命星は{k.getsu_mei_sei}。外と中で異なる顔を持つ。2026年は「{k.year_theme}」。{k.year_desc} 吉方位「{k.lucky_direction}」に出かけてみて。",
        "closing": "気の流れを味方につけて。",
    }


def _numerology_fallback(bundle: DivinationBundle) -> dict:
    n = bundle.numerology
    return {
        "headline": f"数字{n.life_path}に導かれる人",
        "reading": f"ライフパス{n.life_path}「{n.life_path_title}」。{n.life_path_meaning} 誕生日ナンバーは{n.birthday_number}。2026年は個人年{n.personal_year}「{n.personal_year_title}」。{n.personal_year_meaning}",
        "closing": "数字があなたに囁いている。",
    }


def _tarot_fallback(bundle: DivinationBundle) -> dict:
    t = bundle.tarot
    position = "逆位置" if t.is_reversed else "正位置"
    return {
        "headline": f"{t.card_name}からのメッセージ",
        "reading": f"「{t.card_name}」（{position}）。{t.message}",
        "closing": "カードが指し示す方向に、一歩。",
    }


def _ziwei_fallback(bundle: DivinationBundle) -> dict:
    z = bundle.ziwei
    if z is None:
        return {"headline": "紫微斗数", "reading": "紫微斗数のデータがありません。出生時刻を入力してください。", "closing": ""}
    ming_palace = next((p for p in z.palaces if p.palace_name == '命宮'), None)
    ming_stars = '・'.join(ming_palace.main_stars) if ming_palace and ming_palace.main_stars else '空宮'
    sihua_text = '、'.join(f'{star}({hua})' for star, hua in z.sihua_assignments.items())
    return {
        "headline": f"{z.five_element_name}・命宮{z.ming_gong_branch}の命盤",
        "reading": f"あなたの命盤は{z.five_element_name}。命宮は{z.ming_gong_branch}宮に{ming_stars}が座する。身宮は{z.shen_gong_branch}宮。四化は{sihua_text}。大限は{z.da_xian_direction}で巡り、人生のリズムを刻む。",
        "closing": "命盤は設計図。使い方は、あなたが決める。",
    }


def _recommendation_fallback(bundle: DivinationBundle) -> dict:
    return {
        "recommendations": [
            {
                "course": "算命学",
                "rank": 1,
                "reason": f"{bundle.sanmei.chuo_sei}が出ている。性格の核心を突ける。",
                "opening_line": "ちょっと面白い星が出てるよ、見てみる？",
            },
            {
                "course": "星座",
                "rank": 2,
                "reason": f"{bundle.western.sun_sign}。星座は誰でも知ってるから入りやすい。",
                "opening_line": f"星座は{bundle.western.sun_sign}でしょ？ でも本当の意味、知ってる？",
            },
            {
                "course": "タロット",
                "rank": 3,
                "reason": "生年月日関係なく楽しめる。ビジュアルでわかりやすい。",
                "opening_line": "じゃあカード引いてみようか。今のあなたへのメッセージ。",
            },
        ],
        "full_course_note": "",
    }


# ============================================================
# テーマ別深掘り鑑定
# ============================================================

THEME_NAMES = {
    "love": "恋愛運",
    "marriage": "結婚運",
    "career": "仕事運",
    "future10": "10年後の自分",
    "shine": "最大限に自分を輝かせる生き方",
}


def _format_all_data_summary(bundle: DivinationBundle) -> str:
    """全占術データを横断的にまとめたテキストを生成（テーマ別プロンプト用）"""
    s = bundle.sanmei
    w = bundle.western
    k = bundle.kyusei
    n = bundle.numerology

    lines = []
    # 基本情報
    person = bundle.person
    if person.name or person.gender:
        info_parts = []
        if person.name:
            info_parts.append(f"名前: {person.name}")
        if person.gender:
            info_parts.append(f"性別: {person.gender}")
        lines.append("## 基本情報")
        lines.append("- " + " / ".join(info_parts))
        lines.append("")
    lines.append("## 算命学")
    lines.append(f"- 日干: {s.nichikan}（{s.nichikan_gogyo}性・{s.nichikan_inyo}）")
    lines.append(f"- 年柱: {s.nen_kanshi} / 月柱: {s.tsuki_kanshi} / 日柱: {s.hi_kanshi}")
    lines.append(f"- 中央星: {s.chuo_sei}（{s.chuo_honno}）")
    lines.append(f"- 人体図: 北={s.kita_sei} 南={s.minami_sei} 東={s.higashi_sei} 西={s.nishi_sei}")
    lines.append(f"- 天中殺: {s.tenchusatsu}（直近: {', '.join(str(y) for y in s.tenchusatsu_years)}）")
    gogyo = s.gogyo_balance
    lines.append(f"- 五行バランス: 木{gogyo.get('木',0)}・火{gogyo.get('火',0)}・土{gogyo.get('土',0)}・金{gogyo.get('金',0)}・水{gogyo.get('水',0)}")
    if s.kakkyoku:
        lines.append(f"- 特殊格局: {s.kakkyoku}")

    lines.append("\n## 西洋占星術")
    lines.append(f"- 太陽星座: {w.sun_sign}（{w.sun_element}・{w.sun_quality}）")
    if w.moon_sign:
        lines.append(f"- 月星座: {w.moon_sign}")
    if w.asc_sign:
        lines.append(f"- ASC: {w.asc_sign}")
    if w.mc_sign:
        lines.append(f"- MC: {w.mc_sign}")
    if w.planets:
        for p in w.planets:
            house_str = f" {p.house}H" if p.house else ""
            retro = " R" if p.is_retrograde else ""
            lines.append(f"- {p.name}: {p.sign}{retro}{house_str}")
    if w.aspects:
        lines.append("- 主要アスペクト:")
        for a in w.aspects[:10]:
            lines.append(f"  - {a.planet1} {a.aspect_type} {a.planet2}（orb {a.orb:.1f}°）")

    lines.append("\n## 九星気学")
    lines.append(f"- 本命星: {k.honmei_sei}")
    lines.append(f"- 月命星: {k.getsu_mei_sei}")
    lines.append(f"- 2026年: {k.year_theme}（{k.year_desc}）")
    lines.append(f"- 吉方位: {k.lucky_direction} / 凶方位: {k.bad_direction}")

    lines.append("\n## 数秘術")
    lines.append(f"- ライフパス: {n.life_path}（{n.life_path_title}）")
    lines.append(f"- 個人年: {n.personal_year}（{n.personal_year_title}）")
    lines.append(f"- 誕生日数: {n.birthday_number}")

    z = bundle.ziwei
    if z is not None:
        lines.append("\n## 紫微斗数")
        lines.append(f"- 五行局: {z.five_element_name}")
        lines.append(f"- 命宮: {z.ming_gong_branch}宮 / 身宮: {z.shen_gong_branch}宮")
        sihua_text = '、'.join(f'{star}({hua})' for star, hua in z.sihua_assignments.items())
        lines.append(f"- 四化: {sihua_text}")
        lines.append(f"- 大限方向: {z.da_xian_direction}")
        for p in z.palaces:
            if p.main_stars:
                stars = '・'.join(p.main_stars)
                sihua_str = f" [{','.join(p.sihua)}]" if p.sihua else ""
                lines.append(f"- {p.palace_name}（{p.branch}）: {stars}{sihua_str}")

    # 万象学エネルギー
    e = s.bansho_energy
    if e is not None:
        lines.append("\n## 万象学（宿命エネルギー）")
        lines.append(f"- エネルギー指数: {e.total_energy}（{e.energy_type}）")
        lines.append(f"- 第1本能: {e.top_honnou}（{e.top_score}点）")
        lines.append(f"- 第2本能: {e.second_honnou}（{e.second_score}点）")
        gogyo_parts = [f"{h}{score}点" for h, score in e.honnou_ranking]
        lines.append(f"- 五本能: {' / '.join(gogyo_parts)}")
        if e.zero_honnou:
            lines.append(f"- 0点の本能: {'・'.join(e.zero_honnou)}（生まれ持った才能ではないが努力で補える領域）")
        if e.combo_talent:
            lines.append(f"- 才能タイプ: {e.combo_talent}（{e.combo_description}）")
        lines.append(f"- {e.energy_description}")
        lines.append("※エネルギー指数の核心: 高い＝良い、低い＝悪いではない。エンジンの排気量のようなもの。軽自動車は燃費が良く小回りが利く、大型トラックはパワフルだが燃費が悪い。用途に合っているかが大事。")
        lines.append("※基準値: 平均180〜200（組織適応）。160以下=集中特化型（一点突破）。230以上=組織の枠では収まらない。300以上=規格外（複数事業・歴史的人物クラス）。")
        lines.append("※陽転（エネルギーが外向きに消化＝健全）と陰転（内向き＝愚痴・病気・不満）の概念。自分の量に合った生き方をしていないと陰転する。")
        lines.append("※第1本能と第2本能がその人の才能発揮エリア。0点の本能は消耗する領域。")

    return "\n".join(lines)


THEME_LOVE_PROMPT = """以下の全占術データをもとに、**恋愛運**に特化した鑑定文を生成してください。

{data_summary}

## テーマ: 恋愛運

以下の観点を必ず含めること:
1. **恋愛パターン** — この人が恋に落ちる瞬間、惹かれるタイプ、恋の始まり方（算命学の日干+中央星+西の星から）
2. **恋愛中の振る舞い** — 付き合うとどうなるか、愛情表現、嫉妬、距離感（月星座+金星+火星+南の星から）
3. **恋のトラップ** — この人が恋で失敗するパターン、気をつけるべきこと（五行の偏り+天中殺+アスペクトから）
4. **2026年の恋愛運** — 今年の出会い・恋の流れ（個人年+年盤+トランジットから）
5. **この人を落とすなら** — どう接すれば心を開くか（ASC+北の星+本命星から）

相手目線の具体的なシチュエーションを交えて語ること。「こういう場面であなたの心が動くでしょ？」と。

## 出力形式（JSON）
{{
  "headline": "恋愛運のキャッチフレーズ（15〜30文字）",
  "reading": "1,200〜1,800文字の鑑定文",
  "closing": "恋愛に関する締めの一言（30〜60文字）"
}}"""

THEME_MARRIAGE_PROMPT = """以下の全占術データをもとに、**結婚運**に特化した鑑定文を生成してください。

{data_summary}

## テーマ: 結婚運

以下の観点を必ず含めること:
1. **結婚観** — この人にとって結婚とは何か、理想のパートナー像（日干+MC+西の星+7H天体から）
2. **家庭での役割** — 結婚後どんなパートナーになるか、家庭内の顔（月星座+4H+南の星+六白/二黒等から）
3. **相性のいいタイプ** — 算命学的・西洋占星術的に相性がいい相手の特徴（日干の相生関係+金星星座+7H支配星から）
4. **結婚のタイミング** — いつ頃が良縁が来やすいか（天中殺+大運+個人年サイクルから）
5. **夫婦の課題** — 長く一緒にいるために気をつけること（五行の偏り+土星アスペクト+天中殺パターンから）

「この人と結婚したらどうなるか」が目に浮かぶように具体的に語ること。

## 出力形式（JSON）
{{
  "headline": "結婚運のキャッチフレーズ（15〜30文字）",
  "reading": "1,200〜1,800文字の鑑定文",
  "closing": "結婚に関する締めの一言（30〜60文字）"
}}"""

THEME_CAREER_PROMPT = """以下の全占術データをもとに、**仕事運**に特化した鑑定文を生成してください。

{data_summary}

## テーマ: 仕事運

以下の観点を必ず含めること:
1. **天職・適性** — この人が最も輝ける仕事の領域（中央星+東の星+MC+10H+日干から）
2. **働き方のスタイル** — チームか単独か、リーダーか参謀か、ルーティンか変化か（太陽星座+6H+本命星+人体図配置から）
3. **仕事での強み・弱み** — 周りから見た評価と本人が気づいていない武器（ASC+牽牛星/龍高星等+LP+アスペクトから）
4. **お金との関係** — 稼ぐ力、使い方の癖、金運の波（2H+8H+LP8等+金星+木星から）
5. **2026年の仕事運** — 転職・昇進・独立・新プロジェクトの流れ（個人年+年盤+大運から）

「あなたの才能を一番活かせる場所はここ」と具体的な職種・環境を挙げて語ること。

## 出力形式（JSON）
{{
  "headline": "仕事運のキャッチフレーズ（15〜30文字）",
  "reading": "1,200〜1,800文字の鑑定文",
  "closing": "仕事に関する締めの一言（30〜60文字）"
}}"""

THEME_FUTURE10_PROMPT = """以下の全占術データをもとに、**10年後の自分**に特化した鑑定文を生成してください。

{data_summary}

## テーマ: 10年後の自分（2036年のあなた）

以下の観点を必ず含めること:
1. **人生のフェーズ** — 今どの段階にいて、10年後はどのフェーズに入るか（大運+数秘9年サイクル+九星の回り方から）
2. **天中殺との関係** — 天中殺年を経て、その先にどんな開花が待っているか（天中殺後の展開パターンから）
3. **成長のテーマ** — 今の自分から10年後の自分へ、何を手に入れて何を手放すか（五行バランスの補完+MC+北の星から）
4. **10年後の具体像** — どんな仕事をして、どんな人間関係で、どんな場所にいるか（太陽星座+中央星+LP+本命星の組み合わせから描く未来像）
5. **今からやるべきこと** — 10年後の最高の自分に辿り着くための「今日からの一歩」（個人年+年盤の流れ+五行の補い方から）

「10年後のあなたが今のあなたに伝えたいこと」というトーンで語ること。未来は決まっているのではなく、命式が示す最高のシナリオとして語る。

## 出力形式（JSON）
{{
  "headline": "10年後の自分のキャッチフレーズ（15〜30文字）",
  "reading": "1,200〜1,800文字の鑑定文",
  "closing": "未来に関する締めの一言（30〜60文字）"
}}"""

THEME_SHINE_PROMPT = """以下の全占術データをもとに、**最大限に自分を輝かせる生き方**に特化した鑑定文を生成してください。

{data_summary}

## テーマ: 最大限に自分を輝かせる生き方

以下の観点を必ず含めること:
1. **あなたの「核」** — 全占術を横断して見える、この人の最も強い資質・才能（日干+中央星+太陽星座+LP+本命星の共通項から）
2. **輝きを曇らせているもの** — 命式が持つブレーキ、自分で気づいていない制限（五行の欠け+12H+天中殺+土星アスペクトから）
3. **輝くための環境** — どんな場所・人・状況に身を置くと最大限に輝けるか（ASC+吉方位+月星座+北の星から）
4. **輝くための行動** — 具体的にやるべきこと・やめるべきこと（五行の補い方+個人年+年盤+MCから）
5. **この人だけの輝き方** — 他の誰にも真似できない、命式が描く唯一無二の輝き方（全占術の統合。算命学×西洋×数秘×九星が重なるポイントから）

「あなたという存在の最高傑作を見せてほしい」という熱量で語ること。全占術を横断して、一つの大きなメッセージに昇華させる。これは単なるアドバイスではなく、命式が描いた「最高のシナリオ」への招待状。

## 出力形式（JSON）
{{
  "headline": "輝き方のキャッチフレーズ（15〜30文字）",
  "reading": "1,500〜2,000文字の鑑定文",
  "closing": "輝きに関する締めの一言（30〜60文字）"
}}"""

THEME_PROMPTS = {
    "love": THEME_LOVE_PROMPT,
    "marriage": THEME_MARRIAGE_PROMPT,
    "career": THEME_CAREER_PROMPT,
    "future10": THEME_FUTURE10_PROMPT,
    "shine": THEME_SHINE_PROMPT,
}

# ── 万象学 AI鑑定プロンプト（大幅強化版） ──
BANSHO_SYSTEM_PROMPT = """あなたは万象学（宿命エネルギー指数）の鑑定師。
菊池桂子『万象学入門』の知識を完全に持っている。

【万象学の核心思想】
エネルギー指数は「エンジンの排気量」。高い＝良い、低い＝悪いではない。
軽自動車（低エネルギー）は燃費が良く小回りが利く。大型トラック（高エネルギー）はパワフルだが燃費が悪い。
用途に合っているかが大事。自分のエネルギー量に合った生き方をしているかが全て。

【陽転と陰転 — 最重要概念】
- 陽転: エネルギーが外向きに消化される健全な状態。仕事・趣味・スポーツで建設的に消費。落ち着きがあり安定。
- 陰転: エネルギーが内向きに消化される不健全な状態。愚痴っぽい、不満、病気。
- 原因: 自分のエネルギー量に合わない生き方。高い人が抑え込む→爆発/病気。低い人が無理する→燃え尽き。
- 高エネルギーの陰転: パワハラ的・ワンマン・愚痴爆発・身体に出る
- 低エネルギーの陰転: 燃え尽き・「根気がない人」と見られる・命を縮める

【エネルギー帯の解説基準】
- 〜160: 集中特化型。組織不向き。一点突破の専門家。無理に組織に合わせると最悪命を縮める。
- 161〜180: 自分のペースで勝負。フリーランス・自営業向き。
- 181〜200: 組織適応型。会社勤めに最も向いている。常識にのっとって生きていける。
- 200〜230: 組織内リーダー型。管理職・役職者として輝く。会社勤めの上限ゾーン。
- 231〜300: 超活動型。組織の常識では自分を傷つける。仕事+趣味+社会活動の三本柱が必要。
- 301〜: 規格外。歴史的人物クラス。複数事業・社会的リーダーシップを同時に走らせてやっとちょうどいい。

【五本能の鑑定ルール】
- 第1本能と第2本能がその人の最大の才能発揮エリア
- 第1本能の陰陽（陽干/陰干のどちらが大きいか）でキャラクターが変わる
- 0点の本能: 生まれ持った才能ではないが「できない」わけではない。消耗する領域。得意な本能で補うのが正解。

【有名人のエネルギー指数（飲み屋トーク用・参考値）】
- 石原裕次郎: 373（規格外型。昭和を代表するスター。止まれない人の典型）
- 松たか子: 296（超活動型。女優・歌手・舞台と複数のアウトレットで燃焼）
- 中田英寿: 212（組織適応型上位。組織の中で突出するが暴走はしない。引退後に旅・酒・ビジネスで燃焼先を変えた）
- ジョン・レノン: 340超（規格外型。世界を動かすレベルの活動量が「普通」だった人）

【夫婦・親子・上司部下のエネルギー差】
- エネルギー差30以内: 自然体でいられる。ペースが合う。
- エネルギー差60以内: お互い補い合える。良い関係。
- エネルギー差100以上: 生活リズムが大きく異なる。高い方が余ったエネルギーを別で消費しないと、低い方に向けてしまう（＝DVや支配的行動の原因になりうる）。
- 夫婦: 差が大きい場合、高い方が仕事・趣味・社会活動で意識的にエネルギーを消費すること。低い方は「合わせなきゃ」と無理しないこと。
- 親子: 親が高エネルギーで子が低エネルギーの場合、「なんでもっとがんばれないの」は禁句。エンジンの排気量が違う。
- 上司部下: 高エネルギーの上司は「俺ができるんだからお前もできるだろ」が最大の地雷。部下のエネルギー量に合わせたマネジメントが必須。

【書籍の実例エピソード（鑑定文に活かすこと）】
- 160以下の人が大企業勤務を続けて胃潰瘍→退職して専門職に転向→健康回復（典型的な陰転→陽転）
- 300超の経営者が「暇が一番つらい」と語る。仕事3つ掛け持ちで初めて落ち着く。止まると病気になる。
- エネルギー差100以上の夫婦。夫（高）が妻（低）に「もっと動け」と要求→妻が疲弊→夫がゴルフ・ボランティアでエネルギーを外に向けた途端、夫婦関係が改善。

【鑑定の口調・ルール】
- 断定口調（「〜でしょ？」「〜はず。」）
- ネガティブは隠さないが「だからこそ」でポジティブ転換
- 占術の仕組み解説は不要。結論と日常への落とし込みだけ
- 具体的なシチュエーション描写を多用（「会議で〜してるでしょ？」等）
- 有名人のエネルギー指数を適宜引用して「あなたは○○と同じくらいのエネルギー」と伝える（親近感＋説得力）

【鑑定文の構成（2,000〜3,000文字）】
■ 冒頭: エネルギー指数の数字＋一言キャッチ（「あなたは○○のエンジンを持って生まれた人」）
■ エネルギー量の解説: 平均180〜200との比較、この数字が意味する生き方、組織適性
■ 五本能ランキング詳細:
  - 第1本能の才能と日常での発揮パターン（陰陽干のキャラクター含む）
  - 第2本能との掛け算で生まれる才能タイプ
  - 第3〜5本能の位置づけ
  - 0点の本能がある場合: その本能が必要な場面での消耗パターンと代替策
■ 五行バランスの偏り: 強い五行と弱い五行が生む人生パターン
■ 陽転の行動提案: このエネルギー量の人が建設的にエネルギーを使う具体的方法を3〜4つ
■ 陰転の警告サイン: 「こうなったら要注意」を2〜3つ。具体的な日常シーンで描写
■ 上司部下・夫婦関係への影響: このエネルギー量の人が周囲とどう付き合うべきか
■ 締め: この人のエネルギーに合った生き方の核心メッセージ
"""

BANSHO_USER_PROMPT = """【エネルギー診断データ】
- エネルギー指数: {total_energy}（平均: 180〜200）
- エネルギータイプ: {energy_type}
- エネルギー帯: {band_label}（{band_range}）

【五本能ランキング】
  第1: {rank1_name}（{rank1_gogyo}）{rank1_score}点 — {rank1_personality}
  第2: {rank2_name}（{rank2_gogyo}）{rank2_score}点 — {rank2_personality}
  第3: {rank3_name}（{rank3_gogyo}）{rank3_score}点
  第4: {rank4_name}（{rank4_gogyo}）{rank4_score}点
  第5: {rank5_name}（{rank5_gogyo}）{rank5_score}点

【第1本能の陰陽キャラクター】
- 支配的陰陽: {dominant_yinyang}
- キャラクター: {yinyang_character}

【才能タイプ（第1×第2の掛け算）】
{combo_section}

【0点の本能】
{zero_section}

【五行バランス】
{gogyo_balance_section}

【陽転のための行動】
{youten_actions}

【陰転の警告サイン】
{inten_signs}

このデータをもとに、2,000〜3,000文字の万象学鑑定文を生成してください。
出力はJSON形式:
{{"headline": "キャッチフレーズ（15〜30文字）", "reading": "鑑定文（2,000〜3,000文字）", "closing": "締めの一言（30〜60文字）"}}
"""


def generate_bansho_reading(bundle: DivinationBundle) -> dict:
    """万象学コースのAI鑑定文を生成"""
    from core.bansho_energy import HONNOU_DETAIL, HONNOU_MAP

    e = bundle.sanmei.bansho_energy
    if e is None:
        return _bansho_fallback(bundle)

    ranking = e.honnou_ranking

    # 各ランクの本能詳細
    def rank_info(idx):
        if idx < len(ranking):
            name, score = ranking[idx]
            detail = HONNOU_DETAIL.get(name, {})
            gogyo = detail.get("gogyo", "")
            personality = detail.get("personality", "")
            return name, gogyo, score, personality
        return "", "", 0, ""

    r1_name, r1_gogyo, r1_score, r1_personality = rank_info(0)
    r2_name, r2_gogyo, r2_score, r2_personality = rank_info(1)
    r3_name, r3_gogyo, r3_score, _ = rank_info(2)
    r4_name, r4_gogyo, r4_score, _ = rank_info(3)
    r5_name, r5_gogyo, r5_score, _ = rank_info(4)

    # 陰陽キャラクター
    yinyang_char = e.top1_yang_detail or e.top1_yin_detail or "—"

    # コンボセクション
    if e.combo_talent:
        combo_section = f"- 才能タイプ: {e.combo_talent}\n- 説明: {e.combo_description}"
    else:
        combo_section = "（組み合わせデータなし）"

    # 0点本能セクション
    if e.zero_honnou_details:
        zero_parts = []
        for zd in e.zero_honnou_details:
            zero_parts.append(f"- {zd['name']}: {zd['meaning']}。{zd['advice']}\n  代替策: {zd['alternative']}")
        zero_section = "\n".join(zero_parts)
    else:
        zero_section = "（0点の本能なし — 全本能にエネルギーが分配されている）"

    # 五行バランスセクション
    gogyo_parts = []
    for gogyo_name in ["木", "火", "土", "金", "水"]:
        gb = e.gogyo_balance.get(gogyo_name, {})
        score = gb.get("score", 0) if isinstance(gb, dict) else 0
        pct = gb.get("percent", 0) if isinstance(gb, dict) else 0
        honnou = HONNOU_MAP.get(gogyo_name, "")
        gogyo_parts.append(f"- {gogyo_name}（{honnou}）: {score}点（{pct}%）")
    gogyo_balance_section = "\n".join(gogyo_parts)

    # 陽転・陰転セクション
    bd = e.band_detail
    youten_list = bd.get("youten_actions", [])
    inten_list = bd.get("inten_signs", [])
    youten_actions = "\n".join(f"- {a}" for a in youten_list) if youten_list else "—"
    inten_signs = "\n".join(f"- {s}" for s in inten_list) if inten_list else "—"

    prompt = BANSHO_USER_PROMPT.format(
        total_energy=e.total_energy,
        energy_type=e.energy_type,
        band_label=bd.get("label", ""),
        band_range=bd.get("range", ""),
        rank1_name=r1_name, rank1_gogyo=r1_gogyo, rank1_score=r1_score, rank1_personality=r1_personality,
        rank2_name=r2_name, rank2_gogyo=r2_gogyo, rank2_score=r2_score, rank2_personality=r2_personality,
        rank3_name=r3_name, rank3_gogyo=r3_gogyo, rank3_score=r3_score,
        rank4_name=r4_name, rank4_gogyo=r4_gogyo, rank4_score=r4_score,
        rank5_name=r5_name, rank5_gogyo=r5_gogyo, rank5_score=r5_score,
        dominant_yinyang=e.dominant_yinyang,
        yinyang_character=yinyang_char,
        combo_section=combo_section,
        zero_section=zero_section,
        gogyo_balance_section=gogyo_balance_section,
        youten_actions=youten_actions,
        inten_signs=inten_signs,
    )

    try:
        client = _get_client()
        response = client.models.generate_content(
            model="gemini-2.5-pro",
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=BANSHO_SYSTEM_PROMPT,
                max_output_tokens=5000 + 4096,
                temperature=0.9,
                thinking_config=types.ThinkingConfig(thinking_budget=4096),
            ),
        )
        text = response.text or ""
        result = _parse_json_response(text)
        if result and result.get("reading"):
            return result
    except Exception as ex:
        print(f"[万象学] AI鑑定生成エラー: {ex}")

    return _bansho_fallback(bundle)


def _bansho_fallback(bundle: DivinationBundle) -> dict:
    """万象学のフォールバック鑑定文"""
    e = bundle.sanmei.bansho_energy
    if e is None:
        return {"headline": "宿命エネルギー診断", "reading": "", "closing": ""}
    return {
        "headline": f"エネルギー{e.total_energy}——{e.energy_type}の魂",
        "reading": (
            f"あなたのエネルギー指数は{e.total_energy}。{e.energy_type}。"
            f"{e.energy_description}\n\n"
            f"第1本能は{e.top_honnou}（{e.top_score}点）。これがあなたの最大の才能。"
            f"第2本能は{e.second_honnou}（{e.second_score}点）。"
            f"{'才能タイプ: ' + e.combo_talent + '。' + e.combo_description if e.combo_talent else ''}\n\n"
            f"{e.energy_advice}\n\n"
            f"エネルギーの高低に良し悪しはない。自分の量に合った生き方をすることが全て。"
        ),
        "closing": "エネルギーに逆らうな。味方につけろ。",
    }


def generate_theme_reading(bundle: DivinationBundle, theme: str) -> dict:
    """テーマ別深掘り鑑定を生成"""
    prompt_template = THEME_PROMPTS.get(theme)
    if not prompt_template:
        return {"headline": "テーマ不明", "reading": "", "closing": ""}

    data_summary = _format_all_data_summary(bundle)
    prompt = prompt_template.format(data_summary=data_summary)

    max_tokens = 3000 if theme == "shine" else 2800
    try:
        return _call_api(prompt, max_tokens=max_tokens)
    except Exception as e:
        print(f"[くろたん] テーマ別鑑定({theme}) APIエラー: {e}")
        return _theme_fallback(bundle, theme)


def _theme_fallback(bundle: DivinationBundle, theme: str) -> dict:
    """テーマ別鑑定のフォールバック"""
    s = bundle.sanmei
    w = bundle.western
    k = bundle.kyusei
    n = bundle.numerology
    theme_name = THEME_NAMES.get(theme, theme)

    if theme == "love":
        return {
            "headline": f"{w.sun_sign}の恋の仕方",
            "reading": f"太陽星座{w.sun_sign}、日干{s.nichikan}のあなた。恋に落ちる時は一気。{s.chuo_sei}の{s.chuo_honno}が恋愛でも発動する。{w.moon_sign or '月の力'}が感情を揺さぶる時、あなたの恋は始まる。2026年は個人年{n.personal_year}「{n.personal_year_title}」。{n.personal_year_meaning}",
            "closing": "あなたの恋は、あなたにしかできない恋。",
        }
    elif theme == "marriage":
        return {
            "headline": f"{s.nichikan}が築く家庭の形",
            "reading": f"日干{s.nichikan}のあなたにとって、結婚は{s.nichikan_gogyo}性の本質が最も試される場所。{s.chuo_sei}が胸にある人は、パートナーにも{s.chuo_honno}を求める。{k.honmei_sei}の人は、家庭に{k.year_theme}のエネルギーを持ち込む。",
            "closing": "一緒にいて安心できる相手が、最強のパートナー。",
        }
    elif theme == "career":
        return {
            "headline": f"LP{n.life_path}「{n.life_path_title}」の天職",
            "reading": f"ライフパス{n.life_path}のあなたは{n.life_path_meaning}。算命学の{s.chuo_sei}が仕事の核。{w.sun_sign}の{w.sun_element}エレメントが職場での存在感を決める。{k.honmei_sei}の人は{k.year_theme}の年に大きく動く。",
            "closing": "才能を活かす場所は、あなたが一番楽しい場所。",
        }
    elif theme == "future10":
        return {
            "headline": "10年後、今より確実に強い",
            "reading": f"日干{s.nichikan}は時間をかけて輝く命式。天中殺{s.tenchusatsu}を超えた先に本当の開花がある。LP{n.life_path}の9年サイクルで見ると、10年後は新たなフェーズ。{k.honmei_sei}の力が最大化する時期が必ず来る。",
            "closing": "未来のあなたが、今のあなたを誇りに思う日が来る。",
        }
    else:  # shine
        return {
            "headline": "全占術が示す、あなただけの輝き",
            "reading": f"{s.nichikan}×{w.sun_sign}×{k.honmei_sei}×LP{n.life_path}——この組み合わせは世界にあなただけ。{s.chuo_sei}の力を最大限に活かし、{w.sun_element}のエレメントが示す方向へ。吉方位「{k.lucky_direction}」に向かう時、全ての歯車が噛み合う。",
            "closing": "あなたの命式は、最高傑作の設計図。",
        }


# ============================================================
# 相性占い（関係性カテゴリ対応版）
# ============================================================

AISHO_SYSTEM_PROMPT_V2 = """あなたは「占いモンスターくろたん」。相性鑑定の専門家。
2人の命式データと関係性カテゴリに基づいて、具体的・実践的な相性鑑定を行う。

【鑑定の原則】
1. 「相性が悪い」とは絶対に言わない。「違いがある」と表現する。
2. 違いは「学び合えるポイント」として前向きに解釈する。
3. エネルギー差は数字で具体的に示す。
4. 関係性カテゴリに合わせて切り口を変える。
5. 「こうすればうまくいく」という具体的な行動提案を必ず入れる。
6. 断定口調（「〜でしょ？」「〜なはず。」）で語る。

【エネルギー差の解釈基準】
- 差30以内: ペースが合う。自然体でいられる。
- 差60以内: 補い合える良い差。
- 差100以内: 意識的にペースを合わせる努力が必要。
- 差100超: 高い方が余ったエネルギーを別で消費しないと、低い方に向けてしまう。

【点数の解釈ルール — 数字は素材、解釈が本番】
- 90〜100: 「運命だね」
- 70〜89: 「響き合えるよ、この2人」
- 40〜69: 「全然違うタイプ。だから相手が持ってないもの持ってんだよ」
- 10〜39: 「めちゃくちゃ違う。でもこの人から学べることが一番多い」
- 0〜9: 「異次元。理解できない部分にこそ、自分の盲点がある」
"""

AISHO_CATEGORY_PROMPTS = {
    'love': """
【関係性：恋愛・パートナー】
以下の観点で鑑定してください：
1. 2人が惹かれ合う理由（干合・星座の相性から）
2. 恋愛スタイルの違い（攻める/待つ、情熱型/安定型）
3. 付き合い始めのベストタイミング（天中殺を考慮）
4. 長続きさせるコツ（五本能の補完関係から）
5. 要注意ポイント（相剋・天中殺縁がある場合）
""",
    'marriage': """
【関係性：夫婦・結婚】
以下の観点で鑑定してください：
1. 夫婦としての相性の核心（エネルギー差と主導権）
2. 役割分担の最適解（五本能から見た得意分野）
3. すれ違いが起きる原因と対策
4. 家計・お金の価値観の違い
5. 子育ての方針の違い（もし子どもがいる場合）
6. 10年後の夫婦関係の展望
""",
    'boss_subordinate': """
【関係性：上司と部下】
以下の観点で鑑定してください：
1. エネルギー差から見た指導スタイルの調整（上司が高すぎると部下がつぶれる）
2. 部下の五本能に合わせた任せ方（攻撃型には裁量を、守備型には明確な指示を）
3. モチベーションの源泉の違い（名誉/お金/成長/安定/自由）
4. コミュニケーションの最適な頻度と方法
5. 上司がやりがちな失敗（「俺ができるんだからお前もできるはず」の罠）
6. 部下を最も活かすための具体的なアクション3つ
""",
    'business': """
【関係性：仕事のパートナー・取引先】
以下の観点で鑑定してください：
1. ビジネスの相性の核心（五本能の補完関係）
2. 一緒にやると強い分野・弱い分野
3. 意思決定スタイルの違い（即断型 vs 慎重型）
4. 契約・提携のベストタイミング（天中殺年を避ける）
5. 信頼構築のコツ（相手の五本能に響くアプローチ）
6. 長期的なパートナーシップの展望
""",
    'parent_child': """
【関係性：親子・家族】
以下の観点で鑑定してください：
1. エネルギー差から見た親子関係（親が高すぎると子が萎縮する理論）
2. 子どもの五本能に合った育て方（表現型の子に勉強を強制しない等）
3. 親の期待と子どもの宿命のズレ（あれば）
4. 思春期・反抗期の乗り越え方
5. 親が絶対にやってはいけないこと（エネルギー差に基づく）
6. この親子が最も良い関係を築くための具体的なアクション3つ
""",
    'friend': """
【関係性：友人・仲間】
以下の観点で鑑定してください：
1. 気が合う理由（五本能の共通点・エネルギーの近さ）
2. 一緒にやると楽しいこと（五本能の組み合わせから）
3. 友情が長続きするコツ
4. 注意すべき時期（天中殺年の付き合い方）
5. この2人でやったら成功しそうなこと
""",
}

AISHO_PROMPT_V2 = """以下の2人の全占術データと関係性をもとに、**相性鑑定**を生成してください。

## {name1}さんのデータ
{data1}

## {name2}さんのデータ
{data2}

## エネルギー比較
- {name1}さん: エネルギー{energy1}（{type1}）
- {name2}さん: エネルギー{energy2}（{type2}）
- エネルギー差: {energy_diff}
- {energy_advice}

## 相性スコア
- 総合: {score}点（{score_label}）
- {score_meaning}

## 五本能の比較
- {name1}さん: 第1={honnou1} / 第2={honnou2_a}
- {name2}さん: 第1={honnou1_b} / 第2={honnou2_b}
- {honnou_text}

{category_prompt}

## 出力形式（JSON）
{{"headline": "ふたりの相性を一言で（15〜30文字）", "reading": "本文の相性鑑定文。2,000〜3,000文字。", "closing": "ふたりへの締めの一言（30〜60文字）"}}

## 言葉のルール
- {name1}さん、{name2}さんの名前を使って語る
- 「〜かもしれません」禁止、「〜でしょ」「〜はず」で断定
- ネガティブ要素は隠さず「だからこそ」で転換
- エネルギー値の数字を具体的に引用する
- 全体を通して温かく、でも本格的な鑑定のトーンで
"""


def generate_aisho_reading(
    bundle1: DivinationBundle,
    bundle2: DivinationBundle,
    relationship: str = "love",
) -> dict:
    """相性鑑定を生成（関係性カテゴリ対応版）"""
    from core.aisho_scoring import calc_aisho_score

    name1 = bundle1.person.name or "1人目"
    name2 = bundle2.person.name or "2人目"

    data1 = _format_all_data_summary(bundle1)
    data2 = _format_all_data_summary(bundle2)

    # スコア計算
    score_result = calc_aisho_score(bundle1, bundle2, relationship)

    # エネルギー情報
    e1 = bundle1.sanmei.bansho_energy
    e2 = bundle2.sanmei.bansho_energy
    energy1 = e1.total_energy if e1 else 0
    energy2 = e2.total_energy if e2 else 0
    type1 = e1.energy_type if e1 else "不明"
    type2 = e2.energy_type if e2 else "不明"

    # 五本能
    honnou2_a = e1.second_honnou if e1 else ""
    honnou1_b = e2.top_honnou if e2 else ""
    honnou2_b = e2.second_honnou if e2 else ""

    category_prompt = AISHO_CATEGORY_PROMPTS.get(relationship, AISHO_CATEGORY_PROMPTS['love'])
    energy_adv = score_result['energy_advice']
    energy_advice_text = energy_adv.get(relationship, energy_adv.get('general', ''))

    prompt = AISHO_PROMPT_V2.format(
        name1=name1, name2=name2,
        data1=data1, data2=data2,
        energy1=energy1, energy2=energy2,
        type1=type1, type2=type2,
        energy_diff=score_result['energy_diff'],
        energy_advice=energy_advice_text,
        score=score_result['score'],
        score_label=score_result['label'],
        score_meaning=score_result['meaning'],
        honnou1=score_result['honnou1'],
        honnou2_a=honnou2_a,
        honnou1_b=honnou1_b,
        honnou2_b=honnou2_b,
        honnou_text=score_result['honnou_text'],
        category_prompt=category_prompt,
    )

    try:
        client = _get_client()
        response = client.models.generate_content(
            model="gemini-2.5-pro",
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=AISHO_SYSTEM_PROMPT_V2,
                max_output_tokens=5000 + 4096,
                temperature=0.9,
                thinking_config=types.ThinkingConfig(thinking_budget=4096),
            ),
        )
        text = response.text or ""
        result = _parse_json_response(text)
        if result and result.get("reading"):
            result["score"] = str(score_result['score'])
            result["score_label"] = score_result['label']
            result["score_result"] = score_result
            return result
    except Exception as e:
        print(f"[くろたん] 相性鑑定APIエラー: {e}")

    fb = _aisho_fallback(bundle1, bundle2)
    fb["score"] = str(score_result['score'])
    fb["score_label"] = score_result['label']
    fb["score_result"] = score_result
    return fb


def _aisho_fallback(bundle1: DivinationBundle, bundle2: DivinationBundle) -> dict:
    """相性鑑定のフォールバック"""
    n1 = bundle1.person.name or "1人目"
    n2 = bundle2.person.name or "2人目"
    s1 = bundle1.sanmei
    s2 = bundle2.sanmei
    w1 = bundle1.western
    w2 = bundle2.western

    return {
        "headline": f"{s1.nichikan}と{s2.nichikan}の出会い",
        "score": "75",
        "reading": (
            f"{n1}さんの日干は{s1.nichikan}（{s1.nichikan_gogyo}性）、"
            f"{n2}さんの日干は{s2.nichikan}（{s2.nichikan_gogyo}性）。"
            f"太陽星座は{n1}さんが{w1.sun_sign}、{n2}さんが{w2.sun_sign}。"
            f"{n1}さんの中央星{s1.chuo_sei}と{n2}さんの中央星{s2.chuo_sei}の組み合わせが、この関係の核になっている。"
            f"お互いに足りないものを補い合える関係。"
        ),
        "closing": "ふたりの星が重なる場所に、答えがある。",
    }


# ============================================================
# 後方互換: 旧 generate_reading（Phase1a 初期版との互換用）
# ============================================================
def generate_reading(bundle: DivinationBundle) -> dict:
    """
    旧インターフェース互換。裏メニュー導入後は使わない。
    """
    return generate_full_course(bundle)


# ============================================================
# 対話型タロット占い（Phase 2a）
# ============================================================

TAROT_DEEPEN_PROMPT = """あなたはベテランのタロット占い師「くろたん」。
相談者がタロットで占いたい質問をしてきた。
より深い鑑定をするために、質問を1つだけ聞き返して占的を明確にしたい。

## 相談者の質問
「{question}」

## 相談者の命式（この人を知った上で質問すること）
{person_summary}

{context}

## 指示
1. 相談者の**命式を踏まえた**共感の一言（1文）を返す。一般的な共感ではなく「あなたの星的にこうでしょ？」と鋭く当てにいく
2. 占的を深めるための質問を1つする。命式から読み取れるこの人の性質を踏まえた質問にする
3. 回答の選択肢を3個提示する（この人の命式から想定される回答パターンを含める）

## 重要
- 「なるほど」「そうなんだ」のような薄い共感は禁止
- 命式から見えるこの人の性格を活かして「あなた○○な人でしょ？だから〜」と踏み込む
- 2回目の質問では、1回目とは違う角度から深掘りする（同じような質問を繰り返すな）

## 出力（JSON）
{{
  "empathy": "命式を踏まえた共感（30〜60文字）",
  "follow_up": "深掘り質問（30〜60文字）",
  "choices": ["選択肢1", "選択肢2", "選択肢3"]
}}

## 例
質問「転職すべきか迷っています」、日干が庚（鉄・改革者）の場合:
{{
  "empathy": "あなた、本当は答え出てるでしょ。庚の人は迷ってるように見えて腹は決まってる。",
  "follow_up": "背中を押してほしいの？それとも本当にどっちかわからない？",
  "choices": ["実はもう決めてるかも", "本当にわからない", "辞めたいけど怖い"]
}}
"""


def generate_deepen_question(question: str, context: str = "", bundle=None) -> dict:
    """質問を深掘りするためのフォローアップを生成"""
    ctx = f"## これまでの会話\n{context}" if context else ""

    # 命式サマリー
    person_summary = "（命式データなし）"
    if bundle:
        try:
            s = bundle.sanmei
            w = bundle.western
            k = bundle.kyusei
            n = bundle.numerology
            lines = [
                f"- 日干: {s.nichikan}（{s.nichikan_gogyo}性）— 中央星: {s.chuo_sei}（{s.chuo_honno}）",
                f"- 太陽星座: {w.sun_sign} / 本命星: {k.honmei_sei}",
                f"- LP: {n.life_path} / 個人年: {n.personal_year}",
            ]
            person_summary = "\n".join(lines)
        except Exception:
            pass

    prompt = TAROT_DEEPEN_PROMPT.format(question=question, context=ctx, person_summary=person_summary)
    try:
        result = _call_api(prompt, max_tokens=500)
        if "choices" not in result:
            raise ValueError("choices not in response")
        return result
    except Exception:
        return {
            "empathy": "なるほど、それは気になるよね。",
            "follow_up": "もう少し詳しく教えてもらえる？どんな気持ち？",
            "choices": ["不安が大きい", "期待もある", "とにかくモヤモヤする"],
        }


TAROT_SPREAD_SELECT_PROMPT = """あなたはベテランのタロット占い師。
相談者の質問を読み、最適なタロットスプレッド（展開法）を選んでください。

## 質問
{question}

## 選べるスプレッド
1. **one_oracle**（ワンオラクル / 1枚引き）
   - Yes/No系、今日の運勢、シンプルな問い
   - positions: ["今のあなたへのメッセージ"]

2. **three_card**（スリーカード / 3枚引き）
   - 過去・現在・未来を見たい、流れを知りたい
   - positions: ["過去", "現在", "未来"]

3. **situation_advice**（状況とアドバイス / 3枚引き）
   - 今の状況を理解し対処法が知りたい
   - positions: ["現状", "課題", "アドバイス"]

4. **two_choices**（二者択一 / 3枚引き）
   - AかBか迷っている、どちらを選ぶべきか
   - positions: ["選択肢A", "選択肢B", "最終アドバイス"]

5. **celtic_mini**（ミニケルト / 5枚引き）
   - 深い悩み、人生の転機、複合的な問題
   - positions: ["現状", "障害", "顕在意識", "潜在意識", "最終結果"]

## 出力（JSON）
{{
  "spread": "three_card",
  "spread_name": "スリーカード（過去・現在・未来）",
  "n_cards": 3,
  "positions": ["過去", "現在", "未来"],
  "reason": "なぜこのスプレッドを選んだか（1〜2文）"
}}
"""


TAROT_INTERACTIVE_PROMPT = """## 相談者の質問
「{question}」

## 展開法: {spread_name}

## 引かれたカード
{cards_detail}

## 相談者の命式データ（必ず鑑定に織り込むこと）
{data_summary}

## 鑑定指示
タロットカードの解読と命式データを**融合**した鑑定を生成せよ。
カードだけの一般的な解説は禁止。必ず「この人の命式だからこそ、このカードはこう読める」という形で語れ。

### 命式活用の必須ルール
- **各カードの解読で最低1回は命式データに言及**すること
- 日干・中央星・太陽星座・ライフパスナンバーなど、相談者固有のデータとカードの意味を接続する
- 例: 「あなたは日干が辛——磨かれた宝石の人。そこにこの逆位置の塔が出ている。つまり今の環境があなたを磨いている最中だということ」
- 例: 「車騎星を中央に持つあなたに、ソードの3が出た。止まることが苦手なあなたにとって、この痛みは——」
- 天中殺年に該当する場合は必ず触れる
- 九星の年盤位置や個人年数など、「今年」に関するデータがあればカードと絡めて語る

### 構成
1. **導入**（2〜3文）
   - この相談者の命式の最大の特徴に触れつつ、カードがどう応えたかの概要
   - 「あなたの星は〇〇と語っている。そしてカードは〜」という入り方

2. **各カードの解読**（カードごとに4〜6文）
   - ポジション（{positions_str}）の意味と、そこに出たカードの意味を絡めて語る
   - 正位置/逆位置の意味を質問に直結させる
   - **必ず命式データと接続する**（「あなたの○○を考えると〜」）

3. **カード同士の物語 × 命式**（3〜5文）
   - カードの組み合わせと命式が描く一つの物語
   - 「カードと星が同じことを語っている」驚きを演出

4. **具体的アドバイス**（2〜3文）
   - 質問に対する明確な答え/方向性
   - この人の命式を踏まえた、この人だけに向けた行動指針

### 口調
目の前にいる人に語りかけるように。占い辞典の引き写しではなく、この人だけに向けた言葉で。
「〜かもしれません」禁止。「〜でしょ？」「〜はず。」で断定。

### 出力（JSON）
{{
  "headline": "カードと星が伝えるメッセージ（15〜30文字）",
  "reading": "上記構成に沿った鑑定文（2000〜3500文字）",
  "closing": "カードと星からの最後の一言（30〜60文字）"
}}
"""


# スプレッド定義（AIの選択結果が壊れた時のフォールバック用）
SPREAD_DEFAULTS = {
    "one_oracle": {
        "spread_name": "ワンオラクル",
        "n_cards": 1,
        "positions": ["今のあなたへのメッセージ"],
    },
    "three_card": {
        "spread_name": "スリーカード（過去・現在・未来）",
        "n_cards": 3,
        "positions": ["過去", "現在", "未来"],
    },
    "situation_advice": {
        "spread_name": "状況とアドバイス",
        "n_cards": 3,
        "positions": ["現状", "課題", "アドバイス"],
    },
    "two_choices": {
        "spread_name": "二者択一",
        "n_cards": 3,
        "positions": ["選択肢A", "選択肢B", "最終アドバイス"],
    },
    "celtic_mini": {
        "spread_name": "ミニケルト",
        "n_cards": 5,
        "positions": ["現状", "障害", "顕在意識", "潜在意識", "最終結果"],
    },
}


def select_tarot_spread(question: str) -> dict:
    """質問からAIが最適なスプレッドを選択"""
    prompt = TAROT_SPREAD_SELECT_PROMPT.format(question=question)
    try:
        result = _call_api(prompt, max_tokens=500)
        spread_key = result.get("spread", "three_card")
        # バリデーション
        if spread_key not in SPREAD_DEFAULTS:
            spread_key = "three_card"
        # AI結果にデフォルト値をマージ
        defaults = SPREAD_DEFAULTS[spread_key]
        return {
            "spread": spread_key,
            "spread_name": result.get("spread_name", defaults["spread_name"]),
            "n_cards": defaults["n_cards"],
            "positions": result.get("positions", defaults["positions"]),
            "reason": result.get("reason", ""),
        }
    except Exception:
        # フォールバック: スリーカード
        return {
            "spread": "three_card",
            **SPREAD_DEFAULTS["three_card"],
            "reason": "デフォルトのスリーカードで展開します。",
        }


def generate_interactive_tarot(bundle: DivinationBundle, question: str,
                                spread_info: dict, cards: list) -> dict:
    """対話型タロット: 質問×カード×全占術データで深い鑑定を生成"""
    # カード詳細テキスト生成
    cards_lines = []
    for i, card in enumerate(cards):
        pos = spread_info["positions"][i] if i < len(spread_info["positions"]) else f"カード{i+1}"
        pos_text = "逆位置" if card.is_reversed else "正位置"
        kw = "、".join(card.keywords)
        cards_lines.append(
            f"### 【{pos}】{card.card_name}（{card.card_name_en}）— {pos_text}\n"
            f"キーワード: {kw}\n"
            f"メッセージ: {card.message}"
        )
    cards_detail = "\n\n".join(cards_lines)

    # 全占術データサマリー
    data_summary = _format_all_data_summary(bundle)

    positions_str = "・".join(spread_info["positions"])

    prompt = TAROT_INTERACTIVE_PROMPT.format(
        question=question,
        spread_name=spread_info["spread_name"],
        cards_detail=cards_detail,
        data_summary=data_summary,
        positions_str=positions_str,
    )

    try:
        result = _call_api(prompt, max_tokens=3500)
        if "reading" not in result:
            raise ValueError("reading not in response")
        return result
    except Exception:
        return _interactive_tarot_fallback(question, spread_info, cards)


def _interactive_tarot_fallback(question: str, spread_info: dict, cards: list) -> dict:
    """対話型タロットのフォールバック"""
    card_names = "、".join(
        f"{c.card_name}（{'逆' if c.is_reversed else '正'}）" for c in cards
    )
    return {
        "headline": f"カードが語る答え",
        "reading": (
            f"あなたの質問「{question}」に対して、{spread_info['spread_name']}で"
            f"引かれたカードは {card_names} でした。\n\n"
            + "\n\n".join(
                f"【{spread_info['positions'][i] if i < len(spread_info['positions']) else f'カード{i+1}'}】"
                f"{c.card_name}（{'逆位置' if c.is_reversed else '正位置'}）\n"
                f"キーワード: {'、'.join(c.keywords)}\n{c.message}"
                for i, c in enumerate(cards)
            )
        ),
        "closing": "カードの声に、耳を澄ませてみて。",
    }


# ============================================================
# 開運アドバイス AI鑑定文
# ============================================================

KAIYUN_SYSTEM_PROMPT = """あなたは「占いモンスターくろたん」。開運アドバイスの専門家。
命式データと運勢データを基に、具体的・実践的な開運アドバイスを語る。

【ルール】
1. 「運が悪い」とは言わない。「準備の時期」「内側を充実させる時期」と表現する
2. 具体的な行動に落とし込む（「金運が良い」ではなく「営業・商談を積極的に入れると回収率が高い」等）
3. 天中殺年・月・日は前向きに語る（「じっくり力を蓄える時期」）
4. 飲み屋で話せるわかりやすさを保つ
5. 断定口調（「〜でしょ？」「〜なはず。」）で語る
6. エネルギー指数や五本能を使って具体的に語る
7. 相談者の名前を使って語りかける"""


def generate_kaiyun_daily_reading(
    person_name: str, person_summary: str, daily_data: str
) -> str:
    """日運のAI鑑定文を生成する（200〜400字）"""
    prompt = f"""【{person_name}さんの命式】
{person_summary}

【今日の運勢データ】
{daily_data}

以上のデータを基に、今日の開運アドバイスを200〜400字で語ってください。
具体的に「今日は何をすべきか」「何を避けるべきか」を断定口調で。
冒頭に一言キャッチコピー（15字以内）を付けてください。

出力形式（JSONで返してください）:
{{"headline": "一言キャッチコピー", "reading": "本文"}}
"""
    try:
        result = _call_api_with_system(KAIYUN_SYSTEM_PROMPT, prompt, max_tokens=800)
        if "reading" in result:
            return result
    except Exception:
        pass
    return {"headline": "", "reading": ""}


def generate_kaiyun_monthly_reading(
    person_name: str, person_summary: str, monthly_data: str
) -> str:
    """月運のAI鑑定文を生成する（300〜600字）"""
    prompt = f"""【{person_name}さんの命式】
{person_summary}

【今月の運勢データ】
{monthly_data}

以上のデータを基に、今月の開運アドバイスを300〜600字で語ってください。
「今月のテーマ」「やるべきこと3つ」「避けること」「ベストウィーク」を含めて。
仕事・人間関係・健康の3軸で具体的に。

出力形式（JSONで返してください）:
{{"headline": "今月の一言", "reading": "本文"}}
"""
    try:
        result = _call_api_with_system(KAIYUN_SYSTEM_PROMPT, prompt, max_tokens=1200)
        if "reading" in result:
            return result
    except Exception:
        pass
    return {"headline": "", "reading": ""}


def generate_kaiyun_yearly_reading(
    person_name: str, person_summary: str, yearly_data: str
) -> str:
    """年運のAI鑑定文を生成する（400〜800字）"""
    prompt = f"""【{person_name}さんの命式】
{person_summary}

【今年の運勢データ】
{yearly_data}

以上のデータを基に、今年の開運アドバイスを400〜800字で語ってください。
「今年のテーマ」「四半期ごとの過ごし方」「今年やるべき最も重要なこと1つ」を含めて。
エネルギー指数と五本能を踏まえた具体的なアドバイスを。

出力形式（JSONで返してください）:
{{"headline": "今年の一言", "reading": "本文"}}
"""
    try:
        result = _call_api_with_system(KAIYUN_SYSTEM_PROMPT, prompt, max_tokens=1500)
        if "reading" in result:
            return result
    except Exception:
        pass
    return {"headline": "", "reading": ""}


def generate_kaiyun_taiun_reading(
    person_name: str, person_summary: str, taiun_data: str
) -> str:
    """大運のAI鑑定文を生成する（500〜1000字）"""
    prompt = f"""【{person_name}さんの命式】
{person_summary}

【大運データ】
{taiun_data}

以上のデータを基に、人生の大きな流れを500〜1000字で語ってください。
特に以下を含めて：
1. 現在の大運でやるべきこと（具体的な行動）
2. 次の大運への準備（今から始めておくこと）
3. 過去の大運の振り返り（「あの時期こういうことがあったでしょ？」的な）
4. 大運天中殺がある場合はその対策

出力形式（JSONで返してください）:
{{"headline": "人生の流れの一言", "reading": "本文"}}
"""
    try:
        result = _call_api_with_system(KAIYUN_SYSTEM_PROMPT, prompt, max_tokens=2000)
        if "reading" in result:
            return result
    except Exception:
        pass
    return {"headline": "", "reading": ""}


def _call_api_with_system(system: str, prompt: str, max_tokens: int = 1500) -> dict:
    """システムプロンプト指定付きでGemini APIを呼び、JSON応答をパースする"""
    client = _get_client()
    response = client.models.generate_content(
        model="gemini-2.5-pro",
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=system,
            max_output_tokens=max_tokens + 4096,
            temperature=0.9,
            thinking_config=types.ThinkingConfig(thinking_budget=4096),
        ),
    )
    text = response.text or ""
    return _parse_json_response(text)
