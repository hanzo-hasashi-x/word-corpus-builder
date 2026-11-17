import re
import math
from copy import copy

from collections import deque

def extract(target_elem, target_word, words_num, up_growth_factor=1, down_growth_factor=1):
    # target_elem = soup.find(text=target_word)
    
    right_indexer = HTML_Indexer.get_indexer(target_elem, target_word, 
                                             up_growth_factor, down_growth_factor)
    if right_indexer is None:
        return
    left_indexer = right_indexer.get_reverse()

    start_word = right_indexer.get_trim_word()
    if start_word is None:
        return

    words = deque()
    words.append(start_word)

    possible_tags = ("<up>", "<sk>", "<dn>")

    # Whether both start and end of html are reached
    start, end = False, False

    n = 1
    while n < words_num and not (start and end):
        if not start:
            left_word = left_indexer.step()
            if left_word == '<start>':
                start = True
            else:
                words.appendleft(left_word)
        
                if not left_word in possible_tags:
                    n += 1
        
                if n == words_num:
                    break

        if not end:
            right_word = right_indexer.step()
            if right_word == "<end>":
                end = True
            else:
                words.append(right_word)
        
                if not right_word in possible_tags:
                    n += 1

    # skip first tags
    n = 0
    for word in words:
        if word in possible_tags:
            n+=1
            continue
        break

    for _ in range(n):
        words.popleft()

    # skip last tags
    n = 0
    for word in reversed(words):
        if word in possible_tags:
            n+=1
            continue
        break

    for _ in range(n):
        words.pop()

    return "".join(tuple(words))

