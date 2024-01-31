""" Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved. """
""" SPDX-License-Identifier: MIT-0 """

import os
import json
import logging
import pandas as pd

# Global parameters
logger = logging.getLogger("sagemaker")
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())

def save(save_path, results):
    output_path = os.path.join(save_path, "evaluation_report.json")
    with open(output_path, "w") as f:
        json.dump(results, f)
    logger.info(f"Results saved to {output_path}")


if __name__=="__main__":
    data_path = "/opt/ml/processing/input/data/"
    save_path = "/opt/ml/processing/output/data/"
    job_arn = os.environ["JOB_ARN"]
    val_artifact = f"{data_path}model-customization-job-{job_arn.split('/')[-1]}/validation_artifacts/post_fine_tuning_validation/validation/validation_metrics.csv"
    logger.info(f"Reading validation metrics from {val_artifact} ...")
    df = pd.read_csv(val_artifact)
    validation_results = {
        "Loss": df.iloc[-1][-2],
        "Perplexity": df.iloc[-1][-1]
    }
    logger.info(f"Results: {validation_results}")
    logger.info("Saving results ...")
    save(save_path, validation_results)
    logger.info("Done!")