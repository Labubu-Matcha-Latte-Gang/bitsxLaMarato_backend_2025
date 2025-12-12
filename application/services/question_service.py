from __future__ import annotations

import uuid
from random import choice
from typing import List

from domain.entities.question import Question
from domain.entities.user import Patient
from domain.repositories import IQuestionRepository, IScoreRepository, ITranscriptionAnalysisRepository, IQuestionAnswerRepository
from domain.services.recommendation import DailyQuestionFilterStrategy
from domain.unit_of_work import IUnitOfWork
from domain.entities.question_answer import QuestionAnswer
from helpers.exceptions.question_exceptions import (
    QuestionCreationException,
    QuestionNotFoundException,
    QuestionUpdateException,
    QuestionAnswerPersistenceException,
)


class QuestionService:
    def __init__(
        self,
        question_repo: IQuestionRepository,
        uow: IUnitOfWork,
        score_repo: IScoreRepository,
        transcription_repo: ITranscriptionAnalysisRepository,
        question_answer_repo: IQuestionAnswerRepository,
    ) -> None:
        self.question_repo = question_repo
        self.uow = uow
        self.score_repo = score_repo
        self.transcription_repo = transcription_repo
        self.question_answer_repo = question_answer_repo

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

    def record_answer(
        self,
        patient: Patient,
        question_id: uuid.UUID,
        answer_text: str,
        analysis: dict[str, float] | None = None,
    ) -> QuestionAnswer:
        """
        Persist the patient's answer to a question along with analysed metrics.
        """
        question = self.question_repo.get(question_id)
        if not question:
            raise QuestionNotFoundException(
                f"No s'ha trobat cap pregunta amb l'ID {question_id}."
            )

        if not answer_text or not answer_text.strip():
            raise QuestionAnswerPersistenceException("La resposta transcrita és buida.")

        metrics = analysis or {}
        try:
            with self.uow:
                answer = self.question_answer_repo.record_answer(
                    patient=patient,
                    question=question,
                    answer_text=answer_text.strip(),
                    analysis=metrics,
                )
                # Guardar també les mètriques agregades perquè les estratègies les puguin reutilitzar.
                self.transcription_repo.record_session(patient.email, metrics)
                self.uow.commit()
            return answer
        except QuestionNotFoundException:
            raise
        except Exception as exc:
            raise QuestionAnswerPersistenceException(
                f"No s'ha pogut guardar la resposta del pacient: {str(exc)}"
            ) from exc

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

    def get_diary_question(self) -> Question:
        question = self.question_repo.get_diary_question()
        if not question:
            raise QuestionNotFoundException(
                "No hi ha cap pregunta del diari disponible a la base de dades."
            )
        return question