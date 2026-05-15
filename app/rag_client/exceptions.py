# app/rag_client/exceptions.py


class RAGServiceUnavailableError(Exception):
    """RAG service is down or unreachable."""
    pass


class RAGTimeoutError(Exception):
    """RAG service took too long to respond."""
    pass


class RAGIngestError(Exception):
    """RAG service failed to ingest the lecture."""
    pass


class RAGQueryError(Exception):
    """RAG service failed to answer the query."""
    pass


class RAGSessionMismatchError(Exception):
    """lecture_session_id sent does not match active session in RAG."""
    pass