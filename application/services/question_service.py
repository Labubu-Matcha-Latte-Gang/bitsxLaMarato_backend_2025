from __future__ import annotations

import uuid
from random import choice
from typing import List

from domain.entities.question import Question
from domain.entities.user import Patient
from domain.repositories import IQuestionRepository, IScoreRepository, ITranscriptionAnalysisRepository
from domain.services.recommendation import DailyQuestionFilterStrategy
from domain.unit_of_work import IUnitOfWork
from helpers.exceptions.question_exceptions import (
    QuestionCreationException,
    QuestionNotFoundException,
    QuestionUpdateException,
)


class QuestionService:
    def __init__(
        self,
        question_repo: IQuestionRepository,
        uow: IUnitOfWork,
        score_repo: IScoreRepository,
        transcription_repo: ITranscriptionAnalysisRepository,
    ) -> None:
        self.question_repo = question_repo
        self.uow = uow
        self.score_repo = score_repo
        self.transcription_repo = transcription_repo

    def create_questions(self, payloads: List[dict]) -> List[Question]:
        try:
            questions = [
                Question(
                    id=uuid.uuid4(),
                    text=payload["text"],
                    question_type=payload["question_type"],
                    difficulty=payload["difficulty"],
                )
                for payload in payloads
            ]
            with self.uow:
                self.question_repo.add_many(questions)
                self.uow.commit()
            return questions
        except Exception as exc:
            raise QuestionCreationException(
                f"No s'han pogut crear les preguntes: {str(exc)}"
            ) from exc

    def list_questions(self, filters: dict) -> List[Question]:
        questions = self.question_repo.list(filters)
        if filters.get("id") and not questions:
            raise QuestionNotFoundException(
                f"No s'ha trobat cap pregunta amb l'ID {filters.get('id')}."
            )
        return questions

    def update_question(self, question_id: uuid.UUID, update_data: dict) -> Question:
        question = self.question_repo.get(question_id)
        if not question:
            raise QuestionNotFoundException(
                f"No s'ha trobat cap pregunta amb l'ID {question_id}."
            )
        try:
            question.set_properties(update_data)
            with self.uow:
                self.question_repo.update(question)
                self.uow.commit()
            return question
        except Exception as exc:
            raise QuestionUpdateException(
                f"No s'ha pogut actualitzar la pregunta: {str(exc)}"
            ) from exc

    def delete_question(self, question_id: uuid.UUID) -> None:
        question = self.question_repo.get(question_id)
        if not question:
            raise QuestionNotFoundException(
                f"No s'ha trobat cap pregunta amb l'ID {question_id}."
            )
        with self.uow:
            self.question_repo.remove(question)
            self.uow.commit()

    def get_daily_question(self, patient: Patient, strategy: DailyQuestionFilterStrategy | None = None) -> Question:
        if not strategy:
            from domain.services.recommendation import ScoreBasedQuestionStrategy
            strategy = ScoreBasedQuestionStrategy()
        try:
            filters = patient.get_daily_question_filters(
                strategy=strategy,
                score_repo=self.score_repo,
                transcription_repo=self.transcription_repo,
            )
        except ValueError:
            filters = {}
        questions = self.question_repo.list(filters)
        if not questions:
            questions = self.question_repo.list({})
        if not questions:
            raise QuestionNotFoundException(
                "No hi ha preguntes disponibles a la base de dades."
            )
        return choice(questions)
