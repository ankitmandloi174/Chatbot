"""Conversation and chat endpoints."""

from fastapi import APIRouter, Depends, status

from app.api.deps import get_chat_service, get_conversation_repository
from app.core.exceptions import NotFoundError
from app.repositories.conversation_repository import ConversationRepository
from app.schemas.chat import ChatRequest, ConversationDetail, ConversationOut, MessageOut
from app.services.conversation.chat_service import ChatService, message_to_out

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


def _get_or_404(repo: ConversationRepository, conversation_id: str):
    conversation = repo.get(conversation_id)
    if conversation is None:
        raise NotFoundError(f"Conversation {conversation_id} not found")
    return conversation


@router.post("", response_model=ConversationOut, status_code=status.HTTP_201_CREATED)
def create_conversation(repo: ConversationRepository = Depends(get_conversation_repository)):
    return ConversationOut.model_validate(repo.create(), from_attributes=True)


@router.get("", response_model=list[ConversationOut])
def list_conversations(repo: ConversationRepository = Depends(get_conversation_repository)):
    return [ConversationOut.model_validate(c, from_attributes=True) for c in repo.list()]


@router.get("/{conversation_id}", response_model=ConversationDetail)
def get_conversation(
    conversation_id: str, repo: ConversationRepository = Depends(get_conversation_repository)
) -> ConversationDetail:
    conversation = _get_or_404(repo, conversation_id)
    return ConversationDetail(
        id=conversation.id,
        title=conversation.title,
        created_at=conversation.created_at,
        messages=[message_to_out(m) for m in repo.messages(conversation_id)],
    )


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(
    conversation_id: str, repo: ConversationRepository = Depends(get_conversation_repository)
) -> None:
    repo.delete(_get_or_404(repo, conversation_id))


@router.post("/{conversation_id}/messages", response_model=MessageOut)
def send_message(
    conversation_id: str, body: ChatRequest, service: ChatService = Depends(get_chat_service)
) -> MessageOut:
    """Ask a question; returns the assistant reply (text, tables, Plotly charts)."""
    return service.ask(conversation_id, body.question, body.dataset_ids)
