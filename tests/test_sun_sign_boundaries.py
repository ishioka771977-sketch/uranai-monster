"""
太陽星座の境界判定ゴールデンテスト

書籍KB（鏡リュウジSTARMAPシリーズ・各星座の年別イングレス時刻表）の実値を使い、
core/western.py の ephem 判定が境界時刻の前後で正しい星座を返すことを検証する。

境界値の出典: 頭脳/50_知識ストック/56_URANAI-KB の期間表カード
（原典の分単位の値。書籍側に±1分程度の丸め差があるため ±10分マージンで検証）
"""
from datetime import date, datetime, timedelta

import pytest

from core.models import PersonInput
from core.western import calculate_western, EPHEM_AVAILABLE

# (星座, 入座時刻JST, 直前の星座) — 各星座のイングレス（開始）時刻
INGRESS_GOLDEN = [
    ("牡羊座", "1988-03-20 18:39", "魚座"),
    ("牡牛座", "1996-04-20 04:11", "牡羊座"),
    ("双子座", "1996-05-21 03:24", "牡牛座"),
    ("蟹座",   "1996-06-21 11:24", "双子座"),
    ("獅子座", "1996-07-22 22:20", "蟹座"),
    ("乙女座", "1996-08-23 05:22", "獅子座"),
    ("天秤座", "1996-09-23 03:01", "乙女座"),
    ("蠍座",   "1996-10-23 12:20", "天秤座"),
    ("射手座", "1996-11-22 09:50", "蠍座"),
    ("山羊座", "1996-12-21 23:07", "射手座"),
    ("水瓶座", "1996-01-21 03:53", "山羊座"),
    ("魚座",   "1996-02-19 18:01", "水瓶座"),
]

MARGIN = timedelta(minutes=10)


def _sun_sign_at(dt: datetime) -> str:
    person = PersonInput(
        name="境界テスト",
        birth_date=date(dt.year, dt.month, dt.day),
        birth_time=dt.strftime("%H:%M"),
        birth_place="東京",
    )
    return calculate_western(person).sun_sign


@pytest.mark.skipif(not EPHEM_AVAILABLE, reason="ephem未導入環境ではテーブル判定のためスキップ")
@pytest.mark.parametrize("sign,ingress,prev_sign", INGRESS_GOLDEN)
def test_ingress_boundary(sign, ingress, prev_sign):
    t = datetime.strptime(ingress, "%Y-%m-%d %H:%M")
    after = _sun_sign_at(t + MARGIN)
    before = _sun_sign_at(t - MARGIN)
    assert after == sign, f"{ingress}+10分は{sign}のはずが{after}"
    assert before == prev_sign, f"{ingress}-10分は{prev_sign}のはずが{before}"
