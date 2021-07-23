import os
import random
import re

import nltk
from nltk.tokenize.treebank import TreebankWordDetokenizer

from interfaces.SentenceOperation import SentenceOperation
from tasks.TaskTypes import TaskType


def get_(big_list, small_list):
    big_str = " ".join(big_list)
    small_str = " ".join(small_list)

    big_str.index(small_str)


"""
Base Class for implementing the different input transformations a generation should be robust against.
"""


class ColorTransformation(SentenceOperation):
    tasks = [
        TaskType.TEXT_CLASSIFICATION,
        TaskType.TEXT_TO_TEXT_GENERATION,
        TaskType.TEXT_TAGGING,
    ]
    languages = ["en"]

    def __init__(self, seed=0, max_outputs=1):
        super().__init__(seed, max_outputs=max_outputs)
        self.load_color_names()
        self.detokenizer = TreebankWordDetokenizer()

    def load_color_names(self):
        self.color_names = []

        filepath = os.path.realpath(
            os.path.join(
                os.getcwd(), os.path.dirname(__file__), "color_names.txt"
            )
        )

        with open(filepath, "r") as f:
            for line in f.readlines():
                line = line.strip()
                line = re.sub(r"(?<!^)(?=[A-Z])", " ", line).lower()
                self.color_names.append(line)

    def generate(self, sentence: str):
        random.seed(self.seed)

        try:
            words = nltk.word_tokenize(sentence)
        except LookupError:
            nltk.download("punkt")
            words = nltk.word_tokenize(sentence)
        sentence = self.detokenizer.detokenize(words)

        indices = []
        for color in self.color_names:
            try:
                idx = sentence.index(color)
            except ValueError:
                continue
            indices.append((idx, idx + len(color)))

        new_sentences = []
        for _ in range(self.max_outputs):
            new_sentence = sentence
            for start_idx, end_idx in indices[::-1]:
                new_sentence = (
                    new_sentence[:start_idx]
                    + random.choice(self.color_names)
                    + new_sentence[end_idx:]
                )
            new_sentences.append(new_sentence)

        return new_sentences
