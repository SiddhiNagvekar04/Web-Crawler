# crawler.py
import time, random, re, requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; rv:124.0) Gecko/20100101 Firefox/124.0"
]

def get_headers():
    return {"User-Agent": random.choice(USER_AGENTS), "Accept-Language": "en-US,en;q=0.9"}

def create_driver(headless=True):
    options = Options()
    # If you get blocked or no results, set headless=False to see the browser
    if headless:
        # new headless flag for modern Chrome
        options.add_argument("--headless=new")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument(f"user-agent={random.choice(USER_AGENTS)}")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_window_size(1200, 800)
    return driver

# ---------- AMAZON ----------
def search_amazon(product, headless=True):
    data = {"store": "Amazon", "title": "Not Available", "price": None, "url": None}
    driver = None
    try:
        driver = create_driver(headless=headless)
        driver.get(f"https://www.amazon.in/s?k={product.replace(' ', '+')}")
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.s-main-slot")))
        products = driver.find_elements(By.CSS_SELECTOR, "div.s-main-slot div[data-component-type='s-search-result']")
        for p in products[:8]:
            try:
                title = p.find_element(By.CSS_SELECTOR, "h2 a span").text.strip()
                if product.lower() not in title.lower():
                    continue
                price_whole = None
                price_fraction = None
                try:
                    price_whole = p.find_element(By.CSS_SELECTOR, "span.a-price-whole").text.replace(",", "")
                    price_fraction = p.find_element(By.CSS_SELECTOR, "span.a-price-fraction").text
                    price = float(price_whole + "." + price_fraction)
                except:
                    price = None
                link = p.find_element(By.CSS_SELECTOR, "h2 a").get_attribute("href")
                if price and price > 50:
                    data.update({"title": title, "price": price, "url": link})
                    break
            except Exception:
                continue
    except Exception as e:
        # return partial or default data
        # print(f"[Amazon Error] {e}")
        pass
    finally:
        if driver:
            driver.quit()
    return data

# ---------- FLIPKART ----------
def search_flipkart(product, headless=True):
    data = {"store": "Flipkart", "title": "Not Available", "price": None, "url": None}
    driver = None
    try:
        driver = create_driver(headless=headless)
        driver.get(f"https://www.flipkart.com/search?q={product.replace(' ', '+')}")
        # close login popup if present
        time.sleep(random.uniform(1.5, 3))
        try:
            close_btn = driver.find_element(By.CSS_SELECTOR, "button._2KpZ6l._2doB4z")
            close_btn.click()
        except:
            pass
        time.sleep(random.uniform(1, 2))
        # product cards
        products = driver.find_elements(By.CSS_SELECTOR, "div._1AtVbE")
        for p in products[:10]:
            try:
                title_el = p.find_element(By.CSS_SELECTOR, "a.s1Q9rs, a.IRpwTa")
                price_el = p.find_element(By.CSS_SELECTOR, "div._30jeq3")
                title = title_el.text.strip()
                price_text = price_el.text.replace("₹", "").replace(",", "").strip()
                price = float(re.sub(r"[^\d\.]", "", price_text))
                link = title_el.get_attribute("href")
                if product.lower() in title.lower() and price > 50:
                    data.update({"title": title, "price": price, "url": link})
                    break
            except:
                continue
    except Exception as e:
        # print(f"[Flipkart Error] {e}")
        pass
    finally:
        if driver:
            driver.quit()
    return data

# ---------- MYNTRA ----------
def search_myntra(product, headless=True):
    data = {"store": "Myntra", "title": "Not Available", "price": None, "url": None}
    try:
        url = f"https://www.myntra.com/{product.replace(' ', '-')}"
        r = requests.get(url, headers=get_headers(), timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        product_cards = soup.select("li.product-base")
        for p in product_cards[:12]:
            try:
                brand_el = p.select_one("h3.product-brand")
                name_el = p.select_one("h4.product-product")
                price_el = p.select_one("span.product-discountedPrice, span.product-price")
                if not (brand_el and name_el and price_el):
                    continue
                title = f"{brand_el.text.strip()} {name_el.text.strip()}"
                price_text = re.sub(r"[^\d]", "", price_el.text)
                price = float(price_text)
                link = "https://www.myntra.com" + p.select_one("a")["href"]
                if product.lower() in title.lower() and price > 50:
                    data.update({"title": title, "price": price, "url": link})
                    break
            except:
                continue
    except Exception:
        pass
    return data

# ---------- MEESHO ----------
def search_meesho(product, headless=True):
    data = {"store": "Meesho", "title": "Not Available", "price": None, "url": None}
    try:
        url = f"https://www.meesho.com/search?q={product.replace(' ', '%20')}"
        r = requests.get(url, headers=get_headers(), timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        product_cards = soup.select("div.Card__BaseCard, div.sc-dkrFOg")
        for p in product_cards[:12]:
            try:
                title_el = p.select_one("p") or p.select_one("h3")
                price_el = p.select_one("h5")
                if not (title_el and price_el):
                    continue
                title = title_el.text.strip()
                price_text = re.sub(r"[^\d]", "", price_el.text)
                price = float(price_text)
                a = p.select_one("a")
                link = "https://www.meesho.com" + a["href"] if a and a.get("href") else None
                if product.lower() in title.lower() and price > 50:
                    data.update({"title": title, "price": price, "url": link})
                    break
            except:
                continue
    except Exception:
        pass
    return data
