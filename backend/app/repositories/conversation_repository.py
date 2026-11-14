"""Persistence for conversations and messages."""

from collections.abc import Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.conversation import Conversation, Message


class ConversationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, title: str = "New conversation") -> Conversation:
        conversation = Conversation(title=title)
        self._session.add(conversation)
        self._session.commit()
        return conversation

    def get(self, conversation_id: str) -> Conversation | None:
        return self._session.get(Conversation, conversation_id)

    def list(self) -> Sequence[Conversation]:
        return self._session.scalars(
            select(Conversation).order_by(Conversation.created_at.desc())
        ).all()

    def delete(self, conversation: Conversation) -> None:
        for message in self.messages(conversation.id):
            self._session.delete(message)
        self._session.delete(conversation)
        self._session.commit()

    def set_title(self, conversation: Conversation, title: str) -> None:
        conversation.title = title
        self._session.commit()

    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        payload: dict[str, Any] | None = None,
    ) -> Message:
        message = Message(conversation_id=conversation_id, role=role, content=content, payload=payload)
        self._session.add(message)
        self._session.commit()
        return message

    def messages(self, conversation_id: str) -> Sequence[Message]:
        return self._session.scalars(
            select(Message).where(Message.conversation_id == conversation_id).order_by(Message.id)
        ).all()
