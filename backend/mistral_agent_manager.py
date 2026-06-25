import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / '.env')

logger = logging.getLogger(__name__)

MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY")


class MistralAgentError(Exception):
    pass


class MistralAgentManager:
    """Manages conversations with pre-created Mistral agents (via Console).

    Menggunakan Agents.complete() yang mendukung max_tokens,
    berbeda dengan Conversations API yang tidak mengizinkan max_tokens
    untuk pre-created agents.

    Agent IDs harus didefinisikan di .env:
      MISTRAL_AGENT_NEWS_ID=ag_xxx
      MISTRAL_AGENT_SECTOR_ID=ag_xxx
      MISTRAL_AGENT_STOCK_ID=ag_xxx
    """

    def __init__(self):
        if not MISTRAL_API_KEY:
            raise MistralAgentError(
                "MISTRAL_API_KEY tidak ditemukan di .env"
            )
        from mistralai.client import Mistral

        self.client = Mistral(api_key=MISTRAL_API_KEY)

        self._agent_ids: Dict[str, str] = {}
        self._load_agent_ids()

    def _load_agent_ids(self) -> None:
        keys = {
            "news_flow": "MISTRAL_AGENT_NEWS_ID",
            "sector_predictor": "MISTRAL_AGENT_SECTOR_ID",
            "stock_recommender": "MISTRAL_AGENT_STOCK_ID",
            "batch_stock": "MISTRAL_AGENT_BATCH_STOCK_ID",
        }
        for key, env_var in keys.items():
            agent_id = os.environ.get(env_var)
            if agent_id:
                self._agent_ids[key] = agent_id
                logger.info("Loaded agent %s: %s", key, agent_id)
            else:
                logger.warning("Agent ID not set: %s (%s)", key, env_var)

    @property
    def available_agents(self) -> List[str]:
        return list(self._agent_ids.keys())

    def get_agent_id(self, name: str) -> str:
        agent_id = self._agent_ids.get(name)
        if not agent_id:
            raise MistralAgentError(
                f"Agent '{name}' not configured. "
                f"Set MISTRAL_AGENT_{name.upper()}_ID di .env"
            )
        return agent_id

    def run(
        self,
        agent_key: str,
        inputs: Any,
        max_function_calls: int = 30,
        timeout_ms: int = 120000,
    ) -> Dict[str, Any]:
        """Run agent using Agents.complete() with max_tokens support.

        Args:
            agent_key: 'news', 'sector_predictor', or 'stock_recommender'
            inputs: String or list/dict to start the conversation
            max_function_calls: Safety limit for function call loop

        Returns:
            Dict with 'content' (final text output) and 'tool_calls' (list)
        """
        agent_id = self.get_agent_id(agent_key)

        if isinstance(inputs, (dict, list)):
            input_text = json.dumps(inputs, ensure_ascii=False)
        else:
            input_text = str(inputs)

        from mistralai.client.models.usermessage import UserMessage
        from mistralai.client.models.toolmessage import ToolMessage
        from mistralai.client.models.assistantmessage import AssistantMessage

        messages: List[Any] = [UserMessage(role="user", content=input_text)]
        all_tool_calls = []
        function_call_count = 0

        while True:
            response = self.client.agents.complete(
                agent_id=agent_id,
                messages=messages,
                max_tokens=32000,
                timeout_ms=timeout_ms,
            )

            choice = response.choices[0]
            msg = choice.message

            if getattr(choice, 'finish_reason', None) == 'length':
                logger.warning(
                    "Agent %s: response truncated at max_tokens=32000 (finish_reason=length). "
                    "Consider increasing max_tokens or reducing prompt/output size.",
                    agent_key
                )

            # Collect tool calls if any
            raw_tool_calls = getattr(msg, 'tool_calls', None) or []

            if not raw_tool_calls:
                # No tool calls — this is the final response
                final_content = msg.content if isinstance(msg.content, str) else (
                    msg.content[0].text if isinstance(msg.content, list) and msg.content and hasattr(msg.content[0], 'text')
                    else str(msg.content) if msg.content else ""
                )
                return {
                    "content": final_content,
                    "tool_calls": all_tool_calls,
                }

            # Check limit before processing batch
            if function_call_count >= max_function_calls:
                logger.warning(
                    "Agent %s: hit function call limit (%d), stopping",
                    agent_key, max_function_calls
                )
                return {"content": None, "tool_calls": all_tool_calls}

            # Check if this batch would exceed limit
            if function_call_count + len(raw_tool_calls) > max_function_calls:
                # Only process up to the limit, let agent re-request remaining
                raw_tool_calls = raw_tool_calls[:max_function_calls - function_call_count]

            function_call_count += len(raw_tool_calls)
            tool_messages = []

            for tc in raw_tool_calls:
                func = tc.function
                func_name = func.name
                func_args_raw = func.arguments

                if isinstance(func_args_raw, str):
                    try:
                        func_args = json.loads(func_args_raw)
                    except json.JSONDecodeError:
                        func_args = {"raw": func_args_raw}
                else:
                    func_args = func_args_raw or {}

                # Mistral agent may send JSON array instead of object — wrap it
                if not isinstance(func_args, dict):
                    func_args = {"input": func_args}

                all_tool_calls.append({
                    "id": tc.id,
                    "type": "function",
                    "name": func_name,
                    "arguments": func_args,
                })

                result = self._execute_function(func_name, func_args)

                tool_messages.append(ToolMessage(
                    role="tool",
                    tool_call_id=tc.id,
                    content=json.dumps(result, ensure_ascii=False),
                ))

            # Normalize content to string
            content_str = msg.content if isinstance(msg.content, str) else (
                msg.content[0].text if isinstance(msg.content, list) and msg.content and hasattr(msg.content[0], 'text')
                else str(msg.content) if msg.content else ""
            )

            # Convert tool calls to plain dicts (SDK Pydantic models break serialization)
            tool_calls_dicts = [
                {
                    "id": tc.id,
                    "type": getattr(tc, "type", "function"),
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments if isinstance(tc.function.arguments, str)
                                     else json.dumps(tc.function.arguments, ensure_ascii=False),
                    }
                }
                for tc in raw_tool_calls
            ]

            # Append assistant message with tool calls + tool results
            messages.append(AssistantMessage(
                role="assistant",
                content=content_str,
                tool_calls=tool_calls_dicts,
            ))
            messages.extend(tool_messages)

    def _execute_function(self, name: str, args: Dict[str, Any]) -> Any:
        """Execute a function called by the Mistral agent."""
        logger.info("Executing function: %s(%s)", name, args)

        if name == "get_sector_fundamentals":
            from sector_predictor_agent import fetch_sector_data
            return fetch_sector_data()

        elif name == "get_macro_summary":
            from macro_agent import get_macro_summary
            return get_macro_summary()

        elif name == "get_stocks_in_sector":
            sector = args.get("sector", "")
            from stock_recommender_agent import get_stocks_in_sector
            stocks = get_stocks_in_sector(sector)
            simple = []
            for s in stocks[:10]:
                analysis = s.get("analysis") or {}
                simple.append({
                    "ticker": s.get("ticker"),
                    "companyName": s.get("companyName"),
                    "price": s.get("price"),
                    "per": s.get("per"),
                    "pbv": s.get("pbv"),
                    "roe": s.get("roe"),
                    "revenue_growth": s.get("revenue_growth"),
                    "eps_growth": s.get("eps_growth"),
                    "dividend_yield": s.get("dividend_yield"),
                    "debt_to_equity": s.get("debt_to_equity"),
                    "investment_score": analysis.get("investmentScore"),
                    "valuation": s.get("valuation"),
                })
            return simple

        elif name == "get_ticker_news":
            ticker = args.get("ticker", "")
            from stock_recommender_agent import fetch_news_batch
            dummy_stock = {"ticker": ticker}
            news_map = fetch_news_batch([dummy_stock], max_stocks=1, max_articles=5)
            return news_map.get(ticker, [])

        elif name == "get_macro_context":
            sector = args.get("sector", "")
            from macro_agent import get_sector_macro_context
            indices = get_sector_macro_context(sector)
            if isinstance(indices, list):
                result = {}
                for ind in indices:
                    result[ind.get("id", ind.get("label", ""))] = {
                        "label": ind.get("label"),
                        "value": ind.get("value"),
                        "trend": ind.get("trend", "netral"),
                        "impact": ind.get("impact", ""),
                    }
                return result
            return indices or {}

        else:
            logger.warning("Unknown function called by agent: %s", name)
            return {"error": f"Unknown function: {name}"}
