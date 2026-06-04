"""Question discovery and loading for QueryRank."""

from __future__ import annotations

import importlib.util
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


QUESTIONS_DIR = Path(__file__).parent.parent.parent / "questions"


@dataclass
class QuestionConfig:
    id: str
    title: str
    difficulty: str          # easy | medium | hard
    tags: list[str]
    default_dataset_size: str = "medium"   # small | medium | large
    description: str = ""


@dataclass
class Question:
    config: QuestionConfig
    path: Path
    prompt: str
    references: list[Path] = field(default_factory=list)

    @property
    def id(self) -> str:
        return self.config.id

    # ------------------------------------------------------------------

    def setup_schema(self, conn) -> None:  # type: ignore[no-untyped-def]
        """Import schema.py and call create_schema(conn)."""
        mod = _load_module(self.path / "schema.py")
        mod.create_schema(conn)

    def generate_data(self, conn, size: str = "medium") -> None:  # type: ignore[no-untyped-def]
        """Import generate_data.py and call generate(conn, size)."""
        mod = _load_module(self.path / "generate_data.py")
        mod.generate(conn, size)


# ------------------------------------------------------------------
# Discovery helpers
# ------------------------------------------------------------------

def list_questions() -> list[Question]:
    """Return all questions found in the questions/ directory."""
    questions = []
    if not QUESTIONS_DIR.exists():
        return questions
    for d in sorted(QUESTIONS_DIR.iterdir()):
        if d.is_dir() and (d / "config.json").exists():
            q = _load_question(d)
            if q:
                questions.append(q)
    return questions


def get_question(question_id: str) -> Optional[Question]:
    """Return a single question by ID, or None if not found."""
    for q in list_questions():
        if q.id == question_id:
            return q
    return None


def _load_question(path: Path) -> Optional[Question]:
    try:
        raw = json.loads((path / "config.json").read_text())
        config = QuestionConfig(**raw)
        prompt = (path / "prompt.md").read_text()
        refs = sorted((path / "references").glob("*.sql")) if (path / "references").exists() else []
        return Question(config=config, path=path, prompt=prompt, references=refs)
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] Could not load question from {path}: {exc}")
        return None


def _load_module(py_path: Path):  # type: ignore[return]
    """Dynamically import a Python file as a module."""
    spec = importlib.util.spec_from_file_location("_qmodule", py_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {py_path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_qmodule"] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod
