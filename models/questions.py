import uuid

from sqlalchemy.dialects.postgresql import UUID

from db import db
from helpers.enums.question_types import QuestionType


class Question(db.Model):
    __tablename__ = 'questions'
    __allow_unmapped__ = True
    __table_args__ = (
        db.CheckConstraint(
            'difficulty >= 0 AND difficulty <= 5',
            name='check_question_difficulty_range',
        ),
    )

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.Enum(QuestionType), nullable=False)
    difficulty = db.Column(db.Float, nullable=False)

    def get_id(self) -> uuid.UUID:
        """
        Get the question ID.
        """
        return self.id

    def set_id(self, new_id: uuid.UUID) -> None:
        """
        Set the question ID.
        Args:
            new_id (uuid.UUID): The new ID to set.
        """
        self.id = new_id

    def get_text(self) -> str:
        """
        Get the question text.
        """
        return self.text

    def set_text(self, new_text: str) -> None:
        """
        Set the question text.
        Args:
            new_text (str): The new text to set.
        """
        self.text = new_text

    def get_question_type(self) -> QuestionType:
        """
        Get the question type.
        """
        return self.question_type

    def set_question_type(self, new_question_type: QuestionType) -> None:
        """
        Set the question type.
        Args:
            new_question_type (QuestionType): The new question type to set.
        """
        self.question_type = new_question_type

    def get_difficulty(self) -> float:
        """
        Get the question difficulty.
        """
        return self.difficulty

    def set_difficulty(self, new_difficulty: float) -> None:
        """
        Set the question difficulty ensuring it remains within bounds.
        Args:
            new_difficulty (float): The new difficulty value (0 to 5 inclusive).
        Raises:
            ValueError: If the difficulty is outside the allowed range.
        """
        if new_difficulty < 0 or new_difficulty > 5:
            raise ValueError("Difficulty must be between 0 and 5 inclusive.")
        self.difficulty = new_difficulty
