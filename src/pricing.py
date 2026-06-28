# Model token pricing constants (per 1,000,000 tokens) in USD
PRICING = {
    "openai/gpt-4o-mini": {
        "input": 0.150,
        "output": 0.600
    },
    "openai/gpt-3.5-turbo": {
        "input": 0.500,
        "output": 1.500
    },
    "openai/gpt-4o": {
        "input": 2.500,
        "output": 10.000
    },
    "openai/gpt-oss-20b:free": {
        "input": 0.0001,
        "output": 0.0001
    },
    "google/gemini-flash-1.5-free": {
        "input": 0.0001,
        "output": 0.0001
    },
    "llama-3.1-8b-instant": {
        "input": 0.0001,
        "output": 0.0001
    },
    "llama-3.3-70b-versatile": {
        "input": 0.59,
        "output": 0.79
    },
    "openai/gpt-oss-120b": {
        "input": 0.00001,
        "output": 0.00001
    },
    # Default fallback pricing (GPT-4o-mini rates)
    "default": {
        "input": 0.150,
        "output": 0.600
    }
}

def calculate_llm_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """
    Calculates the LLM cost in USD.
    """
    try:
        from genai_prices import calc_price, Usage
        model_ref = model.split("/")[-1] if "/" in model else model
        price_calc = calc_price(
            Usage(input_tokens=input_tokens, output_tokens=output_tokens),
            model_ref
        )
        return float(price_calc.total_price)
    except Exception:
        pass

    rates = PRICING.get(model, PRICING["default"])
    in_cost = (input_tokens * rates["input"]) / 1_000_000
    out_cost = (output_tokens * rates["output"]) / 1_000_000
    return in_cost + out_cost
