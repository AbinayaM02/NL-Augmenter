import random
from functools import partial

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from transformers import GPT2LMHeadModel, GPT2Tokenizer

from interfaces.SentenceOperation import SentenceOperation
from tasks.TaskTypes import TaskType

"""
    Note: This codebase is based upon and adapted from code
    from this repository:
    https://github.com/martiansideofthemoon/style-transfer-paraphrase

"""


MODELS_SUPPORTED = {
    "Bible": "filco306/gpt2-bible-paraphraser",
    "Basic": "filco306/gpt2-base-style-paraphraser",
    "Shakespeare": "filco306/gpt2-shakespeare-paraphraser",
    "Tweets": "filco306/gpt2-tweet-paraphraser",
    "Switchboard": "filco306/gpt2-switchboard-paraphraser",
    "Romantic poetry": "filco306/gpt2-romantic-poetry-paraphraser",
}

MAX_PARAPHRASE_LENGTH = 100

BASE_CONFIG = {
    "keys": [
        {
            "key": "sent1_tokens",
            "position": 3,
            "tokenize": True,
            "metadata": False,
        },
        {
            "key": "sent2_tokens",
            "position": 4,
            "tokenize": True,
            "metadata": False,
        },
        {
            "key": "f1_score",
            "position": 5,
            "tokenize": False,
            "metadata": True,
        },
        {
            "key": "kt_score",
            "position": 6,
            "tokenize": False,
            "metadata": True,
        },
        {
            "key": "ed_score",
            "position": 7,
            "tokenize": False,
            "metadata": True,
        },
        {"key": "langid", "position": 8, "tokenize": False, "metadata": True},
    ],
    "max_total_length": MAX_PARAPHRASE_LENGTH,
    "max_prefix_length": int(MAX_PARAPHRASE_LENGTH / 2),
    "max_suffix_length": int(MAX_PARAPHRASE_LENGTH / 2),
    "max_dense_length": 2,
}


TRAIN_ARGS = {
    "filco306/gpt2-base-style-paraphraser": {
        "do_lower_case": False,
        "global_dense_feature_list": "none",
    },
    "filco306/gpt2-shakespeare-paraphraser": {
        "do_lower_case": False,
        "global_dense_feature_list": "none",
    },
    "filco306/gpt2-bible-paraphraser": {
        "do_lower_case": False,
        "global_dense_feature_list": "none",
    },
    "filco306/gpt2-tweet-paraphraser": {
        "do_lower_case": False,
        "global_dense_feature_list": "none",
    },
    "filco306/gpt2-switchboard-paraphraser": {
        "do_lower_case": False,
        "global_dense_feature_list": "none",
    },
    "filco306/gpt2-romantic-poetry-paraphraser": {
        "do_lower_case": False,
        "global_dense_feature_list": "none",
    },
}


class GPT2ParentModule(nn.Module):
    """
    Parent module for the GPT2 model.

    """

    def __init__(self, args, gpt2):
        super(GPT2ParentModule, self).__init__()
        self.args = args
        self.gpt2 = gpt2

    def forward(self, batch):
        args = self.args
        gpt2 = self.gpt2

        sentences = batch["sentence"].to(args["device"])
        labels = batch["label"].to(args["device"])
        segments = batch["segment"].to(args["device"])

        # if args["global_dense_feature_list"] == "none":
        prefix_input_vectors = None

        gpt2.train()
        if prefix_input_vectors is None:
            outputs = gpt2(
                input_ids=sentences, token_type_ids=segments, labels=labels
            )
        else:
            outputs = gpt2(
                input_ids=sentences,
                token_type_ids=segments,
                labels=labels,
                prefix_input_vectors=prefix_input_vectors,
            )

        loss = {"lm": outputs[0]}

        return loss

    def evaluate(self, batch):
        args = self.args

        sentences = batch["sentence"].to(args["device"])
        labels = batch["label"].to(args["device"])
        segments = batch["segment"].to(args["device"])

        prefix_input_vectors = None

        with torch.no_grad():
            if prefix_input_vectors is None:
                outputs = self.gpt2(
                    input_ids=sentences, token_type_ids=segments, labels=labels
                )
            else:
                outputs = self.gpt2(
                    input_ids=sentences,
                    token_type_ids=segments,
                    labels=labels,
                    prefix_input_vectors=prefix_input_vectors,
                )
            lm_loss = outputs[0]

        return lm_loss.mean().item()


