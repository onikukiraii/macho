import base64
import binascii
import re
from datetime import datetime

from cryptography.hazmat.primitives.asymmetric import ec
from pydantic import BaseModel, Field, field_validator

# endpoint へは worker が POST するため、Web Push のサービス以外へ要求を送らせない
_PUSH_SERVICE_HOSTS = ("fcm.googleapis.com",)
_PUSH_SERVICE_HOST_SUFFIXES = (".push.apple.com", ".push.services.mozilla.com", ".notify.windows.com")
# ホストは英数字とドットとハイフンに限る。\ や @ を含む authority は URL のパーサーごとにホストの解釈が分かれる
_ENDPOINT_PATTERN = re.compile(r"https://([a-z0-9.-]+)(?:/[^\s\\]*)?", re.IGNORECASE)
_BASE64URL_PATTERN = re.compile(r"[A-Za-z0-9_-]+={0,2}")


class PushSubscriptionCreateParams(BaseModel):
    endpoint: str = Field(min_length=1, max_length=500)
    p256dh: str = Field(max_length=88)
    auth: str = Field(max_length=24)

    @field_validator("endpoint")
    @classmethod
    def _validate_endpoint(cls, v: str) -> str:
        matched = _ENDPOINT_PATTERN.fullmatch(v)
        if matched is None:
            raise ValueError("endpoint は https の URL にしてください")
        host = matched.group(1).lower()
        is_push_service = host in _PUSH_SERVICE_HOSTS or host.endswith(_PUSH_SERVICE_HOST_SUFFIXES)
        if not is_push_service:
            raise ValueError("endpoint のホストが Web Push のサービスではありません")
        return v

    @field_validator("p256dh")
    @classmethod
    def _validate_p256dh(cls, v: str) -> str:
        decoded = _decode_base64url(v, byte_length=65)
        # 曲線上に無い点は通知を送るときの暗号化で失敗するため、登録の時点で弾く
        try:
            ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), decoded)
        except ValueError as e:
            raise ValueError("p256dh が P-256 の公開鍵ではありません") from e
        return v

    @field_validator("auth")
    @classmethod
    def _validate_auth(cls, v: str) -> str:
        _decode_base64url(v, byte_length=16)
        return v


class RestTimerStartParams(BaseModel):
    seconds: int = Field(ge=1, le=1800)
    next_set_label: str = Field(max_length=100)


class RestTimerExtendParams(BaseModel):
    seconds: int = Field(ge=1, le=600)


class RestTimerResponse(BaseModel):
    started_at: datetime
    ends_at: datetime
    total_seconds: int
    next_set_label: str


def _decode_base64url(value: str, *, byte_length: int) -> bytes:
    if _BASE64URL_PATTERN.fullmatch(value) is None:
        raise ValueError("base64url の文字列にしてください")
    unpadded = value.rstrip("=")
    try:
        decoded = base64.urlsafe_b64decode(unpadded + "=" * (-len(unpadded) % 4))
    except binascii.Error as e:
        raise ValueError("base64url としてデコードできません") from e
    if len(decoded) != byte_length:
        raise ValueError(f"デコード後の長さが {byte_length} バイトではありません")
    return decoded
