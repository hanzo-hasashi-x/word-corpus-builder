from requests.models import PreparedRequest
import codecs
import httpx
import time
import re


DELAY = 0.5

class Fetcher:

    def __init__(self, language, target_sites, request_args) -> None:
        self.language = language

        self._sites_search_arg = ""
        if target_sites is not None:
            sites_arg = ["site:"+site for site in target_sites]
            self._sites_search_arg = " (" + " OR ".join(sites_arg) + ")"

        # ensure that no content-length is present
        request_args["headers"].pop("content-length", None)

        self.client = httpx.Client(http2=True, follow_redirects=True, **request_args)
        self.req = PreparedRequest()

    def close(self):
        self.client.close()

    def update_cookies(self, cookies):
        self.client.cookies.clear()
        self.client.cookies.update(cookies)

    def request(self, *args, **kwargs):
        time.sleep(DELAY)
        return self.client.get(*args, **kwargs)

    def parse_goto(self, goto):
        r = self.client.get(
            "https://www.google.com" + goto,
            follow_redirects=False,
        )

        page_url = None
        if r.status_code == 302:
            page_url = r.headers.get("location")

        elif r.status_code < 300:

            timeout_match = re.search(r"var delayMillis=(\d+)", r.text)
            url_match = re.search(r"var redirectUrl='([^']+)'", r.text)

            if timeout_match and url_match:
                time.sleep(int(timeout_match.group(1)) / 1000 + .1)
                return self.parse_goto(codecs.decode(url_match.group(1), 'unicode_escape'))

        return page_url

    def parse_text(self, url, target_word, req_args=None):
        if req_args is None:
            req_args = {}

        try:
            r = self.client.get(url, **req_args)
        except httpx.ConnectError:
            r = self.client.get(url, follow_redirects=False, **req_args)
            
        if r.status_code >= 300:
            return ""

        page = r.text

        if not target_word in page:
            return ""

        return page

    def get_start_url(self, target_word):
        params = {
            'q': f'"{target_word}"',
            'sourceid': 'chrome',
            'ie': 'UTF-8',
        }

        if self._sites_search_arg:
            params["q"] += " " + self._sites_search_arg

        if self.language:
            params["lr"] = "lang_"+self.language

        params["oq"] = params["q"]

        self.req.prepare_url("https://www.google.com/search", params)
        return self.req.url
