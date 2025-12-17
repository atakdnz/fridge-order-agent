#!/usr/bin/env python3
"""
SiparisAgent - Fridge Order Automation CLI

Usage:
    python main.py login              - Login to Getir (save session)
    python main.py order              - Add test products to cart
    python main.py order <image>      - Detect missing items from image and order
    python main.py detect <image>     - Detect items in image (no ordering)
    python main.py cart               - Show cart info
    python main.py test               - Dry run with test products
"""

import sys
from browser.getir_client import GetirClient
from detection.detector import get_missing_products, detect_from_image
from config.products import get_test_products


def cmd_login():
    """Handle login command."""
    print("\n🛒 SiparisAgent - Getir Login")
    print("=" * 40)
    
    with GetirClient() as client:
        if client.is_logged_in():
            print("✅ Already logged in!")
            client.save_session()
        else:
            client.login()


def cmd_order(image_path: str = None):
    """Handle order command - add products to cart."""
    print("\n🛒 SiparisAgent - Auto Order")
    print("=" * 40)
    
    # Get missing products (from detector or test)
    products = get_missing_products(image_path)
    
    if not products:
        print("\n✅ No missing products detected!")
        return
    
    print(f"\n📋 Products to order ({len(products)}):")
    for p in products:
        print(f"   • {p['name']} x{p['quantity']}")
    print()
    
    # Don't use context manager - we want to keep browser open
    client = GetirClient()
    client.start()
    
    try:
        # Check login status
        if not client.is_logged_in():
            print("❌ Not logged in. Please run 'python main.py login' first.")
            client.close()
            return
        
        # Clear existing cart first
        client.clear_cart()
        
        print("\n🛒 Adding products to cart...\n")
        
        success_count = 0
        for product in products:
            print(f"➤ {product['name']} (x{product['quantity']})")
            if client.add_product(product['name'], product['quantity']):
                success_count += 1
            print()
        
        print("=" * 40)
        print(f"✅ Added {success_count}/{len(products)} products to cart")
        
        # Navigate to cart so user can checkout
        client.open_cart()
        
        print("\n🌐 Browser is on checkout page - complete your order!")
        print("   (Press ENTER in terminal when you're done)\n")
        
        input(">>> Press ENTER to close browser: ")
        
    finally:
        client.close()
        print("👋 Browser closed.")


def cmd_detect(image_path: str):
    """Detect items in image without ordering."""
    print("\n🔍 SiparisAgent - Fridge Detection")
    print("=" * 40)
    
    products = detect_from_image(image_path)
    
    if products:
        print(f"\n📋 Missing products ({len(products)}):")
        for p in products:
            print(f"   • {p['name']} x{p['quantity']} [{p.get('category', '')}]")
    else:
        print("\n✅ All expected items are present in the fridge!")
    
    print("\n💡 Run 'python main.py order <image>' to order these items.")


def cmd_cart():
    """Show current cart status."""
    print("\n🛒 SiparisAgent - Cart Info")
    print("=" * 40)
    
    with GetirClient() as client:
        if not client.is_logged_in():
            print("❌ Not logged in.")
            return
        
        count = client.get_cart_count()
        print(f"🧺 Items in cart: {count}")


def cmd_test():
    """Test mode - show what would be ordered."""
    print("\n🧪 SiparisAgent - Test Mode")
    print("=" * 40)
    
    products = get_test_products()
    
    print(f"\n📋 Test products ({len(products)}):")
    for p in products:
        print(f"   • {p['name']} x{p['quantity']} [{p['category']}]")
    
    print("\n✅ Dry run complete. Use 'python main.py order' to actually order.")


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nAvailable commands: login, order, detect, cart, test")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    try:
        if command == "login":
            cmd_login()
        elif command == "order":
            image_path = sys.argv[2] if len(sys.argv) > 2 else None
            cmd_order(image_path)
        elif command == "detect":
            if len(sys.argv) < 3:
                print("❌ Usage: python main.py detect <image_path>")
                sys.exit(1)
            cmd_detect(sys.argv[2])
        elif command == "cart":
            cmd_cart()
        elif command == "test":
            cmd_test()
        else:
            print(f"❌ Unknown command: {command}")
            print("Available commands: login, order, detect, cart, test")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⚠ Cancelled by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise


if __name__ == "__main__":
    main()
