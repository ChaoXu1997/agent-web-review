from __future__ import annotations

import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    port: int = 9876
    admin_token: str = ""
    data_dir: str = ""

    @property
    def database_url(self) -> str:
        d = self.data_dir or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "data"
        )
        return os.path.join(d, "awr.db")

    model_config = {"env_prefix": "AWR_"}