def _beam_search(
    model,
    length,
    context,
    segments,
    eos_token_id,
    beam_size: int = 1,
    beam_search_scoring="normalize",
):
    """
    Performs a beam search.

    Args:
        model: The GPT2-model loaded and used.
        length: The length of the desired output.
        context: The sentence encoded, for which we generate output.
        segments: The segments of the context.
        eos_token_id: The id of the end of sentence token.
        beam_size: The size of the beam.
        beam_search_scoring: The scoring function to use. If set to "normalize" (which is default), the score is normalized.
    """

    def merge_pasts(all_beams, prev_past):
        past_indices = [
            beam["past"] for element in all_beams for beam in element
        ]
        return [pp[:, past_indices, :, :, :] for pp in prev_past]

    def merge_input_ids(all_beams):
        input_ids = [
            beam["sequence"][-1] for element in all_beams for beam in element
        ]
        return torch.cat(input_ids, dim=0)

    if beam_search_scoring == "normalize":
        __score_fn = partial(_score_fn, length_normalize=True)
    else:
        __score_fn = partial(_score_fn, length_normalize=False)

    if length is None:
        new_length = 1024 - context.shape[1]
    else:
        new_length = length

    with torch.no_grad():

        logits, past = model(input_ids=context, token_type_ids=segments)

        log_probs = F.log_softmax(logits[:, -1, :], dim=-1)
        top_scores, top_indices = torch.topk(
            input=log_probs, k=beam_size, dim=-1
        )

        all_beams = []
        for elem_num, (ts, ti) in enumerate(zip(top_scores, top_indices)):
            curr_element = []
            for bs in range(beam_size):
                curr_element.append(
                    {
                        "score": ts[bs],
                        "past": elem_num,
                        "sequence": [
                            x.unsqueeze(0).unsqueeze(0)
                            for x in context[elem_num]
                        ]
                        + [ti[bs].unsqueeze(0).unsqueeze(0)],
                        "eos_emitted": False,
                    }
                )
            all_beams.append(curr_element)

        # one time step here since segment IDs remain constant during generation
        tiled_segments = torch.cat(
            [segments[:, -1:] for _ in range(beam_size)], dim=-1
        )

        for _ in range(1, new_length):
            # check if all beams have emitted an EOS token
            all_eos = all(
                [
                    beam["eos_emitted"]
                    for element in all_beams
                    for beam in element
                ]
            )
            if all_eos:
                break

            latest_input_ids = merge_input_ids(all_beams)
            past = merge_pasts(all_beams, past)

            logits, past = model(
                input_ids=latest_input_ids,  # input_ids[:, -1:],
                token_type_ids=tiled_segments,
                past=past,
            )
            log_probs = F.log_softmax(logits[:, -1, :], dim=-1)
            top_scores, top_indices = torch.topk(
                input=log_probs, k=beam_size, dim=-1
            )

            new_beams = []
            curr_element = []
            for mb_num, (ts, ti) in enumerate(zip(top_scores, top_indices)):
                current_elem_num = mb_num // beam_size
                current_elem_beam_num = mb_num % beam_size
                old_beam = all_beams[current_elem_num][current_elem_beam_num]

                if old_beam["eos_emitted"]:
                    curr_element.append(old_beam)
                else:
                    for bs in range(beam_size):
                        token = ti[bs].unsqueeze(0).unsqueeze(0)
                        curr_element.append(
                            {
                                "score": old_beam["score"] + ts[bs],
                                "past": mb_num,
                                "sequence": old_beam["sequence"] + [token],
                                "eos_emitted": token.item() == eos_token_id,
                            }
                        )
                if current_elem_beam_num == beam_size - 1:
                    new_beams.append(curr_element)
                    curr_element = []

            # Sort the beams by score and keep only top scoring elements
            all_beams = []
            for elem in new_beams:
                elem.sort(key=lambda x: __score_fn(x), reverse=True)
                all_beams.append(elem[:beam_size])

        final_beams = []
        for elem in all_beams:
            elem.sort(key=lambda x: __score_fn(x), reverse=True)
            # just return the highest scoring prediction
            final_beams.append(elem[:1])

        final_input_ids = [
            torch.cat(elem[0]["sequence"], dim=1).squeeze(0)
            for elem in final_beams
        ]

        return final_input_ids, [__score_fn(fb[0]) for fb in final_beams]


