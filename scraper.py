import csv
import time
import argparse
import random
import os
import json
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError
import re

class GoogleMapsScraper:
    """
    Advanced Scraper for Google Maps Reviews with Google Login support.
    Designed for Headless Cloud environments (Render).
    """

    def __init__(self, url, max_reviews=100, headless=True):
        self.url = url
        self.max_reviews = max_reviews
        self.headless = headless
        self.reviews_data = []
        self.REVIEW_CONTAINER_CLASS = "jJc9Ad"
        self.email = os.environ.get("GOOGLE_EMAIL")
        self.password = os.environ.get("GOOGLE_PASSWORD")
        
    def log(self, message):
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}")

    def random_sleep(self, min_s=1.0, max_s=3.0):
        time.sleep(random.uniform(min_s, max_s))

    def login_google(self, page):
        """Attempts to log in to Google with strict validation and debugging."""
        if not self.email or not self.password:
            self.log("⚠️ Credentials not found. Aborting login (Anonymous mode).")
            return False

        self.log("🔐 Starting Google Login (Strict Debug Mode)...")
        debug_dir = "debug"
        if not os.path.exists(debug_dir):
            os.makedirs(debug_dir)

        try:
            # STEP 1: Navigate to Login (Force ServiceLogin)
            login_url = "https://accounts.google.com/ServiceLogin?hl=es"
            self.log(f"STEP 1: Navigating to {login_url}...")
            page.goto(login_url, timeout=60000)
            page.wait_for_load_state("domcontentloaded")
            
            # Check for immediate redirects or wrong page
            current_url = page.url
            self.log(f"Current URL after load: {current_url}")
            
            if "accounts.google.com" not in current_url:
                self.log(f"❌ CRITICAL ERROR: Redirected away from login page to: {current_url}")
                page.screenshot(path=f"{debug_dir}/login_error_redirected.png")
                return False
                
            page.screenshot(path=f"{debug_dir}/login_step1_loaded.png")

            # Check for "Browser not secure" error immediately
            if page.locator("text=This browser or app may not be secure").is_visible() or \
               page.locator("text=Este navegador o aplicación no es seguro").is_visible():
                self.log("❌ CRITICAL: Google blocked this browser instance (Anti-bot detection).")
                page.screenshot(path=f"{debug_dir}/login_error_blocked.png")
                return False

            # STEP 2: Email Input
            self.log("STEP 2: Locating Email Input...")
            email_input = page.locator('input[type="email"]')
            
            # Additional check: Is it really the login form?
            if not email_input.is_visible(timeout=10000):
                self.log("❌ ERROR: Email input not found. Dumping HTML...")
                page.screenshot(path=f"{debug_dir}/login_error_no_email.png")
                with open(f"{debug_dir}/login_page_dump.html", "w") as f:
                    f.write(page.content())
                return False
            
            self.log(f"Entering email: {self.email[:3]}***@...")
            email_input.fill(self.email)
            self.random_sleep(1, 2)
            page.screenshot(path=f"{debug_dir}/login_step2_email_filled.png")

            # STEP 3: Click Next
            self.log("STEP 3: Clicking 'Next'...")
            next_btn = page.locator("#identifierNext, button:has-text('Siguiente'), button:has-text('Next')").first
            if not next_btn.is_visible():
                self.log("❌ ERROR: Next button not found.")
                return False
            
            next_btn.click()
            self.log("Clicked Next. Waiting for transition...")
            page.wait_for_load_state("networkidle")
            self.random_sleep(2, 4)
            page.screenshot(path=f"{debug_dir}/login_step3_after_next.png")

            # Check for immediate errors after email (e.g. "Couldn't find your Google Account")
            if page.locator("text=Couldn't find your Google Account").is_visible():
                self.log("❌ ERROR: Email not recognized by Google.")
                return False

            # STEP 4: Password Input
            self.log("STEP 4: Waiting for Password Field...")
            try:
                page.wait_for_selector('input[type="password"]', state="visible", timeout=10000)
            except TimeoutError:
                self.log("❌ ERROR: Password field did not appear.")
                self.log(f"Stuck at URL: {page.url}")
                page.screenshot(path=f"{debug_dir}/login_error_no_password.png")
                return False

            self.log("Password field detected. Entering password...")
            pwd_input = page.locator('input[type="password"]')
            pwd_input.fill(self.password)
            self.random_sleep(1, 2)
            page.screenshot(path=f"{debug_dir}/login_step4_password_filled.png")

            # STEP 5: Click Password Next
            self.log("STEP 5: Clicking Password Next...")
            pwd_next = page.locator("#passwordNext, button:has-text('Siguiente'), button:has-text('Next')").first
            pwd_next.click()
            
            # STEP 6: Validate Login Success
            self.log("STEP 6: Validating authentication...")
            try:
                # Wait for navigation to My Account or similar authenticated page
                # or wait for the URL to NOT contain 'signin' or 'ServiceLogin'
                page.wait_for_url(re.compile(r"myaccount\.google\.com|accounts\.google\.com/ManageAccount"), timeout=30000)
                self.log("✅ LOGIN SUCCESSFUL: Redirected to validated account page.")
                page.screenshot(path=f"{debug_dir}/login_success.png")
                return True
            except TimeoutError:
                self.log("⚠️ WARNING: No redirect to MyAccount. Checking if we are stuck or CAPTCHA'd...")
                page.screenshot(path=f"{debug_dir}/login_uncertain.png")
                # Sometimes it redirects back to the service (Maps? or empty)
                # Let's assume if no error message is visible, we might be good?
                # But safer to fail strict validation if requested.
                if page.locator('text=Wrong password').is_visible():
                    self.log("❌ ERROR: Wrong password.")
                    return False
                return True # Tentative success if no error checking matches

        except Exception as e:
            self.log(f"❌ EXCEPTION during login: {e}")
            page.screenshot(path=f"{debug_dir}/login_exception.png")
            return False

    def save_cookies(self, context, path="cookies.json"):
        """Saves current cookies to a file."""
        cookies = context.cookies()
        with open(path, "w") as f:
            json.dump(cookies, f)
        self.log(f"✅ Cookies guardadas en {path}. Úsalas en Render.")

    def load_cookies(self, context, path="cookies.json"):
        """Loads cookies from a file if it exists."""
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    cookies = json.load(f)
                context.add_cookies(cookies)
                self.log(f"✅ Cookies cargadas desde {path}. Sesión restaurada.")
                return True
            except Exception as e:
                self.log(f"⚠️ Error cargando cookies: {e}")
        return False

    def setup_login_manual(self):
        """
        Runs a non-headless browser for manual login and cookie saving.
        """
        self.log("🔵 MODO CONFIGURACIÓN: Inicia sesión manualmente en la ventana que se abrirá.")
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False) # Must be visible
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                locale="es-ES"
            )
            context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            page = context.new_page()
            
            self.log("Navegando a Google Login...")
            page.goto("https://accounts.google.com/ServiceLogin?hl=es")
            
            print("\n" + "="*50)
            print("⏳ ESPERANDO LOGIN MANUAL...")
            print("1. Introduce tu correo y contraseña en el navegador.")
            print("2. Completa cualquier verificación 2FA.")
            print("3. Cuando veas tu cuenta (MyAccount) o Google Maps, presiona ENTER aquí en la terminal.")
            print("="*50 + "\n")
            
            input("Program paused. Press Enter after successful login...")
            
            # Check if really logged in (optional check)
            if "accounts.google.com" in page.url or "myaccount.google.com" in page.url or "google.com/maps" in page.url:
                 self.log("Detectada posible sesión activa.")
            
            self.save_cookies(context, "cookies.json")
            browser.close()

    def _extract_business_name(self, page):
        """Extracts the business name from the page."""
        try:
            # Selector identified in prompt: class "a5H0ec" or "DUwDvf" (common title classes)
            # a5H0ec seems to be the main title header class often
            title_el = page.locator(".a5H0ec, h1.DUwDvf").first
            if title_el.is_visible():
                return title_el.inner_text()
            return "Unknown Business"
        except:
            return "Unknown Business"

    def scrape(self, return_data=False):
        self.log(f"Iniciando scraping (Headless: {self.headless})")
        
        # Ensure debug directory exists
        if not os.path.exists("debug"):
            os.makedirs("debug")
            
        # RESTORING STEALTH ARGUMENTS (CRITICAL FOR LOGIN)
        browser_args = [
            #"--disable-blink-features=AutomationControlled",
            #"--no-sandbox",
            #"--disable-setuid-sandbox",
            #"--disable-infobars",
            #"--start-maximized",
            "--disable-gpu",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-setuid-sandbox",
        ]

        with sync_playwright() as p:
            # Launch Browser
            browser = p.chromium.launch(
                headless=self.headless,
                args=browser_args
            )
            
            # Create Stealth Context
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080},
                locale="es-ES",
                device_scale_factor=1,
            )
            
            # Mask Webdriver property
            context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """)

            # --- AUTH STRATEGY ---
            # 1. Try Cookie Login first
            if self.load_cookies(context, "cookies.json"):
                self.log("🍪 Usando autenticación por Cookies.")
            else:
                self.log("⚠️ Ejecutándose como ANÓNIMO (sin cookies).")
            
            page = context.new_page()

            # Continue to Maps...
            try:
                self.log(f"Navegando a: {self.url}")
                page.goto(self.url, timeout=60000)
                self.random_sleep(3, 5)

                # Extract Business Name
                business_name = self._extract_business_name(page)
                self.log(f"📍 Business Found: {business_name}")

                # Intentar abrir el panel de reseñas si no está abierto
                # Buscamos botón que diga "Reseñas" o el conteo de estrellas
                self.log("Buscando panel de reseñas...")
                try:
                    # Selector genérico para el tab de 'Reseñas'
                    reviews_tab = page.locator("button[aria-label*='Reseñas'], button[aria-label*='Reviews']").first
                    if reviews_tab.is_visible():
                         reviews_tab.click()
                         self.random_sleep(2, 4)
                except:
                    pass

                # Esperar contenedor de reseñas
                try:
                    page.wait_for_selector(f".{self.REVIEW_CONTAINER_CLASS}", timeout=20000)
                except TimeoutError:
                    self.log("⚠️ No se encontraron reseñas visiblemente.")
                    return [] if return_data else None

                # Scroll loop
                processed_ids = set()
                last_count = 0
                retries = 0
                max_retries = 5
                
                # Elemento contenedor para scroll es usualmente el padre directo de los items
                # o usamos el mouse wheel global si el mouse está sobre el panel
                
                while len(self.reviews_data) < self.max_reviews:
                    # Parse current visible reviews
                    elements = page.locator(f".{self.REVIEW_CONTAINER_CLASS}").all()
                    self.log(f"Found {len(elements)} visible review elements.")
                    
                    for i, el in enumerate(elements):
                        if len(self.reviews_data) >= self.max_reviews:
                            break
                        
                        try:
                            # Unique ID based on text
                            text_content = el.inner_text()
                            content_hash = hash(text_content)
                            
                            if content_hash in processed_ids:
                                continue
                                
                            processed_ids.add(content_hash)
                            
                            # Parse fields
                            username = self._extract_username(el)
                            rating = self._extract_rating(el)
                            review_text = self._extract_text(el)
                            
                            record = {
                                "business_name": business_name,
                                "username": username,
                                "rating": rating,
                                "review_text": review_text,
                                "source": "Google Maps",
                                "scraping_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            }
                            self.reviews_data.append(record)
                        except Exception as e:
                            self.log(f"Error processing review item: {e}")
                            continue
                            
                    self.log(f"Progreso: {len(self.reviews_data)}/{self.max_reviews}")
                    
                    # Scroll logic
                    if elements:
                        # Scroll to last element
                        elements[-1].scroll_into_view_if_needed()
                        
                        # Mouse wheel en el centro de la pantalla (a veces el panel está a la izquierda)
                        # Coordenadas aproximadas del panel lateral
                        page.mouse.move(400, 600)
                        page.mouse.wheel(0, 3000)
                        
                        # Keyboard End
                        page.keyboard.press("End")
                    
                    self.random_sleep(2, 4)
                    
                    if len(self.reviews_data) == last_count:
                        retries += 1
                        self.log(f"Esperando nuevas reseñas... (Intento {retries}/{max_retries})")
                        if retries >= max_retries:
                            break
                    else:
                        retries = 0
                        last_count = len(self.reviews_data)

            except Exception as e:
                self.log(f"❌ Error en scraping: {e}")
                page.screenshot(path="debug/crash_screenshot.png")
            finally:
                browser.close()
                
        return self.reviews_data if return_data else None

    def _extract_username(self, element):
        try:
            return element.get_attribute("aria-label") or element.inner_text().split('\n')[0]
        except:
            return "Unknown"

    def _extract_rating(self, element):
        try:
            star_el = element.locator('[aria-label*="estrella"], [aria-label*="star"], [aria-label*="Estrella"]').first
            if star_el and star_el.is_visible():
                aria = star_el.get_attribute("aria-label")
                match = re.search(r'(\d+(\.|,)?\d*)', aria)
                if match:
                    val = match.group(1).replace(',', '.')
                    return float(val)
            return 0
        except:
            return 0

    def _extract_text(self, element):
        try:
            more_btn = element.locator("button[aria-label^='Ver más'], button[aria-label^='See more'], button:has-text('Más')").first
            if more_btn.is_visible():
                try: more_btn.click(timeout=1000)
                except: pass
            
            content_span = element.locator(".wiI7pd").first
            if content_span.is_visible():
                return content_span.inner_text()
            
            full_text = element.inner_text()
            lines = [l.strip() for l in full_text.split('\n') if l.strip()]
            ignored = ["Me gusta", "Compartir", "Más", "Like", "Share", "More", "Responder", "Response", "Estrella", "star"]
            candidates = [l for l in lines if l not in ignored and len(l) > 2]
            
            if candidates:
                name = self._extract_username(element)
                if candidates[0] == name: candidates.pop(0)
                return " ".join(candidates).strip()

            return ""
        except:
            return ""

    def save_to_csv(self, filename=None):
        if not self.reviews_data:
            self.log("⚠️ No se extrajeron reseñas.")
            return
            
        # Auto-name based on URL hash if no filename
        if not filename:
            import hashlib
            url_hash = hashlib.md5(self.url.encode()).hexdigest()[:8]
            filename = f"reviews_{url_hash}.csv"
            
        with open(filename, 'w', encoding='utf-8', newline='') as f:
            fieldnames = ["business_name", "username", "rating", "review_text", "source", "scraping_date"]
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(self.reviews_data)
        self.log(f"✅ Archivo guardado: {filename}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="https://maps.app.goo.gl/Ti7ixa3owkmGMdTo9")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--setup-cookies", action="store_true", help="Launch browser for manual login and save cookies")
    args = parser.parse_args()
    
    if args.setup_cookies:
        scraper = GoogleMapsScraper(args.url, max_reviews=0, headless=False)
        scraper.setup_login_manual()
    else:
        # Force headless in cloud, but allow override locally if desired (here we enforce logic compatible with render)
        # Render environment usually sets RENDER=true
        is_render = os.environ.get("RENDER") is not None
        
        scraper = GoogleMapsScraper(args.url, max_reviews=args.limit, headless=True)
        scraper.scrape()
        scraper.save_to_csv()
