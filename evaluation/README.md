# Evaluation

A transformation would be most effective when it can either reveal potential failures in a model or act as a data augmenter to generate more training data. 


### Table of Contents
* [Table of Contents](#table-of-contents)
* [Evaluation Guideline and Scripts](#evaluation-guideline-and-scripts)
* [Leaderboard](#leaderboard)
    * [Text Classification](#text-classification)
    * [Text-to-Text Generation](#text2text-generation)
    * [Text Tagging](#text-tagging)
    * [Dialog Action to Text](#dialog-action-to-text)
    * [Table-to-Text](#table-to-text)
    * [RDF-to-Text](#rdf2text)
    * [RDF-to-RDF](#rdf-to-rdf)
    * [Question Answering](#question-answering)
    * [Question Generation](#question-generation)
    * [AMR-to-Text](#amr-to-text)
    * [End-to-End Task](#end-to-end-task)


## Evaluation Guideline and Scripts

To evaluate how good a transformation is, you can simply call `evaluate.py` in the following manner:  

```bash
python evaluate.py -t ButterFingersPerturbation 
```

Depending on the interface of the transformation, `evaluate.py` would transform every example of a pre-defined dataset and evaluate how well the model performs on these new examples. The default dataset and models are mentioned [here](../interfaces/README.md). These dataset and model combinations are mapped to each task. The first task you specify in the `tasks` field is used by default.
The [task](../tasks/TaskTypes.py) (`-t`), [dataset](https://huggingface.co/datasets) (`-d`) and [model](https://huggingface.co/models) (`-m`) can be overridden in the following way.

```bash
python evaluate.py -t ButterFingersPerturbation -task "TEXT_CLASSIFICATION" -m "aychang/roberta-base-imdb" -d "imdb"
```  

Note that it's highly possible that some of the evaluate_* functionality won't work owing to the variety of dataset and model formats. We've tried to mitigate this by using models and datasets of HuggingFace. If you wish to evaluate on models and datasets apart from those mentioned [here](evaluation_engine.py), you are welcome to do so. Do mention in your README how they turned out!


Note that it's highly possible that some of the evaluate_* functionality won't work owing to the variety of dataset and model formats. We've tried to mititgate this by using models and datasets which are commonly used. If you wish to evaluate on models and datasets apart from those mentioned [here](evaluation_engine.py), you are free to do so. Do mention in your `README` how they turned out!

## Leaderboard

Here, we provide a leaderboards for each default task, by executing transformations on typical models in each task. If you would like to join the leaderboard party encourage you to submit pull requests!

### Text Classification



### Text-to-Text Generation
### Text Tagging
### Dialog Action to Text
### Table-to-Text
### RDF-to-Text
### RDF-to-RDF
### Question Answering

| Transformation        |   deepset/roberta-base-squad2 |   bert-large-uncased-whole-word-masking-finetuned-squad |
|:----------------------|------------------------------:|--------------------------------------------------------:|
| RedundantContextForQa |                           5.6 |                                                    -1.9 |

### Question Generation
### AMR-to-Text
### End-to-End Task