def _generate(
    gpt2_sentences,
    model,
    args,
    segments,
    init_context_size=1,
    eos_token_id=None,
    top_p=None,
):
    """
    Generate a paraphrased sentence.

    Args:
        gpt2_sentences: The sentences to generate paraphrases for.
        model: The model to use.
        args: The default configuration arguments.
    """
    gpt2 = model

    generation_length = (
        None
        if args["stop_token"] == "eos"
        else len(gpt2_sentences[0]) - init_context_size
    )
    dense_length = 0

    if args["beam_size"] > 1:
        out, scores = _beam_search(
            model=gpt2,
            length=generation_length,
            context=gpt2_sentences[:, 0:init_context_size],
            segments=segments[:, 0 : dense_length + init_context_size],
            eos_token_id=eos_token_id,
            beam_size=args["beam_size"],
            beam_search_scoring=args["beam_search_scoring"],
        )
    else:
        out, scores = _sample_sequence(
            model=gpt2,
            context=gpt2_sentences[:, 0:init_context_size],
            segments=segments[:, 0 : dense_length + init_context_size],
            eos_token_id=eos_token_id,
            length=generation_length,
            temperature=args["temperature"],
            top_k=args["top_k"],
            top_p=top_p or args["top_p"],
            get_scores=True,
        )
    return out, dense_length, scores


def _top_k_top_p_filtering(
    logits, top_k=0, top_p=0.0, filter_value=-float("Inf")
):
    """Filter a distribution of logits using top-k and/or nucleus (top-p) filtering
    Args:
        logits: logits distribution shape (batch size x vocabulary size)
        top_k > 0: keep only top k tokens with highest probability (top-k filtering).
        top_p > 0.0: keep the top tokens with cumulative probability >= top_p (nucleus filtering).
            Nucleus filtering is described in Holtzman et al. (http://arxiv.org/abs/1904.09751)
    From: https://gist.github.com/thomwolf/1a5a29f6962089e871b94cbd09daf317
    """
    top_k = min(top_k, logits.size(-1))  # Safety check
    if top_p > 0.0:
        sorted_logits, sorted_indices = torch.sort(logits, descending=True)
        cumulative_probs = torch.cumsum(
            F.softmax(sorted_logits, dim=-1), dim=-1
        )
        # Remove tokens with cumulative probability above the threshold
        sorted_indices_to_remove = cumulative_probs > top_p
        # Shift the indices to the right to keep also the first token above the threshold
        sorted_indices_to_remove[..., 1:] = sorted_indices_to_remove[
            ..., :-1
        ].clone()
        sorted_indices_to_remove[..., 0] = 0

        # scatter sorted tensors to original indexing
        indices_to_remove = sorted_indices_to_remove.scatter(
            dim=1, index=sorted_indices, src=sorted_indices_to_remove
        )
        logits[indices_to_remove] = filter_value

    elif top_k > 0:
        # Remove all tokens with a probability less than the last token of the top-k
        indices_to_remove = (
            logits < torch.topk(logits, top_k)[0][..., -1, None]
        )
        logits[indices_to_remove] = filter_value

    return logits


def _get_logits(model, iteration, generated, segments, past):
    """
    Compute logits.

    Args:
        model: GPT2 model
        iteration: current iteration
    """
    if iteration == 0:
        pred = model(
            input_ids=generated, token_type_ids=segments, return_dict=True
        )
    else:
        # used the cached representations to speed up decoding
        pred = model(
            input_ids=generated[:, -1:],
            token_type_ids=segments[:, -1:],
            past_key_values=past,
            return_dict=True,
        )
    logits = pred["logits"]
    past = pred["past_key_values"]
    return logits, past


