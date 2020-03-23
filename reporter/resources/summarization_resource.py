import logging
from typing import List, Type

from reporter.core.models import Fact, Message
from reporter.core.realize_slots import SlotRealizerComponent
from reporter.newspaper_message_generator import TaskResult
from reporter.resources.processor_resource import ProcessorResource

log = logging.getLogger("root")


TEMPLATE = """
en: the following summary of the contents was automatically created: "{result_value}"
fi: teksteistä luotiin automaattisesti seuraava tiivistelmä: "{result_value}"
| analysis_type = Summarization
"""


class SummarizationResource(ProcessorResource):
    def templates_string(self) -> str:
        return TEMPLATE

    def parse_messages(self, task_result: TaskResult, context: List[TaskResult]) -> List[Message]:
        if not task_result.processor == "Summarization":
            return []

        corpus, corpus_type = self.build_corpus_fields(task_result)

        messages = []
        for summary, interestingness in zip(
            task_result.task_result["result"]["summary"], task_result.task_result["interestingness"]["sentence_scores"]
        ):
            interestingness *= task_result.task_result["interestingness"]["overall"]
            messages.append(
                Message(
                    [
                        Fact(
                            corpus,  # corpus
                            corpus_type,  # corpus_type
                            None,  # timestamp_from
                            None,  # timestamp_to
                            "all_time",  # timestamp_type
                            "Summarization",  # analysis_type
                            "Summary",  # result_key
                            summary,  # result_value
                            interestingness,  # outlierness
                        )
                    ]
                )
            )
        # For now, we limit the summaries to one per result. This needs to be re-evaluated later on.
        return [max(*messages, key=lambda m: m.main_fact.outlierness)]

    def slot_realizer_components(self) -> List[Type[SlotRealizerComponent]]:
        return []
