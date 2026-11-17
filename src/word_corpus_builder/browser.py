import os
import re
import time
import platform
import subprocess
from pathlib import Path

from playwright.sync_api import TimeoutError
from playwright.sync_api import sync_playwright, expect


PORT = 9222

# Linux
CHROME_PATH = "google-chrome"
local_dir = Path("~/.local/share").expanduser()

if platform.system() == 'Windows':
    CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    LOCAL_DIR = Path(os.environ["LOCALAPPDATA"])

data_dir = local_dir / "word-corpus-builder"

PROFILE_DIR = data_dir / "profile"
URL = "https://www.google.com/search?q=%22murder%22&oq=%22murder%22&sourceid=chrome&ie=UTF-8"


class BrowserNotOpeningException(Exception):
    """Process responsible for starting a real Chrome instance has failed.
    """
    pass


class PermanentCaptchaException(Exception):
    """Captcha persists across multiple runs.

    At the start of profile, captcha is present, but after restart, it usually disappears.
    """
    pass


def start_chrome():
    """Start chrome instance

    Preconditions:
        - There is no debugging chrome instance running at `PORT`.
    """
    # ensure profile dir presence
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)

    cmd = [
        CHROME_PATH,
        f"--remote-debugging-port={PORT}",
        f"--user-data-dir={PROFILE_DIR}",
        "--start-maximized"
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # wait to completely boot
    time.sleep(2)
    
    return proc

class BrowserManager:
    """Manage a persistent Playwright browser session."""


    def __init__(self, wait_for_captcha_solved=False) -> None:
        self.wait_for_captcha_solved = wait_for_captcha_solved
        self.restarted = False

    def launch(self) -> None:
        """Start chrome instance, and set connection to that instance via playwright.

        Preconditions:
            - There is no debugging chrome instance running at `PORT`.
            - `launch()` has not been called OR `close()` has been called after previous `launch()`.
        """
        self.proc = start_chrome()

        if self.proc.poll() is not None:
            stdout, stderr = self.proc.communicate()
            raise BrowserNotOpeningException(f'Chrome couldn\'t start; Standard output: "{stdout}"; standard error: "{stderr}"')

        self.playwright = sync_playwright().start()

        self.browser = self.playwright.chromium.connect_over_cdp(f"http://localhost:{PORT}")
        self.context = self.browser.contexts[0]

    def set_header_listener(self, page, url):
        """Set up a request listener, to collect Google specific headers.

        Args:
            page (playwright.Page): a page with which Google search will be done

        Returns:
            A dictionary that will be updated with Google specific headers after Google search.
        """
        captured = {}

        def handle_request(req):
            # Capture the document navigation
            if (
                req.resource_type == "document"
                and req.url.startswith(url)
            ):
                captured.update(
                    {key: value for key, value in req.all_headers().items() 
                     if not key.startswith(":") and key != 'cookie' and key!="accept-encoding"})
 
        page.on("request", handle_request)
        return captured, lambda: page.remove_listener('request', handle_request)

    def solve_captcha(self, page):
        try:
            page.get_by_title("reCAPTCHA").wait_for(timeout=2000)

            if self.restarted:
                if self.wait_for_captcha_solved:
                    req = input("There is persistent captcha, please solve it. If you want to quit, type `q` and then enter.")
                    if req == "q":
                        page.close()
                        return {}
                else:
                    raise PermanentCaptchaException("Browser stuck on the CAPTCHA permanently.")
            else:
                page.close()
                
                self.close()
                self.launch()
    
                self.restarted = True
                return self.get_search_request_args()
        except TimeoutError:
            pass
        
        try:
            page.locator("xpath=//div/button[@id][./div][2]").click(timeout=5000)
            
            time.sleep(2)
        except TimeoutError:
            print("Button didn't appear within 5 seconds")

    def get_search_request_args(self) -> dict:
        """Get headers and cookies required for requests to Google.

        Preconditions:
            - `launch()` has been called.
            - `close()` has not been called.

        Returns:
            A dictionary with keys:
                "cookies": for cookies dictionary and 
                "headers": for headers dictionary sufficient to make
                for a working request to https://www.google.com search.
        """
        return self.get_request_args("https://www.google.com/search?", to_solve_captcha=True)

    def get_request_args(self, url, to_solve_captcha=False) -> dict:
        """Get headers and cookies required for requests to domain of `url`.

        Preconditions:
            - `launch()` has been called.
            - `close()` has not been called.

        Returns:
            A dictionary with keys:
                "cookies": for cookies dictionary and 
                "headers": for headers dictionary sufficient to make
                for a working request to `url`.
        """
        page = self.context.new_page()
        headers, remove_listener = self.set_header_listener(page, url)
    
        page.goto(URL, wait_until="commit", timeout=10000)

        if to_solve_captcha:
            self.solve_captcha(page)
        else:
            time.sleep(5)
            self.restarted = False

        domain = re.match(r"(https?://)([^/:?#]+)", url)[2]
        domain = domain.replace("www.", "")

        cookies = {cookie['name']: cookie['value'] for cookie in self.context.cookies() 
                   if cookie['domain'].endswith(domain)}
        # self.cookies_time = {cookie['name']: cookie['expires'] for cookie in self.context.cookies()}

        remove_listener()
        page.close()

        return {"headers": headers, "cookies": cookies}

    def check_expires_cookies(self):
        now = time.time()
        for cookie, expires in self.cookies_time.items():
            if expires < now:
                return True

        return False

    def close(self) -> None:
        """Close chrome instance, and connection to it.

        Preconditions:
            - `launch()` has been called.
            - `close()` has not been called.
        """
        session = self.browser.new_browser_cdp_session()
        session.send("Browser.close")

        self.context.close()
        self.browser.close()

        self.playwright.stop()

        try:
            self.proc.wait(timeout=10) # returns as soon as Chrome exits
        except subprocess.TimeoutExpired:
            self.proc.terminate()
            self.proc.wait()
