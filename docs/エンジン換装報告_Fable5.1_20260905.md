# エンジン換装報告: Claude Fable 5 → Claude Fable 5.1

- 報告者: こどたん(実装担当)
- 宛先: くろたん(レビュー) / ひでさん(マージ判断)
- 日付: 2026-09-05
- ステータス: **実装完了・実機テスト完了 → PRマージ待ち**

---

## 1. 変更内容

変更ファイルは `ai/interpreter.py` の1行のみ。鑑定プロンプト本文・鑑定ロジック・max_tokens・字数床(_call_api_length_floor)には一切触れていない。

| 項目 | 変更前 | 変更後 |
|---|---|---|
| `_claude_model_name()` デフォルト値 | `claude-fable-5` | `claude-fable-5-1` |

切り戻し: デフォルト値を `claude-fable-5` に戻す。またはStreamlit Cloud Secretsに `CLAUDE_MODEL="claude-fable-5"` を置けばコード変更なしで即時切り戻し可能(現在Secretsに `CLAUDE_MODEL` 行は無い=コードデフォルトが効く状態)。

## 2. Fable 5 → 5.1 の破壊的変更3点と本アプリへの影響

| 破壊的変更 | 内容 | 本アプリ |
|---|---|---|
| 強制tool_choice廃止 | `tool_choice: any/tool` が400 | **影響なし**(ツール未使用・単発テキスト生成のみ) |
| thinkingブロックのモデル拘束 | 他モデルは5.1のthinkingを読めない | **影響なし**(毎回単発リクエスト・履歴再送なし) |
| 会話プレフィックス拘束(preserved thinking) | 履歴編集で後続thinkingが無効 | **影響なし**(同上) |

その他: 価格は同一($10/$50 per MTok)、トークナイザ同一、thinking常時ON(パラメータ未指定=そのまま)、refusal stop_reasonは従来どおり `_log_claude_response_model` でログ検知。**Fable 5.xはレート制限プールを共有**するため、旧5と併走しても枠は増えない。

## 3. 実機テスト(ローカル・本番と同じ generate_single_course 経路)

テスト対象: テスト太郎 1977-07-19(出生時刻なし)、`AI_PROVIDER=claude`、`CLAUDE_MODEL` 未設定(=コードデフォルト)。

| # | コース | served model | stop_reason | reading字数 | 所要時間 |
|---|---|---|---|---|---|
| T1 | 算命学 | claude-fable-5-1 | end_turn | 2,362字 | 126秒 |
| T2 | 数秘術 | claude-fable-5-1 | end_turn | 1,714字 | 83秒 |
| T3 | 九星気学 | claude-fable-5-1 | end_turn | 1,758字 | 65秒 |

- フォールバック(Opus等への振り替え)ゼロ、字数床(1,600字)のリトライ発動ゼロ。
- Fable 5.1は1ターンが長くなる傾向あり(公式ガイド記載)。Streamlit側はスピナー表示で待つ設計のため運用上の変更は不要だが、本番ログで所要時間を継続観察する。

## 4. 本番反映手順(前回Fable 5換装の運用知見どおり)

1. PRマージ
2. Streamlit Cloud「Manage app」で**手動Reboot**(自動再デプロイは当てにならない)
3. Manage appログで `[interpreter] claude model=claude-fable-5-1 stop_reason=end_turn` を確認

## 5. スコープ外(据え置き)

- 手相(`ai/palm_interpreter.py`)は Opus 4.7ハードコードのまま(従来どおり別系統)
- `scripts/blind_engine_test.py` の4エンジン比較はFable 5のまま(馨さんブラインドテストの継続性を優先。次回テスターからは5.1へ差し替え可)
- `scripts/generate_seeds_v3.py`(古神道の種生成・完了済みバッチ)はFable 5表記のまま