class HTML_Indexer:

    def __init__(self, curr_index, context_stack, up_growth_factor, down_growth_factor, direction) -> None:
        self.up_growth = up_growth_factor
        self.down_growth = down_growth_factor

        self.direction = direction

        self.context_stack = deque()
        for context in context_stack:
            self.context_stack.append(context)

        self.down_flag = True
        if context_stack[-1][1] == 'tail':
            self.down_flag = False

        self.curr_text = self.form_curr_text(*context_stack[-1])
        self.curr_index = curr_index

        self.skip = 0

    def prev(self):
        self.curr_index -= 1

        if self.curr_index >= 0:
            return self.curr_text[self.curr_index]

        while self.context_stack:
            # invariant: we always start with curr elem that doesn't have any text
            # invariant ensured at the end of the loop
            curr_elem, belongs = self.context_stack.pop()

            action = None
            if belongs == 'tail':
                if len(curr_elem) == 0:
                    self.context_stack.append((curr_elem, 'text'))

                    if not self.down_flag:
                        self.down_flag = True
                        action = '<dn>'

                else:
                    last_index = len(curr_elem)-1

                    self.context_stack.append((curr_elem, last_index))
                    self.context_stack.append((curr_elem[last_index], 'tail'))

                    action = "<dn>"

            elif belongs == 'text':
                if not self.context_stack:
                    parent_elem = curr_elem.getparent()
                    if parent_elem is None:
                        return '<start>'
                    self.context_stack.append((parent_elem, parent_elem.index(curr_elem)))

                    action = "<up>"

                curr_elem, index = self.context_stack.pop() 
                prev_index = index - 1
                if prev_index < 0:
                    # go by upper element
                    self.context_stack.append((curr_elem, 'text'))

                else:
                    self.context_stack.append((curr_elem, prev_index))
                    self.context_stack.append((curr_elem[prev_index], 'tail'))

            else:
                raise Exception(f'Unexisting state of context: "{belongs}"')

            curr_text = self.form_curr_text(*self.context_stack[-1])
            if (action == '<dn>' and self.down_growth > 0) or (action == '<up>' and self.up_growth > 0):
                self.curr_text = curr_text
                self.curr_index = len(curr_text) # start with zero, at next `next` execution

                return action

            if len(curr_text) > 0:
                self.curr_text = curr_text
                self.curr_index = len(curr_text) - 1

                return curr_text[self.curr_index]

    def next(self):
        self.curr_index += 1

        if self.curr_index < len(self.curr_text):
            return self.curr_text[self.curr_index]

        # take left sibling, go up
        self.curr_index = 0

        while self.context_stack:
            # invariant (accross `step` execution & sibling iteration): curr elem that doesn't have any text
            # invariant checked at the beginning of function & at the end
            curr_elem, belongs = self.context_stack.pop()

            action = None
            if belongs == 'text':
                if len(curr_elem) == 0:
                    self.context_stack.append((curr_elem, 'tail'))

                else:
                    self.context_stack.append((curr_elem, 0))
                    self.context_stack.append((curr_elem[0], 'text'))

                    action = "<dn>"

            elif belongs == 'tail':
                if not self.context_stack:
                    parent_elem = curr_elem.getparent()
                    if parent_elem is None:
                        return '<end>'
                    self.context_stack.append((parent_elem, parent_elem.index(curr_elem)))

                    action = "<up>"

                curr_elem, index = self.context_stack.pop() 
                next_index = index + 1
                if next_index == len(curr_elem):
                    # go by upper element
                    self.context_stack.append((curr_elem, 'tail'))

                else:
                    self.context_stack.append((curr_elem, next_index))
                    self.context_stack.append((curr_elem[next_index], 'text'))

                    if not self.down_flag:
                        self.down_flag = True
                        action = '<dn>'

            else:
                raise Exception(f'Unexisting state of context: "{belongs}"')

            curr_text = self.form_curr_text(*self.context_stack[-1])
            if (action == '<dn>' and self.down_growth > 0) or (action == '<up>' and self.up_growth > 0):
                self.curr_text = curr_text
                self.curr_index = -1 # start with zero, at next `next` execution

                return action

            if len(curr_text) > 0:
                self.curr_text = curr_text
                return curr_text[self.curr_index]


    def step(self):
        if self.skip > 0:
            self.skip -= 1
            return '<sk>'

        value = self.next() if self.direction == 'right' else self.prev()

        if value == '<up>' and self.up_growth > 1:
            self.skip = self.up_growth - 1

        elif value == '<dn>' and self.down_growth > 1:
            self.skip = self.down_growth - 1

        return value

    def get_trim_word(self):
        regexp = r'\w+' # trim from both sides
        if self.curr_index == len(self.curr_text)-1:
            regexp += r'\W*' # trim from left side
        if self.curr_index == 0:
            regexp = r'\W*' + regexp # trim from right side
        match = re.search(regexp,self.curr_text[self.curr_index])

        if match is None:
            return ""

        return match.group(0)

    def form_curr_text(self, curr_elem, belongs):
        text = curr_elem.text if belongs == 'text' else curr_elem.tail

        if text is None:
            return []

        words = re.split(r'(\W+)', text)
        if words[0] == '':
            words[2] = words[1] + words[2]
            words = words[2:]

        if words[-1] == '':
            words[-3] = words[-3] + words[-2]
            words = words[:-2]

        if self.direction == 'left':
            curr_text = []
            for i in range(0, len(words)-2, 2):
                curr_text.append( words[i] + words[i+1] )
            curr_text.append(words[-1])

        else:
            curr_text = words[:1]
            for i in range(1, len(words), 2):
                curr_text.append( words[i] + words[i+1] )

        return curr_text

    def get_reverse(self):
        return HTML_Indexer(self.curr_index, copy(self.context_stack), 
                            self.up_growth, self.down_growth, 'left')

    @staticmethod
    def get_indexer(element, target_word, up_growth_factor=1, down_growth_factor=1):
        words = []
        words_belongs = []

        def aux_add(text, belongs):
            nonlocal words, words_belongs

            if text is None:
                return

            sub_words = re.split(r'\W+', text)

            if sub_words[0] == "":
                sub_words = sub_words[1:]
            if sub_words[-1] == "":
                sub_words = sub_words[:-1]

            if len(sub_words) == 0:
                return

            words += sub_words
            words_belongs += [belongs] * len(sub_words)

        aux_add(element.text, 'text')

        for i, sub_elem in enumerate(element):
            aux_add(sub_elem.tail, i)
    
        # find closest occurence of `target_word` to middle
        middle = math.floor(len(words) / 2)
        n = len(words)
    
        f1 = None
        for i in range(middle+1):
            index = middle - i
            if words[index].lower() == target_word:
                f1 = index
                break

            index = middle + i
            # skip  there has to be at least one occurence
            if (index < n) and words[index].lower() == target_word:
                f1 = index
                break
        else:
            return
            # raise Exception(f'No word "{target_word}" occurence in `element`')
    
        belongs = words_belongs[f1]
        if belongs == 'text':
            context_stack = [[element, belongs]]
        else:
            context_stack = [[element, belongs], [element[belongs], "tail"]]

        f1 = f1 - words_belongs.index(belongs)
        return HTML_Indexer(f1, context_stack, 
                            up_growth_factor, down_growth_factor, 'right')
