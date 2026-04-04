"""
全占術エンジンのテスト
ひでさん（1977年5月24日）のデータで正解を確認する
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import date
from core.models import PersonInput
from core.sanmei import calculate_sanmei
from core.western import calculate_western
from core.kyusei import calculate_kyusei
from core.numerology import calculate_numerology
from core.tarot import draw_tarot

# ============================================================
# テストデータ
# ============================================================
HIDESAN = PersonInput(
    birth_date=date(1977, 5, 24),
    birth_time="01:34",
    birth_place="函館市",
    blood_type="A",
    name="石岡秀貴"
)

# 立春前テスト用
RISSHUN_BEFORE = PersonInput(birth_date=date(1990, 1, 15))  # 立春前→1989年扱い
BOUNDARY = PersonInput(birth_date=date(2000, 3, 21))         # 牡羊座境界日


def test_sanmei_hidesan():
    print("=" * 60)
    print("■ 算命学テスト（ひでさん: 1977/5/24）")
    print("=" * 60)
    r = calculate_sanmei(HIDESAN)
    print(f"  年柱: {r.nen_kanshi}  （期待値: 丁巳）")
    print(f"  月柱: {r.tsuki_kanshi}  （期待値: 乙巳）")
    print(f"  日柱: {r.hi_kanshi}  （期待値: 辛巳）")
    print(f"  日干: {r.nichikan}  （期待値: 辛）")
    print(f"  五行: {r.nichikan_gogyo}  （期待値: 金）")
    print(f"  陰陽: {r.nichikan_inyo}  （期待値: 陰）")
    print(f"  中央星: {r.chuo_sei}  （期待値: 牽牛星）")
    print(f"  本能: {r.chuo_honno}  （期待値: 攻撃本能）")
    print(f"  天中殺: {r.tenchusatsu}  （期待値: 申酉天中殺）")
    print(f"  天中殺年: {r.tenchusatsu_years}")
    print(f"  キーワード: {r.keywords}")
    print(f"  褒め言葉: {r.charm_words}")

    # 正解チェック
    assert r.nen_kanshi == "丁巳", f"年柱エラー: {r.nen_kanshi}"
    assert r.hi_kanshi == "辛巳", f"日柱エラー: {r.hi_kanshi}"
    assert r.nichikan == "辛", f"日干エラー: {r.nichikan}"
    assert r.nichikan_gogyo == "金", f"五行エラー: {r.nichikan_gogyo}"
    assert r.chuo_sei == "牽牛星", f"中央星エラー: {r.chuo_sei}"
    assert r.tenchusatsu == "申酉天中殺", f"天中殺エラー: {r.tenchusatsu}"
    print("  ✓ 算命学: 全項目正解！")
    return r


def test_sanmei_risshun():
    print("\n■ 算命学テスト（立春前: 1990/1/15）")
    r = calculate_sanmei(RISSHUN_BEFORE)
    print(f"  年柱: {r.nen_kanshi}  （立春前なので1989年扱い→己巳）")
    print(f"  日柱: {r.hi_kanshi}")
    print(f"  天中殺: {r.tenchusatsu}")


def test_western_hidesan():
    print("\n" + "=" * 60)
    print("■ 西洋占星術テスト（ひでさん: 1977/5/24）")
    print("=" * 60)
    r = calculate_western(HIDESAN)
    print(f"  太陽星座: {r.sun_sign} {r.sun_sign_symbol}  （期待値: 双子座 ♊）")
    print(f"  エレメント: {r.sun_element}  （期待値: 風）")
    print(f"  クオリティ: {r.sun_quality}  （期待値: 柔軟宮）")
    print(f"  月星座: {r.moon_sign}")
    print(f"  キーワード: {r.keywords}")

    assert r.sun_sign == "双子座", f"太陽星座エラー: {r.sun_sign}"
    assert r.sun_element == "風", f"エレメントエラー: {r.sun_element}"
    print("  ✓ 西洋占星術: 正解！")
    return r


def test_western_boundary():
    print("\n■ 西洋占星術テスト（境界日: 2000/3/21）")
    r = calculate_western(BOUNDARY)
    print(f"  太陽星座: {r.sun_sign}  （期待値: 牡羊座）")


def test_kyusei_hidesan():
    print("\n" + "=" * 60)
    print("■ 九星気学テスト（ひでさん: 1977/5/24）")
    print("=" * 60)
    r = calculate_kyusei(HIDESAN)
    print(f"  本命星: {r.honmei_sei}  （期待値: 五黄土星）")
    print(f"  月命星: {r.getsu_mei_sei}  （期待値: 八白土星）")
    print(f"  2026年位置: {r.year_position}")
    print(f"  2026年テーマ: {r.year_theme}")
    print(f"  2026年説明: {r.year_desc}")
    print(f"  吉方位: {r.lucky_direction}")
    print(f"  キーワード: {r.keywords}")

    assert r.honmei_sei == "五黄土星", f"本命星エラー: {r.honmei_sei}"
    assert r.getsu_mei_sei == "八白土星", f"月命星エラー: {r.getsu_mei_sei}"
    print("  ✓ 九星気学: 正解！")
    return r


def test_numerology_hidesan():
    print("\n" + "=" * 60)
    print("■ 数秘術テスト（ひでさん: 1977/5/24）")
    print("=" * 60)
    r = calculate_numerology(HIDESAN, target_year=2026)
    print(f"  ライフパス: {r.life_path}  （期待値: 8）")
    print(f"  LP タイトル: {r.life_path_title}  （期待値: 達成者）")
    print(f"  LP 意味: {r.life_path_meaning}")
    print(f"  個人年数: {r.personal_year}  （期待値: 3）")
    print(f"  個人年タイトル: {r.personal_year_title}  （期待値: 表現の年）")
    print(f"  個人年意味: {r.personal_year_meaning}")
    print(f"  キーワード: {r.keywords}")

    assert r.life_path == 8, f"ライフパスエラー: {r.life_path}"
    assert r.personal_year == 3, f"個人年数エラー: {r.personal_year}"
    print("  ✓ 数秘術: 正解！")
    return r


def test_tarot():
    print("\n" + "=" * 60)
    print("■ タロットテスト")
    print("=" * 60)
    # 固定シードでテスト
    results = draw_tarot(1, seed=42)
    r = results[0]
    print(f"  カード名: {r.card_name}（{r.card_name_en}）")
    print(f"  カード番号: {r.card_number}")
    print(f"  逆位置: {r.is_reversed}")
    print(f"  キーワード: {r.keywords}")
    print(f"  メッセージ: {r.message}")

    # ランダムで3回引いてみる
    print("\n  ランダムドロー3回:")
    for i in range(3):
        res = draw_tarot(1)
        pos = "逆" if res[0].is_reversed else "正"
        print(f"    {i+1}. {res[0].card_name}（{pos}位置）")

    print("  ✓ タロット: 動作OK！")
    return r


if __name__ == "__main__":
    print("=" * 60)
    print("占いモンスターくろたん Phase 1a - 全エンジンテスト")
    print("=" * 60)

    try:
        sanmei = test_sanmei_hidesan()
        test_sanmei_risshun()
        western = test_western_hidesan()
        test_western_boundary()
        kyusei = test_kyusei_hidesan()
        numerology = test_numerology_hidesan()
        tarot = test_tarot()

        print("\n" + "=" * 60)
        print("✓ 全テスト完了！ひでさんデータで全占術が正解しました")
        print("=" * 60)
        print(f"""
【ひでさん（1977/5/24）の鑑定サマリー】
  算命学: 日柱={sanmei.hi_kanshi} / 中央星={sanmei.chuo_sei} / {sanmei.tenchusatsu}
  西洋占星術: 太陽={western.sun_sign} {western.sun_sign_symbol}
  九星気学: {kyusei.honmei_sei} / 2026年={kyusei.year_theme}
  数秘術: ライフパス{numerology.life_path}（{numerology.life_path_title}）/ 個人年{numerology.personal_year}
  タロット: {tarot.card_name}（{'逆位置' if tarot.is_reversed else '正位置'}）
""")

    except AssertionError as e:
        print(f"\n✗ テスト失敗: {e}")
        sys.exit(1)
    except Exception as e:
        import traceback
        print(f"\n✗ エラー: {e}")
        traceback.print_exc()
        sys.exit(1)
