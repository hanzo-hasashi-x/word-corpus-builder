from word_corpus_builder.parser import GoogleParser
import re

def test_parse():
    texts_num = 10
    target_word = "lorem"

    p = GoogleParser(texts_num=texts_num)
    results = p.parse(target_word) 

    p.close()

    assert len(results) > 0

    texts = [text for _, texts in results for text in texts]
    assert len(texts) >= texts_num

    for text in texts:
        assert target_word in text.lower()

    for url, _ in results:
        domain = re.match(r"(https?://)([^/:?#]+)", url)
        assert domain is not None
