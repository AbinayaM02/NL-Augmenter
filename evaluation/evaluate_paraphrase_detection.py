import numpy as np
import torch
from datasets import load_dataset
from torch.nn.functional import cosine_similarity
from transformers import AutoModel, AutoTokenizer

from dataset import KeyValueDataset
from tasks.TaskTypes import TaskType


# Mean Pooling - Take attention mask into account for correct averaging
def mean_pooling(model_output, attention_mask):
    token_embeddings = model_output[
        0
    ].cpu()  # First element of model_output contains all token embeddings
    input_mask_expanded = (
        attention_mask.cpu()
        .unsqueeze(-1)
        .expand(token_embeddings.size())
        .float()
    )
    return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(
        input_mask_expanded.sum(1), min=1e-9
    )


def evaluate(
    operation, evaluate_filter, model_name, dataset_name, split="test[:20%]"
):
    # load model
    if model_name is None:
        model_name = "sentence-transformers/paraphrase-xlm-r-multilingual-v1"
    # load test set
    if dataset_name is None:
        dataset_name = "paws"

    print(
        f"Loading <{dataset_name}> dataset to evaluate <{model_name}> model."
    )
    hf_dataset = (
        load_dataset(dataset_name, "labeled_final", split=split)
        if dataset_name == "paws"
        else load_dataset(dataset_name, split=split)
    )

    dataset = KeyValueDataset.from_huggingface(
        hf_dataset,
        TaskType.PARAPHRASE_DETECTION,
        ["sentence1", "sentence2", "label"],
    )

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = AutoModel.from_pretrained(model_name).to(device)

    print(
        f"Here is the performance of the model {model_name} on the {split} split of the {dataset_name} dataset"
    )
    if evaluate_filter:
        performance = filter_performance(
            dataset, tokenizer, model, device, filter=operation
        )
    else:
        performance = transformation_performance(
            dataset, tokenizer, model, device, transformation=operation
        )

    performance["model_name"] = model_name
    performance["split"] = split
    performance["dataset_name"] = dataset_name
    return performance


def filter_performance(dataset, tokenizer, model, device, filter):
    print("Here is the performance of the model on the filtered set")
    filtered_dataset = dataset.apply_filter(
        filter, subfields=["sentence1", "sentence2", "label"]
    )
    return performance_on_dataset(filtered_dataset, tokenizer, model, device)


"""
Evaluates performance on the original set
and on the perturbed set.
"""


def transformation_performance(
    dataset, tokenizer, model, device, transformation
):
    performance = performance_on_dataset(dataset, tokenizer, model, device)
    pt_dataset = dataset.apply_transformation(
        transformation, subfields=["sentence1", "sentence2", "label"]
    )
    print("Here is the performance of the model on the transformed set")
    performance = performance_on_dataset(pt_dataset, tokenizer, model, device)

    return performance


def performance_on_dataset(dataset, tokenizer, model, device):
    labels = []
    preds = []
    print(f"Length of Evaluation dataset is {len(dataset)}")

    for example in dataset:
        sentence1, sentence2, label = example

        sentences = [sentence1, sentence2]

        # Tokenize sentences
        encoded_input = tokenizer(
            sentences, padding=True, truncation=True, return_tensors="pt"
        ).to(device)

        # Compute token embeddings
        with torch.no_grad():
            model_output = model(**encoded_input)

        # Perform pooling. In this case, max pooling.
        sentence_embeddings = mean_pooling(
            model_output, encoded_input["attention_mask"]
        )

        similarity = cosine_similarity(
            sentence_embeddings[0], sentence_embeddings[1], dim=0
        )

        labels.append(label)
        if similarity > 0.5:
            preds.append(1)
        else:
            preds.append(0)

    accuracy = np.round(100 * np.mean(np.array(labels) == np.array(preds)))
    total = len(labels)

    print(
        f"The accuracy on this subset which has {total} examples = {accuracy}"
    )
    return {"accuracy": accuracy, "total": total}
