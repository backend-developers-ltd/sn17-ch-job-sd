FROM continuumio/miniconda3:25.1.1-2

ARG MODEL_CONFIG_FILE

WORKDIR /app

# Initialize the environment first as it takes a lot of time
COPY --from=codebase /setup_env.sh /conda_env.yml /requirements.txt /app/
RUN bash setup_env.sh

# Copy latest sn17 image generation code
COPY --from=codebase / /app/

# Define the model and pull it into the image
COPY --from=additional_context model_config.yml /app/configs/model_config.yml
RUN conda run --no-capture-output -n three-gen-image-generator python preload.py

# Allow running scripts from docker run CLI with the conda environment enabled
ENTRYPOINT ["conda", "run", "--no-capture-output", "-n", "three-gen-image-generator", "python"]
