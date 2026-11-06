import logging

from langchain_core.callbacks import BaseCallbackHandler

logger = logging.getLogger(__name__)


class LLMMonitor(BaseCallbackHandler):

    def on_chat_model_start(
        self,
        serialized,
        messages,
        **kwargs,
    ):
        logger.info(
            "LLM INVOCATION STARTED | model=%s | provider=%s",
            serialized.get("kwargs", {}).get("model"),
            serialized.get("kwargs", {}).get("model_provider"),
        )

    def on_llm_end(self, response, **kwargs):
        logger.info("LLM INVOCATION COMPLETED")

    def on_llm_error(self, error, **kwargs):
        logger.exception("LLM INVOCATION FAILED: %s", error)