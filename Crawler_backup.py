from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
import time
import re

class SmartCrawler:
    def __init__(self):
        chrome_options = Options()
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    def is_sponsored(self, product_element, full_text):
        """SMARTER sponsored detection - less aggressive"""
        text_lower = full_text.lower()
        
        # Only flag if CLEARLY sponsored
        clear_sponsored_indicators = [
            'sponsored', 
            'advertisement',
            'promoted by',
            'brand: amazon'
        ]
        
        for indicator in clear_sponsored_indicators:
            if indicator in text_lower:
                return True
        
        return False
    
    def search_flipkart(self, product_name):
        """Flipkart search with better filtering"""
        print(f"🔍 Searching Flipkart for: {product_name}")
        
        try:
            search_url = f"https://www.flipkart.com/search?q={product_name.replace(' ', '+')}"
            self.driver.get(search_url)
            time.sleep(4)
            
            products = self.driver.find_elements(By.CSS_SELECTOR, "[data-id]")
            print(f"   Found {len(products)} products total")
            
            for i, product in enumerate(products[:10]):  # Check first 10 only
                try:
                    full_text = product.text
                    
                    # Skip if clearly sponsored
                    if self.is_sponsored(product, full_text):
                        print(f"   ⏩ Skipping clearly sponsored product {i+1}")
                        continue
                    
                    # Extract title - more flexible approach
                    lines = full_text.split('\n')
                    title = lines[0] if lines else ""
                    
                    # Skip if title is too short or doesn't contain product keywords
                    if len(title) < 3:
                        continue
                    
                    # Extract price - look for ₹ symbol
                    price_match = re.search(r'₹(\d+[,]?\d*)', full_text)
                    if price_match:
                        price = float(price_match.group(1).replace(',', ''))
                        
                        # Reasonable price ranges for different product types
                        if (price > 100 and price < 500000):  
                            print(f"✅ Product {i+1}: {title[:50]}... - ₹{price}")
                            
                            # Try to get individual product URL
                            try:
                                product_link = product.find_element(By.CSS_SELECTOR, "a._1fQZEK, a.s1Q9rs, a._2rpwqI")
                                product_url = product_link.get_attribute('href')
                            except:
                                product_url = search_url
                            
                            return {
                                'store': 'Flipkart',
                                'title': title,
                                'price': price,
                                'availability': 'In Stock',
                                'url': product_url,
                                'search_url': search_url
                            }
                            
                except Exception as e:
                    continue
            
            print("❌ No suitable products found on Flipkart")
            return None
                    
        except Exception as e:
            print(f"❌ Flipkart error: {e}")
            return None

    def search_amazon(self, product_name):
        """Amazon search - FIXED selector with multiple approaches"""
        print(f"🔍 Searching Amazon for: {product_name}")
        
        try:
            search_url = f"https://www.amazon.in/s?k={product_name.replace(' ', '+')}"
            self.driver.get(search_url)
            time.sleep(5)  # Give more time for Amazon to load
            
            # MULTIPLE Amazon selectors - try different approaches
            selectors_to_try = [
                "div[data-component-type='s-search-result']",
                "div.s-result-item",
                "div[data-asin]",
                ".s-main-slot .s-result-item",
                "[cel_widget_id*='MAIN-SEARCH_RESULTS']"
            ]
            
            products = []
            for selector in selectors_to_try:
                try:
                    found_products = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if found_products:
                        products = found_products
                        print(f"   Found {len(products)} products using: {selector}")
                        break
                except:
                    continue
            
            if not products:
                print("   ⚠️  Trying fallback: looking for any product-like divs")
                # Last resort - get all divs and filter
                all_divs = self.driver.find_elements(By.CSS_SELECTOR, "div")
                products = [div for div in all_divs if len(div.text) > 50]  # Products have more text
            
            print(f"   Checking {len(products)} potential products")
            
            for i, product in enumerate(products[:12]):  # Check more products
                try:
                    full_text = product.text
                    
                    # Skip if empty or too short
                    if len(full_text) < 20:
                        continue
                    
                    # Skip if clearly sponsored
                    if self.is_sponsored(product, full_text):
                        print(f"   ⏩ Skipping sponsored product {i+1}")
                        continue
                    
                    # Extract title - look for meaningful product name
                    lines = [line.strip() for line in full_text.split('\n') if line.strip()]
                    title = None
                    
                    for line in lines:
                        # Look for lines that seem like product names (not prices, not ratings)
                        if (len(line) > 10 and 
                            not re.search(r'₹\d|rating|bought|\d+%', line.lower()) and
                            not line.lower() in ['best seller', 'sponsored', 'ad']):
                            title = line
                            break
                    
                    if not title and lines:
                        title = lines[0]
                    
                    # Skip if title is garbage
                    if not title or len(title) < 5:
                        continue
                    
                    # Extract price - multiple patterns
                    price_match = re.search(r'₹\s*(\d+[,]?\d*)', full_text)
                    if not price_match:
                        # Try without ₹ symbol
                        price_match = re.search(r'(\d+[,]?\d*)\s*(?=M\.R\.P|₹|rs|rupees)', full_text, re.IGNORECASE)
                    
                    if price_match:
                        price = float(price_match.group(1).replace(',', ''))
                        
                        if price > 10 and price < 500000:  # Wider price range
                            print(f"✅ Amazon Product {i+1}: {title[:50]}... - ₹{price}")
                            
                            # Try to get individual product URL
                            try:
                                product_link = product.find_element(By.CSS_SELECTOR, "h2 a, a.a-link-normal, a.a-text-normal")
                                product_url = product_link.get_attribute('href')
                            except:
                                product_url = search_url
                            
                            return {
                                'store': 'Amazon',
                                'title': title,
                                'price': price,
                                'availability': 'In Stock', 
                                'url': product_url,
                                'search_url': search_url
                            }
                            
                except Exception as e:
                    continue
            
            print("❌ No suitable products found on Amazon")
            return None
                    
        except Exception as e:
            print(f"❌ Amazon error: {e}")
            return None

    def compare_prices(self, product_name):
        """Compare prices"""
        print(f"\n🎯 Comparing prices for: {product_name}")
        print("=" * 50)
        
        results = []
        
        # Search both sites
        flipkart_result = self.search_flipkart(product_name)
        if flipkart_result:
            results.append(flipkart_result)
        
        amazon_result = self.search_amazon(product_name)
        if amazon_result:
            results.append(amazon_result)
        
        # Display results
        if results:
            print("\n📊 PRICE COMPARISON RESULTS:")
            print("-" * 50)
            
            for result in results:
                print(f"🏪 {result['store']:10} | ₹{result['price']:8.2f} | {result['availability']}")
                print(f"   📦 {result['title'][:70]}...")
                print()
            
            # Find best deal
            best_deal = min(results, key=lambda x: x['price'])
            print("🎉 BEST DEAL FOUND!")
            print(f"💚 {best_deal['store']} - ₹{best_deal['price']:.2f}")
            print(f"   for '{product_name}'")
            print(f"🔗 Product Link: {best_deal['url']}")
            
            # Show savings if multiple results
            if len(results) > 1:
                other_prices = [r['price'] for r in results if r['store'] != best_deal['store']]
                if other_prices:
                    savings = other_prices[0] - best_deal['price']
                    print(f"💰 You save: ₹{savings:.2f} compared to {[r['store'] for r in results if r['store'] != best_deal['store']][0]}")
            
            return results
        else:
            print("❌ No products found")
            return []

    def close(self):
        self.driver.quit()

def main():
    crawler = SmartCrawler()
    
    print("🕷️  SMART PRICE COMPARISON CRAWLER")
    print("==================================")
    print("🎯 Fixed Amazon detection - should work better now!")
    print()
    
    try:
        while True:
            product = input("\nEnter product to compare (or 'quit'): ").strip()
            
            if product.lower() == 'quit':
                break
                
            if product:
                crawler.compare_prices(product)
            else:
                print("Please enter a product name")
                
    finally:
        crawler.close()

if __name__ == "__main__":
    main()