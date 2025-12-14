from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List

from domain.entities.score import Score
from domain.entities.question_answer import QuestionAnswer
from domain.services.progress import (
    CompositeProgressStrategy,
    InverseEfficiencyProgressStrategy,
)
from helpers.debugger.logger import AbstractLogger
from helpers.enums.question_types import QuestionType


class AbstractGraphicAdapter(ABC):
    """Abstract base class for graphic adapters.

    Implementations must provide methods that take domain objects and
    return dictionaries suitable for consumption by graphic libraries.
    """

    logger = AbstractLogger.get_instance()

    @abstractmethod
    def create_score_graphs(self, scores: List[Score]) -> Dict[str, dict]:
        """Generate graph definitions for activity scores.

        Args:
            scores (List[Score]): A list of score domain objects.

        Returns:
            Dict[str, dict]: A mapping keyed by a descriptive name to a
                figure dictionary (with ``data`` and ``layout`` keys).
        """
        raise NotImplementedError

    @abstractmethod
    def create_question_graphs(self, answers: List[QuestionAnswer]) -> Dict[str, dict]:
        """Generate graph definitions for answered question metrics.

        Args:
            answers (List[QuestionAnswer]): Answered questions with analysis.

        Returns:
            Dict[str, dict]: A mapping keyed by a descriptive name to a
                figure dictionary.
        """
        raise NotImplementedError


