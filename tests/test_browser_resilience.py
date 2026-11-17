import pytest
import shutil
from unittest.mock import patch

from word_corpus_builder.browser import (BrowserManager, PROFILE_DIR,
                                         BrowserNotOpeningException, PermanentCaptchaException)

@pytest.fixture()
def browser_manager():
    """Maintain one instance of `BrowserManager` per module.
    """
    return BrowserManager()


def test_captcha(browser_manager):
    original_method = BrowserManager.launch

    def delete_profile(self):
        """Starting with new profile sometimes leads to appeareance of ReCAPTCHA
        """
        shutil.rmtree(PROFILE_DIR)
        original_method(self)

    with patch.object(BrowserManager, "launch", delete_profile):
        browser_manager.launch()

        with pytest.raises(PermanentCaptchaException):
            browser_manager.get_search_request_args()

            # this exception is hugely depends on IP address of testing machine
            raise PermanentCaptchaException()

    browser_manager.close()

def test_browser_not_opening(browser_manager):
    browser_manager.launch()

    with pytest.raises(BrowserNotOpeningException):
        browser_manager.launch()

    browser_manager.close()
