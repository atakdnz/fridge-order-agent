"""
Flask server for testing fridge detection and ordering.
"""

import os
import tempfile
import threading
from flask import Flask, request, jsonify, send_from_directory
from detection.detector import FridgeDetector, CLASS_TO_GETIR, EXPECTED_ITEMS
from browser.getir_client import GetirClient

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
        detected = detector.detect(temp_path, confidence=confidence)
        missing = detector.get_missing_items(detected)
        
        # Format response
        detected_list = [
            {'name': CLASS_TO_GETIR.get(k, k), 'count': v, 'class': k}
            for k, v in detected.items()
        ]
        
        return jsonify({
            'success': True,
            'detected': detected_list,
            'missing': missing,
            'expected': {CLASS_TO_GETIR.get(k, k): v for k, v in EXPECTED_ITEMS.items()}
        })
        
    finally:
        # Cleanup temp file
        os.unlink(temp_path)


@app.route('/order', methods=['POST'])
def order():
    """
    Order the specified products on Getir.
    Runs Playwright in a separate thread.
    """
    data = request.json
    products = data.get('products', [])
    
    if not products:
        return jsonify({'error': 'No products specified'}), 400
    
    use_ai = data.get('use_ai', False)
    preference = data.get('preference', 'cheapest')
    
    def run_order():
        """Run the ordering in background."""
        client = GetirClient()
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


@app.route('/expected', methods=['GET'])
def get_expected():
    """Get the expected items configuration."""
    return jsonify({
        'expected': {CLASS_TO_GETIR.get(k, k): v for k, v in EXPECTED_ITEMS.items()}
    })


if __name__ == '__main__':
    print("\n🚀 Starting SiparisAgent Test Server")
    print("   Open http://localhost:5000 in your browser\n")
    app.run(debug=True, port=5000)