def _sample_sequence(
    model,
    length: int,
    context: torch.Tensor,
    segments,
    eos_token_id,
    temperature: float = 1.0,
    top_k: int = 0,
    top_p: int = 0.0,
    get_scores: bool = False,
):
    """
    Samples a sequence of a given length from a given context.

    Args:
        model: model to use to sample (the GPT2 model)
        length: length of the sequence to sample


    """

    if length is None:
        new_length = 1024 - context.shape[1]
    else:
        new_length = length

    batch_size = context.shape[0]

    eos_emitted = [False for _ in range(batch_size)]

    generated = context
    scores = [{"score": 0, "sequence": []} for _ in range(batch_size)]

    with torch.no_grad():
        past = None
        for i in range(new_length):
            logits, past = _get_logits(model, i, generated, segments, past)

            next_token_logits = logits[:, -1, :] / (
                temperature if temperature > 0 else 1.0
            )
            original_scores = F.log_softmax(next_token_logits, dim=-1)

            filtered_logits = _top_k_top_p_filtering(
                next_token_logits, top_k=top_k, top_p=top_p
            )
            if temperature == 0 and top_k in [0, 1] and top_p == 0.0:
                # greedy sampling
                next_token = torch.argmax(filtered_logits, dim=-1).unsqueeze(
                    -1
                )
            else:
                next_token = torch.multinomial(
                    F.softmax(filtered_logits, dim=-1), num_samples=1
                )

            if get_scores:
                for batch_elem in range(batch_size):
                    if eos_emitted[batch_elem]:
                        continue
                    scores[batch_elem]["score"] += original_scores[
                        batch_elem, next_token[batch_elem].item()
                    ].item()
                    scores[batch_elem]["sequence"].append("token")

            generated = torch.cat((generated, next_token), dim=1)
            segments = torch.cat((segments, segments[:, -1:]), dim=1)

            for batch_elem in range(batch_size):
                if next_token[batch_elem].item() == eos_token_id:
                    eos_emitted[batch_elem] = True

            if length is None and all(eos_emitted):
                break

    if get_scores:
        scores = [_score_fn(x, True) for x in scores]

    return generated, scores


def _score_fn(x, length_normalize):
    if length_normalize:
        return x["score"] / len(x["sequence"])
    else:
        return x["score"]


