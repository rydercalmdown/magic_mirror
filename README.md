# Magic Mirror
A smart bathroom mirror with gesture recognition and automatic habit tracking.

---

## To Do / Ideas


### Ideas
- When a person appears, show a small person icon in the bottom
- Surfer gesture recognition to bring up and close the menu
- automatic habit detection based on current actions
- Needs to work entirely offline - this device shouldn't be internet connected
- to track habits in your phone, a QR code you can scan to get the data
- to update settings on the device, a QR code you can show to the camera from your phone



### To Do

Software:
- Implement camera module
- Implement surfer gesture recognition and menu opening and closing
- Implement action recognition and marking tasks complete
    - Action must be performed for a certain amount of time
    - brushing teeth should trigger a timer countdown; same with floss, other things
- Create habit object; for implementing, etc.
- Create day and night modes based on current time of day
- Create person recognition / facial recognition; and a "hello ryder" quick display
- Create a simple date display on the bottom


Hardware:
- Create mirror glass overlay
- Print out case for the pi
- Print out case for the mirror
- Print out case for the camera and embed at the top


---

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
