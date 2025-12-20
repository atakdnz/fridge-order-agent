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
# Use Llama for reliable responses (free tier)
DEFAULT_MODEL = "meta-llama/llama-3.1-405b-instruct:free"


def extract_json_array(text: str) -> str | None:
    """
    Extract a JSON array from text, properly handling nested structures.

    Args:
        text: Text that may contain a JSON array

    Returns:
        The extracted JSON array string, or None if not found
    """
    if not text:
        return None

    # First, try to find JSON in markdown code blocks
    code_block_match = re.search(r'```(?:json)?\s*(\[[\s\S]*?\])\s*```', text)
    if code_block_match:
        candidate = code_block_match.group(1)
        try:
            json.loads(candidate)
            return candidate
        except json.JSONDecodeError:
            pass  # Continue to other methods

    # Find the first '[' and match brackets properly
    start = text.find('[')
    if start == -1:
        return None

    # Track bracket depth, handling strings properly
    depth = 0
    in_string = False
    escape_next = False

    for i, char in enumerate(text[start:], start):
        if escape_next:
            escape_next = False
            continue

        if char == '\\' and in_string:
            escape_next = True
            continue

        if char == '"' and not escape_next:
            in_string = not in_string
            continue

        if in_string:
            continue

        if char == '[':
            depth += 1
        elif char == ']':
            depth -= 1
            if depth == 0:
                candidate = text[start:i+1]
                try:
                    json.loads(candidate)
                    return candidate
                except json.JSONDecodeError:
                    # This bracket pair didn't form valid JSON, try finding next [
                    next_start = text.find('[', start + 1)
                    if next_start != -1:
                        return extract_json_array(text[next_start:])
                    return None

    return None


def call_openrouter(prompt: str, model: str = DEFAULT_MODEL) -> str:
    """
    Call OpenRouter API with a prompt.
    
    Args:
        prompt: The prompt to send
        model: Model to use (default: deepseek-r1)
        
    Returns:
        The model's response text (content only, not thinking)
    """
    result = call_openrouter_with_thinking(prompt, model)
    return result.get("answer", "")


def call_openrouter_with_thinking(prompt: str, model: str = DEFAULT_MODEL) -> dict:
    """
    Call OpenRouter API and return both thinking process and answer.
    
    Args:
        prompt: The prompt to send
        model: Model to use
        
    Returns:
        Dict with 'thinking' and 'answer' keys
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
        "max_tokens": 2000,  # Increased for reasoning models
    }
    
    print(f"   📡 Calling OpenRouter ({model})...")
    response = requests.post(OPENROUTER_URL, headers=headers, json=data, timeout=120)
    
    if response.status_code != 200:
        print(f"   ❌ API error: {response.status_code} - {response.text}")
        raise Exception(f"API error: {response.status_code}")
    
    result = response.json()

    # Debug: print raw response structure
    print(f"   📦 Raw response keys: {list(result.keys())}")

    if "choices" not in result:
        print(f"   ❌ Unexpected response: {json.dumps(result, indent=2)}")
        raise Exception("No choices in response")

    choice = result["choices"][0]
    message = choice.get("message", {})

    # Debug: print message structure
    print(f"   📦 Message keys: {list(message.keys())}")
    
    # DeepSeek R1 returns reasoning in 'reasoning_content' and final answer in 'content'
    content = message.get("content", "") or ""
    reasoning = message.get("reasoning_content", "") or ""
    
    print(f"   🧠 Thinking: {len(reasoning)} chars")
    print(f"   📝 Answer: {len(content)} chars")
    
    # If content is empty but we have reasoning, try to extract JSON from reasoning
    if not content.strip() and reasoning:
        print(f"   ⚠ Empty content, extracting from reasoning...")
        extracted = extract_json_array(reasoning)
        if extracted:
            content = extracted
            print(f"   ✅ Extracted JSON from reasoning ({len(extracted)} chars)")
    
    return {
        "thinking": reasoning.strip(),
        "answer": content.strip()
    }


def choose_product(
    products: list[dict],
    search_term: str,
    preference: str = "cheapest",
    history_context: str = None
) -> int:
    """
    Use AI to choose the best product from a list.
    
    Args:
        products: List of product dicts with 'name', 'price', 'index' keys
        search_term: What we searched for (e.g., "Süt")
        preference: Selection criteria (cheapest, organic, specific brand, etc.)
        history_context: String description of past fridge contents for smart decisions
        
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
    
    # Add history context block if available
    history_block = ""
    if history_context:
        history_block = f"""
Facts about my consumption history (use this to decide quantity or brand preference if relevant):
{history_context}
"""
    
    prompt = f"""You are shopping on Getir (Turkish grocery app). Choose the best product.

Search term: "{search_term}"
{history_block}
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


def analyze_history(history_context: str, item_translations: dict = None) -> list[dict]:
    """
    Analyze fridge history and suggest what items to order.
    
    Args:
        history_context: Formatted history string from get_history_context()
        item_translations: Dict mapping class names to Turkish (for output)
        
    Returns:
        List of dicts with 'name' and 'quantity' keys
    """
    if not history_context or history_context == "No previous fridge history available.":
        print("   ⚠ No history to analyze")
        return []

    # Debug: print what history we're analyzing
    print(f"   📋 History context:\n{history_context}")

    prompt = f"""Look at fridge history. Order only items that are COMPLETELY GONE.