class Instance(object):
    """
    Instance of a sentence to generate a paraphrase for.

    Args:
        args: Standard, default arguments to use.
        config : configurations specified.
        instance_dict : dictionary containing the sentence to paraphrase.

    """

    def __init__(self, args, config, instance_dict):
        self.dict = instance_dict
        self.args = args
        self.config = config
        self.truncated = False
        self.sent1_tokens = np.array(
            instance_dict["sent1_tokens"], dtype=np.int32
        )
        self.sent2_tokens = np.array(
            instance_dict["sent2_tokens"], dtype=np.int32
        )
        self.init_context_size = config["max_prefix_length"] + 1

    def preprocess(self, tokenizer):
        # shorten the very long sequences in the instance based on DATASET_CONFIG
        self.truncate()
        # whenever args.prefix_input_type has "original_shuffle" or "original_reverse"
        # exchange prefix/suffix with 50% probability or 100% probability
        self.shuffle_prefix_suffix()
        # Finally, perform prefix and suffix padding to build the sentence, label and segments
        self.build_sentence(tokenizer)
        self.build_label(tokenizer)
        self.build_segment(tokenizer)
        # check if the padding worked out correctly and all the lengths are aligned
        self.check_constraints()

    def truncate(self):
        config = self.config
        max_prefix_length = config["max_prefix_length"]
        max_suffix_length = config["max_suffix_length"]
        if len(self.sent1_tokens) > max_prefix_length:
            self.truncated = True
            self.sent1_tokens = self.sent1_tokens[:max_prefix_length]
        if len(self.sent2_tokens) > max_suffix_length:
            self.truncated = True
            self.sent2_tokens = self.sent2_tokens[:max_suffix_length]

    def shuffle_prefix_suffix(self):
        if not hasattr(self.args, "prefix_input_type"):
            # Keeping this check for backward compatibility with previous models
            return
        if self.args["prefix_input_type"] == "original_shuffle":
            # shuffle with 50% probability
            if random.random() <= 0.5:
                self.sent1_tokens, self.sent2_tokens = (
                    self.sent2_tokens,
                    self.sent1_tokens,
                )

        elif self.args["prefix_input_type"] == "original_reverse":
            self.sent1_tokens, self.sent2_tokens = (
                self.sent2_tokens,
                self.sent1_tokens,
            )

    def build_sentence(self, tokenizer):
        self.sent_prefix = self.left_padding(
            self.sent1_tokens,
            tokenizer.pad_token_id,
            self.config["max_prefix_length"],
        )

        self.sent_suffix = self.right_padding(
            np.append(self.sent2_tokens, tokenizer.eos_token_id),
            tokenizer.pad_token_id,
            self.config["max_suffix_length"] + 1,
        )
        self.sentence = np.concatenate(
            [self.sent_prefix, [tokenizer.bos_token_id], self.sent_suffix]
        )

    def left_padding(self, data, pad_token, total_length):
        tokens_to_pad = total_length - len(data)
        return np.pad(data, (tokens_to_pad, 0), constant_values=pad_token)

    def right_padding(self, data, pad_token, total_length):
        tokens_to_pad = total_length - len(data)
        return np.pad(data, (0, tokens_to_pad), constant_values=pad_token)

    def build_label(self, tokenizer):
        dense_length = self.config["global_dense_length"]
        self.label_suffix = self.right_padding(
            np.append(self.sent2_tokens, tokenizer.eos_token_id),
            -100,
            self.config["max_suffix_length"] + 1,
        )
        self.label = np.concatenate(
            [
                [-100 for _ in range(dense_length)],
                [-100 for _ in self.sent_prefix],
                [-100],
                self.label_suffix,
            ]
        ).astype(np.int64)

    def build_segment(self, tokenizer):
        dense_length = self.config["global_dense_length"]
        prefix_segment = [
            tokenizer.additional_special_tokens_ids[1]
            for _ in self.sent_prefix
        ]
        suffix_segment_tag = tokenizer.additional_special_tokens_ids[2]

        self.segment = np.concatenate(
            [
                [
                    tokenizer.additional_special_tokens_ids[0]
                    for _ in range(dense_length)
                ],
                prefix_segment,
                [suffix_segment_tag],
                [suffix_segment_tag for _ in self.sent_suffix],
            ]
        ).astype(np.int64)

    def check_constraints(self):
        dense_length = self.config["global_dense_length"]
        assert len(self.sentence) == len(self.label) - dense_length
        assert len(self.sentence) == len(self.segment) - dense_length


