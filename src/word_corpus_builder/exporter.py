import csv

def write(filename, texts):

    with open(filename, 'w', newline="", encoding="utf-8") as csvfile:
        texts_writer = csv.writer(csvfile, quoting=csv.QUOTE_MINIMAL)
        texts_writer.writerow(("url", "text"))

        for url, url_texts in texts:
            for text in url_texts:
                texts_writer.writerow((url, text))
