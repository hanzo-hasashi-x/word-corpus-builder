class Parser:

    def __init__(self, number=10, target_sites=None, sentence_start=False, multiple_repetitions=False, language=None) -> None:
        """
        Args:
            number (int): number of texts per word
            target_sites (list): a list of strings, where each string is domain
            sentence_start (bool): whether to include texts where `word` starts with capital letter
            multiple_repetitions (bool): whether to ignore texts with multiple appeareances
                                         of `word`
            language (string): double character string, to sort pages by their language
        """

        self.multiple_repetitions = multiple_repetitions
        self.sentence_start = sentence_start
        self.target_sites = target_sites
        self.language = language
        self.number = number

    def parse(self, target_word):
        """
        Args:
            target_word (string): a word, which has to be in texts

        Returns:
            texts (list): a list of found texts containing a tuple `(text, source)`
                          where `source` is a link toward the page of text
        """
        raise Exception("Abstract class")