class StyleTransferParaphraser(SentenceOperation):
    tasks = [TaskType.TEXT_CLASSIFICATION, TaskType.TEXT_TO_TEXT_GENERATION]
    languages = ["en"]
    heavy = True

    """
        Style transfer paraphraser, using a GPT2-model of choice.

        Args:
            style : str
                The style to use. Options include Bible, Shakespeare, Basic, Romantic Poetry and Tweets.
            device : device to use for computations.
                Default: None, and it will then resort to CUDA if available, else CPU.
            upper_length :
                The maximum length.
                Options: "eos" or "same_5"
            beam_size : size of the beam during beam search (if top_p == 0.0)
                Default: 1
            top_p : float
                top_p sampling, between 0.0 and 1.0
                Default: 0.0 (meaning using a greedy approach)
            temperate : float
                Sampling temperate
                Default: 0.0
    """

    def __init__(
        self,
        style: str = "Shakespeare",
        device=None,
        upper_length="eos",
        beam_size: int = 1,
        top_p: int = 0.0,
        temperature: float = 0.0,
    ):

        self.style = style

        assert (
            style in MODELS_SUPPORTED.keys()
        ), f"Style not supported. The following styles are supported: {', '.join(list(MODELS_SUPPORTED.keys()))}"
        model_path = MODELS_SUPPORTED[style]
        self.args = TRAIN_ARGS[model_path]
        self.device = device
        if self.device is None:
            self.device = torch.device(
                "cuda" if torch.cuda.is_available() else "cpu"
            )
        self.args["upper_length"] = upper_length
        self.args["stop_token"] = "eos" if upper_length == "eos" else None
        self.args["beam_size"] = beam_size
        self.args["temperature"] = temperature
        self.args["top_p"] = top_p
        self.args["top_k"] = 1
        self.args["device"] = self.device
        self.config = BASE_CONFIG

        self.config["global_dense_length"] = 0

        self.gpt2_model, self.tokenizer = self.init_gpt2_model(
            checkpoint_dir=model_path,
            do_lower_case=self.args["do_lower_case"],
            device=self.device,
            model_class=GPT2LMHeadModel,
            tokenizer_class=GPT2Tokenizer,
        )

    def init_gpt2_model(
        self,
        checkpoint_dir,
        do_lower_case,
        device,
        model_class,
        tokenizer_class=None,
    ):
        """Load a trained model and vocabulary that you have fine-tuned."""

        model = model_class.from_pretrained(checkpoint_dir)
        model.to(device)

        if tokenizer_class:
            tokenizer = tokenizer_class.from_pretrained(
                checkpoint_dir, do_lower_case=do_lower_case
            )
        else:
            tokenizer = None

        return GPT2ParentModule(args=self.args, gpt2=model), tokenizer

    def modify_p(self, top_p):
        self.args["top_p"] = top_p

    def generate_batch(
        self,
        contexts,
        top_p=None,
    ):
        tokenizer = self.tokenizer
        instances = []

        for context in contexts:
            context_ids = tokenizer.convert_tokens_to_ids(
                tokenizer.tokenize(context)
            )

            instance = Instance(
                self.args,
                self.config,
                {"sent1_tokens": context_ids, "sent2_tokens": context_ids},
            )
            instance.preprocess(tokenizer)
            global_dense_vectors = np.zeros((1, 768), dtype=np.float32)
            instance.gdv = global_dense_vectors
            instances.append(instance)

        output, _, scores = _generate(
            gpt2_sentences=torch.tensor(
                [inst.sentence for inst in instances]
            ).to(self.device),
            model=self.gpt2_model.gpt2,
            args=self.args,
            segments=torch.tensor([inst.segment for inst in instances]).to(
                self.device
            ),
            init_context_size=instances[0].init_context_size,
            eos_token_id=tokenizer.eos_token_id,
            top_p=top_p,
        )

        all_output = []
        for out_num in range(len(output)):
            instance = instances[out_num]
            curr_out = output[out_num, instance.init_context_size :].tolist()

            if tokenizer.eos_token_id in curr_out:
                curr_out = curr_out[: curr_out.index(tokenizer.eos_token_id)]

            if self.args["upper_length"].startswith("same"):
                extra = int(self.args["upper_length"].split("_")[-1])
                curr_out = curr_out[: len(instance.sent1_tokens) + extra]

            all_output.append(
                tokenizer.decode(
                    curr_out,
                    clean_up_tokenization_spaces=True,
                    skip_special_tokens=True,
                )
            )

        return all_output, scores

    def generate(
        self,
        sentence,
        top_p=None,
    ):
        out = self.generate_batch([sentence], top_p=top_p,)[
            0
        ][0]
        return [out]


"""
# Sample code to demonstrate usage of the this perturbation module.

if __name__ == "__main__":
    import argparse
    import sys


    parser = argparse.ArgumentParser()
    parser.add_argument("--style", default="Shakespeare", type=str)
    parser.add_argument("--input_sentence", default="Hi there! How are you doing today? ", type=str)
    parser.add_argument("--top_p_value", default=0.6, type=float)
    args = parser.parse_args()

    if not torch.cuda.is_available():
        print(
            "Please check if a GPU is available or your Pytorch installation is correct."
        )
        sys.exit()

    print("Loading paraphraser...")
    paraphraser = StyleTransferParaphraser(args.style, upper_length="same_5")

    print(
        "\n\nNOTE: Ignore the weight mismatch error, this is due to different huggingface/transformer versions + minor modifications I did myself, shouldn't affect the paraphrases.\n\n"
    )

    input_sentence = args.input_sentence
    paraphraser.modify_p(top_p=0.0)
    greedy_decoding = paraphraser.generate(input_sentence)
    print("\ngreedy sample:\n{}\n".format(greedy_decoding))

    top_p_60_samples, _ = paraphraser.generate_batch(
        [input_sentence, input_sentence, input_sentence], top_p=args.top_p_value
    )
    top_p_60_samples = "\n".join(top_p_60_samples)
    print(
        "top_p = {:.2f} samples:\n{}\n".format(
            args.top_p_value, top_p_60_samples
        )
    )
"""
