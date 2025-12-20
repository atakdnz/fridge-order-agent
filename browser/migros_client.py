"""
Migros Sanal Market browser automation client using Playwright.
Handles login, product search, and cart management.
"""

import time
from playwright.sync_api import sync_playwright, Browser, Page, BrowserContext
from config.settings import (
    MIGROS_BASE_URL,
    MIGROS_AUTH_FILE,
    HEADLESS,
    TIMEOUT,
)


class MigrosClient:
    """Browser automation client for Migros Sanal Market"""

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

        # Browser launch args to avoid detection
        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--no-sandbox",
        ]

        # Try Chrome channel first (better for bot detection), fall back to Chromium
        try:
            self.browser = self.playwright.chromium.launch(
                headless=HEADLESS,
                channel="chrome",
                args=launch_args
            )
            print("🌐 Using Chrome browser")
        except Exception:
            print("⚠️  Chrome not found, using Chromium")
            self.browser = self.playwright.chromium.launch(
                headless=HEADLESS,
                args=launch_args
            )

        # Context options to appear more like a real browser
        context_options = {
            "viewport": {"width": 1920, "height": 1080},
            "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "locale": "tr-TR",
            "timezone_id": "Europe/Istanbul",
        }

        # Load existing session if available
        if MIGROS_AUTH_FILE.exists():
            print("📂 Loading saved Migros session...")
            context_options["storage_state"] = str(MIGROS_AUTH_FILE)
            self.context = self.browser.new_context(**context_options)
        else:
            print("🆕 Starting fresh Migros session...")
            self.context = self.browser.new_context(**context_options)

        self.page = self.context.new_page()
        self.page.set_default_timeout(TIMEOUT)

        # Remove webdriver property to avoid detection
        self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)

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
            self.context.storage_state(path=str(MIGROS_AUTH_FILE))
            print(f"💾 Migros session saved to {MIGROS_AUTH_FILE}")

    def _handle_popups(self) -> None:
        """Handle cookie consent and delivery method popups."""
        # Cookie consent popup
        try:
            cookie_btn = self.page.locator("button:has-text('Kabul Et'), button:has-text('Tümünü Kabul Et')").first
            if cookie_btn.is_visible(timeout=3000):
                cookie_btn.click()
                print("🍪 Accepted cookies")
                time.sleep(0.5)
        except:
            pass

        # Delivery method popup - select "Adresime Gelsin" (home delivery)
        try:
            delivery_btn = self.page.locator("button:has-text('Adresime Gelsin'), [data-testid='delivery-type-home']").first
            if delivery_btn.is_visible(timeout=2000):
                delivery_btn.click()
                print("🏠 Selected home delivery")
                time.sleep(0.5)
        except:
            pass

    def is_logged_in(self) -> bool:
        """Check if user is currently logged in."""
        self.page.goto(MIGROS_BASE_URL)
        self.page.wait_for_load_state("networkidle")
        self._handle_popups()

        # Look for signs of being logged in
        # Migros shows "Giriş Yap" button when not logged in
        try:
            login_btn = self.page.locator("button:has-text('Giriş Yap'), a:has-text('Giriş Yap')").first
            if login_btn.is_visible(timeout=3000):
                return False
        except:
            pass

        # Check for user menu/profile icon as a sign of being logged in
        try:
            user_menu = self.page.locator("[data-testid='user-menu'], .user-menu, .account-menu").first
            if user_menu.is_visible(timeout=2000):
                return True
        except:
            pass

        return True

    def login(self) -> bool:
        """
        Open browser for manual login.
        User completes login, then session is saved.
        """
        print("\n🔐 Login to Migros Sanal Market")
        print("=" * 40)

        self.page.goto(MIGROS_BASE_URL)
        self.page.wait_for_load_state("networkidle")
        self._handle_popups()

        print("\n📱 Please complete the login in the browser:")
        print("   1. Click 'Giriş Yap'")
        print("   2. Enter your credentials or use SMS")
        print("   3. Select your delivery address")
        print("\n⏳ Waiting for you to complete login...")
        print("   (Press Enter in terminal when done)\n")

        input(">>> Press ENTER after completing login: ")

        # Verify login was successful
        if self.is_logged_in():
            self.save_session()
            print("✅ Migros login successful! Session saved.\n")
            return True
        else:
            print("❌ Migros login verification failed. Please try again.\n")
            return False

    def search_product(self, query: str) -> bool:
        """
        Search for a product on Migros.
        Returns True if products were found.
        """
        print(f"🔍 Searching Migros for: {query}")

        # Navigate using URL search (more reliable)
        search_url = f"{MIGROS_BASE_URL}/arama?q={query}"
        self.page.goto(search_url)
        self.page.wait_for_load_state("domcontentloaded")
        time.sleep(2)  # Let the page settle

        self._handle_popups()

        # Check if products are visible
        try:
            products = self.page.locator("[data-monitor-product], .product-card, article[class*='product']").first
            if products.is_visible(timeout=5000):
                print(f"   ✓ Search completed")
                return True
        except:
            pass

        print(f"   ⚠ No products found for '{query}'")
        return False

    def get_product_list(self, limit: int = 10) -> list[dict]:
        """
        Scrape visible products from search results.

        Returns:
            List of dicts with 'name', 'price', 'index' keys
        """
        products = []

        try:
            time.sleep(2)

            # Migros product card selectors
            product_cards = self.page.locator("[data-monitor-product], .product-card, article[class*='product']")
            count = product_cards.count()
            print(f"   📦 Found {count} products on page")

            if count == 0:
                print(f"   ⚠ No products visible!")
                return []

            count = min(count, limit)

            for i in range(count):
                try:
                    card = product_cards.nth(i)

                    # Try to extract product name
                    name = ""
                    name_selectors = [
                        "[data-monitor-name]",
                        ".product-name",
                        "[class*='ProductName']",
                        "h5",
                        "[class*='name']"
                    ]
                    for sel in name_selectors:
                        try:
                            name_el = card.locator(sel).first
                            if name_el.is_visible(timeout=500):
                                name = name_el.text_content() or ""
                                if name.strip():
                                    break
                        except:
                            continue

                    if not name:
                        name = card.text_content() or f"Product {i+1}"

                    # Try to extract price
                    price = "N/A"
                    price_selectors = [
                        "[data-monitor-price]",
                        ".product-price",
                        "[class*='Price']",
                        "[class*='price']",
                        ".amount"
                    ]
                    for sel in price_selectors:
                        try:
                            price_el = card.locator(sel).first
                            if price_el.is_visible(timeout=500):
                                price_text = price_el.text_content() or ""
                                if price_text.strip():
                                    price = price_text.strip()
                                    break
                        except:
                            continue

                    # Clean up name
                    name = name.strip()[:50]

                    products.append({
                        "name": name,
                        "price": price,
                        "index": i
                    })
                    print(f"      {i+1}. {name[:40]} - {price}")

                except Exception as e:
                    print(f"   ! Error scraping product {i}: {e}")

        except Exception as e:
            print(f"   ⚠ Could not scrape products: {e}")

        return products

    def add_product_by_index(self, index: int, quantity: int = 1) -> bool:
        """
        Add a product at specific index to cart.

        Args:
            index: 0-based index of the product
            quantity: How many to add
        """
        try:
            print(f"   🛒 Adding product at index {index}...")

            # Get product cards
            product_cards = self.page.locator("[data-monitor-product], .product-card, article[class*='product']")
            total = product_cards.count()

            if total == 0:
                print(f"   ❌ No products found!")
                return False

            if index >= total:
                print(f"   ⚠ Index {index} out of range (only {total} products), using 0")
                index = 0

            card = product_cards.nth(index)

            # Find and click add to cart button
            add_btn_selectors = [
                "button:has-text('Sepete Ekle')",
                "[data-testid='add-to-cart']",
                "[class*='add-to-cart']",
                "button[class*='AddToCart']",
                ".add-button",
                "button:has-text('Ekle')"
            ]

            clicked = False
            for sel in add_btn_selectors:
                try:
                    add_btn = card.locator(sel).first
                    if add_btn.is_visible(timeout=1000):
                        add_btn.click()
                        clicked = True
                        print(f"   ✓ Clicked add to cart")
                        time.sleep(0.5)
                        break
                except:
                    continue

            if not clicked:
                # Try clicking on the card first to open product modal
                try:
                    card.click()
                    time.sleep(1)
                    # Then find add to cart in the modal
                    modal_add = self.page.locator("button:has-text('Sepete Ekle')").first
                    if modal_add.is_visible(timeout=3000):
                        modal_add.click()
                        clicked = True
                        print(f"   ✓ Added via product modal")
                        time.sleep(0.5)
                except:
                    pass

            if not clicked:
                print(f"   ⚠ Could not find add to cart button")
                return False

            # Add more if quantity > 1
            for i in range(1, quantity):
                time.sleep(0.3)
                try:
                    # Find plus/increment button
                    plus_btn = self.page.locator("button:has-text('+'), [data-testid='increment'], .increment-btn").first
                    if plus_btn.is_visible(timeout=2000):
                        plus_btn.click()
                        print(f"   ✓ Quantity increased to {i + 1}")
                except Exception as e:
                    print(f"   ! Could not increase quantity: {e}")
                    break

            return True

        except Exception as e:
            print(f"   ❌ Failed to add product at index {index}: {e}")
            return False

    def add_product_smart(self, name: str, quantity: int = 1, preference: str = "cheapest") -> bool:
        """
        Search for a product and add it to cart using AI to choose the best option.

        Args:
            name: Product to search for
            quantity: How many to add
            preference: Selection criteria for AI (cheapest, organic, etc.)
        """
        print(f"\n🔍 Searching Migros for: {name}")

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
            from db.database import get_history_context

            # Get fridge history context for smarter decisions
            history_context = get_history_context(limit=10)
            print(f"   📜 History available: {len(history_context) > 0}")

            print(f"   🤖 Asking AI to choose...")
            selected_index = choose_product(products, name, preference, history_context)
            print(f"   ✅ AI chose: #{selected_index + 1} - {products[selected_index]['name']}")
        except Exception as e:
            print(f"   ⚠ AI selection failed: {e}")
            print(f"   ⚠ Falling back to first product")
            selected_index = 0

        # Add the selected product
        return self.add_product_by_index(selected_index, quantity)

    def add_product(self, name: str, quantity: int = 1) -> bool:
        """
        Search for a product and add first result to cart.
        """
        if not self.search_product(name):
            return False

        return self.add_product_by_index(0, quantity)

    def clear_cart(self) -> bool:
        """
        Clear all items from the cart.
        """
        print("🗑️  Clearing Migros cart...")
        try:
            self.page.goto(f"{MIGROS_BASE_URL}/sepetim")
            self.page.wait_for_load_state("domcontentloaded")
            time.sleep(2)

            # Look for clear/empty cart option
            clear_selectors = [
                "button:has-text('Sepeti Boşalt')",
                "button:has-text('Tümünü Sil')",
                "[data-testid='clear-cart']",
                ".clear-cart"
            ]

            for sel in clear_selectors:
                try:
                    clear_btn = self.page.locator(sel).first
                    if clear_btn.is_visible(timeout=2000):
                        clear_btn.click()
                        time.sleep(1)

                        # Handle confirmation dialog
                        try:
                            confirm = self.page.locator("button:has-text('Evet'), button:has-text('Onayla')").first
                            if confirm.is_visible(timeout=2000):
                                confirm.click()
                                time.sleep(1)
                        except:
                            pass

                        print("   ✓ Cart cleared")
                        return True
                except:
                    continue

            print("   ℹ Cart may already be empty")
            return True

        except Exception as e:
            print(f"   ⚠ Could not clear cart: {e}")
            return False

    def open_cart(self) -> None:
        """Open the cart/basket page."""
        print("🛒 Opening Migros cart...")
        try:
            self.page.goto(f"{MIGROS_BASE_URL}/sepetim")
            self.page.wait_for_load_state("domcontentloaded")
            time.sleep(1)
            print("   ✓ Cart opened")
        except Exception as e:
            print(f"   Could not open cart: {e}")

    def get_cart_count(self) -> int:
        """Get current number of items in cart."""
        try:
            cart_badge = self.page.locator("[data-testid='cart-count'], .cart-count, .basket-count").first
            if cart_badge.is_visible(timeout=2000):
                text = cart_badge.text_content()
                return int(text) if text and text.isdigit() else 0
        except:
            pass
        return 0
