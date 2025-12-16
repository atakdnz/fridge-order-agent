#!/usr/bin/env python3
"""
SiparisAgent - Fridge Order Automation CLI

Usage:
    python main.py login   - Login to Getir (save session)
    python main.py order   - Add missing products to cart
    python main.py cart    - Show cart info
    python main.py test    - Dry run with test products
"""

import sys
from browser.getir_client import GetirClient
from detection.detector import get_missing_products
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


def cmd_order():
    """Handle order command - add products to cart."""
    print("\n🛒 SiparisAgent - Auto Order")
    print("=" * 40)
    
    # Get missing products (from detector or test)
    products = get_missing_products()
    
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
        print("\nAvailable commands: login, order, cart, test")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    commands = {
        "login": cmd_login,
        "order": cmd_order,
        "cart": cmd_cart,
        "test": cmd_test,
    }
    
    if command in commands:
        try:
            commands[command]()
        except KeyboardInterrupt:
            print("\n\n⚠ Cancelled by user")
        except Exception as e:
            print(f"\n❌ Error: {e}")
            raise
    else:
        print(f"❌ Unknown command: {command}")
        print("Available commands: login, order, cart, test")
        sys.exit(1)


if __name__ == "__main__":
    main()