class SimplePlotlyAdapter(AbstractGraphicAdapter):
    """Concrete adapter providing basic visualisations for scores and answers.

    This implementation generates line charts for activity scores and
    answered question metrics.  It groups scores by activity type and
    further by activity identifier so that repeated activities are
    displayed as separate traces.  For answered questions, it builds a
    trace per metric across time, allowing users to track how
    linguistic and executive function metrics evolve.
    """
    LEGEND_BELOW = {
        "orientation": "h",
        "x": 0.5,
        "xanchor": "center",
        "y": -0.35,
        "yanchor": "top",
        "traceorder": "normal",
    }

    def __init__(self, progress_strategy: CompositeProgressStrategy | None = None) -> None:
        self.progress_strategy = progress_strategy or InverseEfficiencyProgressStrategy()

    def create_score_graphs(self, scores: List[Score]) -> Dict[str, dict]:
        """Create figures summarising patient scores.

        Each activity type gets its own figure containing traces for each
        distinct activity within that type.  Traces are labelled with
        the activity title (and a shortened identifier when multiple
        activities share the same type).  The x-axis corresponds to the
        completion timestamp and the y-axis to the score achieved.

        Additional figures:
            - ``scores_by_question_type``: bar chart with average score per QuestionType.
            - ``speed_<activity_type>``: line chart of seconds to finish per activity.
            - ``progress_composite``: holistic curve blending accuracy and speed via IES.

        Args:
            scores (List[Score]): All score records for the patient.

        Returns:
            Dict[str, dict]: A dictionary keyed by ``scores_<activity_type>``
                and other descriptive names containing Plotly figure definitions.
        """
        # Organise scores by activity type and activity id
        groups: Dict[str, Dict[str, Dict[str, Any]]] = {}
        type_scores: Dict[str, List[float]] = {}
        speed_groups: Dict[str, Dict[str, Dict[str, Any]]] = {}
        for s in scores:
            activity_type = s.activity.activity_type.value if s.activity.activity_type else "unknown"
            activity_id = str(s.activity.id)
            title = s.activity.title
            groups.setdefault(activity_type, {})
            groups[activity_type].setdefault(activity_id, {"title": title, "points": []})
            groups[activity_type][activity_id]["points"].append((s.completed_at, s.score))
            type_scores.setdefault(activity_type, []).append(s.score)

            speed_groups.setdefault(activity_type, {})
            speed_groups[activity_type].setdefault(activity_id, {"title": title, "points": []})
            speed_groups[activity_type][activity_id]["points"].append((s.completed_at, s.seconds_to_finish))

        figures: Dict[str, dict] = {}
        # Build one figure per activity type
        for activity_type, activities in groups.items():
            traces = []
            for activity_id, info in activities.items():
                points = sorted(info["points"], key=lambda x: x[0])
                x_vals = [p[0].isoformat() for p in points]
                y_vals = [p[1] for p in points]

                name = info["title"]
                traces.append({
                    "type": "scatter",
                    "mode": "lines+markers",
                    "name": name.replace('TEST - ', '').replace('ACTIVITAT - ', ''),
                    "x": x_vals,
                    "y": y_vals,
                })
            layout = {
                "xaxis": {"title": "Data de finalització", "automargin": True},
                "yaxis": {"title": "Puntuació", "automargin": True},
                "legend": self.LEGEND_BELOW,
                "margin": {
                    "l": 100,
                    "r": 70,
                    "t": 60,
                    "b": 120,
                },
            }
            figures[f"scores_{activity_type}"] = {"data": traces, "layout": layout}

        # Average score per question type (bar chart)
        labels_map = {
            "concentration": "Concentració",
            "speed": "Velocitat de Processament",
            "words": "Fluïdesa de Paraules",
            "sorting": "Capacitat d'Ordenament"
        }
        if type_scores:
            ordered_labels = [qt.value for qt in QuestionType if qt.value in type_scores]
            display_labels = [
                labels_map.get(label, label)
                for label in ordered_labels
            ]
            # Preserve any unknowns at the end
            for label in type_scores.keys():
                if label not in ordered_labels:
                    ordered_labels.append(label)

            avg_scores = [sum(type_scores[label]) / len(type_scores[label]) for label in ordered_labels]
            figures["scores_by_question_type"] = {
                "data": [
                    {
                        "type": "bar",
                        "x": display_labels,
                        "y": avg_scores,
                        "marker": {"color": "#1f77b4"},
                    }
                ],
                "layout": {
                    "xaxis": {"title": "Tipus de pregunta", "automargin": True},
                    "yaxis": {"title": "Puntuació mitjana", "range": [0, 10], "automargin": True},
                    "legend": self.LEGEND_BELOW,
                    "margin": {
                        "l": 100,
                        "r": 70,
                        "t": 80,
                        "b": 80,
                    }
                },
            }

        # Speed evolution per activity type (seconds to finish)
        for activity_type, activities in speed_groups.items():
            traces = []
            for activity_id, info in activities.items():
                points = sorted(info["points"], key=lambda x: x[0])
                x_vals = [p[0].isoformat() for p in points]
                y_vals = [p[1] for p in points]
                name = info["title"]
                traces.append({
                    "type": "scatter",
                    "mode": "lines+markers",
                    "name": name.replace('TEST - ', '').replace('ACTIVITAT - ', ''),
                    "x": x_vals,
                    "y": y_vals,
                })
            layout = {
                "xaxis": {"title": "Data de finalització", "automargin": True},
                "yaxis": {"title": {
                    "text": "Segons per completar<br><span style='font-size: 10px; font-weight: normal'><i>(menys és millor)</i></span>",
                    "font": {"size": 16, "color": "black"}
                }, "automargin": True},
                "legend": self.LEGEND_BELOW,
                "margin": {
                    "l": 130,
                    "r": 70,
                    "t": 80,
                    "b": 80,
                },
            }
            figures[f"speed_{activity_type}"] = {"data": traces, "layout": layout}

        # Composite progress curve blending accuracy and speed (IES-based)
        composite_series = self.progress_strategy.build_progress_series(scores)
        if composite_series:
            x_vals = [ts.isoformat() for ts, _ in composite_series]
            y_vals = [val for _, val in composite_series]
            figures["progress_composite"] = {
                "data": [
                    {
                        "type": "scatter",
                        "mode": "lines+markers",
                        "name": "Índex compost (IES)",
                        "x": x_vals,
                        "y": y_vals,
                        "line": {"shape": "spline"},
                    }
                ],
                "layout": {
                    "xaxis": {"title": "Data", "automargin": True},
                    "yaxis": {"title": "Eficiència<br><span style='font-size: 10px; font-weight: normal'><i>(més alt és millor)</i></span>", "range": [0, 1], "automargin": True},
                    "legend": self.LEGEND_BELOW,
                    "margin": {
                        "l": 130,
                        "r": 70,
                        "t": 60,
                        "b": 70,
                    },
                },
            }
        return figures

    def create_question_graphs(self, answers: List[QuestionAnswer]) -> Dict[str, dict]:
        """Create figures summarising question analysis metrics.

        Collates all analysis metrics across answered questions and
        constructs a single figure where each metric is a trace showing
        its progression over time.  If no metrics are available, an
        empty dictionary is returned.

        Args:
            answers (List[QuestionAnswer]): All answered questions for the patient.

        Returns:
            Dict[str, dict]: A dictionary with a single key
                ``question_metrics`` containing the figure definition, or
                an empty dictionary if no metrics were present.
        """
        metric_name_map = {
            "topic_adherence": "Adherència al Tema",
            "global_coherence": "Coherència Global",
            "semantic_drift": "Desviació Semàntica",
            "idea_density": "Densitat d'Idees",
            "avg_sentence_length": "Longitud Mitjana de Frase",
            "sentence_count": "Nombre de Frases",
            "noun_count": "Frequència de Substantius",
            "pronoun_count": "Frequència de Pronoms",
            "pronoun_noun_ratio": "Ràtio Pronom/Substantiu"
        }
        metrics_map: Dict[str, List[tuple]] = {}
        for answer in answers:
            for metric, value in answer.analysis.items():
                metrics_map.setdefault(metric, [])
                metrics_map[metric].append((answer.answered_at, value))

        figures: Dict[str, dict] = {}
        if not metrics_map:
            return figures
        traces = []
        for metric, points in metrics_map.items():
            pts_sorted = sorted(points, key=lambda x: x[0])
            x_vals = [p[0].isoformat() for p in pts_sorted]
            y_vals = [p[1] for p in pts_sorted]
            traces.append({
                "type": "scatter",
                "mode": "lines+markers",
                "name": metric_name_map.get(metric, metric),
                "x": x_vals,
                "y": y_vals,
            })
        layout = {
            "xaxis": {"title": "Data de resposta", "automargin": True},
            "yaxis": {"title": "Valor de la mètrica", "automargin": True},
            "legend": self.LEGEND_BELOW,
            "margin": {
                "l": 100,
                "r": 70,
                "t": 60,
                "b": 150,
            },
        }
        figures["question_metrics"] = {"data": traces, "layout": layout}
        return figures
