-- ===============================================================
-- Migration: 2026-05-04
-- 同名異人を区別するため customers の UNIQUE 制約を変更
-- 旧: (user_id, name)         ← 同名で上書きバグの原因
-- 新: (user_id, name, birth_year, birth_month, birth_day)
-- ===============================================================

-- 1. 旧制約を削除（存在すれば）
ALTER TABLE customers DROP CONSTRAINT IF EXISTS customers_user_id_name_key;

-- 2. 新しい複合ユニーク制約を追加
ALTER TABLE customers
  ADD CONSTRAINT customers_user_id_name_birth_key
  UNIQUE (user_id, name, birth_year, birth_month, birth_day);

-- 3. 確認用クエリ（実行後に SELECT で確認すると良い）
-- SELECT conname, contype FROM pg_constraint WHERE conrelid = 'customers'::regclass;
