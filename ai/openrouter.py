"""
OpenRouter AI client for intelligent product selection.
Uses LLM to choose the best product from search results.
"""

import os
import re
import json
import requests
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
# DeepSeek R1 returns empty content - use Llama instead
DEFAULT_MODEL = "meta-llama/llama-3.1-405b-instruct:free"


def call_openrouter(prompt: str, model: str = DEFAULT_MODEL) -> str:
    """
    Call OpenRouter API with a prompt.
    
    Args:
        prompt: The prompt to send
        model: Model to use (default: deepseek-r1)
        
    Returns:
        The model's response text
    """
    if not OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY not set in environment")
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/atakdnz/fridge-order-agent",
        "X-Title": "SiparisAgent"
    }
    
    data = {
        "model": model,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1,
        "max_tokens": 500,  # Increased for reasoning models
    }
    
    print(f"   📡 Calling OpenRouter ({model})...")
    response = requests.post(OPENROUTER_URL, headers=headers, json=data, timeout=60)
    
    if response.status_code != 200:
        print(f"   ❌ API error: {response.status_code} - {response.text}")
        raise Exception(f"API error: {response.status_code}")
    
    result = response.json()
    
    # Debug: print raw response for troubleshooting
    print(f"   📨 Raw response keys: {list(result.keys())}")
    
    # Debug: print the full response structure
    if "choices" not in result:
        print(f"   ❌ Unexpected response: {json.dumps(result, indent=2)}")
        raise Exception("No choices in response")
    
    choice = result["choices"][0]
    message = choice.get("message", {})
    
    # DeepSeek R1 reasoning models may have 'reasoning_content' separate from 'content'
    content = message.get("content", "")
    reasoning = message.get("reasoning_content", "")
    
    # If content is empty but we have reasoning, extract answer from reasoning
    if not content and reasoning:
        print(f"   🧠 Got reasoning response, extracting answer...")
        # Look for numbers in the reasoning
        import re
        numbers = re.findall(r'\b([1-5])\b', reasoning[-100:])  # Check last part
        if numbers:
            content = numbers[-1]  # Take the last number mentioned
            print(f"   📝 Extracted answer: {content}")
    
    if content:
        print(f"   ✅ AI response: {content[:50]}...")
    else:
        print(f"   ⚠ Empty response from AI")
    
    return content.strip() if content else ""


def choose_product(
    products: list[dict],
    search_term: str,
    preference: str = "cheapest"
) -> int:
    """
    Use AI to choose the best product from a list.
    
    Args:
        products: List of product dicts with 'name', 'price', 'index' keys
        search_term: What we searched for (e.g., "Süt")
        preference: Selection criteria (cheapest, organic, specific brand, etc.)
        
    Returns:
        Index of the selected product (0-based)
    """
    if not products:
        raise ValueError("No products to choose from")
    
    if len(products) == 1:
        return 0
    
    # Build product list for prompt
    product_lines = []
    for i, p in enumerate(products, 1):
        line = f"{i}. {p.get('name', 'Unknown')} - {p.get('price', 'N/A')}"
        product_lines.append(line)
    
    prompt = f"""You are shopping on Getir (Turkish grocery app). Choose the best product.

Search term: "{search_term}"

Available products:
{chr(10).join(product_lines)}

Selection criteria: {preference}

Reply with ONLY a single number (1, 2, 3, etc.) for your choice. No explanation."""

    print(f"🤖 Asking AI to choose best product for '{search_term}'...")
    
    try:
        response = call_openrouter(prompt)
        
        # Parse the number from response
        # Handle responses like "1", "1.", "Product 1", etc.
        import re
        numbers = re.findall(r'\d+', response)
        
        if numbers:
            choice = int(numbers[0])
            if 1 <= choice <= len(products):
                print(f"   ✓ AI selected: {products[choice-1].get('name', 'Unknown')}")
                return choice - 1  # Convert to 0-based index
        
        # Fallback to first product if parsing fails
        print(f"   ⚠ Could not parse AI response '{response}', using first product")
        return 0
        
    except Exception as e:
        print(f"   ⚠ AI error: {e}, using first product")
        return 0
