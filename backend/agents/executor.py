from typing import Any, Dict

from backend.tools.orders import get_order_status
from backend.tools.products import get_product_info
from backend.tools.returns import check_return_eligibility


class AgentActionExecutor:
    """
    Executes validated W16 agent actions.

    Heavy dependencies such as the embedding/RAG stack are imported
    lazily only when the agent actually chooses search_knowledge.
    """

    def execute(
        self,
        action: str,
        arguments: Dict[str, Any],
    ) -> Dict[str, Any]:

        if action == "search_knowledge":
            return self._search_knowledge(arguments)

        if action == "get_order_status":
            return self._get_order_status(arguments)

        if action == "get_product_info":
            return self._get_product_info(arguments)

        if action == "check_return_eligibility":
            return self._check_return_eligibility(arguments)

        if action == "ask_clarification":
            return {
                "success": True,
                "type": "clarification",
                "message": arguments.get(
                    "question",
                    "Could you provide more information so I can help?"
                ),
            }

        if action == "final_answer":
            return {
                "success": True,
                "type": "final_answer",
            }

        raise ValueError(f"Unsupported action: {action}")

    def _search_knowledge(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        query = arguments.get("query")

        if not query:
            return {
                "success": False,
                "error": "Knowledge search requires a query.",
            }

        try:
            # Lazy import: PyTorch/sentence-transformers are loaded
            # only when the agent actually requests knowledge search.
            from backend.rag.retrieval import retrieve

            results = retrieve(query, top_k=3)

            return {
                "success": True,
                "type": "knowledge_search",
                "query": query,
                "results": results,
            }

        except Exception as exc:
            return {
                "success": False,
                "type": "knowledge_search",
                "error": (
                    f"Knowledge search failed: "
                    f"{type(exc).__name__}: {exc}"
                ),
            }

    def _get_order_status(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        order_id = arguments.get("order_id")

        if not order_id:
            return {
                "success": False,
                "error": "Order status requires an order_id.",
            }

        try:
            return get_order_status(order_id)

        except Exception as exc:
            return {
                "success": False,
                "error": (
                    f"Order lookup failed: "
                    f"{type(exc).__name__}: {exc}"
                ),
            }

    def _get_product_info(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        product_id = arguments.get("product_id")

        if not product_id:
            return {
                "success": False,
                "error": "Product lookup requires a product_id.",
            }

        try:
            return get_product_info(product_id)

        except Exception as exc:
            return {
                "success": False,
                "error": (
                    f"Product lookup failed: "
                    f"{type(exc).__name__}: {exc}"
                ),
            }

    def _check_return_eligibility(
        self,
        arguments: Dict[str, Any],
    ) -> Dict[str, Any]:

        order_id = arguments.get("order_id")

        if not order_id:
            return {
                "success": False,
                "error": "Return eligibility requires an order_id.",
            }

        try:
            return check_return_eligibility(order_id)

        except Exception as exc:
            return {
                "success": False,
                "error": (
                    f"Return eligibility check failed: "
                    f"{type(exc).__name__}: {exc}"
                ),
            }
