import torch
from transformers import T5ForConditionalGeneration, T5Tokenizer

from interfaces.QuestionAnswerOperation import QuestionAnswerOperation
from tasks.TaskTypes import TaskType
import random

"""
The T5 model and code has been taken from https://huggingface.co/ramsrigouthamg/t5_paraphraser.

"""


class QuoraT5QaPairGenerator(QuestionAnswerOperation):
    tasks = [
        TaskType.TEXT_CLASSIFICATION,
        TaskType.TEXT_TO_TEXT_GENERATION
    ]
    languages = ["en"]
    heavy = True

    def __init__(self, seed=0, model_name="ramsrigouthamg/t5_paraphraser", max_len=256):
        super().__init__(seed)
        self.model = T5ForConditionalGeneration.from_pretrained(model_name)
        self.tokenizer = T5Tokenizer.from_pretrained(model_name)
        self.max_len = max_len
        self.num_return_sequences = 3
        torch.manual_seed(self.seed)
        random.seed(self.seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(self.seed)

    def generate(self, context: str, question: str, answers: [str]):

        text = "paraphrase: " + question + "</s>"
        encoding = self.tokenizer.encode_plus(text, padding="longest", return_tensors="pt")
        input_ids, attention_masks = encoding["input_ids"], encoding["attention_mask"]
        beam_outputs = self.model.generate(
            input_ids=input_ids, attention_mask=attention_masks,
            do_sample=True,
            max_length=256,
            top_k=120,
            top_p=0.98,
            early_stopping=True,
            num_return_sequences=self.num_return_sequences
        )
        unique_question_paraprases = []
        for beam_output in beam_outputs:
            sent = self.tokenizer.decode(beam_output, skip_special_tokens=True, clean_up_tokenization_spaces=True)
            if sent.strip() and sent.lower() != question.lower():
                unique_question_paraprases.append(sent)

        paraphrased_question = unique_question_paraprases[0] if len(unique_question_paraprases) > 0 else question

        return context, paraphrased_question, answers
