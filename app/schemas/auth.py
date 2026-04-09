from pydantic import BaseModel, ConfigDict, Field


class OAuthCodeExchangeRequest(BaseModel):
    code: str = Field(..., min_length=1)


class AuthAccessTokenResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    access_token: str
    token_type: str = "bearer"
    expires_in: int


class AuthTokenResponse(AuthAccessTokenResponse):
    pass
