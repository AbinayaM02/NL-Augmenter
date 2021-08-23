from interfaces.SentencePairOperation import SentencePairOperation
from tasks.TaskTypes import TaskType
from transformations.decontextualize_sentence.decontextualizer import decontextualize_text


class Decontextualize(SentencePairOperation):
    tasks = [
        TaskType.TEXT_CLASSIFICATION,
        TaskType.TEXT_TO_TEXT_GENERATION,
        TaskType.TEXT_TAGGING,
        TaskType.TEXTUAL_ENTAILMENT
    ]
    languages = ["en"]

    def __init__(self, seed=0, max_outputs=3):
        super().__init__(seed, max_outputs=max_outputs)
        from allennlp.predictors.predictor import Predictor
        self.predictor = Predictor.from_path(
            "https://storage.googleapis.com/allennlp-public-models/structured-prediction-srl-bert.2020.12.15.tar.gz"
        )

    def generate(self, sentence1: str, sentence2: str, target: str):

        srl = self.predictor.predict(sentence=sentence2)

        verbs_list = srl["verbs"]
        decon_texts = []

        for verb in verbs_list:
            general_sen = decontextualize_text(verb, srl["words"])
            if general_sen not in decon_texts:
                if general_sen != " ".join(srl["words"]):
                    decon_texts.append((sentence1, general_sen, target))

        if not decon_texts:
            decon_texts.append((sentence1, sentence2, target))

        if len(decon_texts) > self.max_outputs:
            decon_texts = decon_texts[:self.max_outputs]


        return decon_texts


if __name__ == '__main__':
    sentence1 = "American Airlines began laying off hundreds of flight attendants on Tuesday, after a federal judge turned aside a union’s bid to block the job losses"
    sentence2 = "American Airlines will recall hundreds of flight attendants as it steps up the number of flights it operates"
    label = "Contradiction"
    decon = Decontextualize()
    print(decon.generate(sentence1, sentence2, label))


"""
# Sample code to demonstrate usage. Can also assist in adding test cases.
# You don't need to keep this code in your transformation.
if __name__ == '__main__':
    import json
    from TestRunner import convert_to_snake_case

    tf = ButterFingersPerturbation(max_outputs=3)
    sentence = "Andrew finally returned the French book to Chris that I bought last week"
    test_cases = []
    for sentence in ["Andrew finally returned the French book to Chris that I bought last week",
                     "Sentences with gapping, such as Paul likes coffee and Mary tea, lack an overt predicate to indicate the relation between two or more arguments.",
                     "Alice in Wonderland is a 2010 American live-action/animated dark fantasy adventure film",
                     "Ujjal Dev Dosanjh served as 33rd Premier of British Columbia from 2000 to 2001",
                     "Neuroplasticity is a continuous processing allowing short-term, medium-term, and long-term remodeling of the neuronosynaptic organization."]:
        test_cases.append({
            "class": tf.name(),
            "inputs": {"sentence": sentence}, "outputs": [{"sentence": o} for o in tf.generate(sentence)]}
        )
    json_file = {"type": convert_to_snake_case(tf.name()), "test_cases": test_cases}
    print(json.dumps(json_file))
"""
