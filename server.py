"""
Flask server for testing fridge detection and ordering.
"""

import os
import tempfile
import threading
from flask import Flask, request, jsonify, send_from_directory
from detection.detector import FridgeDetector, CLASS_TO_GETIR, EXPECTED_ITEMS
from browser.getir_client import GetirClient
from browser.migros_client import MigrosClient
from browser.akbal_client import AkbalClient
from db.database import (
    add_history, get_history, delete_history, clear_history,
    get_preferences, set_preferences, get_history_context,
    get_preferred_provider
)

app = Flask(__name__, static_folder='static')

# Global detector (lazy loaded)
_detector = None

def get_detector():
    global _detector
    if _detector is None:
        _detector = FridgeDetector()
    return _detector


@app.route('/')
def index():
    """Serve the frontend."""
    return send_from_directory('static', 'index.html')


@app.route('/detect', methods=['POST'])
def detect():
    """
    Detect products in uploaded image.
    Returns detected items and missing items for ordering.
    """
    if 'image' not in request.files:
        return jsonify({'error': 'No image provided'}), 400
    
    file = request.files['image']
    
    # Save to temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp:
        file.save(tmp.name)
        temp_path = tmp.name
    
    try:
        detector = get_detector()
        confidence = float(request.form.get('confidence', 0.5))
        detected_counts, detections = detector.detect(temp_path, confidence=confidence)
        missing = detector.get_missing_items(detected_counts)
        
        # Format response - summarized counts
        detected_list = [
            {'name': CLASS_TO_GETIR.get(k, k), 'count': v, 'class': k}
            for k, v in detected_counts.items()
        ]
        
        return jsonify({
            'success': True,
            'detected': detected_list,
            'detections': detections,  # Full bounding box info for canvas
            'missing': missing,
            'expected': {CLASS_TO_GETIR.get(k, k): v for k, v in EXPECTED_ITEMS.items()}
        })
        
    finally:
        # Cleanup temp file
        os.unlink(temp_path)


@app.route('/order', methods=['POST'])
def order():
    """
    Order the specified products on the selected provider (Getir or Migros).
    Runs Playwright in a separate thread.
    """
    data = request.json
    products = data.get('products', [])

    if not products:
        return jsonify({'error': 'No products specified'}), 400

    use_ai = data.get('use_ai', False)
    preference = data.get('preference', 'cheapest')
    provider = get_preferred_provider()

    def run_order():
        """Run the ordering in background."""
        # Select client based on provider preference
        if provider == 'migros':
            client = MigrosClient()
            provider_name = "Migros"
        elif provider == 'akbal':
            client = AkbalClient()
            provider_name = "Akbal Market"
        else:
            client = GetirClient()
            provider_name = "Getir"

        print(f"🏪 Using {provider_name} for ordering...")
        client.start()
        
        try:
            if not client.is_logged_in():
                print("❌ Not logged in!")
                return
            
            client.clear_cart()
            
            for product in products:
                print(f"➤ Adding {product['name']} x{product['quantity']}")
                
                if use_ai:
                    # Use AI to pick the best product
                    client.add_product_smart(product['name'], product['quantity'], preference)
                else:
                    # Just pick the first result
                    client.add_product(product['name'], product['quantity'])
            
            client.open_cart()
            
            # Keep browser open for user
            print("\n🌐 Browser open - complete checkout manually")
            print("   Close browser when done.")
            
            # Wait for browser to be closed manually
            input("Press Enter to close browser...")
            
        finally:
            client.close()
    
    # Start ordering in background thread
    thread = threading.Thread(target=run_order)
    thread.start()
    
    return jsonify({
        'success': True,
        'message': f'Ordering {len(products)} products...',
        'products': products
    })


@app.route('/history', methods=['GET'])
def history_list():
    """Get all fridge history records."""
    records = get_history(limit=50)
    return jsonify({'success': True, 'history': records})


@app.route('/history', methods=['POST'])
def history_add():
    """Add a detection to history with custom date."""
    data = request.json
    date = data.get('date')  # YYYY-MM-DD
    items = data.get('items', {})
    
    if not date or not items:
        return jsonify({'error': 'Date and items required'}), 400
    
    record_id = add_history(date, items)
    return jsonify({'success': True, 'id': record_id})


@app.route('/history/<int:record_id>', methods=['DELETE'])
def history_delete(record_id):
    """Delete a history record."""
    deleted = delete_history(record_id)
    if deleted:
        return jsonify({'success': True})
    return jsonify({'error': 'Record not found'}), 404


@app.route('/history/clear', methods=['DELETE'])
def history_clear():
    """Delete all history records."""
    count = clear_history()
    return jsonify({'success': True, 'deleted': count})


@app.route('/expected', methods=['GET'])
def get_expected():
    """Get the expected items configuration."""
    return jsonify({
        'expected': {CLASS_TO_GETIR.get(k, k): v for k, v in EXPECTED_ITEMS.items()}
    })


@app.route('/analyze-history', methods=['POST'])
def analyze_history_route():
    """Use AI to analyze fridge history and suggest what to order."""
    try:
        from ai.openrouter import analyze_history
        
        # Get history context
        history_context = get_history_context(limit=10)
        
        if not history_context or history_context == "No previous fridge history available.":
            return jsonify({'success': False, 'error': 'No history to analyze'}), 400
        
        # Call AI to analyze (returns dict with thinking and suggestions)
        print("🧠 Analyzing fridge history with AI...")
        result = analyze_history(history_context, CLASS_TO_GETIR)
        
        suggestions = result.get("suggestions", [])
        thinking = result.get("thinking", "")
        
        if not suggestions:
            return jsonify({
                'success': False, 
                'error': 'AI could not suggest items',
                'thinking': thinking
            }), 400
        
        return jsonify({
            'success': True,
            'suggestions': suggestions,
            'thinking': thinking
        })
        
    except Exception as e:
        print(f"❌ Analysis error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/preferences', methods=['GET'])
def preferences_get():
    """Get user preferences (custom instructions, etc.)."""
    prefs = get_preferences()
    return jsonify({'success': True, 'preferences': prefs})


@app.route('/preferences', methods=['POST'])
def preferences_set():
    """Update user preferences."""
    data = request.json or {}
    custom_instructions = data.get('custom_instructions')
    default_mode = data.get('default_mode')
    preferred_provider = data.get('preferred_provider')
    detection_threshold = data.get('detection_threshold')

    set_preferences(
        custom_instructions=custom_instructions,
        default_mode=default_mode,
        preferred_provider=preferred_provider,
        detection_threshold=detection_threshold
    )
    return jsonify({'success': True})


@app.route('/translations', methods=['GET'])
def get_translations():
    """Get item name translations (class name -> Turkish name)."""
    return jsonify({
        'success': True,
        'translations': CLASS_TO_GETIR
    })


if __name__ == '__main__':
    print("\n🚀 Starting SiparisAgent Test Server")
    print("   Open http://localhost:5000 in your browser\n")
    app.run(debug=True, port=5000)

