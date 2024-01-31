""" Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved. """
""" SPDX-License-Identifier: MIT-0 """

import os
from datasets import load_dataset, DatasetDict

# Global parameters
logger = logging.getLogger("sagemaker")
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())


def load(dataset_name="cnn_dailymail", config="3.0.0"):
    dataset = load_dataset(dataset_name, config)
    return dataset

def process(dataset, input_feature_name='input', output_feature_name='output'):
    dataset = dataset.remove_columns(['id'])
    dataset = dataset.rename_columns({'article': input_feature_name, 'highlights': output_feature_name})
    dataset = dataset.shuffle(seed=123)
    return dataset

def clip_text(dataset):
    def clip(example, feature_name='input', max_char_length=5000):
        example[feature_name] = example[feature_name][:max_char_length]
        return example
    
    return dataset.map(clip)

def sample(dataset, sample_size):
    train = dataset['train'].select(range(sample_size))
    test = dataset['test'].select(range(sample_size))
    validation = dataset['validation'].select(range(sample_size))
    return DatasetDict({
        'train': train,
        'test': test,
        'validation': validation
    })

def save(dataset, path):
    dataset['train'].to_json(os.path.join(path,'train','data.jsonl'))
    dataset['test'].to_json(os.path.join(path,'test','data.jsonl'))
    dataset['validation'].to_json(os.path.join(path,'validation','data.jsonl'))

if __name__ == '__main__':
    output_path = '/opt/ml/processing/output'
    dataset = load("cnn_dailymail", "3.0.0")
    dataset = process(dataset,'input','output')
    dataset = sample(dataset, sample_size=1)
    dataset = clip_text(dataset)
    logger.info("Saving datasets to S3 ...")
    save(dataset, output_path)
    logger.info("Done!")
