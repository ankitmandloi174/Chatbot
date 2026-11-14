"""Coordinates one chat turn: retrieve -> analyse -> explain -> persist."""

import logging
import time
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from app.core.config import Settings
from app.core.exceptions import BadRequestError, NotFoundError
from app.models.conversation import Message
from app.models.dataset import Dataset, DatasetRelationship
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.dataset_repository import DatasetRepository
from app.schemas.chat import MessageOut, TablePayload
from app.services.analysis.explainer import ResultExplainer
from app.services.analysis.models import AnalysisOutcome
from app.services.analysis.pipeline import AnalysisPipeline
from app.services.analysis.result_metrics import extract_kpis
from app.services.conversation.context import previous_columns
from app.services.conversation.trace import build_sources, build_trace
from app.services.llm.prompts import render_history, render_schema
from app.services.retrieval.retriever import RetrievedSchema, SchemaRetriever
from app.services.suggestions.context import build_follow_up_context
from app.services.suggestions.follow_up_service import FollowUpService

logger = logging.getLogger(__name__)
_DEFAULT_TITLE = "New conversation"
_TITLE_MAX = 60


def _elapsed_ms(start: float) -> int:
    return int((time.perf_counter() - start) * 1000)


def message_to_out(message: Message) -> MessageOut:
    """Flatten a stored message (and its payload) into the API schema."""
    return MessageOut(
        id=message.id,
        role=message.role,
        content=message.content,
        created_at=message.created_at,
        **(message.payload or {}),
    )


class ChatService:
    def __init__(
        self,
        settings: Settings,
        datasets: DatasetRepository,
        conversations: ConversationRepository,
        retriever: SchemaRetriever,
        pipeline: AnalysisPipeline,
        explainer: ResultExplainer,
        follow_ups: FollowUpService,
    ) -> None:
        self._settings = settings
        self._datasets = datasets
        self._conversations = conversations
        self._retriever = retriever
        self._pipeline = pipeline
        self._explainer = explainer
        self._follow_ups = follow_ups

    def ask(self, conversation_id: str, question: str, dataset_ids: list[str] | None) -> MessageOut:
        conversation = self._conversations.get(conversation_id)
        if conversation is None:
            raise NotFoundError(f"Conversation {conversation_id} not found")

        datasets = list(self._datasets.get_many(dataset_ids) if dataset_ids else self._datasets.list())
        if not datasets:
            raise BadRequestError("Upload at least one CSV before asking questions")

        history = self._conversations.messages(conversation_id)
        relationships = list(self._datasets.list_relationships([d.id for d in datasets]))
        started = time.perf_counter()
        schema = self._retriever.retrieve(
            question, datasets, relationships, context_columns=previous_columns(history, datasets)
        )
        retrieval_ms = _elapsed_ms(started)
        schema_text = render_schema(schema)

        outcome = self._pipeline.run(
            question,
            [item.dataset for item in schema.datasets],
            schema_text,
            render_history(history, self._settings.history_turns),
        )
        answer, payload = self._build_response(
            question, outcome, schema, schema_text, retrieval_ms, datasets, relationships, history
        )

        self._conversations.add_message(conversation_id, "user", question)
        assistant = self._conversations.add_message(conversation_id, "assistant", answer, payload)
        if conversation.title == _DEFAULT_TITLE:
            self._conversations.set_title(conversation, question[:_TITLE_MAX])
        return message_to_out(assistant)

    def _build_response(
        self,
        question: str,
        outcome: AnalysisOutcome,
        schema: RetrievedSchema,
        schema_text: str,
        retrieval_ms: int,
        datasets: Sequence[Dataset],
        relationships: Sequence[DatasetRelationship],
        history: Sequence[Message],
    ) -> tuple[str, dict[str, Any]]:
        payload: dict[str, Any] = {
            "code": outcome.code,
            "plan": outcome.plan.model_dump(),
            "attempts": outcome.attempts,
            "sources": [s.model_dump() for s in build_sources(schema, outcome)],
        }
        execution = outcome.execution
        if execution is None:
            payload["error"] = outcome.error
            payload["trace"] = build_trace(schema, outcome, retrieval_ms, 0).model_dump()
            answer = (
                f"I couldn't compute a reliable answer after {outcome.attempts} attempts. "
                "Try rephrasing the question or naming the columns involved."
            )
            return answer, payload

        if execution.result["kind"] == "table":
            payload["tables"] = [TablePayload(**{k: v for k, v in execution.result.items() if k != "kind"}).model_dump()]
        if execution.figure:
            payload["charts"] = [execution.figure]
        payload["kpis"] = extract_kpis(execution.result)

        context = build_follow_up_context(
            question, datasets, relationships, build_sources(schema, outcome), execution, history
        )
        started = time.perf_counter()
        # Follow-ups do not depend on the explanation, so they are computed alongside it.
        with ThreadPoolExecutor(max_workers=1) as pool:
            pending = pool.submit(self._follow_ups.suggest, context)
            text = self._explainer.explain(question, outcome.plan, execution, schema_text)
            payload["followups"] = pending.result()
        payload["trace"] = build_trace(schema, outcome, retrieval_ms, _elapsed_ms(started)).model_dump()
        return text, payload
