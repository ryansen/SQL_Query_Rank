"""Local user profile management for QueryRank."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


def _profile_path() -> Path:
    base = Path(os.getenv("QUERYRANK_HOME", Path.home() / ".queryrank"))
    base.mkdir(parents=True, exist_ok=True)
    return base / "profile.json"


@dataclass
class UserProfile:
    username: str
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    questions_attempted: list[str] = field(default_factory=list)
    questions_passed: list[str] = field(default_factory=list)
    best_scores: dict[str, float] = field(default_factory=dict)

    # ---------- persistence ----------

    def save(self) -> None:
        _profile_path().write_text(json.dumps(asdict(self), indent=2))

    @classmethod
    def load(cls) -> Optional["UserProfile"]:
        path = _profile_path()
        if not path.exists():
            return None
        data = json.loads(path.read_text())
        return cls(**data)

    @classmethod
    def delete(cls) -> None:
        path = _profile_path()
        if path.exists():
            path.unlink()

    # ---------- helpers ----------

    def record_attempt(self, question_id: str, score: float, passed: bool) -> None:
        if question_id not in self.questions_attempted:
            self.questions_attempted.append(question_id)
        if passed and question_id not in self.questions_passed:
            self.questions_passed.append(question_id)
        prev = self.best_scores.get(question_id, 0.0)
        if score > prev:
            self.best_scores[question_id] = round(score, 1)
        self.save()

    @property
    def total_score(self) -> float:
        return sum(self.best_scores.values())

    @property
    def pass_rate(self) -> float:
        if not self.questions_attempted:
            return 0.0
        return len(self.questions_passed) / len(self.questions_attempted) * 100
