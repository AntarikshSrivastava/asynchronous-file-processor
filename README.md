# Asynchronous File Processing Service

This project implements an asynchronous file processing service designed to chunk and parse large files efficiently. It leverages Celery for distributed task processing with Redis as the message broker and uses MongoDB for storing the results. The service provides real-time progress updates through WebSockets.

## Features

- **File Chunking and Parsing**: Efficiently processes large files by breaking them down into manageable chunks.
- **Content Indexing**: Parses file chunks and indexes the content, making it searchable.
- **Real-Time Progress Tracking**: Utilizes WebSockets to provide clients with real-time updates on the processing status.
- **Scalable Architecture**: Designed to scale horizontally, accommodating large-scale file processing needs.

## Getting Started

Follow these instructions to get the project up and running on your local machine for development and testing purposes.

### Prerequisites

- Docker and Docker Compose
- Git

### Installation

1. **Clone the Repository**

    ```bash
    git clone https://github.com/AntarikshSrivastava/indexing-service-simulator.git
    cd your-repo-name
    ```

2. **Environment Configuration**

    Create a `.env` file in the root directory and define the necessary environment variables:

    ```plaintext
    DB_HOST=yourDBHost
    DB_USER=yourMongoUser
    DB_PASS=yourMongoPassword
    DB_PORT=27017
    REDIS_HOST=yourRedisHost
    REDIS_PORT=6379
    ```

3. **Build and Run with Docker Compose**

    ```bash
    docker-compose up --build
    ```

    This command builds the Docker images and starts the services defined in `docker-compose.yml`.

### Usage

1. **Upload a File**

    Use the provided API endpoint to upload a file for processing:

    `POST /jobs/`

    Include the file in the request body as form-data.

    Sample Curl Request:

    ```
    curl -X 'POST' \
    'http://localhost:8000/jobs/' \
    -H 'accept: application/json' \
    -H 'Content-Type: multipart/form-data' \
    -F 'file=@/Users/antariksh/codebase/file1.txt'
    ```
    

2. **Track Progress**

    Connect to the WebSocket endpoint using the `job_id` returned from the file upload response:

    `/ws/jobs/{job_id}`

    Receive real-time progress updates as JSON messages.


## Authors

- **Antariksh Srivastava** - *Initial Work* - [AntarikshSrivastava](https://github.com/AntarikshSrivastava)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Thanks to the Celery and Redis communities for their excellent documentation and support.
- Inspired by the need for efficient, scalable file processing in modern web applications.
