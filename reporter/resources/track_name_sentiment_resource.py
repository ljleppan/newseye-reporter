import logging
from typing import List, Type, Dict, Tuple

from reporter.core.models import Fact, Message
from reporter.core.realize_slots import SlotRealizerComponent
from reporter.newspaper_message_generator import TaskResult
from reporter.resources.processor_resource import ProcessorResource

log = logging.getLogger("root")


TEMPLATE = """
en: the most negative sentiment towards {result_key} ( {result_value} ) occurred at {timestamp} {analysis_id}
| analysis_type = TrackNameSentiment:Min

en: the most positive sentiment towards {result_key} ( {result_value} ) occurred at {timestamp} {analysis_id}
| analysis_type = TrackNameSentiment:Max

en: the mean sentiments towards {result_key} between {timestamp_from} and {timestamp_to}  was {result_value} {analysis_id}
| analysis_type = TrackNameSentiment:Mean

en: {result_key} was discussed during {result_value} distinct years between {timestamp_from} and {timestamp_to} {analysis_id}
| analysis_type = TrackNameSentiment:CountYears
"""  # noqa: E501


class TrackNameSentimentResource(ProcessorResource):
    def templates_string(self) -> str:
        return TEMPLATE

    def parse_messages(self, task_result: TaskResult, context: List[TaskResult], language: str) -> List[Message]:

        language = language.split("-")[0]

        if not task_result.processor == "TrackNameSentiment":
            return []

        corpus, corpus_type = self.build_corpus_fields(task_result)

        entries: Dict[str, Dict[int, Tuple[float, float]]] = {}
        for entity in task_result.task_result["result"]:
            print("ENTITY:", entity)
            entity_name_map: Dict[str, str] = task_result.task_result["result"][entity].get("names", {})
            entity_name_priority_list = [
                entity_name_map.get(language, None),
                entity_name_map.get("en", None),
                list(entity_name_map.values())[0] if list(entity_name_map.values()) else None,
                entity,
            ]
            name = next(name for name in entity_name_priority_list if name)

            years: Dict[int, Tuple[float, float]] = {}
            for year in task_result.task_result["result"][entity]:
                if year == "names":
                    # Skip the names-map
                    continue
                sentiment = task_result.task_result["result"][entity][year]
                interestingness = task_result.task_result["interestingness"][entity][year]
                if sentiment != 0 or interestingness != 0:
                    years[int(year)] = (sentiment, interestingness)

            entries[name] = years

        messages: List[Message] = []

        for entry, years in entries.items():
            if not years:
                continue
            max_interestingness = max(interestingness for (year, (sentiment, interestingness)) in years.items())
            max_sentiment, max_sentiment_year = max(
                (sentiment, year) for (year, (sentiment, interestingness)) in years.items()
            )
            min_sentiment, min_sentiment_year = min(
                (sentiment, year) for (year, (sentiment, interestingness)) in years.items()
            )
            mean_sentiment = sum(sentiment for (year, (sentiment, interestingness)) in years.items()) / len(years)
            min_year = min(years)
            max_year = max(years)
            year_count = len(years)

            messages.append(
                Message(
                    Fact(
                        corpus,
                        corpus_type,
                        min_year,
                        max_year,
                        "between_years",
                        "TrackNameSentiment:CountYears",
                        "[ENTITY:NAME:{}]".format(entry),
                        year_count,
                        max_interestingness,
                        "[LINK:{}]".format(task_result.uuid),  # uuid
                    )
                )
            )

            messages.append(
                Message(
                    Fact(
                        corpus,
                        corpus_type,
                        min_year,
                        max_year,
                        "between_years",
                        "TrackNameSentiment:Mean",
                        "[ENTITY:NAME:{}]".format(entry),
                        mean_sentiment,
                        max_interestingness,
                        "[LINK:{}]".format(task_result.uuid),  # uuid
                    )
                )
            )

            messages.append(
                Message(
                    Fact(
                        corpus,
                        corpus_type,
                        min_sentiment_year,
                        min_sentiment_year,
                        "during_year",
                        "TrackNameSentiment:Min",
                        "[ENTITY:NAME:{}]".format(entry),
                        min_sentiment,
                        max_interestingness,
                        "[LINK:{}]".format(task_result.uuid),  # uuid
                    )
                )
            )

            messages.append(
                Message(
                    Fact(
                        corpus,
                        corpus_type,
                        max_sentiment_year,
                        max_sentiment_year,
                        "between_years",
                        "TrackNameSentiment:Max",
                        "[ENTITY:NAME:{}]".format(entry),
                        max_sentiment,
                        max_interestingness,
                        "[LINK:{}]".format(task_result.uuid),  # uuid
                    )
                )
            )

        return messages

    def slot_realizer_components(self) -> List[Type[SlotRealizerComponent]]:
        return []
