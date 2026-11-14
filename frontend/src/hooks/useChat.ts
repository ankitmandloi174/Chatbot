import { useCallback, useEffect, useState } from "react";

import { api } from "../services/api";
import type { ChatMessage, Conversation } from "../types/api";

export interface UseChat {
  conversations: Conversation[];
  activeId: string | null;
  messages: ChatMessage[];
  sending: boolean;
  error: string | null;
  select: (id: string | null) => Promise<void>;
  remove: (id: string) => Promise<void>;
  send: (question: string, datasetIds: string[]) => Promise<void>;
}

function pendingUserMessage(content: string): ChatMessage {
  return {
    id: -Date.now(),
    role: "user",
    content,
    created_at: new Date().toISOString(),
    tables: [],
    charts: [],
    code: null,
    plan: null,
    attempts: 0,
    error: null,
    kpis: [],
    sources: [],
    trace: null,
    followups: [],
  };
}

export function useChat(): UseChat {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setConversations(await api.listConversations());
  }, []);

  useEffect(() => {
    refresh().catch((e: Error) => setError(e.message));
  }, [refresh]);

  const select = useCallback(async (id: string | null) => {
    setActiveId(id);
    setError(null);
    if (id === null) {
      setMessages([]);
      return;
    }
    try {
      setMessages((await api.getConversation(id)).messages);
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);

  const remove = useCallback(
    async (id: string) => {
      await api.deleteConversation(id);
      if (id === activeId) await select(null);
      await refresh();
    },
    [activeId, refresh, select],
  );

  const send = useCallback(
    async (question: string, datasetIds: string[]) => {
      setSending(true);
      setError(null);
      setMessages((prev) => [...prev, pendingUserMessage(question)]);
      try {
        const conversationId = activeId ?? (await api.createConversation()).id;
        setActiveId(conversationId);
        const reply = await api.sendMessage(conversationId, question, datasetIds);
        setMessages((prev) => [...prev, reply]);
        await refresh();
      } catch (e) {
        setError((e as Error).message);
      } finally {
        setSending(false);
      }
    },
    [activeId, refresh],
  );

  return { conversations, activeId, messages, sending, error, select, remove, send };
}
