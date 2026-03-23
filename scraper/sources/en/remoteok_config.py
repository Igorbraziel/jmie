from enum import Enum
from dataclasses import dataclass, asdict
from typing import List

@dataclass
class RemoteOkSearchParams:
    tags: List[str]
    location: str

    def normalize_tags(self) -> str:
        """Normalize the tags into a single comma separeted string, required by Remote OK."""
        return ",".join(self.tags)

    def to_dict(self) -> dict:
        search_params_dict = {}

        for k, v in asdict(self).items():
            if v is not None:
                search_params_dict[k] = v if k != "tags" else self.normalize_tags()

        return search_params_dict