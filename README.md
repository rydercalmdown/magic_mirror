# Magic Mirror
A smart bathroom mirror with gesture recognition and automatic habit tracking.

## Project Structure

-   `frontend/`: Contains the Next.js frontend application.
-   `backend/`: Contains the Flask backend application and Docker configuration.
-   `Makefile`: Provides convenient commands for building, running, and cleaning the project.

## Setup

1.  **Install Dependencies:**
    Run the following command in the root directory to install frontend dependencies and build the backend Docker image:
    ```bash
    make install
    ```
    *Note: You need Docker installed and running.*

## Usage

-   **Run Backend:**
    To start the backend server (Docker container):
    ```bash
    make run
    ```
    The backend will be available at `http://localhost:5001`.

-   **Run Frontend:**
    To start the frontend development server:
    ```bash
    make frontend
    ```
    The frontend will usually be available at `http://localhost:3000`.

-   **Clean Up:**
    To stop the backend container, remove it, remove the Docker image, and clean frontend build artifacts:
    ```bash
    make clean
    ```
