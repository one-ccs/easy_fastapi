"""i18n 扩展配置。"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, model_validator


class I18nConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    default_locale: str = "zh_CN"
    available_locales: list[str] = ["zh_CN", "en_US"]

    @model_validator(mode="after")
    def _validate_default_locale(self) -> I18nConfig:
        if self.default_locale not in self.available_locales:
            raise ValueError(
                f"default_locale '{self.default_locale}' must be in available_locales {self.available_locales}"
            )
        return self
