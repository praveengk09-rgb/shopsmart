import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import pandas as pd
import time
import random
import re
from urllib.parse import quote, quote_plus

class UniversalEcommerceScraper:
    def __init__(self, debug_mode=False):
        self.driver = None
        self.debug_mode = debug_mode
    
    def debug_print(self, message):
        """Print debug messages if debug mode is enabled"""
        if self.debug_mode:
            print(f"  [DEBUG] {message}")

    def create_driver(self):
        options = uc.ChromeOptions()

        # Tell Chrome where it's installed on Render
        options.binary_location = "/usr/bin/chromium"

        # These make Chrome work without a screen
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--single-process")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")

        prefs = {
            "profile.default_content_setting_values.geolocation": 1,
            "profile.default_content_settings.popups": 0,
            "profile.default_content_setting_values.notifications": 2
        }
        options.add_experimental_option("prefs", prefs)

        # Try to create driver with Render's Chrome
        try:
            self.driver = uc.Chrome(
                options=options,
                driver_executable_path="/usr/bin/chromedriver"
            )
        except:
            # Fallback if path is different
            self.driver = uc.Chrome(options=options)

        # Set location to Mumbai
        try:
            self.driver.execute_cdp_cmd("Emulation.setGeolocationOverride", {
                "latitude": 19.0760,
                "longitude": 72.8777,
                "accuracy": 100
            })
        except:
            pass

        return self.driver
    def extract_price(self, price_text):
        """Extract numeric price from price text, handling various formats"""
        if not price_text or price_text == "N/A":
            return None
        
        # Remove currency symbols and extra spaces
        cleaned = price_text.replace('₹', '').replace('Rs', '').replace(',', '').strip()
        
        # Try to find a number pattern
        price_match = re.search(r'(\d+)(?:\.(\d+))?', cleaned)
        
        if price_match:
            integer_part = int(price_match.group(1))
            decimal_part = price_match.group(2)
            
            if decimal_part and len(decimal_part) == 2:
                return integer_part
            else:
                return integer_part
        
        return None

    def extract_offers(self, container):
        """Extract all offer information from product container"""
        offers = []
        
        # Common offer text patterns
        offer_keywords = ['off', 'discount', 'bank offer', 'exchange', 'cashback', 'save', 
                         'bonus', 'deal', 'extra', 'free', 'coupon', 'promo']
        
        try:
            # Get all text from container
            all_text = container.text.lower()
            lines = [line.strip() for line in all_text.split('\n') if line.strip()]
            
            for line in lines:
                # Check if line contains offer keywords
                if any(keyword in line for keyword in offer_keywords):
                    # Skip if it's just a price or percentage alone
                    if not re.match(r'^[\d,]+$', line) and not re.match(r'^\d+%$', line):
                        if len(line) > 3 and len(line) < 200:  # Reasonable offer text length
                            offers.append(line.title())
        except:
            pass
        
        return offers[:5]  # Return max 5 offers

    def is_relevant_product(self, title, search_query):
        """Enhanced product relevance check to filter accessories and other models"""
        if not title or len(title) < 3:
            return False
        
        title_lower = title.lower()
        query_lower = search_query.lower()
        
        # Define main device keywords and accessory keywords
        main_device_keywords = ['iphone', 'phone', 'mobile', 'samsung', 'pixel', 'oneplus', 'laptop', 'macbook']
        accessory_keywords = [
            'cover', 'case', 'protector', 'screen guard', 'tempered glass', 'pouch', 'skin',
            'charger', 'cable', 'adapter', 'earphone', 'headphone', 'power bank',
            'stand', 'holder', 'mount', 'strap', 'band', 'connector', 'splitter',
            'jack', 'aux', 'usb', 'type c', 'lightning', 'wire', 'cord', 'bumper',
            'magsafe battery', 'kickstand', 'rugged case', 'techwoven', 'clear case',
            'back cover', 'flip cover', 'vinyl', 'sticker', 'decal'
        ]
        
        # If searching for a main device (like iPhone, phone, etc.)
        if any(dev in query_lower for dev in main_device_keywords):
            # Filter out accessories
            if any(acc in title_lower for acc in accessory_keywords):
                return False
        
        # Enhanced filtering for iPhone models
        if 'iphone' in query_lower:
            # Extract iPhone model from search query (e.g., "15" from "iphone 15")
            query_model_match = re.search(r'iphone\s+(\d+)', query_lower)
            if query_model_match:
                query_model = query_model_match.group(1)
                
                # Check if title contains iPhone and extract model
                title_model_match = re.search(r'iphone\s+(\d+)', title_lower)
                if title_model_match:
                    title_model = title_model_match.group(1)
                    
                    # Only return True if models match (e.g., both are iPhone 15)
                    if title_model != query_model:
                        self.debug_print(f"Model mismatch: query={query_model}, title={title_model}")
                        return False
                else:
                    # If no model found in title but query has model, likely not relevant
                    return False
        
        # Check for stop words
        stop_words = {'for', 'the', 'a', 'an', 'in', 'on', 'at', 'to', 'and', 'or', 'with', 'only'}
        query_words = [word for word in query_lower.split() if len(word) > 2 and word not in stop_words]
        
        if not query_words:
            return False
        
        # Count matching words
        match_count = sum(1 for word in query_words if word in title_lower)
        return match_count >= len(query_words) / 2

    def auto_categorize_product(self, title):
        title_lower = title.lower()
        if any(word in title_lower for word in ['phone', 'mobile', 'iphone', 'samsung', 'oneplus', 'pixel']):
            return "Mobile Phones"
        elif any(word in title_lower for word in ['laptop', 'notebook', 'macbook', 'chromebook']):
            return "Laptops"
        elif any(word in title_lower for word in ['tv', 'television', 'smart tv', 'led tv']):
            return "Television"
        elif any(word in title_lower for word in ['headphone', 'earphone', 'earbud', 'airpods']):
            return "Audio Accessories"
        elif any(word in title_lower for word in ['charger', 'cable', 'adapter', 'power bank']):
            return "Mobile Accessories"
        elif any(word in title_lower for word in ['watch', 'smartwatch', 'fitness band']):
            return "Wearables"
        elif any(word in title_lower for word in ['camera', 'dslr', 'gopro']):
            return "Cameras"
        elif any(word in title_lower for word in ['shirt', 't-shirt', 'tshirt', 'polo', 'top', 'blouse', 'hoodie', 'sweatshirt']):
            return "Apparel"
        elif any(word in title_lower for word in ['jeans', 'trouser', 'pant', 'cargo', 'chino']):
            return "Bottoms"
        elif any(word in title_lower for word in ['dress', 'gown', 'frock', 'kurti', 'saree', 'lehenga']):
            return "Ethnic & Dresses"
        elif any(word in title_lower for word in ['shoe', 'sneaker', 'boot', 'sandal', 'slipper', 'footwear']):
            return "Footwear"
        elif any(word in title_lower for word in ['jacket', 'coat', 'sweater']):
            return "Outerwear"
        elif any(word in title_lower for word in ['belt', 'wallet', 'bag', 'purse', 'handbag']):
            return "Fashion Accessories"
        elif any(word in title_lower for word in ['rice', 'wheat', 'flour', 'atta', 'dal', 'pulses']):
            return "Staples"
        elif any(word in title_lower for word in ['oil', 'ghee', 'butter', 'cooking oil']):
            return "Cooking Oils"
        elif any(word in title_lower for word in ['sugar', 'salt', 'spice', 'masala', 'tea', 'coffee']):
            return "Beverages & Condiments"
        elif any(word in title_lower for word in ['biscuit', 'cookie', 'chips', 'namkeen', 'snack']):
            return "Snacks & Biscuits"
        elif any(word in title_lower for word in ['milk', 'curd', 'yogurt', 'cheese', 'paneer']):
            return "Dairy Products"
        elif any(word in title_lower for word in ['fruit', 'vegetable', 'apple', 'banana', 'tomato', 'potato']):
            return "Fresh Produce"
        elif any(word in title_lower for word in ['mixer', 'grinder', 'blender', 'juicer', 'cooker']):
            return "Kitchen Appliances"
        elif any(word in title_lower for word in ['bed', 'mattress', 'pillow', 'bedsheet', 'blanket']):
            return "Bedroom"
        elif any(word in title_lower for word in ['sofa', 'chair', 'table', 'furniture']):
            return "Furniture"
        elif any(word in title_lower for word in ['curtain', 'carpet', 'rug', 'cushion']):
            return "Home Decor"
        elif any(word in title_lower for word in ['shampoo', 'conditioner', 'hair oil', 'soap', 'facewash']):
            return "Personal Care"
        elif any(word in title_lower for word in ['perfume', 'deodorant', 'fragrance', 'cologne']):
            return "Fragrances"
        elif any(word in title_lower for word in ['makeup', 'lipstick', 'kajal', 'mascara', 'foundation']):
            return "Beauty & Cosmetics"
        elif any(word in title_lower for word in ['book', 'novel', 'textbook', 'guide']):
            return "Books"
        elif any(word in title_lower for word in ['gym', 'dumbbell', 'yoga', 'fitness', 'treadmill', 'cycle']):
            return "Sports & Fitness"
        else:
            return "General Products"

    def scrape_flipkart(self, search_query):
        print("  📱 Loading Flipkart...")
        search_url = f"https://www.flipkart.com/search?q={quote_plus(search_query)}"
        try:
            self.driver.get(search_url)
            time.sleep(random.uniform(4, 6))
            for _ in range(4):
                self.driver.execute_script("window.scrollBy(0, 1000);")
                time.sleep(2)
            container_selectors = [
                "div[data-id]", "div._1AtVbE", "div._13oc-S", "div.tUxRFH",
                "div._2kHMtA", "div.cPHDOP", "div.slAVV4", "div._2-gKeQ"
            ]
            containers = []
            for selector in container_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if len(elements) >= 3:
                        containers = elements
                        break
                except:
                    continue
            products = []
            for container in containers[:20]:
                try:
                    title = ""
                    for selector in ["a.wjcEIp", "a.WKTcLC", "div.KzDlHZ", "a.IRpwTa",
                                     "div._2WkVRV", "a.s1Q9rs", "a._2rpwqI", "div._4rR01T",
                                     "a.CGtC98", "a[title]", "div[title]"]:
                        try:
                            title_elem = container.find_element(By.CSS_SELECTOR, selector)
                            title = title_elem.text.strip() or title_elem.get_attribute('title') or ""
                            if title and len(title) > 3:
                                break
                        except:
                            continue
                    if not title:
                        continue
                    if not self.is_relevant_product(title, search_query):
                        continue
                    product_url = search_url
                    try:
                        link_elem = container.find_element(By.CSS_SELECTOR, "a[href]")
                        href = link_elem.get_attribute('href')
                        if href and ('/p/' in href or '/dp/' in href or 'pid=' in href):
                            product_url = href if href.startswith('http') else f"https://www.flipkart.com{href}"
                    except: pass
                    price_text = "N/A"
                    for selector in ["div.Nx9bqj", "div._30jeq3", "div._3I9_wc", "div._25b18c",
                                     "div.hl05eU", "div._16Jk6d", "div._2rQ-NK"]:
                        try:
                            price_elem = container.find_element(By.CSS_SELECTOR, selector)
                            price_text = price_elem.text.strip()
                            if price_text and ('₹' in price_text or re.search(r'\d{2,}', price_text)):
                                break
                        except: continue
                    if price_text == "N/A":
                        continue
                    rating = "N/A"
                    for selector in ["span.Wphh3N", "div.XQDdHH", "div._3LWZlK", "span._2_R_DZ"]:
                        try:
                            rating_elem = container.find_element(By.CSS_SELECTOR, selector)
                            rating = rating_elem.text.strip()
                            if rating:
                                break
                        except: continue
                    
                    offers = self.extract_offers(container)
                    category = self.auto_categorize_product(title)
                    image_url = "N/A"
                    try:
                        img_elem = container.find_element(By.CSS_SELECTOR, "img")
                        src = img_elem.get_attribute('src') or img_elem.get_attribute('data-src') or ""
                        # Only use real product images, not placeholders
                        if src and 'placeholder' not in src.lower() and len(src) > 20:
                            image_url = src
                    except: pass
                    products.append({
                        'title': title, 'price': price_text, 'price_num': self.extract_price(price_text),
                        'rating': rating, 'category': category, 'source': 'Flipkart',
                        'url': product_url, 'image': image_url, 'offers': ' | '.join(offers) if offers else 'N/A'
                    })
                except Exception:
                    continue
            print(f"  ✅ Found {len(products)} relevant products on Flipkart")
            return products
        except Exception as e:
            print(f"  ❌ Error scraping Flipkart: {str(e)}")
            return []

    def scrape_amazon(self, search_query):
        print("  🛒 Loading Amazon...")
        search_url = f"https://www.amazon.in/s?k={quote_plus(search_query)}&ref=nb_sb_noss"
        try:
            self.driver.get(search_url)
            time.sleep(random.uniform(5, 7))  # Longer wait for Amazon
            
            # Scroll to load more content
            for _ in range(3):
                self.driver.execute_script("window.scrollBy(0, 800);")
                time.sleep(1.5)
            
            product_containers = self.driver.find_elements(By.CSS_SELECTOR, "[data-component-type='s-search-result']")
            products = []
            
            for idx, container in enumerate(product_containers[:15]):
                try:
                    # FIRST: Extract ASIN - this is the most important step
                    asin = None
                    product_url = None
                    
                    # Method 1: Get data-asin attribute from container (MOST RELIABLE)
                    try:
                        asin = container.get_attribute('data-asin')
                        if asin and len(asin) == 10 and asin.isalnum():
                            product_url = f"https://www.amazon.in/dp/{asin}"
                            self.debug_print(f"✓ ASIN from data-asin: {asin}")
                    except Exception as e:
                        self.debug_print(f"Method 1 failed: {str(e)[:40]}")
                    
                    # Method 2: Extract from any link href in container
                    if not product_url:
                        try:
                            all_links = container.find_elements(By.TAG_NAME, "a")
                            for link in all_links:
                                href = link.get_attribute('href')
                                if href and '/dp/' in href:
                                    asin_match = re.search(r'/dp/([A-Z0-9]{10})', href)
                                    if asin_match:
                                        asin = asin_match.group(1)
                                        product_url = f"https://www.amazon.in/dp/{asin}"
                                        self.debug_print(f"✓ ASIN from link href: {asin}")
                                        break
                        except Exception as e:
                            self.debug_print(f"Method 2 failed: {str(e)[:40]}")
                    
                    # Method 3: Look specifically for h2 a tag
                    if not product_url:
                        try:
                            h2_link = container.find_element(By.CSS_SELECTOR, "h2 a, .a-link-normal")
                            href = h2_link.get_attribute('href')
                            if href:
                                asin_match = re.search(r'/dp/([A-Z0-9]{10})', href)
                                if asin_match:
                                    asin = asin_match.group(1)
                                    product_url = f"https://www.amazon.in/dp/{asin}"
                                    self.debug_print(f"✓ ASIN from h2 link: {asin}")
                        except Exception as e:
                            self.debug_print(f"Method 3 failed: {str(e)[:40]}")
                    
                    # If still no URL found, skip this product
                    if not product_url:
                        self.debug_print(f"⚠ Could not extract product URL for container {idx+1}, skipping")
                        continue
                    
                    # THEN: Extract title
                    title = ""
                    for selector in ["h2 a span", "h2 span", ".a-size-mini span",
                                     ".a-size-base-plus", ".a-size-base", "span.a-text-normal",
                                     "h2.a-size-base-plus span", ".a-size-medium"]:
                        try:
                            title_elem = container.find_element(By.CSS_SELECTOR, selector)
                            title = title_elem.text.strip()
                            if title and len(title) > 5:
                                break
                        except:
                            continue
                    
                    if not title:
                        self.debug_print(f"No title found for container {idx+1}")
                        continue
                    
                    if not self.is_relevant_product(title, search_query):
                        continue
                    
                    # Extract price
                    price_text = "N/A"
                    for selector in [".a-price-whole", ".a-price .a-offscreen", ".a-price"]:
                        try:
                            price_elem = container.find_element(By.CSS_SELECTOR, selector)
                            price_text = price_elem.text.strip() or price_elem.get_attribute("textContent").strip()
                            if price_text and ('₹' in price_text or re.search(r'\d', price_text)):
                                break
                        except:
                            continue
                    
                    if price_text == "N/A":
                        continue
                    
                    # Extract rating
                    rating = "N/A"
                    for selector in [".a-icon-alt", "span[aria-label*='out of']"]:
                        try:
                            rating_elem = container.find_element(By.CSS_SELECTOR, selector)
                            rating_text = rating_elem.get_attribute("title") or rating_elem.text
                            if rating_text and any(char.isdigit() for char in rating_text):
                                rating = rating_text
                                break
                        except: pass
                    
                    offers = self.extract_offers(container)
                    category = self.auto_categorize_product(title)
                    
                    # Extract product image
                    image_url = "N/A"
                    try:
                        img_elem = container.find_element(By.CSS_SELECTOR, "img.s-image")
                        src = img_elem.get_attribute('src') or ""
                        if src and 'placeholder' not in src.lower() and len(src) > 20:
                            image_url = src
                    except: pass
                    
                    # Final validation: make sure we have a proper product URL
                    if product_url == search_url or not asin:
                        self.debug_print(f"⚠ Skipping product - invalid URL: {title[:50]}")
                        continue
                    
                    self.debug_print(f"✅ Amazon product added: {title[:40]} | URL: {product_url}")
                    
                    products.append({
                        'title': title, 'price': price_text, 'price_num': self.extract_price(price_text),
                        'rating': rating, 'category': category, 'source': 'Amazon',
                        'url': product_url, 'image': image_url, 'offers': ' | '.join(offers) if offers else 'N/A'
                    })
                    
                except Exception as e:
                    self.debug_print(f"Error processing Amazon container {idx+1}: {str(e)[:100]}")
                    continue
            
            print(f"  ✅ Found {len(products)} relevant products on Amazon")
            return products
        except Exception as e:
            print(f"  ❌ Error scraping Amazon: {str(e)}")
            return []

    def scrape_vijay_sales(self, search_query):
        print("  🏬 Loading Vijay Sales...")
        search_url = f"https://www.vijaysales.com/search-listing?q={quote_plus(search_query)}"
        try:
            self.driver.get(search_url)
            time.sleep(random.uniform(8, 10))  # Longer wait for Vijay Sales
            
            self.debug_print(f"Current URL: {self.driver.current_url}")
            
            # Better scrolling for lazy-loaded content
            for i in range(8):
                self.driver.execute_script("window.scrollBy(0, 800);")
                time.sleep(2)
            
            # Scroll back to top to ensure all content is loaded
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(2)
            
            products = []
            
            if self.debug_mode:
                with open('vijaysales_debug.html', 'w', encoding='utf-8') as f:
                    f.write(self.driver.page_source)
                self.debug_print("Page source saved to vijaysales_debug.html")
            
            # Try multiple container selector strategies
            container_selectors = [
                "div.product-layout.product-grid",
                "div.product-layout",
                "div.product-thumb",
                "article.product-item",
                "div.product-item",
                "li.product-item",
                ".product-grid > div",
                "div[class*='col-'][class*='product']"
            ]
            
            containers = []
            for selector in container_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if len(elements) >= 2:
                        containers = elements
                        self.debug_print(f"Found {len(elements)} containers using: {selector}")
                        print(f"  📦 Found {len(elements)} product containers")
                        break
                except Exception as e:
                    self.debug_print(f"Selector {selector} failed: {str(e)[:50]}")
                    continue
            
            # Fallback: Try to find containers with images and prices
            if not containers or len(containers) < 2:
                self.debug_print("Trying alternative: find divs with product images...")
                try:
                    # Look for divs containing product images
                    all_divs = self.driver.find_elements(By.XPATH, "//div[.//img[contains(@class, 'img-responsive')] and .//span[contains(@class, 'price')]]")
                    if all_divs and len(all_divs) >= 2:
                        containers = all_divs
                        self.debug_print(f"Found {len(all_divs)} containers using image+price method")
                except Exception as e:
                    self.debug_print(f"Alternative method failed: {str(e)[:50]}")
            
            for idx, container in enumerate(containers[:25]):
                try:
                    self.debug_print(f"\n--- Processing container {idx+1} ---")
                    
                    # Try to get container HTML for debugging
                    if self.debug_mode and idx < 3:
                        try:
                            container_html = container.get_attribute('outerHTML')[:500]
                            self.debug_print(f"Container HTML preview: {container_html}")
                        except:
                            pass
                    
                    title = ""
                    product_url = search_url
                    
                    # Expanded title selectors
                    title_selectors = [
                        "h4.product-name a",
                        "div.product-name a",
                        "a.product-name",
                        ".caption h4 a",
                        ".caption h4",
                        "h4 a",
                        "h3 a",
                        "div.name a",
                        "div.name",
                        "a[href*='/p/']",
                        "a[href*='product']",
                        "a[title]",
                        ".product-title a",
                        ".product-title"
                    ]
                    
                    for selector in title_selectors:
                        try:
                            elem = container.find_element(By.CSS_SELECTOR, selector)
                            title_text = elem.text.strip() or elem.get_attribute('title') or elem.get_attribute('alt') or ""
                            
                            if title_text and len(title_text) > 3:
                                title = title_text
                                
                                # Try to get URL from the element or its parent
                                if elem.tag_name == 'a':
                                    href = elem.get_attribute('href')
                                    if href and href != search_url:
                                        product_url = href if href.startswith('http') else f"https://www.vijaysales.com{href}"
                                else:
                                    # If not an anchor, look for parent anchor
                                    try:
                                        parent_link = elem.find_element(By.XPATH, "./ancestor::a[1]")
                                        href = parent_link.get_attribute('href')
                                        if href and href != search_url:
                                            product_url = href if href.startswith('http') else f"https://www.vijaysales.com{href}"
                                    except:
                                        pass
                                
                                self.debug_print(f"Title found with {selector}: {title[:50]}")
                                self.debug_print(f"URL: {product_url[:80]}")
                                break
                        except Exception as e:
                            self.debug_print(f"Selector {selector} failed: {str(e)[:30]}")
                            continue
                    
                    if not title:
                        self.debug_print("No title found, skipping container")
                        continue
                    
                    if not self.is_relevant_product(title, search_query):
                        self.debug_print(f"Product not relevant: {title[:50]}")
                        continue
                    
                    # Extract price with more selectors
                    price_text = "N/A"
                    price_selectors = [
                        "span.price-new",
                        "div.price span.price-new",
                        "div.price",
                        ".price-new",
                        "span.price",
                        ".product-price",
                        "p.price",
                        ".amount",
                        "span[class*='price']",
                        "div[class*='price']"
                    ]
                    
                    for selector in price_selectors:
                        try:
                            price_elem = container.find_element(By.CSS_SELECTOR, selector)
                            price_text = price_elem.text.strip()
                            if price_text and ('₹' in price_text or 'Rs' in price_text or re.search(r'\d{3,}', price_text)):
                                self.debug_print(f"Price found with {selector}: {price_text}")
                                break
                        except:
                            continue
                    
                    if price_text == "N/A":
                        self.debug_print(f"No price found for: {title[:50]}")
                        continue
                    
                    # Extract rating
                    rating = "N/A"
                    try:
                        rating_elem = container.find_element(By.CSS_SELECTOR, ".rating, .rating-result, [class*='rating'], [class*='star']")
                        rating = rating_elem.get_attribute('title') or rating_elem.text.strip()
                    except:
                        pass
                    
                    offers = self.extract_offers(container)
                    category = self.auto_categorize_product(title)
                    
                    # Extract image
                    image_url = "N/A"
                    try:
                        img_elem = container.find_element(By.CSS_SELECTOR, "img")
                        src = img_elem.get_attribute('src') or img_elem.get_attribute('data-src') or img_elem.get_attribute('data-lazy') or ""
                        if src and 'placeholder' not in src.lower() and len(src) > 20:
                            if src.startswith('/'):
                                image_url = f"https://www.vijaysales.com{src}"
                            else:
                                image_url = src
                    except:
                        pass
                    
                    products.append({
                        'title': title, 'price': price_text, 'price_num': self.extract_price(price_text),
                        'rating': rating, 'category': category, 'source': 'Vijay Sales',
                        'url': product_url, 'image': image_url, 'offers': ' | '.join(offers) if offers else 'N/A'
                    })
                    
                    self.debug_print(f"✅ Added: {title[:40]} - {price_text}")
                    
                except Exception as e:
                    self.debug_print(f"Error in container {idx+1}: {str(e)[:100]}")
                    continue
            
            print(f"  ✅ Found {len(products)} relevant products on Vijay Sales")
            return products
        except Exception as e:
            print(f"  ❌ Error scraping Vijay Sales: {str(e)}")
            return []
    
    def scrape_jiomart(self, search_query):
        print("  🔵 Loading JioMart...")
        search_url = f"https://www.jiomart.com/search/{quote(search_query)}"
        try:
            self.driver.get(search_url)
            time.sleep(random.uniform(5, 7))
            for _ in range(4):
                self.driver.execute_script("window.scrollBy(0, 1000);")
                time.sleep(2)
            
            products = []
            
            if self.debug_mode:
                with open('jiomart_debug.html', 'w', encoding='utf-8') as f:
                    f.write(self.driver.page_source)
                self.debug_print("Page source saved to jiomart_debug.html")
            
            container_selectors = [
                "div.plp-card-container",
                "div[data-test='product-card']",
                "div.product-card",
                "article.product"
            ]
            
            containers = []
            for selector in container_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if len(elements) >= 2:
                        containers = elements
                        self.debug_print(f"Found {len(elements)} containers using: {selector}")
                        break
                except:
                    continue
            
            for idx, container in enumerate(containers[:20]):
                try:
                    self.debug_print(f"\n--- Processing JioMart container {idx+1} ---")
                    
                    title = ""
                    title_selectors = [
                        "div.plp-card-details-name",
                        "div.jm-body-xs",
                        "h3",
                        "a[title]"
                    ]
                    
                    for selector in title_selectors:
                        try:
                            title_elem = container.find_element(By.CSS_SELECTOR, selector)
                            title = title_elem.text.strip() or title_elem.get_attribute('title') or ""
                            if title and len(title) > 3:
                                self.debug_print(f"Title: {title[:50]}")
                                break
                        except:
                            continue
                    
                    if not title or not self.is_relevant_product(title, search_query):
                        self.debug_print(f"Skipping: {title[:50] if title else 'No title'}")
                        continue
                    
                    price_text = "N/A"
                    price_selectors = [
                        "span.jm-heading-xxs",
                        "span.jm-heading-xs", 
                        "span[class*='price']",
                        "div[class*='price']"
                    ]
                    
                    for selector in price_selectors:
                        try:
                            price_elem = container.find_element(By.CSS_SELECTOR, selector)
                            price_text = price_elem.text.strip()
                            if price_text and ('₹' in price_text or re.search(r'\d', price_text)):
                                self.debug_print(f"Price: {price_text}")
                                break
                        except:
                            continue
                    
                    if price_text == "N/A":
                        self.debug_print("No price found")
                        continue
                    
                    product_url = search_url
                    url_found = False
                    
                    try:
                        parent_link = container.find_element(By.XPATH, "./ancestor::a[1]")
                        href = parent_link.get_attribute("href")
                        if href and href != search_url and ('/p/' in href or 'product' in href.lower()):
                            if href.startswith('http'):
                                product_url = href
                            elif href.startswith('/'):
                                product_url = f"https://www.jiomart.com{href}"
                            self.debug_print(f"Product URL from parent anchor: {product_url}")
                            url_found = True
                    except:
                        pass
                    
                    if not url_found:
                        try:
                            all_links = container.find_elements(By.TAG_NAME, "a")
                            for link in all_links:
                                href = link.get_attribute("href")
                                if href and href != search_url and ('/p/' in href or 'product' in href.lower()):
                                    if href.startswith('http'):
                                        product_url = href
                                    elif href.startswith('/'):
                                        product_url = f"https://www.jiomart.com{href}"
                                    self.debug_print(f"Product URL from container link: {product_url}")
                                    url_found = True
                                    break
                        except Exception as e:
                            self.debug_print(f"Link extraction failed: {str(e)}")
                    
                    if not url_found:
                        try:
                            data_url = container.get_attribute("data-url") or container.get_attribute("data-href")
                            if data_url:
                                if data_url.startswith('http'):
                                    product_url = data_url
                                elif data_url.startswith('/'):
                                    product_url = f"https://www.jiomart.com{data_url}"
                                self.debug_print(f"Product URL from data attribute: {product_url}")
                                url_found = True
                        except:
                            pass
                    
                    if not url_found:
                        self.debug_print(f"Could not find specific product URL, using search URL")
                    
                    image_url = "N/A"
                    try:
                        img_elem = container.find_element(By.CSS_SELECTOR, "img")
                        src = img_elem.get_attribute("src") or img_elem.get_attribute("data-src") or ""
                        if src and 'placeholder' not in src.lower() and len(src) > 20:
                            image_url = src
                    except:
                        pass
                    
                    offers = self.extract_offers(container)
                    
                    products.append({
                        'title': title, 'price': price_text, 'price_num': self.extract_price(price_text),
                        'rating': "N/A", 'category': self.auto_categorize_product(title),
                        'source': 'JioMart', 'url': product_url, 'image': image_url,
                        'offers': ' | '.join(offers) if offers else 'N/A'
                    })
                    
                    self.debug_print(f"✅ Added product")
                    
                except Exception as e:
                    self.debug_print(f"Error in container {idx+1}: {str(e)}")
                    continue
            
            print(f"  ✅ Found {len(products)} relevant products on JioMart")
            return products
        except Exception as e:
            print(f"  ❌ Error scraping JioMart: {str(e)}")
            return []

    def scrape_croma(self, search_query):
        print("  🟠 Loading Croma...")
        search_url = f"https://www.croma.com/searchB?q={quote_plus(search_query)}%3Arelevance&text={quote_plus(search_query)}"
        try:
            self.driver.get(search_url)
            time.sleep(random.uniform(3, 4))
            
            # Handle location permission popup
            try:
                wait = WebDriverWait(self.driver, 5)
                allow_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Allow this time') or contains(text(), 'Allow') or @id='allow-button']")))
                allow_button.click()
                self.debug_print("Clicked location permission: Allow this time")
                time.sleep(2)
            except TimeoutException:
                self.debug_print("No location popup found or already handled")
            except Exception as e:
                self.debug_print(f"Error handling location popup: {str(e)}")
            
            self.debug_print(f"Current URL: {self.driver.current_url}")
            self.debug_print(f"Page title: {self.driver.title}")
            
            for i in range(5):
                self.driver.execute_script("window.scrollBy(0, 1000);")
                time.sleep(2)
            
            products = []
            
            if self.debug_mode:
                with open('croma_debug.html', 'w', encoding='utf-8') as f:
                    f.write(self.driver.page_source)
                self.debug_print("Page source saved to croma_debug.html")
            
            container_selectors = [
                "li.product-item",
                "div.product-item",
                "div.product",
                "li[class*='product']",
                "div[class*='product-card']",
                "article.product"
            ]
            
            containers = []
            for selector in container_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if len(elements) >= 2:
                        containers = elements
                        self.debug_print(f"Found {len(elements)} containers using: {selector}")
                        print(f"  📦 Found {len(elements)} product containers")
                        break
                except Exception as e:
                    self.debug_print(f"Selector {selector} failed: {str(e)}")
                    continue
            
            for idx, container in enumerate(containers[:20]):
                try:
                    self.debug_print(f"\n--- Processing Croma container {idx+1} ---")
                    
                    title = ""
                    product_url = search_url
                    
                    title_selectors = [
                        "h3.product-title a",
                        "a.product-title",
                        "h3 a",
                        "a[class*='product-title']",
                        "div.product-title",
                        "span.product-title",
                        "a[href*='/p/']"
                    ]
                    
                    for selector in title_selectors:
                        try:
                            title_elem = container.find_element(By.CSS_SELECTOR, selector)
                            title = title_elem.text.strip() or title_elem.get_attribute('title') or ""
                            href = title_elem.get_attribute('href')
                            
                            if title and len(title) > 3:
                                if href and href != search_url:
                                    product_url = href if href.startswith('http') else f"https://www.croma.com{href}"
                                self.debug_print(f"Title: {title[:50]}")
                                self.debug_print(f"URL: {product_url}")
                                break
                        except:
                            continue
                    
                    if not title:
                        self.debug_print("No title found, skipping")
                        continue
                    
                    if not self.is_relevant_product(title, search_query):
                        self.debug_print(f"Product not relevant: {title[:50]}")
                        continue
                    
                    price_text = "N/A"
                    price_selectors = [
                        "span.amount",
                        "span.price",
                        "div.price",
                        "span[class*='price']",
                        "div[class*='price']",
                        "span.new-price",
                        "span.plp-srp-new-amount"
                    ]
                    
                    for selector in price_selectors:
                        try:
                            price_elem = container.find_element(By.CSS_SELECTOR, selector)
                            price_text = price_elem.text.strip()
                            if price_text and ('₹' in price_text or re.search(r'\d{3,}', price_text)):
                                self.debug_print(f"Price: {price_text}")
                                break
                        except:
                            continue
                    
                    if price_text == "N/A":
                        self.debug_print("No price found")
                        continue
                    
                    rating = "N/A"
                    try:
                        rating_elem = container.find_element(By.CSS_SELECTOR, ".rating, [class*='rating'], [class*='star']")
                        rating = rating_elem.get_attribute('title') or rating_elem.text.strip()
                    except:
                        pass
                    
                    offers = self.extract_offers(container)
                    category = self.auto_categorize_product(title)
                    
                    image_url = "N/A"
                    try:
                        img_elem = container.find_element(By.CSS_SELECTOR, "img")
                        src = img_elem.get_attribute('src') or img_elem.get_attribute('data-src') or ""
                        if src and 'placeholder' not in src.lower() and len(src) > 20:
                            if not src.startswith('http'):
                                image_url = f"https://www.croma.com{src}"
                            else:
                                image_url = src
                    except:
                        pass
                    
                    products.append({
                        'title': title, 'price': price_text, 'price_num': self.extract_price(price_text),
                        'rating': rating, 'category': category, 'source': 'Croma',
                        'url': product_url, 'image': image_url, 'offers': ' | '.join(offers) if offers else 'N/A'
                    })
                    
                    self.debug_print(f"✅ Added: {title[:40]} - {price_text}")
                    
                except Exception as e:
                    self.debug_print(f"Error in container {idx+1}: {str(e)}")
                    continue
            
            print(f"  ✅ Found {len(products)} relevant products on Croma")
            return products
        except Exception as e:
            print(f"  ❌ Error scraping Croma: {str(e)}")
            return []

    def compare_prices(self, search_query, websites=None):
        """
        Compare prices across selected websites
        
        Args:
            search_query: Product to search for
            websites: List of websites to scrape. If None, scrapes all.
                     Options: ['flipkart', 'amazon', 'vijay_sales', 'jiomart', 'croma']
        """
        print(f"\n🔍 UNIVERSAL PRICE COMPARISON - 5 WEBSITES")
        print(f"Searching for: '{search_query}'")
        print("=" * 70)
        
        all_products = []
        self.create_driver()
        
        # Default to all websites if none specified
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
            print("\n⚠️  Scraping interrupted by user")
        finally:
            if self.driver:
                try:
                    print("\n👋 Closing browser...")
                    self.driver.quit()
                except Exception:
                    pass
                time.sleep(0.5)
        
        valid_products = [p for p in all_products if p['price_num'] is not None and p['price_num'] >= 10]
        valid_products.sort(key=lambda x: x['price_num'])
        return valid_products

    def display_results_by_website(self, products):
        if not products:
            print("\n❌ No products found with valid prices")
            return
        print(f"\n🎯 PRICE COMPARISON RESULTS BY WEBSITE")
        print("=" * 80)
        print(f"Total Products Found: {len(products)}")
        print("=" * 80)
        source_dict = {}
        for product in products:
            src = product['source']
            if src not in source_dict:
                source_dict[src] = []
            source_dict[src].append(product)
        website_order = ['Flipkart', 'Amazon', 'Vijay Sales', 'JioMart', 'Croma']
        for src in website_order:
            if src in source_dict:
                items = source_dict[src]
                print(f"\n{'='*80}")
                print(f"🌐 {src.upper()} - {len(items)} Products")
                print(f"{'='*80}")
                for i, item in enumerate(items, 1):
                    price_display = f"₹{item['price_num']:,}" if item['price_num'] else item['price']
                    print(f"\n{i}. {item['title']}")
                    print(f"   💰 Price: {price_display}")
                    if item['rating'] != "N/A":
                        print(f"   ⭐ Rating: {item['rating']}")
                    if item['offers'] != "N/A":
                        print(f"   🎁 Offers: {item['offers']}")
                    print(f"   📂 Category: {item['category']}")
                    print(f"   🔗 URL: {item['url']}")
                    if item['image'] != "N/A":
                        print(f"   🖼️  Image: {item['image']}")
        
        print(f"\n{'='*80}")
        print(f"📊 SUMMARY BY WEBSITE")
        print(f"{'='*80}")
        for src in website_order:
            if src in source_dict:
                count = len(source_dict[src])
                print(f"  {src}: {count} products")
        
        print(f"\n{'='*80}")
        if len(products) > 0:
            lowest_price_product = min(products, key=lambda x: x['price_num'])
            print(f"🏆 BEST DEAL:")
            print(f"   {lowest_price_product['title']}")
            print(f"   💰 ₹{lowest_price_product['price_num']:,} on {lowest_price_product['source']}")
            if lowest_price_product['offers'] != "N/A":
                print(f"   🎁 {lowest_price_product['offers']}")
            print(f"   🔗 {lowest_price_product['url']}")
        print(f"{'='*80}\n")
        
        return products

    def export_to_csv(self, products, filename="price_comparison_results.csv"):
        if not products:
            print("No products to export")
            return
        df = pd.DataFrame(products)
        df = df[['source', 'title', 'price', 'price_num', 'rating', 'offers', 'category', 'url', 'image']]
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"\n✅ Results exported to {filename}")

