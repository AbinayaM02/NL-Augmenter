import random
import string
import numeric2word

from interfaces.SentenceOperation import SentenceOperation
from tasks.TaskTypes import TaskType

class NumericToWord(SentenceOperation):
    tasks = [
        TaskType.TEXT_CLASSIFICATION,
        TaskType.TEXT_TO_TEXT_GENERATION
    ]
    languages = ["en"]

    def __init__(self, seed=0):
        super().__init__(seed)

    def generate(self, sentence: str):
        pertubed = ""
        words = sentence.split()
        for word in words:
            if pertubed != "":
                pertubed += " "
            perturbed += numeric2word(word, seed=self.seed)
        return pertubed

# if __name__ == '__main__':
#     import json
#     # from TestRunner import convert_to_snake_case
#     tf = NumericToWord()
#     sentence = "Please buy me 20 apples"
#     test_cases = []
#     for sentence in ["Please buy me 20 apples",
#                     "The deadline is in 2020/01/02",
#                     "The deadline is in 2020/01",
#                     "The deadline is in Jan 2020",
#                     "Slow down, it\'s still 5:00",
#                     "Quick!, it\'s already 23:00",
#                     "This is 2020!",
#                     "My phone number is +1371893178",
#                     "My phone number is +6287822216501",
#                     "My phone number is 6287822216501",
#                     "The price is $300",
#                     "The price is 300$",
#                     "The price is USD300",
#                     "The price is 300USD",
#                     "The price is USD300!@#!"]:
#         test_cases.append({
#             "class": tf.name(),
#             "inputs": {"sentence": sentence}, "outputs": {"sentence": tf.generate(sentence)}}
#         )
#     json_file = {"type": "numeric_to_word", "test_cases": test_cases}
#     # json_file = {"type": convert_to_snake_case(tf.name()), "test_cases": test_cases}
#     print(json.dumps(json_file))

#     with open("test.json", "w") as out_file:
#         json.dump(json_file, out_file, indent=2, ensure_ascii=True)