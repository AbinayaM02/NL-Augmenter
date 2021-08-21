# Speech Disfluency Perturbation 🦎  + ⌨️ → 🐍
This perturbation randomly inserts speech disfluencies, specifically English filler words.

Author name: Ian Berlot-Attwell
Author Affiliation: University of Toronto

## What type of a transformation is this?
This transformation acts like a perturbation to test robustness,
particularly with respect to spoken language. With independent probability `insert_prob`, a
speech disfluency (specifically, a randomly selected filler word)
is inserted between words. The default disfluencies are
"um", "uh", "erm", "ah", and "er"; they can be alternatively specified
by the user using `filler_words`. At least one filler word is always
inserted by the transformation.

## What tasks does it intend to benefit?
This perturbation would benefit all tasks which have a sentence/paragraph/document as input like text classification,
text generation, etc.

Performing the default evaluation (i.e., `python evaluate.py -t SpeechDisfluencyPerturbation`),
 we find a 2% decrease in performance on the TEXT_CLASSIFICATION task.
Specifically, a degradation from 96.0% to 94.0% for the model `aychang/roberta-base-imdb`
on the imdb dataset.

## What are the limitations of this transformation?
The transformation's outputs are simple, and incapable of
 generating linguistically diverse text. Currently, the transformation
only contains English filler words, therefore the user must provide
filler words for other languages should they wish to use this tranformation
on other languages. Finally, the current implementation
inserts disfluencies between words denoted by whitespace, therefore even with
user-provided filler words it will not work on languages without whitespace.

