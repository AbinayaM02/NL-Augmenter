from interfaces.SentenceOperation import SentenceOperation
from tasks.TaskTypes import TaskType
import random
from spacy import load
from typing import List
from names import extract_names_genders


def is_candidate_word(word):
    """
    check a word is correct candidate word for identifying pronoun
    """
    discarded_words = ["a", "an", "the"] # can enhance this list
    if len(word)<=2 or word.lower() in discarded_words:
        return False
    return True


def extract_nsubj_phrase(parse):
    """
    extract phrase from nsubj subtree
    """
    nsubj_phrase = []
    for token in parse:
        if token.dep_ == "nsubj" and token.head.dep_ == "ROOT":
            nsubj_phrase.append(token.text)
        if token.head.dep_ == "nsubj" or token.head.head.dep_ == "nsubj":
            nsubj_phrase.append(token.text)
    return " ".join(nsubj_phrase)


def map_pronoun(word, male_names, female_names):
    """
    map word with male and females names, profession, title etc.
    """
    pronoun = ""
    if word in male_names or word.lower() in male_names:
        pronoun = "he"
    elif word in female_names or word.lower() in female_names:
        pronoun = "she"
    return pronoun


def fetch_corresponding_pronoun(nsubj_phrase, male_names, female_names):
    """
    Fetch pronoun of nsubj phrase
    """
    if nsubj_phrase.lower() in ["i", "you", "we", "he", "she", "they"]:
        return nsubj_phrase.lower()
    if len(nsubj_phrase.split(" ")) > 1:
        for ph in nsubj_phrase.split(" "): # if nsubj phrase contains multiple words.
            if is_candidate_word(ph):
                pronoun = map_pronoun(ph, male_names, female_names)
                if(pronoun != ""):
                    return pronoun
        return "they" # default pronoun
    else:
        return map_pronoun(nsubj_phrase)


def get_transformation(sentence, nlp, factive_verbs, non_factive_verbs, initial_verbs, male_names, female_names, seed):
    """
    transform a input sentence by adding factive verb
    """
    parse = nlp(sentence)
    nsubj_phrase = extract_nsubj_phrase(parse)
    pronoun = fetch_corresponding_pronoun(nsubj_phrase, male_names, female_names)
    random.seed(0)
    verb = random.choice(factive_verbs + non_factive_verbs) # pick random verb
    #initial_verb = random.choice(initial_verbs) # TODO:
    sentence = sentence.replace(nsubj_phrase, pronoun)
    return f"{nsubj_phrase} {verb} that, {sentence}"#, f"{nsubj} didn't {verb} that, {sentence}"


class FactiveVerbTransformation(SentenceOperation):
    tasks = [
        TaskType.TEXT_CLASSIFICATION,
        TaskType.TEXT_TO_TEXT_GENERATION,
        TaskType.SENTIMENT_ANALYSIS,
    ]
    languages = ["en"]

    def __init__(self, seed=1, max_outputs=1):
        super().__init__(seed, max_outputs=max_outputs)
        self.nlp = load('en_core_web_sm')
        self.initial_verbs = ["", "have to", "has to", "need to"] # TODO: use this in next push after discussion
        #TODO: we can add third person variation like (after discussion)
        # "Peter published a research paper. => John revealed that, Peter published a research paper."
        self.male_names, self.female_names = extract_names_genders()
        self.factive_verbs = ["accept", "accepts", "accepted",
                              "establish", "establishes", "established",
                              "note", "notes", "noted",
                              "reveal", "reveals", "revealed",
                              "acknowledge","acknowledges", "acknowledged",
                              "explain", "explains", "explained",
                              "observe", "observes", "observed",
                              "see", "saw", "seen",
                              "know", "knows", "knew",
                              "prove", "proves", "proved",
                              "show", "shows", "showed",
                              "demonstrate", "demonstrates","demonstrated",
                              "learn", "learns", "learnt",
                              "recognise", "recognises", "recognised",
                              "inform", "informs", "informed",
                              "understand", "understands", "understood"
                              "confirm", "confirms", "confirmed"] # more verbs can be added
        self.non_factive_verbs = ["argue", "argues", "argued",
                                  "doubt", "doubts", "doubted",
                                  "hypothesise", "hypothesises", "hypothesised",
                                  "recommend", "recommends", "recommended",
                                  "assume", "assumes", "assumed",
                                  "estimate", "estimates", "estimated",
                                  "imply", "implies", "implied",
                                  "suggest", "suggests", "suggested",
                                  "believe", "believes", "believed",
                                  "expect", "expects", "expected",
                                  "predict", "predicts", "predicted",
                                  "suspect", "suspects", "suspected",
                                  "claim", "claims", "claimed",
                                  "foresee", "foresaw", "foreseen",
                                  "presume", "presumes", "presumed",
                                  "think", "thinks", "thought"]

    def generate(self, sentence: str) -> List[str]:
        transformed_sentences = []
        for _ in range(self.max_outputs):
            transformed_sentence = get_transformation(sentence, self.nlp,
                                                    self.factive_verbs, self.non_factive_verbs,
                                                    self.initial_verbs, self.male_names,
                                                    self.female_names, self.seed)
            transformed_sentences.append(transformed_sentence)
        return transformed_sentences


# if __name__ == "__main__":
#     import json
#     from TestRunner import convert_to_snake_case
#
#     tf = FactiveVerbTransformation()
#     test_cases=[]
#     input_sent = ["He killed a street dog yesterday.",
#                   "An actress made her debut in hollywood.",
#                   "John Watson was enjoying the summer in Baker street.",
#                   "The lady doctor made a huge mistake during the operation.",
#                   "Mr. Harry T. Potter won the Quidditch championship.",
#                   "A small group of researchers found a new variant of Coivd-19."]
#     for i, sentence in enumerate(input_sent):
#         transformed_sentence = tf.generate(sentence)
#         test_cases.append({
#             "class": tf.name(),
#             "inputs": {"sentence": sentence},
#             "outputs": [],}
#         )
#         for trans_sentence in transformed_sentence:
#             test_cases[i]["outputs"].append({"sentence":trans_sentence})
#     json_file = {"type":convert_to_snake_case("factive_verb_transformation"),
#                  "test_cases": test_cases}
#     print(json.dumps(json_file))
#     # for ip in input_sent:
#     #     print(ip)
#     #     trans_sent = tf.generate(ip)
#     #     print(trans_sent)
