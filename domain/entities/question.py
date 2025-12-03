from __future__ import annotations

from dataclasses import dataclass
import uuid

from helpers.enums.question_types import QuestionType


@dataclass
class Question:
    id: uuid.UUID
    text: str
    question_type: QuestionType
    difficulty: float

    def set_properties(self, data: dict) -> None:
        """
        Update mutable fields from a payload, ignoring None values.

        Args:
            data (dict): Fields to update: text, question_type, difficulty.
        """
        if "text" in data and data["text"] is not None:
            self.text = data["text"]
        if "question_type" in data and data["question_type"] is not None:
            self.question_type = data["question_type"]
        if "difficulty" in data and data["difficulty"] is not None:
            self.set_difficulty(data["difficulty"])

    def set_difficulty(self, new_difficulty: float) -> None:
        """
        Validate and set difficulty.

        Args:
            new_difficulty (float): Difficulty in range [0, 5].

        Raises:
            ValueError: If the difficulty is outside the valid range.
        """
        if new_difficulty < 0 or new_difficulty > 5:
            raise ValueError("Difficulty must be between 0 and 5 inclusive.")
        self.difficulty = new_difficulty

    def to_dict(self) -> dict:
        """
        Serialize the question to a dictionary.

        Returns:
            dict: Public representation of the question.
        """
        return {
            "id": str(self.id),
            "text": self.text,
            "question_type": self.question_type.value if self.question_type else None,
            "difficulty": self.difficulty,
        }
