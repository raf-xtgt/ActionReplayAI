# Gemini Workspace Context

## Project Overview

This project is the backend API for ActionReplayAI, a conversational AI training platform. It is built with Python and Flask, and it uses the `dspy` library for interacting with large language models (LLMs) and `ollama` for local LLM inference. The application simulates a client-salesperson interaction to help train users' communication and sales skills.

The key technologies used are:

*   **Backend:** Python, Flask, Flask-SocketIO
*   **AI:** dspy, Ollama, Kimi (Moonshot AI)
*   **Database:** TiDB with vector support (tidb-vector)
*   **Environment Management:** `dotenv` for managing environment variables

The application is structured into the following components:

*   **`app.py`:** The main entry point of the Flask application, which initializes the app, SocketIO, and blueprints.
*   **`agent/`:** Contains the AI agent logic for simulating the client.
*   **`config/`:** Holds the database configuration, specifically for TiDB.
*   **`controller/`:** Defines the API endpoints for client profiles and sessions.
*   **`model/`:** Contains the Pydantic data models for the application.
*   **`util/`:** Includes utility functions for database services and knowledge graph interactions.

## Building and Running

To run the application, you need to have Python and the required dependencies installed. The main application can be started with the following command:

```bash
# TODO: Add instructions for installing dependencies from requirements.txt

# Run the Flask application
python app.py
```

The application will start on `localhost:5000`.

## Development Conventions

### Project Structure

The project follows a modular structure, with different functionalities separated into different directories.

*   **`agent/`:** This directory contains the core AI logic. The `client_agent.py` file defines the `ClientAgent` class, which uses `dspy` to generate responses from the simulated client based on a given profile and objections.
*   **`config/`:** This directory is for configuration files. `tidb_config.py` sets up the connection to the TiDB database.
*   **`controller/`:** This directory contains the Flask blueprints for different API endpoints. For example, `client_profile_controller.py` handles requests related to client profiles.
*   **`model/`:** This directory defines the data models used in the application, using Pydantic for data validation.
*   **`util/`:** This directory contains utility functions. `db_service.py` provides functions for interacting with the database, and `knowledge_graph.py` contains logic related to the knowledge graph.

### API Endpoints

The following are the main API endpoints:

*   `/api/client_profile/get-all`: Get all available client profiles.
*   `/api/client_profile/get-by-id/<client_profile_id>`: Get a specific client profile by ID.
*   `/api/client_profile/objections/<client_profile_id>`: Get the objections for a specific client profile.
*   `/api/session/...`: Endpoints for managing training sessions (details in `session_controller.py`).

### AI Integration

The application uses `dspy` to create and manage AI agents. The `ClientAgent` in `agent/client_agent.py` is a `dspy.Module` that uses a `dspy.Signature` to define the behavior of the AI. The `dspy.LM` class is used to configure the language model, which can be a local model served by `ollama` or a remote API like Kimi.
