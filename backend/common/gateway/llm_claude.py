import logging

import anthropic
from pydantic import BaseModel

from common.errors import LLMError

logger = logging.getLogger(__name__)


class ClaudeLLM:
    def __init__(self, client: anthropic.Anthropic, model: str, max_tokens: int) -> None:
        self._client = client
        self._model = model
        self._max_tokens = max_tokens

    def complete[T: BaseModel](self, *, system: str, prompt: str, output: type[T], trace_id: str) -> T:
        try:
            response = self._client.messages.parse(
                model=self._model,
                max_tokens=self._max_tokens,
                system=system,
                messages=[{"role": "user", "content": prompt}],
                output_format=output,
            )
        except anthropic.RateLimitError as e:
            raise LLMError(f"rate limited: trace_id={trace_id}", retryable=True) from e
        except anthropic.APIStatusError as e:
            raise LLMError(
                f"api error: trace_id={trace_id} status={e.status_code}",
                retryable=e.status_code >= 500,
            ) from e
        except anthropic.APIConnectionError as e:
            raise LLMError(f"connection failed: trace_id={trace_id}", retryable=True) from e

        logger.info("llm.completed trace_id=%s usage=%s", trace_id, response.usage.model_dump())

        if response.stop_reason == "refusal":
            raise LLMError(f"refused: trace_id={trace_id}", retryable=False)
        if response.parsed_output is None:
            raise LLMError(
                f"no structured output: trace_id={trace_id} stop_reason={response.stop_reason}",
                retryable=response.stop_reason == "max_tokens",
            )
        return response.parsed_output
