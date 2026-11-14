"""FastAPI dependency providers. Shared resources live on `app.state`."""

from collections.abc import Iterator

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.dataset_repository import DatasetRepository
from app.services.analysis.code_generator import CodeGenerator
from app.services.analysis.explainer import ResultExplainer
from app.services.analysis.pipeline import AnalysisPipeline
from app.services.analysis.planner import AnalysisPlanner
from app.services.analysis.sandbox import SandboxExecutor
from app.services.conversation.chat_service import ChatService
from app.services.ingestion.dataset_service import DatasetService
from app.services.llm.client import LLM, build_llm
from app.services.retrieval.retriever import SchemaRetriever
from app.services.retrieval.vector_store import ColumnVectorStore
from app.services.suggestions.follow_up_service import FollowUpService
from app.services.suggestions.llm_suggester import LLMSuggester


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_db(request: Request) -> Iterator[Session]:
    session = request.app.state.session_factory()
    try:
        yield session
    finally:
        session.close()


def get_vector_store(request: Request) -> ColumnVectorStore:
    return request.app.state.vector_store


def get_llm(request: Request, settings: Settings = Depends(get_settings)) -> LLM:
    """Build the LLM lazily so the app can start (and ingest) without an API key."""
    if request.app.state.llm is None:
        request.app.state.llm = build_llm(settings)
    return request.app.state.llm


def get_dataset_repository(db: Session = Depends(get_db)) -> DatasetRepository:
    return DatasetRepository(db)


def get_conversation_repository(db: Session = Depends(get_db)) -> ConversationRepository:
    return ConversationRepository(db)


def get_dataset_service(
    settings: Settings = Depends(get_settings),
    repository: DatasetRepository = Depends(get_dataset_repository),
    vector_store: ColumnVectorStore = Depends(get_vector_store),
) -> DatasetService:
    return DatasetService(settings, repository, vector_store)


def get_chat_service(
    settings: Settings = Depends(get_settings),
    datasets: DatasetRepository = Depends(get_dataset_repository),
    conversations: ConversationRepository = Depends(get_conversation_repository),
    vector_store: ColumnVectorStore = Depends(get_vector_store),
    llm: LLM = Depends(get_llm),
) -> ChatService:
    pipeline = AnalysisPipeline(
        AnalysisPlanner(llm),
        CodeGenerator(llm),
        SandboxExecutor(settings.sandbox_timeout_seconds, settings.sandbox_memory_mb, settings.result_max_rows),
        settings.max_code_retries,
    )
    return ChatService(
        settings,
        datasets,
        conversations,
        SchemaRetriever(vector_store, settings.retrieval_top_k),
        pipeline,
        ResultExplainer(llm),
        FollowUpService(
            LLMSuggester(llm, settings.follow_up_count) if settings.follow_up_llm_enabled else None,
            settings.follow_up_count,
        ),
    )
