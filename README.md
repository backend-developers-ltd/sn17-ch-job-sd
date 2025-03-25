# sn17-ch-job-sd

ComputeHorde + SN17 PoC job for running Stable Diffusion generation

# Usage

Use the `build-image.sh` script to turn a model-config yaml file into a tagged docker image.

You can then use the image locally or upload it to an online registry for use as a ComputeHorde job.

# TODO

- [ ] Preload the model into the image in a way that doesn't also load it into the memory at image
  build time
- [ ] Support for other models via different model-config
- [ ] Shrink the image if possible - without a model, it's >18GB just for the environment

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