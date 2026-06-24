from __future__ import annotations

import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    port: int = 9876
    host: str = "127.0.0.1"
    data_dir: str = ""

    @property
    def mappings_json_path(self) -> str:
        d = self.data_dir or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "data"
        )
        return os.path.join(d, "projects.json")

    model_config = {"env_prefix": "AWR_"}
