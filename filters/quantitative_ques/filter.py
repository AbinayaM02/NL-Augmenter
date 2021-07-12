import spacy
from interfaces.SentenceOperation import SentenceOperation
from tasks.TaskTypes import TaskType


class QuantitativeQuestion(SentenceOperation):
    tasks = [TaskType.QUESTION_ANSWERING, TaskType.QUESTION_GENERATION]
    languages = ["en"]

    def __init__(self):
        super().__init__()
        self.nlp = spacy.load("en_core_web_sm")

    def filter(self, sentence: str = None) -> bool:
        tokenized = self.nlp(sentence, disable=["parser", "tagger", "ner"])
        if 'how' == tokenized[0].text.lower() and tokenized[1].text.lower() in ['many','far','long','much','old']:
            return True
        else:
            return False



