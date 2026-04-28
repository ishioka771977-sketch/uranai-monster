-- ============================================================
-- 占いモンスター Phase 1 Auth — DB セットアップ
-- 実行日: 2026-04-28
-- 実行者: ひでさん（Supabase SQL Editor）
-- 対象 Supabase: ky-navigator (https://koxovaejdkfkbcygriuu.supabase.co)
-- ============================================================
--
-- ⚠ 実行前確認:
--   1. プロジェクト名が「ky-navigator」であること
--   2. URL が https://koxovaejdkfkbcygriuu.supabase.co であること
--   3. 既存の users_profile / app_registry テーブルが存在していること
--
-- 実行方法:
--   Supabase Dashboard → SQL Editor → 新しいクエリ → 全文ペースト → Run
--
-- ============================================================

-- ① app_registry に占いモンスターを登録
-- （存在チェックあり、既登録なら何もしない）
INSERT INTO app_registry (id, name, url, display_order)
VALUES (
  'uranai-monster',
  '占いモンスターくろたん',
  'https://uranai-monster.streamlit.app',
  50
)
ON CONFLICT (id) DO NOTHING;

-- ② ひでさん（社員番号 0001）の enabled_apps に uranai-monster を追加
-- （既に追加されていればスキップ）
UPDATE users_profile
SET enabled_apps = array_append(enabled_apps, 'uranai-monster')
WHERE employee_number = '0001'
  AND NOT (enabled_apps @> ARRAY['uranai-monster']);

-- ③ 確認クエリ：登録結果を表示
SELECT id, name, url, display_order
  FROM app_registry
  WHERE id = 'uranai-monster';

SELECT employee_number, display_name, enabled_apps
  FROM users_profile
  WHERE employee_number = '0001';

-- ============================================================
-- 期待結果:
--   ① app_registry に1行: uranai-monster | 占いモンスターくろたん | https://uranai-monster.streamlit.app | 50
--   ② users_profile (0001) の enabled_apps に "uranai-monster" が含まれること
-- ============================================================
