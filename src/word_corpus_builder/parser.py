from .browser import BrowserManager
from .fetcher import Fetcher
from .extractor import extract

from bs4 import BeautifulSoup
from lxml import etree
import json
import time

class Parser:
    """Abstract class for getting texts"""

    def __init__(self, texts_num=10, words_num=40, target_sites=None, sentence_start=False, multiple_repetitions=False, language=None) -> None:
        """
        Args:
            texts_num (int): number of texts per word
            words_num (int): target number of words around `word` in each text
            target_sites (list): a list of strings, where each string is domain
            sentence_start (bool): whether to include texts where `word` starts with capital letter
            multiple_repetitions (bool): whether to ignore repetitions of `word` in text
            language (string): double character string, to sort pages by their language
        """

        self.multiple_repetitions = multiple_repetitions
        self.sentence_start = sentence_start
        self.target_sites = target_sites
        self.language = language
        self.texts_num = texts_num
        self.words_num = words_num

    def parse(self, target_word):
        """
        Args:
            target_word (string): a word, which has to be in texts

        Returns:
            texts (list): a list of found texts containing a tuple `(text, source)`
                          where `source` is a link toward the page of text
        """
        raise Exception("Abstract class")


class GoogleParser(Parser):
    """Parser from Google search"""

    def __init__(self, wait_for_captcha_solved=False, **kwargs):
        super().__init__(**kwargs)

        self._bm = BrowserManager(wait_for_captcha_solved)
        self._bm.launch()

        request_args = self._bm.get_search_request_args()
        with open("res.json", "w") as f:
            json.dump(request_args, f)

        self.fetcher = Fetcher(
            target_sites=kwargs.get('target_sites', None),
            language=self.language,
            request_args=request_args
        )

    def close(self):
        self._bm.close()
        self.fetcher.close()

    @staticmethod
    def get_urls(html_page):
        """Returns the status of search, and urls if there are
    
        Returns:
            search_status (int): 
                0, if search was successful
                1, if search hasn't given any results
                2, if search wasn't authorized (mostly due cookie expires)
            urls (list): a list of urls to pages that search has found
        """
        next_link = ""
        if "having trouble accessing Google Search, please" in html_page:
            return 2, next_link, []

        with open("html_page_test.html", 'w') as f:
            f.write(html_page)

        soup = BeautifulSoup(html_page, 'html.parser')
        search_results = soup.find(id='search')
    
        if len(search_results.contents) == 0: # cannot find any content
            return 1, next_link, []
        
        links = [title.parent for title in search_results.select("a h3")]
        links += search_results.select("a[aria-hidden]")

        # URL to the next page | to test whether it's working solution | or it's necessary to change headers
        next_link = soup.find(id='pnnext')['href']
    
        return 0, next_link, [link['href'] for link in links]

    def get_texts(self, page, target_word):
        body = etree.HTML(page).find("body")
    
        elems = body.xpath(f".//*[contains(., '{target_word}') and not(.//*[contains(., '{target_word}')])]")
        if self.sentence_start:
            elems += body.xpath(f".//*[contains(., '{target_word.capitalize()}') and not(.//*[contains(., '{target_word.capitalize()}')])]")
    
        texts = []
        for elem in elems:
            text = extract(elem, target_word, self.words_num,
                                up_growth_factor=2, down_growth_factor=1)
            if text is not None:
                texts.append(text)

                if self.multiple_repetitions:
                    break

        return texts

    def parse(self, target_word):
        """
        Args:
            target_word (string): a word, which has to be in texts

        Returns:
            texts (list): a list of found texts containing a tuple `(url, url_texts)`
                          where `url_texts` are all parsed texts from `url` containing `target_word`
        """
        next_page_url = self.fetcher.get_start_url(target_word)

        texts_num = 0
        texts = []
        while texts_num < self.texts_num:
            r = self.fetcher.request(next_page_url)

            if r.status_code == 429:
                print('waiting for 30 seconds')
                time.sleep(300)
                return self.parse(target_word)

            elif r.status_code != 200:
                raise Exception("Error `status_code` "+str(r.status_code))

            code, next_page_url, page_urls = self.get_urls(r.text)
    
            if code == 2:
                if self._bm.check_expires_cookies():
                    _, cookies = self._bm.get_search_request_args()
                    self.fetcher.update_cookies(cookies)
    
                    return self.parse(target_word)
    
                raise Exception("Error with parsing urls, without a coherent precoded solution.")

            for goto_url in page_urls:
                page_url = self.fetcher.parse_goto(goto_url)

                if page_url is None:
                    continue

                page = self.fetcher.parse_text(page_url, target_word)
                if page == "":
                    request_args = self._bm.get_request_args(page_url)
                    page = self.fetcher.parse_text(page_url, target_word, request_args)

                    if page == "":
                        continue

                page_texts = self.get_texts(page, target_word)

                if len(page_texts) > 0:
                    texts_num += len(page_texts)
                    texts.append((page_url, page_texts))

            next_page_url = "https://www.google.com"+next_page_url

        return texts
