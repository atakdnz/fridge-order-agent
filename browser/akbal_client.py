"""
Akbal Market browser automation client using Playwright.
Handles product search and cart management. No login required.
"""

import time
from playwright.sync_api import sync_playwright, Browser, Page, BrowserContext
from config.settings import (
    AKBAL_BASE_URL,
    AKBAL_SEARCH_URL,
    HEADLESS,
    TIMEOUT,
)


class AkbalClient:
    """Browser automation client for Akbal Market (no login required)"""

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
        """Start the browser."""
        self.playwright = sync_playwright().start()

        # Browser launch args
        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--no-sandbox",
        ]

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

        # Context options
        context_options = {
            "viewport": {"width": 1920, "height": 1080},
            "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "locale": "tr-TR",
            "timezone_id": "Europe/Istanbul",
        }

        self.context = self.browser.new_context(**context_options)
        self.page = self.context.new_page()
        self.page.set_default_timeout(TIMEOUT)

        # Remove webdriver property
        self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)

        print("🛒 Akbal Market client ready (no login required)")

    def close(self) -> None:
        """Close browser and cleanup."""
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()

    def is_logged_in(self) -> bool:
        """Always returns True since login is not required."""
        return True

    def search_product(self, query: str) -> bool:
        """
        Search for a product on Akbal Market.
        Returns True if products were found.
        """
        print(f"🔍 Searching Akbal for: {query}")

        # Navigate using URL search
        search_url = f"{AKBAL_SEARCH_URL}?q={query}"
        self.page.goto(search_url)
        self.page.wait_for_load_state("domcontentloaded")
        time.sleep(2)

        # Check if products are visible
        try:
            products = self.page.locator(".product-item, .item.product-item").first
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
            time.sleep(1)

            # Magento product selectors
            product_cards = self.page.locator(".product-item, .item.product-item")
            count = product_cards.count()
            print(f"   📦 Found {count} products on page")

            if count == 0:
                print(f"   ⚠ No products visible!")
                return []

            count = min(count, limit)

            for i in range(count):
                try:
                    card = product_cards.nth(i)

                    # Extract product name
                    name = ""
                    name_selectors = [
                        ".product-item-link",
                        ".product-item-name a",
                        ".product-item-name",
                        "a.product-item-link"
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
                        name = f"Product {i+1}"

                    # Extract price
                    price = "N/A"
                    price_selectors = [
                        ".price",
                        ".price-wrapper .price",
                        "[data-price-type='finalPrice'] .price",
                        ".special-price .price",
                        ".regular-price .price"
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

            product_cards = self.page.locator(".product-item, .item.product-item")
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
                "button.tocart",
                "button.action.tocart",
                "button[title='Sepete Ekle']",
                "button:has-text('Sepete Ekle')",
                ".action.tocart.primary",
                "form button[type='submit']"
            ]

            clicked = False
            for sel in add_btn_selectors:
                try:
                    add_btn = card.locator(sel).first
                    if add_btn.is_visible(timeout=1000):
                        add_btn.click()
                        clicked = True
                        print(f"   ✓ Added to cart")
                        time.sleep(1)
                        break
                except:
                    continue

            if not clicked:
                print(f"   ⚠ Could not find add to cart button")
                return False

            # Add more if quantity > 1
            for i in range(1, quantity):
                time.sleep(0.5)
                try:
                    # Click add button again for each additional item
                    for sel in add_btn_selectors:
                        try:
                            add_btn = card.locator(sel).first
                            if add_btn.is_visible(timeout=1000):
                                add_btn.click()
                                print(f"   ✓ Added another (qty: {i + 1})")
                                time.sleep(0.5)
                                break
                        except:
                            continue
                except Exception as e:
                    print(f"   ! Could not add more: {e}")
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
            preference: Selection criteria for AI
        """
        print(f"\n🔍 Searching Akbal for: {name}")

        if not self.search_product(name):
            print(f"   ❌ Search failed for '{name}'")
            return False

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

            history_context = get_history_context(limit=10)
            print(f"   📜 History available: {len(history_context) > 0}")

            print(f"   🤖 Asking AI to choose...")
            selected_index = choose_product(products, name, preference, history_context)
            print(f"   ✅ AI chose: #{selected_index + 1} - {products[selected_index]['name']}")
        except Exception as e:
            print(f"   ⚠ AI selection failed: {e}")
            print(f"   ⚠ Falling back to first product")
            selected_index = 0

        return self.add_product_by_index(selected_index, quantity)

    def add_product(self, name: str, quantity: int = 1) -> bool:
        """Search for a product and add first result to cart."""
        if not self.search_product(name):
            return False
        return self.add_product_by_index(0, quantity)

    def clear_cart(self) -> bool:
        """Clear all items from the cart."""
        print("🗑️  Clearing Akbal cart...")
        try:
            # Go to cart page
            self.page.goto(f"{AKBAL_BASE_URL}/checkout/cart/")
            self.page.wait_for_load_state("domcontentloaded")
            time.sleep(2)

            # Look for remove buttons and click them all
            remove_btns = self.page.locator("a.action-delete, .action.delete, a[title='Sil']")
            count = remove_btns.count()

            if count == 0:
                print("   ℹ Cart is already empty")
                return True

            for i in range(count):
                try:
                    remove_btns.first.click()
                    time.sleep(1)
                except:
                    pass

            print(f"   ✓ Removed {count} items from cart")
            return True

        except Exception as e:
            print(f"   ⚠ Could not clear cart: {e}")
            return False

    def open_cart(self) -> None:
        """Open the cart page."""
        print("🛒 Opening Akbal cart...")
        try:
            self.page.goto(f"{AKBAL_BASE_URL}/checkout/cart/")
            self.page.wait_for_load_state("domcontentloaded")
            time.sleep(1)
            print("   ✓ Cart opened")
        except Exception as e:
            print(f"   Could not open cart: {e}")

    def get_cart_count(self) -> int:
        """Get current number of items in cart."""
        try:
            cart_count = self.page.locator(".counter-number, .minicart-wrapper .counter-number").first
            if cart_count.is_visible(timeout=2000):
                text = cart_count.text_content()
                return int(text) if text and text.isdigit() else 0
        except:
            pass
        return 0
