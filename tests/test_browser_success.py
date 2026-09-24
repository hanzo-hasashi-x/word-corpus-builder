import pytest
from subprocess import Popen
from word_corpus_builder.chrome import BrowserManager


@pytest.fixture(scope="module")
def browser_manager():
    """Maintain one instance of `BrowserManager` per module.
    """
    return BrowserManager()


def test_launch(browser_manager):
    """Test whether Chrome process isn't closed and all connection objects are working
    """
    browser_manager.launch()

    assert isinstance(browser_manager.proc, Popen)
    assert browser_manager.proc.poll() is None

    assert browser_manager.browser.is_connected()
    assert not browser_manager.context.is_closed()

def test_request_args(browser_manager):
    """Test whether all required for further request cookies and headers are present.

    Tests also the header listerner setter method (getting headers means it works).
    """
    cookies, headers = browser_manager.get_request_args()
    input("Tes")

    # test cookies by choosing the required ones
    cookies_required = ['SNID', 'AEC', 'SEARCH_SAMESITE', 'DV', '__Secure-STRP']
    for cookie in cookies_required:
        assert cookie in cookies

    # test headers by looking at the required ones
    headers_required = ['upgrade-insecure-requests', 'downlink', 'rtt', 'sec-ch-prefers-color-scheme', 
        'sec-ch-ua', 'sec-ch-ua-arch', 'sec-ch-ua-bitness', 'sec-ch-ua-form-factors', 'sec-ch-ua-full-version', 
        'sec-ch-ua-full-version-list', 'sec-ch-ua-mobile', 'sec-ch-ua-model', 'sec-ch-ua-platform', 'sec-ch-ua-platform-version',
        'sec-ch-ua-wow64']

    for header in headers_required:
        assert header in headers

def test_close(browser_manager):
    """Test whether closing, actually closes Chrome process and connection objects.
    """
    browser_manager.close()

    assert browser_manager.proc.poll() is not None

    assert not browser_manager.browser.is_connected()
    assert browser_manager.context.is_closed()
