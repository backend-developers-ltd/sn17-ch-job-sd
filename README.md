# sn17-ch-job-sd

ComputeHorde + SN17 PoC job for running Stable Diffusion generation

## Building job image

In order to schedule jobs on ComputeHorde, a docker image containing the code and model to execute
must be first build and uploaded to a registry. The registry must be accessible by miners.

The `ch-job-image` directory contains a simple Dockerfile and a script (`build-image.sh`) to turn a
"model config" into a ComputeHorde job image:

```shell
cd ch-job-image
./build-job-image.sh ./model-configs/sd15.yml some.docker.registry/sn17-job-sd15:latest
docker push some.docker.registry/sn17-job-sd15:latest
```

## Executing a job

The `ch-job-client` directory contains a sample python project for submitting and validating jobs
on ComputeHorde:

### Prerequisites
- Python 3.13
- Bittensor wallet+hotkey for authentication - can be generated just for this purpose
- ComputeHorde Facilitator API key
- SS58 Address of a validator who whitelisted the above wallet
- AWS bucket and credentials with read+write access to the bucket 

### Setup
_(within the ch-job-client directory)_

Initialize a venv and install requirements:
```shell
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
Configure the client:
```shell
cp .env.example .env
```
Open the `.env` file with a text editor and fill in the configuration

### Running
Run `python submit_jobs.py`.

This will:
- Scan each subdirectory in the `batches`, each containing a list of prompts 
- Submit it as a ComputeHorde job using the configured image
- Pull in job results - generated images
- In the meantime, submit a "trusted" job with prompt samples to validate the results
- Cross-validate job results with the trusted job
- Report issues

# Stable Diffusion License notice

This repository contains code that builds and packages a complete Docker image that is essentially
a distribution of a Stable Diffusion model (SD 1.5, SD 2, SDXL).

The models are licensed under The CreativeML OpenRAIL M license available at
[https://huggingface.co/spaces/CompVis/stable-diffusion-license](https://huggingface.co/spaces/CompVis/stable-diffusion-license)

**Note that the license contains some use case restrictions.** Therefore, you agree not to use the
model or this distribution:

- In any way that violates any applicable national, federal, state, local
  or international law or regulation;
- For the purpose of exploiting, harming or attempting to exploit or harm
  minors in any way;
- To generate or disseminate verifiably false information and/or content
  with the purpose of harming others;
- To generate or disseminate personal identifiable information that can
  be used to harm an individual;
- To defame, disparage or otherwise harass others;
- For fully automated decision making that adversely impacts an
  individual’s legal rights or otherwise creates or modifies a binding,
  enforceable obligation;
- For any use intended to or which has the effect of discriminating
  against or harming individuals or groups based on online or offline
  social behavior or known or predicted personal or personality
  characteristics;
- To exploit any of the vulnerabilities of a specific group of persons
  based on their age, social, physical or mental characteristics, in order
  to materially distort the behavior of a person pertaining to that group
  in a manner that causes or is likely to cause that person or another
  person physical or psychological harm;
- For any use intended to or which has the effect of discriminating
  against individuals or groups based on legally protected characteristics
  or categories;
- To provide medical advice and medical results interpretation;
- To generate or disseminate information for the purpose to be used for
  administration of justice, law enforcement, immigration or asylum
  processes, such as predicting an individual will commit fraud/crime
  commitment (e.g. by text profiling, drawing causal relationships between
  assertions made in documents, indiscriminate and arbitrarily-targeted
  use).