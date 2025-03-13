# Use the latest Python 3.13 image (if available)
FROM python:3.9-buster

# Set the working directory inside the container
WORKDIR /app


# Copy the application files into the container
COPY . /app

# Install dependencies including GCC, OpenBLAS, LAPACK, etc.
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libopenblas-dev \
    liblapack-dev \
    libatlas-base-dev \
    python3-dev \
    && apt-get clean
# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port Flask runs on
EXPOSE 5000

# Define the command to run the Flask app
CMD ["python", "app/app.py"]
