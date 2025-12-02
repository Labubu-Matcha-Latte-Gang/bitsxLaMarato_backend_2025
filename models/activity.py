import uuid

from sqlalchemy.dialects.postgresql import UUID

from db import db
from helpers.enums.question_types import QuestionType


class Activity(db.Model):
    __tablename__ = 'activities'
    __allow_unmapped__ = True
    __table_args__ = (
        db.CheckConstraint(
            'difficulty >= 0 AND difficulty <= 5',
            name='check_activity_difficulty_range',
        ),
    )

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = db.Column(db.String(255), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=False)
    activity_type = db.Column(db.Enum(QuestionType), nullable=False)
    difficulty = db.Column(db.Float, nullable=False)

    def get_id(self) -> uuid.UUID:
        """
        Get the activity ID.
        """
        return self.id

    def set_id(self, new_id: uuid.UUID) -> None:
        """
        Set the activity ID.
        Args:
            new_id (uuid.UUID): The new ID to set.
        """
        self.id = new_id

    def get_title(self) -> str:
        """
        Get the activity title.
        """
        return self.title
    
    def set_title(self, new_title: str) -> None:
        """
        Set the activity title.
        Args:
            new_title (str): The new title to set.
        """
        self.title = new_title

    def get_description(self) -> str:
        """
        Get the activity description.
        """
        return self.description
    
    def set_description(self, new_description: str) -> None:
        """
        Set the activity description.
        Args:
            new_description (str): The new description to set.
        """
        self.description = new_description

    def get_activity_type(self) -> QuestionType:
        """
        Get the activity type.
        """
        return self.activity_type

    def set_activity_type(self, new_activity_type: QuestionType) -> None:
        """
        Set the activity type.
        Args:
            new_activity_type (QuestionType): The new activity type to set.
        """
        self.activity_type = new_activity_type

    def get_difficulty(self) -> float:
        """
        Get the activity difficulty.
        """
        return self.difficulty

    def set_difficulty(self, new_difficulty: float) -> None:
        """
        Set the activity difficulty ensuring it remains within bounds.
        Args:
            new_difficulty (float): The new difficulty value (0 to 5 inclusive).
        Raises:
            ValueError: If the difficulty is outside the allowed range.
        """
        if new_difficulty < 0 or new_difficulty > 5:
            raise ValueError("Difficulty must be between 0 and 5 inclusive.")
        self.difficulty = new_difficulty

    def set_properties(self, data: dict) -> None:
        """
        Set multiple properties for the activity from a dictionary.
        Args:
            data (dict): A dictionary containing the properties to set.
        """
        if 'title' in data:
            self.set_title(data['title'])
        if 'description' in data:
            self.set_description(data['description'])
        if 'activity_type' in data:
            self.set_activity_type(data['activity_type'])
        if 'difficulty' in data:
            self.set_difficulty(data['difficulty'])

    def to_dict(self) -> dict:
        """
        Convert the question to a serializable dictionary.
        Returns:
            dict: A dictionary representation of the question.
        """
        return {
            "id": str(self.id),
            "title": self.title,
            "description": self.description,
            "activity_type": self.activity_type.value if self.activity_type else None,
            "difficulty": self.difficulty,
        }
