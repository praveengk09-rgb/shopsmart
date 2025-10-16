import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import random
import re
from urllib.parse import quote_plus, quote

class UniversalEcommerceScraper:
    def __init__(self, debug_mode=False):
        self.driver = None
        self.debug_mode = debug_mode
    
    def debug_print(self, message):
        if self.debug_mode:
            print(f"  [DEBUG] {message}")

    def create_driver(self):
        options = uc.ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        prefs = {
            "profile.default_content_setting_values.geolocation": 1,  # Allow geolocation
            "profile.default_content_settings.popups": 0,
            "profile.default_content_setting_values.notifications": 2
        }
        options.add_experimental_option("prefs", prefs)
        
        self.driver = uc.Chrome(options=options)
        
        # Set geolocation to Mumbai coordinates for Croma
        try:
            self.driver.execute_cdp_cmd("Emulation.setGeolocationOverride", {
                "latitude": 19.0760,
                "longitude": 72.8777,
                "accuracy": 100
            })
        except:
            pass
        
        return self.driver

    def handle_location_popup(self, timeout=5):
        """Handle location permission popup by clicking 'Allow this time' or similar buttons"""
        try:
            wait = WebDriverWait(self.driver, timeout)
            
            # Try multiple possible button texts and selectors
            location_button_selectors = [
                "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'allow this time')]",
                "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'allow')]",
                "//button[contains(@class, 'allow')]",
                "//button[@id='allow-button']",
                "//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'allow')]"
            ]
            
            for selector in location_button_selectors:
                try:
                    button = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                    button.click()
                    self.debug_print("✅ Clicked location permission button")
                    time.sleep(2)
                    return True
                except:
                    continue
            
            self.debug_print("No location popup found or already handled")
            return False
            
        except TimeoutException:
            self.debug_print("No location popup appeared")
            return False
        except Exception as e:
            self.debug_print(f"Error handling location popup: {str(e)[:50]}")
            return False

    def extract_price(self, price_text):
        if not price_text or price_text == "N/A":
            return None
        cleaned = re.sub(r'[^\d.]', '', price_text)
        match = re.search(r'(\d+)', cleaned)
        return int(match.group(1)) if match else None

    def is_relevant_product(self, title, query):
        if not title or len(title) < 3:
            return False
        
        title_lower = title.lower()
        query_lower = query.lower()
        
        # Filter accessories
        accessory_keywords = ['cover', 'case', 'protector', 'charger', 'cable', 'adapter', 
                             'earphone', 'headphone', 'stand', 'holder', 'skin', 'bumper']
        if any(acc in title_lower for acc in accessory_keywords):
            return False
        
        # iPhone model matching
        if 'iphone' in query_lower:
            query_model = re.search(r'iphone\s*(\d+)', query_lower)
            title_model = re.search(r'iphone\s*(\d+)', title_lower)
            if query_model and title_model:
                return query_model.group(1) == title_model.group(1)
        
        # General matching
        query_words = [w for w in query_lower.split() if len(w) > 2]
        if not query_words:
            return False
        match_count = sum(1 for word in query_words if word in title_lower)
        return match_count >= len(query_words) / 2

    def auto_categorize_product(self, title):
        title_lower = title.lower()
        categories = {
            'Mobile Phones': ['phone', 'mobile', 'iphone', 'samsung', 'oneplus', 'pixel'],
            'Laptops': ['laptop', 'notebook', 'macbook', 'chromebook'],
            'Television': ['tv', 'television', 'smart tv'],
            'Groceries': ['rice', 'wheat', 'oil', 'dal', 'sugar', 'tea', 'coffee'],
            'Home Appliances': ['mixer', 'grinder', 'cooker', 'refrigerator', 'washing machine']
        }
        for category, keywords in categories.items():
            if any(kw in title_lower for kw in keywords):
                return category
        return "General Products"

    def scrape_flipkart(self, search_query):
        print("  📱 Loading Flipkart...")
        url = f"https://www.flipkart.com/search?q={quote_plus(search_query)}"
        try:
            self.driver.get(url)
            time.sleep(5)
            
            # Scroll to load content
            for _ in range(3):
                self.driver.execute_script("window.scrollBy(0, 1000);")
                time.sleep(1.5)
            
            products = []
            containers = self.driver.find_elements(By.CSS_SELECTOR, "div[data-id], div._1AtVbE, div.tUxRFH")
            
            for container in containers[:15]:
                try:
                    # Title
                    title = ""
                    for sel in ["a.wjcEIp", "a.WKTcLC", "div.KzDlHZ", "a.IRpwTa"]:
                        try:
                            elem = container.find_element(By.CSS_SELECTOR, sel)
                            title = elem.text.strip() or elem.get_attribute('title') or ""
                            if title and len(title) > 5:
                                break
                        except:
                            continue
                    
                    if not title or not self.is_relevant_product(title, search_query):
                        continue
                    
                    # Price
                    price_text = "N/A"
                    for sel in ["div.Nx9bqj", "div._30jeq3", "div._3I9_wc"]:
                        try:
                            elem = container.find_element(By.CSS_SELECTOR, sel)
                            price_text = elem.text.strip()
                            if price_text and re.search(r'\d{2,}', price_text):
                                break
                        except:
                            continue
                    
                    if price_text == "N/A":
                        continue
                    
                    # URL
                    product_url = url
                    try:
                        link = container.find_element(By.CSS_SELECTOR, "a[href]")
                        href = link.get_attribute('href')
                        if href and ('/p/' in href or '/dp/' in href):
                            product_url = href if href.startswith('http') else f"https://www.flipkart.com{href}"
                    except:
                        pass
                    
                    # Rating
                    rating = "N/A"
                    for sel in ["span.Wphh3N", "div.XQDdHH", "div._3LWZlK"]:
                        try:
                            elem = container.find_element(By.CSS_SELECTOR, sel)
                            rating = elem.text.strip()
                            if rating:
                                break
                        except:
                            continue
                    
                    # Image
                    image_url = "N/A"
                    try:
                        img = container.find_element(By.CSS_SELECTOR, "img")
                        src = img.get_attribute('src') or img.get_attribute('data-src') or ""
                        if src and 'placeholder' not in src.lower():
                            image_url = src
                    except:
                        pass
                    
                    products.append({
                        'title': title,
                        'price': price_text,
                        'price_num': self.extract_price(price_text),
                        'rating': rating,
                        'category': self.auto_categorize_product(title),
                        'source': 'Flipkart',
                        'url': product_url,
                        'image': image_url,
                        'offers': 'N/A'
                    })
                    
                except Exception as e:
                    self.debug_print(f"Error: {str(e)[:50]}")
                    continue
            
            print(f"  ✅ Found {len(products)} products on Flipkart")
            return products
        except Exception as e:
            print(f"  ❌ Error scraping Flipkart: {str(e)}")
            return []

    def scrape_amazon(self, search_query):
        print("  🛒 Loading Amazon...")
        url = f"https://www.amazon.in/s?k={quote_plus(search_query)}"
        try:
            self.driver.get(url)
            time.sleep(6)
            
            for _ in range(3):
                self.driver.execute_script("window.scrollBy(0, 800);")
                time.sleep(1.5)
            
            products = []
            containers = self.driver.find_elements(By.CSS_SELECTOR, "[data-component-type='s-search-result']")
            
            for container in containers[:15]:
                try:
                    # ASIN and URL
                    asin = container.get_attribute('data-asin')
                    if not asin or len(asin) != 10:
                        continue
                    product_url = f"https://www.amazon.in/dp/{asin}"
                    
                    # Title
                    title = ""
                    for sel in ["h2 a span", "h2 span", ".a-size-medium"]:
                        try:
                            elem = container.find_element(By.CSS_SELECTOR, sel)
                            title = elem.text.strip()
                            if title and len(title) > 5:
                                break
                        except:
                            continue
                    
                    if not title or not self.is_relevant_product(title, search_query):
                        continue
                    
                    # Price
                    price_text = "N/A"
                    for sel in [".a-price-whole", ".a-price .a-offscreen"]:
                        try:
                            elem = container.find_element(By.CSS_SELECTOR, sel)
                            price_text = elem.text.strip() or elem.get_attribute("textContent").strip()
                            if price_text and re.search(r'\d', price_text):
                                break
                        except:
                            continue
                    
                    if price_text == "N/A":
                        continue
                    
                    # Rating
                    rating = "N/A"
                    try:
                        elem = container.find_element(By.CSS_SELECTOR, ".a-icon-alt")
                        rating = elem.get_attribute("title") or elem.text
                    except:
                        pass
                    
                    # Image
                    image_url = "N/A"
                    try:
                        img = container.find_element(By.CSS_SELECTOR, "img.s-image")
                        src = img.get_attribute('src') or ""
                        if src and len(src) > 20:
                            image_url = src
                    except:
                        pass
                    
                    products.append({
                        'title': title,
                        'price': price_text,
                        'price_num': self.extract_price(price_text),
                        'rating': rating,
                        'category': self.auto_categorize_product(title),
                        'source': 'Amazon',
                        'url': product_url,
                        'image': image_url,
                        'offers': 'N/A'
                    })
                    
                except Exception as e:
                    self.debug_print(f"Error: {str(e)[:50]}")
                    continue
            
            print(f"  ✅ Found {len(products)} products on Amazon")
            return products
        except Exception as e:
            print(f"  ❌ Error scraping Amazon: {str(e)}")
            return []

    def scrape_vijay_sales(self, search_query):
        print("  🏬 Loading Vijay Sales...")
        # Try the main search endpoint
        url = f"https://www.vijaysales.com/search/{quote_plus(search_query)}"
        try:
            self.driver.get(url)
            time.sleep(10)  # Longer wait for Vijay Sales
            
            # Aggressive scrolling
            for i in range(8):
                self.driver.execute_script("window.scrollBy(0, 600);")
                time.sleep(1.5)
            
            # Scroll back to top
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(2)
            
            products = []
            
            # Multiple container strategies
            container_found = False
            container_selectors = [
                "div.product-grid div.product-layout",
                "div.product-layout",
                "div.product-item",
                "article[class*='product']",
                "li.product-item",
                "div[class*='product-thumb']"
            ]
            
            containers = []
            for selector in container_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if len(elements) >= 2:
                        containers = elements
                        self.debug_print(f"Found {len(elements)} containers with: {selector}")
                        container_found = True
                        break
                except:
                    continue
            
            # Fallback: Find any div with product image and price
            if not container_found:
                try:
                    containers = self.driver.find_elements(By.XPATH, 
                        "//div[.//img and (.//span[contains(@class, 'price')] or .//div[contains(@class, 'price')])]")
                    if len(containers) >= 2:
                        self.debug_print(f"Found {len(containers)} containers using fallback XPath")
                        container_found = True
                except:
                    pass
            
            for idx, container in enumerate(containers[:20]):
                try:
                    # Title and URL - Multiple strategies
                    title = ""
                    product_url = url
                    
                    title_selectors = [
                        "h4.product-name a",
                        "a.product-name",
                        "div.product-name a",
                        ".name a",
                        "h4 a",
                        "h3 a",
                        "a[title]",
                        ".caption h4 a",
                        ".caption a"
                    ]
                    
                    for sel in title_selectors:
                        try:
                            elem = container.find_element(By.CSS_SELECTOR, sel)
                            title = elem.text.strip() or elem.get_attribute('title') or ""
                            if title and len(title) > 5:
                                href = elem.get_attribute('href')
                                if href and href != url:
                                    product_url = href if href.startswith('http') else f"https://www.vijaysales.com{href}"
                                break
                        except:
                            continue
                    
                    if not title or not self.is_relevant_product(title, search_query):
                        continue
                    
                    # Price - Multiple strategies
                    price_text = "N/A"
                    price_selectors = [
                        "span.price-new",
                        "div.price span.price-new",
                        "div.price span",
                        ".price-new",
                        "span.price",
                        "div.price",
                        "span[class*='price']"
                    ]
                    
                    for sel in price_selectors:
                        try:
                            elem = container.find_element(By.CSS_SELECTOR, sel)
                            price_text = elem.text.strip()
                            if price_text and re.search(r'\d{3,}', price_text):
                                break
                        except:
                            continue
                    
                    if price_text == "N/A":
                        continue
                    
                    # Image
                    image_url = "N/A"
                    try:
                        img = container.find_element(By.CSS_SELECTOR, "img")
                        src = img.get_attribute('src') or img.get_attribute('data-src') or ""
                        if src and len(src) > 20:
                            image_url = src if src.startswith('http') else f"https://www.vijaysales.com{src}"
                    except:
                        pass
                    
                    products.append({
                        'title': title,
                        'price': price_text,
                        'price_num': self.extract_price(price_text),
                        'rating': 'N/A',
                        'category': self.auto_categorize_product(title),
                        'source': 'Vijay Sales',
                        'url': product_url,
                        'image': image_url,
                        'offers': 'N/A'
                    })
                    
                except Exception as e:
                    self.debug_print(f"Error in container {idx+1}: {str(e)[:50]}")
                    continue
            
            print(f"  ✅ Found {len(products)} products on Vijay Sales")
            return products
        except Exception as e:
            print(f"  ❌ Error scraping Vijay Sales: {str(e)}")
            return []

    def scrape_jiomart(self, search_query):
        print("  🔵 Loading JioMart...")
        url = f"https://www.jiomart.com/search/{quote(search_query)}"
        try:
            self.driver.get(url)
            time.sleep(8)  # Longer wait for JioMart
            
            # Aggressive scrolling to load products
            for i in range(6):
                self.driver.execute_script("window.scrollBy(0, 800);")
                time.sleep(2)
            
            products = []
            
            # Multiple container strategies
            container_selectors = [
                "div.plp-card-container",
                "div[data-test='product-card']",
                "div.product-card",
                "article.product",
                "div[class*='plp-card']",
                "div[class*='product']"
            ]
            
            containers = []
            for selector in container_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if len(elements) >= 2:
                        containers = elements
                        self.debug_print(f"Found {len(elements)} containers with: {selector}")
                        break
                except:
                    continue
            
            # Fallback: Find divs with images and price-like text
            if not containers:
                try:
                    containers = self.driver.find_elements(By.XPATH,
                        "//div[.//img and (.//span[contains(text(), '₹')] or .//span[contains(@class, 'price')])]")
                    self.debug_print(f"Found {len(containers)} containers using fallback")
                except:
                    pass
            
            for idx, container in enumerate(containers[:20]):
                try:
                    # Title - Multiple strategies
                    title = ""
                    title_selectors = [
                        "div.plp-card-details-name",
                        "div.jm-body-xs",
                        "h3",
                        "h2",
                        "a[title]",
                        "div[class*='name']",
                        "div[class*='title']"
                    ]
                    
                    for sel in title_selectors:
                        try:
                            elem = container.find_element(By.CSS_SELECTOR, sel)
                            title = elem.text.strip() or elem.get_attribute('title') or ""
                            if title and len(title) > 5:
                                break
                        except:
                            continue
                    
                    if not title or not self.is_relevant_product(title, search_query):
                        continue
                    
                    # Price - Multiple strategies
                    price_text = "N/A"
                    price_selectors = [
                        "span.jm-heading-xxs",
                        "span.jm-heading-xs",
                        "span[class*='price']",
                        "div[class*='price']",
                        "span[class*='amount']"
                    ]
                    
                    for sel in price_selectors:
                        try:
                            elem = container.find_element(By.CSS_SELECTOR, sel)
                            price_text = elem.text.strip()
                            if price_text and re.search(r'\d', price_text):
                                break
                        except:
                            continue
                    
                    if price_text == "N/A":
                        continue
                    
                    # URL - Multiple strategies
                    product_url = url
                    
                    # Strategy 1: Find parent anchor
                    try:
                        parent_link = container.find_element(By.XPATH, "./ancestor::a[1]")
                        href = parent_link.get_attribute("href")
                        if href and '/p/' in href:
                            product_url = href if href.startswith('http') else f"https://www.jiomart.com{href}"
                    except:
                        pass
                    
                    # Strategy 2: Find any anchor inside
                    if product_url == url:
                        try:
                            links = container.find_elements(By.TAG_NAME, "a")
                            for link in links:
                                href = link.get_attribute("href")
                                if href and '/p/' in href:
                                    product_url = href if href.startswith('http') else f"https://www.jiomart.com{href}"
                                    break
                        except:
                            pass
                    
                    # Image
                    image_url = "N/A"
                    try:
                        img = container.find_element(By.CSS_SELECTOR, "img")
                        src = img.get_attribute("src") or img.get_attribute("data-src") or ""
                        if src and len(src) > 20:
                            image_url = src
                    except:
                        pass
                    
                    products.append({
                        'title': title,
                        'price': price_text,
                        'price_num': self.extract_price(price_text),
                        'rating': 'N/A',
                        'category': self.auto_categorize_product(title),
                        'source': 'JioMart',
                        'url': product_url,
                        'image': image_url,
                        'offers': 'N/A'
                    })
                    
                except Exception as e:
                    self.debug_print(f"Error in container {idx+1}: {str(e)[:50]}")
                    continue
            
            print(f"  ✅ Found {len(products)} products on JioMart")
            return products
        except Exception as e:
            print(f"  ❌ Error scraping JioMart: {str(e)}")
            return []

    def scrape_croma(self, search_query):
        print("  🟠 Loading Croma...")
        url = f"https://www.croma.com/searchB?q={quote_plus(search_query)}%3Arelevance&text={quote_plus(search_query)}"
        try:
            self.driver.get(url)
            time.sleep(3)
            
            # CRITICAL: Handle location permission popup
            self.handle_location_popup(timeout=5)
            
            # Additional wait after handling popup
            time.sleep(3)
            
            # Scroll to load products
            for i in range(5):
                self.driver.execute_script("window.scrollBy(0, 1000);")
                time.sleep(2)
            
            products = []
            
            # Multiple container strategies
            container_selectors = [
                "li.product-item",
                "div.product-item",
                "article.product",
                "div[class*='product-item']",
                "li[class*='product']"
            ]
            
            containers = []
            for selector in container_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if len(elements) >= 2:
                        containers = elements
                        self.debug_print(f"Found {len(elements)} containers with: {selector}")
                        break
                except:
                    continue
            
            for idx, container in enumerate(containers[:20]):
                try:
                    # Title and URL
                    title = ""
                    product_url = url
                    
                    title_selectors = [
                        "h3.product-title a",
                        "a.product-title",
                        "h3 a",
                        ".product-title",
                        "a[href*='/p/']"
                    ]
                    
                    for sel in title_selectors:
                        try:
                            elem = container.find_element(By.CSS_SELECTOR, sel)
                            title = elem.text.strip() or elem.get_attribute('title') or ""
                            if title and len(title) > 5:
                                if elem.tag_name == 'a':
                                    href = elem.get_attribute('href')
                                    if href and href != url:
                                        product_url = href if href.startswith('http') else f"https://www.croma.com{href}"
                                break
                        except:
                            continue
                    
                    if not title or not self.is_relevant_product(title, search_query):
                        continue
                    
                    # Price
                    price_text = "N/A"
                    price_selectors = [
                        "span.amount",
                        "span.price",
                        "div.price",
                        "span.plp-srp-new-amount",
                        "span.new-price",
                        "span[class*='amount']",
                        "span[class*='price']"
                    ]
                    
                    for sel in price_selectors:
                        try:
                            elem = container.find_element(By.CSS_SELECTOR, sel)
                            price_text = elem.text.strip()
                            if price_text and re.search(r'\d{3,}', price_text):
                                break
                        except:
                            continue
                    
                    if price_text == "N/A":
                        continue
                    
                    # Rating
                    rating = "N/A"
                    try:
                        elem = container.find_element(By.CSS_SELECTOR, ".rating, [class*='rating'], [class*='star']")
                        rating = elem.get_attribute('title') or elem.text.strip()
                    except:
                        pass
                    
                    # Image
                    image_url = "N/A"
                    try:
                        img = container.find_element(By.CSS_SELECTOR, "img")
                        src = img.get_attribute('src') or img.get_attribute('data-src') or ""
                        if src and len(src) > 20:
                            image_url = src if src.startswith('http') else f"https://www.croma.com{src}"
                    except:
                        pass
                    
                    products.append({
                        'title': title,
                        'price': price_text,
                        'price_num': self.extract_price(price_text),
                        'rating': rating,
                        'category': self.auto_categorize_product(title),
                        'source': 'Croma',
                        'url': product_url,
                        'image': image_url,
                        'offers': 'N/A'
                    })
                    
                except Exception as e:
                    self.debug_print(f"Error in container {idx+1}: {str(e)[:50]}")
                    continue
            
            print(f"  ✅ Found {len(products)} products on Croma")
            return products
        except Exception as e:
            print(f"  ❌ Error scraping Croma: {str(e)}")
            return []

    def compare_prices(self, search_query, websites=None):
        print(f"\n🔍 UNIVERSAL PRICE COMPARISON - 5 WEBSITES")
        print(f"Searching for: '{search_query}'")
        print("=" * 70)
        
        all_products = []
        self.create_driver()
        
        if websites is None:
            websites = ['flipkart', 'amazon', 'vijay_sales', 'jiomart', 'croma']
        
        try:
            if 'flipkart' in websites:
                all_products += self.scrape_flipkart(search_query)
            
            if 'amazon' in websites:
                all_products += self.scrape_amazon(search_query)
            
            if 'vijay_sales' in websites:
                all_products += self.scrape_vijay_sales(search_query)
            
            if 'jiomart' in websites:
                all_products += self.scrape_jiomart(search_query)
            
            if 'croma' in websites:
                all_products += self.scrape_croma(search_query)
                
        except KeyboardInterrupt:
            print("\n⚠️ Scraping interrupted by user")
        finally:
            if self.driver:
                try:
                    print("\n👋 Closing browser...")
                    self.driver.quit()
                except:
                    pass
        
        valid_products = [p for p in all_products if p['price_num'] and p['price_num'] >= 10]
        valid_products.sort(key=lambda x: x['price_num'])
        return valid_products