HISTORY (first line = CURRENT fridge contents):
{history_context}

RULES:
1. ONLY order items that are NOT in the first line (completely missing)
2. Do NOT order items that still exist in the first line (even if count=1)
3. Quantity: always use 1 for eggs (sold in packages), use 2-4 for other items

Example: If first line is "orange x1, water_bottle x1" and old lines had "eggs x4, milk x2":
- eggs: NOT in first line → ORDER eggs
- milk: NOT in first line → ORDER milk
- orange: IS in first line → DO NOT order
- water_bottle: IS in first line → DO NOT order

Return JSON array only: [{{"name": "eggs", "quantity": 1}}, {{"name": "milk", "quantity": 2}}]
Valid names: milk, eggs, water_bottle, orange, butter, cheese, tomato, cucumber, lemon"""

    try:
        # Debug: print the prompt being sent
        print(f"   📤 Prompt length: {len(prompt)} chars")

        result = call_openrouter_with_thinking(prompt)
        thinking = result.get("thinking", "")
        response = result.get("answer", "")

        # Debug: print the actual AI response
        print(f"   📥 AI Response: {response[:500] if response else 'empty'}")

        # Extract JSON from response using robust extractor
        json_str = extract_json_array(response)
        if not json_str:
            # Try to find in thinking if not in answer
            json_str = extract_json_array(thinking)
            if not json_str:
                print(f"   ⚠ No JSON found in response or thinking")
                print(f"   📝 Response was: {response[:200] if response else 'empty'}...")
                print(f"   🧠 Thinking was: {thinking[:200] if thinking else 'empty'}...")
                return {"thinking": thinking, "suggestions": []}

        items = json.loads(json_str)
        
        # Validate and translate items
        suggestions = []
        for item in items:
            if isinstance(item, dict) and 'name' in item and 'quantity' in item:
                name = item['name']
                quantity = int(item['quantity'])
                # Use translation if available
                display_name = item_translations.get(name, name) if item_translations else name
                suggestions.append({
                    'name': display_name,
                    'quantity': quantity,
                    'category': name  # Keep original for ordering
                })
        
        print(f"   ✅ AI suggested {len(suggestions)} items to order")
        return {
            "thinking": thinking,
            "suggestions": suggestions
        }
        
    except Exception as e:
        print(f"   ❌ AI analysis failed: {e}")
        return {"thinking": "", "suggestions": []}


