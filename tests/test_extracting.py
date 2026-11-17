from word_corpus_builder.extractor import HTML_Indexer, extract
from lxml import etree
import pytest

@pytest.fixture
def target_string():
    return "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Cras posuere id augue vestibulum sollicitudin. Sed rhoncus lorem in odio pharetra suscipit. Vivamus tincidunt feugiat semper. Suspendisse porttitor condimentum sapien molestie cursus. Sed mauris risus, eleifend sed orci quis, hendrerit feugiat."

@pytest.fixture
def target_word():
    return "suscipit"

@pytest.fixture
def test_page():

    def test(html_page, target_word, expected_string, up_growth_factor=1, down_growth_factor=1):
        html = etree.HTML(html_page)
    
        elems = html.xpath(f"//*[contains(., '{target_word}') and not(.//*[contains(., '{target_word}')])]")
        assert len(elems) == 1
    
        found_str = extract(elems[0], target_word, 40,
                            up_growth_factor=up_growth_factor, down_growth_factor=down_growth_factor)
        assert expected_string == found_str

    return test

def test_plain_text(target_string, target_word, test_page):
    """Test the capability to parse in one go the text without moving by any element"""


    # at the beginning (element.text)
    html_page = "<html><p>"+target_string+"</p></html>"
    test_page(html_page, target_word, target_string)

    # test only that with -k argument
    # add addition method or function to parse for collecting from both sides

    # at the middle (sub_element.tail)
    html_page = "<html><p><i></i>"+target_string+"<i></i></p></html>"
    test_page(html_page, target_word, target_string)

    # at the end (element.tail)
    html_page = "<html><p><i></i>"+target_string+"</p></html>"
    test_page(html_page, target_word, target_string)

def test_spaces_around_tags(target_string, target_word, test_page):
    """Around end and start of blocks, triming spaces has to be different"""
    split_string = target_string.split()
    target_index, = [i for i, word in enumerate(split_string) if target_word in word]

    # Space after span tag
    elem_text = " ".join(split_string[:target_index+1])
    child_text = " ".join(split_string[target_index+1:])

    html_page = "<html><p>"+elem_text+"<span> "+child_text+"</span></p></html>"
    expected_string = elem_text + "<dn> " + child_text

    test_page(html_page, target_word, expected_string)

    # Space before span tag
    html_page = "<html><p>"+elem_text+" <span>"+child_text+"</span></p></html>"
    expected_string = elem_text + " <dn>" + child_text

    test_page(html_page, target_word, expected_string)

def test_children_elements(target_string, target_word, test_page):
    """Test any type of interaction with children elements text content"""
    split_string = target_string.split()
    target_index, = [i for i, word in enumerate(split_string) if target_word in word]

    # Text, half text inside next element
    elem_text = " ".join(split_string[:target_index+1])
    child_text = " ".join(split_string[target_index+1:])

    html_page = "<html><p>"+elem_text+"<span> "+child_text+"</span></p></html>"
    expected_string = elem_text + "<dn> " + child_text

    test_page(html_page, target_word, expected_string)

    # Text, half text inside next elements
    elem_text = " ".join(split_string[:target_index+1])

    quarter_3 = target_index + (len(split_string) - target_index) // 2
    child1_text = " ".join(split_string[target_index+1:quarter_3])
    child2_text = " ".join(split_string[quarter_3:])

    html_page = f"<html><p>{elem_text}<span> {child1_text}</span><span> {child2_text}</span></p></html>"
    test_page(html_page, target_word, expected_string)

    # Child Element tail, half text inside next elements
    elem_text = " ".join(split_string[:target_index+1])
    child_text = " ".join(split_string[target_index+1:])

    html_page = f"<html><p><span></span>{elem_text} <span>{child_text}</span></p></html>"
    expected_string = elem_text + " <dn>" + child_text
    test_page(html_page, target_word, expected_string)

    # At the child elem tail, half text inside element text, half at the end of element tail
    elem_text = " ".join(split_string[:target_index])
    child_text = " ".join(split_string[target_index+1:])

    html_page = f"<html><p>{elem_text}<span></span> {split_string[target_index]} <span></span>{child_text}</p></html>"
    expected_string = elem_text + f"<dn> {split_string[target_index]} <dn>" + child_text
    test_page(html_page, target_word, expected_string)

def test_parent_elements(target_string, target_word, test_page):
    """Test any type of interaction with parent element text content"""

    split_string = target_string.split()
    target_index, = [i for i, word in enumerate(split_string) if target_word in word]

    # Text inside parent element
    parent_text = " ".join(split_string[:target_index])
    elem_text = " ".join(split_string[target_index:])

    html_page = "<html><p>"+parent_text+"<span> "+elem_text+"</span></p></html>"
    expected_string = parent_text + "<up> " + elem_text

    test_page(html_page, target_word, expected_string)

    # Text in parent of parent
    parent_text = " ".join(split_string[:target_index-1])
    elem_text = " ".join(split_string[target_index-1:])

    html_page = "<html><p>"+parent_text+"<span><span> "+elem_text+"</span></span></p></html>"
    expected_string = parent_text + "<up><up> " + elem_text

    test_page(html_page, target_word, expected_string)

    # Text in parent text and tail
    parent_text = " ".join(split_string[:target_index])

    quarter_3 = target_index + (len(split_string) - target_index) // 2

    elem_text = " ".join(split_string[target_index:quarter_3])
    parent_tail = " ".join(split_string[quarter_3:])

    html_page = "<html><p>"+parent_text+"<span> "+elem_text+" </span>" + parent_tail + "</p></html>"
    expected_string = parent_text + "<up> " + elem_text + " " + parent_tail

    test_page(html_page, target_word, expected_string)

def test_zero_growth_factors(target_string, target_word, test_page):
    """Check text resting the same whether it goes to children or parent for zero grow factors"""
    split_string = target_string.split()
    target_index, = [i for i, word in enumerate(split_string) if target_word in word]

    # Text inside parent element
    parent_text = " ".join(split_string[:target_index])
    elem_text = " ".join(split_string[target_index:])

    html_page = "<html><p>"+parent_text+"<span> "+elem_text+"</span></p></html>"

    test_page(html_page, target_word, target_string, up_growth_factor=0, down_growth_factor=0)

def test_skip_token(target_string, target_word, test_page):
    """Check behavior with growth factors greater than 1, supposed to return skip"""

    split_string = target_string.split()
    target_index, = [i for i, word in enumerate(split_string) if target_word in word]

    # Text inside parent element
    parent_text = " ".join(split_string[:target_index])
    elem_text = " ".join(split_string[target_index:])

    html_page = "<html><p>"+parent_text+"<span> "+elem_text+"</span></p></html>"
    expected_string = parent_text + "<sk><up> " + elem_text

    test_page(html_page, target_word, expected_string, up_growth_factor=2)

def test_skipping_split_words(target_word, test_page):
    """Check whether the string is skipped if word is split between elements"""

    first_part = target_word[:1]
    second_part = target_word[1:]

    html_page = f"<html><p>{first_part}<span>{second_part}</span</p></html>"
    test_page(html_page, target_word, None)
