"""
Getir.com browser automation client using Playwright.
Handles login, product search, and cart management.
"""

import time
from playwright.sync_api import sync_playwright, Browser, Page, BrowserContext
from config.settings import (
    GETIR_BASE_URL,
    AUTH_FILE,
    HEADLESS,
    TIMEOUT,
)


class GetirClient:
    """Browser automation client for Getir.com"""

    def __init__(self):
        self.playwright = None
        self.browser: Browser | None = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def start(self) -> None:
        """Start the browser and load session if available."""
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=HEADLESS)
        
        # Load existing session if available
        if AUTH_FILE.exists():
            print("📂 Loading saved session...")
            self.context = self.browser.new_context(storage_state=str(AUTH_FILE))
        else:
            print("🆕 Starting fresh session...")
            self.context = self.browser.new_context()
        
        self.page = self.context.new_page()
        self.page.set_default_timeout(TIMEOUT)

    def close(self) -> None:
        """Close browser and cleanup."""
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()

    def save_session(self) -> None:
        """Save current session to file."""
        if self.context:
            self.context.storage_state(path=str(AUTH_FILE))
            print(f"💾 Session saved to {AUTH_FILE}")

    def clear_cart(self) -> bool:
        """
        Clear all items from the cart.
        Navigates to cart page and clicks 'Sepeti temizle' button.
        """
        print("🗑️  Clearing cart...")
        try:
            # Navigate to cart page
            self.page.goto(f"{GETIR_BASE_URL}/sepet/")
            self.page.wait_for_load_state("domcontentloaded")
            time.sleep(2)
            
            # Look for clear cart button
            clear_btn = self.page.get_by_text("Sepeti temizle", exact=False)
            
            if clear_btn.is_visible(timeout=3000):
                clear_btn.click()
                time.sleep(1)
                
                # Handle confirmation dialog if present
                try:
                    confirm_btn = self.page.get_by_text("Evet", exact=False)
                    if confirm_btn.is_visible(timeout=2000):
                        confirm_btn.click()
                        time.sleep(1)
                except:
                    pass
                
                print("   ✓ Cart cleared")
                return True
            else:
                print("   ℹ Cart is already empty")
                return True
                
        except Exception as e:
            print(f"   ⚠ Could not clear cart: {e}")
            return False

    def is_logged_in(self) -> bool:
        """Check if user is currently logged in."""
        self.page.goto(GETIR_BASE_URL)
        self.page.wait_for_load_state("networkidle")
        
        # Look for signs of being logged in (profile icon, no login prompt)
        # Getir shows phone input when not logged in
        try:
            phone_input = self.page.locator("input[placeholder*='telefon']").first
            if phone_input.is_visible(timeout=3000):
                return False
        except:
            pass
        
        # Also check for login button visibility
        try:
            login_btn = self.page.get_by_text("Giriş yap", exact=False).first
            if login_btn.is_visible(timeout=2000):
                return False
        except:
            pass
            
        return True

    def login(self) -> bool:
        """
        Open browser for manual login.
        User completes SMS verification, then session is saved.
        """
        print("\n🔐 Login to Getir.com")
        print("=" * 40)
        
        self.page.goto(GETIR_BASE_URL)
        self.page.wait_for_load_state("networkidle")
        
        # Accept cookies if present
        try:
            cookie_btn = self.page.get_by_text("Tümünü Kabul Et", exact=False)
            if cookie_btn.is_visible(timeout=3000):
                cookie_btn.click()
                print("🍪 Accepted cookies")
        except:
            pass
        
        print("\n📱 Please complete the login in the browser:")
        print("   1. Enter your phone number")
        print("   2. Complete SMS verification")
        print("   3. Select your delivery address")
        print("\n⏳ Waiting for you to complete login...")
        print("   (Press Enter in terminal when done)\n")
        
        input(">>> Press ENTER after completing login: ")
        
        # Verify login was successful
        if self.is_logged_in():
            self.save_session()
            print("✅ Login successful! Session saved.\n")
            return True
        else:
            print("❌ Login verification failed. Please try again.\n")
            return False

    def search_product(self, query: str) -> bool:
        """
        Search for a product on Getir.
        Returns True if products were found.
        """
        print(f"🔍 Searching for: {query}")
        
        # Navigate to home first
        self.page.goto(GETIR_BASE_URL)
        self.page.wait_for_load_state("domcontentloaded")
        time.sleep(2)  # Let SPA settle - Getir is a React app
        
        # Find and click search input
        try:
            # Try multiple selectors for search
            search_selectors = [
                "input[placeholder*='Ürün ara']",
                "[aria-label='Search Bar']",
                "input[placeholder*='ara']",
            ]
            
            search_input = None
            for selector in search_selectors:
                try:
                    search_input = self.page.locator(selector).first
                    if search_input.is_visible(timeout=3000):
                        break
                except:
                    continue
            
            if search_input and search_input.is_visible():
                search_input.click()
                search_input.fill(query)
                search_input.press("Enter")
                time.sleep(2)  # Wait for search results
                print(f"   ✓ Search completed")
                return True
            else:
                print(f"   ⚠ Search input not found, trying URL search")
                # Fallback: direct URL navigation
                search_url = f"{GETIR_BASE_URL}/arama?q={query}"
                self.page.goto(search_url)
                self.page.wait_for_load_state("domcontentloaded")
                time.sleep(2)
                return True
                
        except Exception as e:
            print(f"   ❌ Search failed: {e}")
            return False

    def get_product_list(self, limit: int = 10) -> list[dict]:
        """
        Scrape visible products from search results.
        
        Returns:
            List of dicts with 'name', 'price', 'index' keys
        """
        products = []
        
        try:
            # Wait for products to load
            time.sleep(2)
            
            # Get all product buttons
            product_buttons = self.page.locator("button[aria-label='Show Product']")
            count = product_buttons.count()
            print(f"   📦 Found {count} products on page")
            
            if count == 0:
                print(f"   ⚠ No products visible!")
                return []
            
            count = min(count, limit)
            
            for i in range(count):
                try:
                    btn = product_buttons.nth(i)
                    # Get text content which usually contains name and price
                    text = btn.text_content() or ""
                    
                    # Try to extract name and price
                    # Format is usually: "Product Name ₺XX.XX"
                    parts = text.strip().split("₺")
                    name = parts[0].strip() if parts else text.strip()
                    price = f"₺{parts[1].strip()}" if len(parts) > 1 else "N/A"
                    
                    products.append({
                        "name": name[:50],  # Truncate long names
                        "price": price,
                        "index": i
                    })
                    print(f"      {i+1}. {name[:40]} - {price}")
                except Exception as e:
                    print(f"   ! Error scraping product {i}: {e}")
                    
        except Exception as e:
            print(f"   ⚠ Could not scrape products: {e}")
        
        return products

    def add_product_smart(self, name: str, quantity: int = 1, preference: str = "cheapest") -> bool:
        """
        Search for a product and add it to cart using AI to choose the best option.
        
        Args:
            name: Product to search for
            quantity: How many to add
            preference: Selection criteria for AI (cheapest, organic, etc.)
        """
        print(f"\n🔍 Searching for: {name}")
        
        if not self.search_product(name):
            print(f"   ❌ Search failed for '{name}'")
            return False
        
        # Get available products
        print(f"   📋 Scraping products...")
        products = self.get_product_list()
        
        if not products:
            print(f"   ⚠ No products found for '{name}'")
            return False
        
        print(f"   📊 {len(products)} products scraped, preference: {preference}")
        
        # Use AI to choose the best product
        try:
            from ai.openrouter import choose_product
            print(f"   🤖 Asking AI to choose...")
            selected_index = choose_product(products, name, preference)
            print(f"   ✅ AI chose: #{selected_index + 1} - {products[selected_index]['name']}")
        except Exception as e:
            print(f"   ⚠ AI selection failed: {e}")
            print(f"   ⚠ Falling back to first product")
            selected_index = 0
        
        # Click the selected product's counter button
        return self.add_product_by_index(selected_index, quantity)

    def add_product_by_index(self, index: int, quantity: int = 1) -> bool:
        """
        Add a product at specific index to cart.
        
        Args:
            index: 0-based index of the product
            quantity: How many to add
        """
        try:
            print(f"   🛒 Adding product at index {index}...")
            
            # Each product has a counter button following the Show Product button
            # Structure is: [ShowProduct0, Counter0, ShowProduct1, Counter1, ...]
            counter_buttons = self.page.locator("button[aria-label='counter']")
            total_counters = counter_buttons.count()
            print(f"   🔢 Found {total_counters} counter buttons")
            
            if total_counters == 0:
                print(f"   ❌ No counter buttons found!")
                return False
            
            if index >= total_counters:
                print(f"   ⚠ Index {index} out of range (only {total_counters} buttons), using 0")
                index = 0
            
            # Find the counter button for the product at index
            counter_btn = counter_buttons.nth(index)
            
            if counter_btn.is_visible(timeout=3000):
                counter_btn.click()
                print(f"   ✓ Clicked counter button at index {index}")
                time.sleep(0.5)
                
                # Add more if quantity > 1
                for i in range(1, quantity):
                    time.sleep(0.3)
                    # After first add, click the plus button (second counter)
                    plus_btn = self.page.locator("button[aria-label='counter']").nth(1)
                    if plus_btn.is_visible(timeout=2000):
                        plus_btn.click()
                        print(f"   ✓ Quantity increased to {i + 1}")
                
                return True
            else:
                print(f"   ⚠ Counter button not visible at index {index}")
                return False
                
        except Exception as e:
            print(f"   ❌ Failed to add product at index {index}: {e}")
            return False

    def add_first_product_to_cart(self) -> bool:
        """
        Add the first visible product to cart.
        The page structure is: [ShowProduct, Counter, ShowProduct, Counter, ...]
        So the first counter button belongs to the first product.
        Returns True if successful.
        """
        try:
            # Wait for products to load
            time.sleep(1)
            
            # Wait for products to appear
            try:
                self.page.locator("button[aria-label='Show Product']").first.wait_for(timeout=5000)
            except:
                print(f"   ⚠ No products found")
                return False
            
            # Products are in order: [ShowProduct1, Counter1, ShowProduct2, Counter2, ...]
            # Simply click the FIRST counter button - it belongs to the first product
            counter_btn = self.page.locator("button[aria-label='counter']").first
            
            try:
                if counter_btn.is_visible(timeout=3000):
                    counter_btn.click()
                    print(f"   ✓ Added to cart")
                    time.sleep(0.5)
                    return True
                else:
                    print(f"   ⚠ Counter button not visible")
                    return False
            except Exception as e:
                print(f"   ! Counter button error: {e}")
                return False
            
        except Exception as e:
            print(f"   ❌ Failed to add to cart: {e}")
            return False

    def add_product(self, name: str, quantity: int = 1) -> bool:
        """
        Search for a product and add it to cart.
        Handles quantity > 1 by clicking plus button for subsequent adds.
        """
        if not self.search_product(name):
            return False
        
        # First add - click the first counter button
        if not self.add_first_product_to_cart():
            return False
        
        # For quantity > 1, we need to click the SECOND counter button (plus)
        # because after first add, buttons become [minus, plus]
        for i in range(1, quantity):
            time.sleep(0.3)  # Small delay between clicks
            try:
                counter_buttons = self.page.locator("button[aria-label='counter']")
                # After adding, there are 2 buttons: first=minus, second=plus
                # We want to click the second one (plus)
                if counter_buttons.count() >= 2:
                    counter_buttons.nth(1).click()  # Click the plus (second button)
                    print(f"   ✓ Quantity increased to {i + 1}")
                else:
                    # Fallback to first button if structure different
                    counter_buttons.first.click()
            except Exception as e:
                print(f"   ! Could not increase quantity: {e}")
                break
        
        return True

    def get_cart_count(self) -> int:
        """Get current number of items in cart."""
        try:
            # Look for cart badge
            cart_badge = self.page.locator("[class*='cart'] [class*='badge'], [class*='Cart'] [class*='count']").first
            if cart_badge.is_visible(timeout=2000):
                text = cart_badge.text_content()
                return int(text) if text and text.isdigit() else 0
        except:
            pass
        return 0

    def open_cart(self) -> None:
        """Open the cart/basket page."""
        print("🛒 Opening cart...")
        try:
            self.page.goto(f"{GETIR_BASE_URL}/sepet/")
            self.page.wait_for_load_state("domcontentloaded")
            time.sleep(1)
            print("   ✓ Cart opened")
        except Exception as e:
            print(f"   Could not open cart: {e}")
