from typing import Any, Dict, List


def compact_observation(
    action: str,
    observation: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Convert a potentially verbose tool/RAG result into compact,
    structured evidence for subsequent agent iterations.
    """

    if not observation.get("success", False):
        return {
            "source": action,
            "success": False,
            "relevant_facts": [],
            "missing_information": [
                observation.get("error", "The action failed.")
            ],
            "uncertainty": [
                "The requested information could not be verified."
            ],
            "sources": [],
        }

    if action == "get_order_status":
        order = observation.get("order", {})

        return {
            "source": action,
            "success": True,
            "relevant_facts": [
                f"Order ID: {order.get('order_id', 'unknown')}",
                f"Status: {order.get('status', 'unknown')}",
            ],
            "missing_information": [],
            "uncertainty": [],
            "sources": ["orders.json"],
        }

    if action == "get_product_info":
        product = observation.get("product", {})

        return {
            "source": action,
            "success": True,
            "relevant_facts": [
                f"Product ID: {product.get('product_id', 'unknown')}",
                f"Product name: {product.get('name', 'unknown')}",
                f"Price: {product.get('price', 'unknown')}",
                f"Description: {product.get('description', 'unknown')}",
            ],
            "missing_information": [],
            "uncertainty": [],
            "sources": ["products.json"],
        }

    if action == "check_return_eligibility":
        return {
            "source": action,
            "success": True,
            "relevant_facts": [
                f"Return eligible: {observation.get('eligible')}",
                f"Reason: {observation.get('reason', 'Not provided')}",
            ],
            "missing_information": [],
            "uncertainty": [],
            "sources": ["return_policy"],
        }

    if action == "search_knowledge":
        results = observation.get("results", [])

        compact_results: List[Dict[str, Any]] = []

        for result in results[:3]:
            if isinstance(result, dict):
                compact_results.append(
                    {
                        "source": result.get("source"),
                        "content": result.get("content", result.get("text", "")),
                    }
                )
            else:
                compact_results.append(
                    {
                        "source": "knowledge_base",
                        "content": str(result),
                    }
                )

        return {
            "source": action,
            "success": True,
            "relevant_facts": compact_results,
            "missing_information": [],
            "uncertainty": [],
            "sources": [
                item.get("source")
                for item in compact_results
                if item.get("source")
            ],
        }

    if action == "ask_clarification":
        return {
            "source": action,
            "success": True,
            "relevant_facts": [
                observation.get(
                    "message",
                    "Additional information is required.",
                )
            ],
            "missing_information": [
                observation.get(
                    "message",
                    "Additional information is required.",
                )
            ],
            "uncertainty": [],
            "sources": [],
        }

    return {
        "source": action,
        "success": observation.get("success", False),
        "relevant_facts": [],
        "missing_information": [],
        "uncertainty": [],
        "sources": [],
    }
