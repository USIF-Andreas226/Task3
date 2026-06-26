import uuid
from datetime import datetime
from typing import Any, List, Dict

class UsageLogger:
    def __init__(self, crm_client) -> None:
        self.crm = crm_client

    def log(
        self,
        user_id: str,
        conversation_id: str,
        message_id: str,
        model: str,
        provider: str,
        input_tokens: int,
        output_tokens: int,
        embedding_tokens: int,
        llm_cost_usd: float,
        embedding_cost_usd: float,
        total_cost_usd: float,
        tool_calls: List[Dict[str, Any]],
        think_step: str,
        final_response: str,
        latency_ms: int
    ) -> str:
        """
        Inserts a usage log record into MongoDB and in-memory fallback list.
        """
        log_id = str(uuid.uuid4())
        log_data = {
            "log_id": log_id,
            "user_id": user_id,
            "conversation_id": conversation_id,
            "message_id": message_id,
            "model": model,
            "provider": provider,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "embedding_tokens": embedding_tokens,
            "llm_cost_usd": llm_cost_usd,
            "embedding_cost_usd": embedding_cost_usd,
            "total_cost_usd": total_cost_usd,
            "tool_calls": tool_calls,
            "think_step": think_step,
            "final_response": final_response,
            "latency_ms": latency_ms,
            "timestamp": datetime.now()
        }

        if self.crm._connected and self.crm.usage_logs_collection is not None:
            try:
                self.crm.usage_logs_collection.insert_one(log_data)
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"❌ Failed to insert usage log to MongoDB: {e}")
        
        # Save in-memory
        self.crm._in_memory_usage_logs.append(log_data)
        return log_id
