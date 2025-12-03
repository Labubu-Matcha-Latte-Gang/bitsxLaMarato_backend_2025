from __future__ import annotations

from dataclasses import dataclass
import uuid

from helpers.enums.question_types import QuestionType


@dataclass
class Activity:
    id: uuid.UUID
    title: str
    description: str
    activity_type: QuestionType
    difficulty: float

    def set_properties(self, data: dict) -> None:
        if "title" in data and data["title"] is not None:
            self.title = data["title"]
        if "description" in data and data["description"] is not None:
            self.description = data["description"]
        if "activity_type" in data and data["activity_type"] is not None:
            self.activity_type = data["activity_type"]
        if "difficulty" in data and data["difficulty"] is not None:
            self.set_difficulty(data["difficulty"])

    def set_difficulty(self, new_difficulty: float) -> None:
        if new_difficulty < 0 or new_difficulty > 5:
            raise ValueError("Difficulty must be between 0 and 5 inclusive.")
        self.difficulty = new_difficulty

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "title": self.title,
            "description": self.description,
            "activity_type": self.activity_type.value if self.activity_type else None,
            "difficulty": self.difficulty,
        }
