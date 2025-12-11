"""
Domain strategy interfaces.
"""
from .metrics_normaliser_strategy import IMetricsNormaliserStrategy
from .gender_parser_strategy import IGenderParserStrategy

__all__ = ["IMetricsNormaliserStrategy", "IGenderParserStrategy"]
