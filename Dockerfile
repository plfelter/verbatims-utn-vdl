# Use an official Python runtime as a parent image
FROM python:3.10.17-slim-bullseye

# Set working directory in the container
WORKDIR /verbatims-utn-vdl-app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -

# Add Poetry to PATH
ENV PATH="${PATH}:/root/.local/bin"

# Copy poetry configuration files first (dockerfile layers are cachable: subsequent builds will skip unchanged steps;
# it is more performant to only load useful files)
COPY pyproject.toml poetry.lock* ./

# Configure poetry to not create a virtual environment
#RUN poetry config virtualenvs.create false

# Install dependencies
RUN poetry install --no-interaction --no-ansi --without dev --no-root

# Copy the rest of the application and the local database (when it exists)
COPY . .


# Expose the port the app runs on
EXPOSE 5001

# Command to run the application using wsgi.py
#CMD ["gunicorn", "--bind", "0.0.0.0:5001", "wsgi:app"]

CMD ["poetry", "run", "python", "wsgi.py"]