if __name__ == "__main__":
    print("\n" + "="*70)
    print("🛒 UNIVERSAL E-COMMERCE PRICE COMPARISON TOOL")
    print("="*70)
    
    debug_choice = input("\n🐛 Enable debug mode? (shows detailed logs) [y/N]: ").strip().lower()
    debug_mode = debug_choice in ['y', 'yes']
    
    scraper = UniversalEcommerceScraper(debug_mode=debug_mode)
    
    search_query = input("\n🔍 Enter product to search: ").strip()
    
    if not search_query:
        print("❌ Please enter a valid search query.")
        exit()
    
    # Default to all 5 websites
    print("\n📌 Scraping all 5 websites by default")
    print("   (Flipkart, Amazon, Vijay Sales, JioMart, Croma)")
    
    custom_choice = input("\n⚙️  Use custom website selection? [y/N]: ").strip().lower()
    
    websites = None
    if custom_choice in ['y', 'yes']:
        print("\n📌 Select websites to scrape:")
        print("1. All websites (default)")
        print("2. Major e-commerce only (Flipkart, Amazon, Vijay Sales, Croma)")
        print("3. Quick delivery focus (JioMart)")
        print("4. Custom selection")
        
        choice = input("\nEnter your choice (1-4): ").strip() or "1"
        
        if choice == "2":
            websites = ['flipkart', 'amazon', 'vijay_sales', 'croma']
            print("✅ Scraping: Flipkart, Amazon, Vijay Sales, Croma")
        elif choice == "3":
            websites = ['jiomart']
            print("✅ Scraping: JioMart")
        elif choice == "4":
            print("\nSelect websites (separate with commas):")
            print("Options: flipkart, amazon, vijay_sales, jiomart, croma")
            custom = input("Enter websites: ").strip().lower()
            websites = [w.strip() for w in custom.split(',') if w.strip()]
            print(f"✅ Scraping: {', '.join(websites)}")
        else:
            print("✅ Scraping all 5 websites")
    else:
        print("✅ Scraping all 5 websites")
    
    products = scraper.compare_prices(search_query, websites)
    scraper.display_results_by_website(products)
    
    if products:
        export_choice = input("\n💾 Do you want to export results to CSV? (yes/no): ").strip().lower()
        if export_choice in ['yes', 'y']:
            filename = f"price_comparison_{search_query.replace(' ', '_')}.csv"
            scraper.export_to_csv(products, filename)