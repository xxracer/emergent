# Binance Alpha Trader

This is a personal trading platform for the Binance exchange, designed to execute trades based on identifying small, profitable spreads in real-time.

## Project Structure

-   `/frontend`: Contains the React-based user interface.
-   `/backend`: Contains the Python/FastAPI server, trading logic, and Binance API integration.

## Setup and Installation

This project has been configured for a simplified setup process. You can install all dependencies (for both frontend and backend) and run the application with just a few commands from this root directory.

### Prerequisites

-   [Node.js](https://nodejs.org/) (which includes npm)
-   [Python](https://www.python.org/)
-   An active account on [Binance](https://www.binance.com/)

### 1. Configure API Keys

Before you start, you need to add your Binance API keys to the backend configuration.

1.  Navigate to the `backend` directory.
2.  You will find a file named `.env`. Open it.
3.  Add your API Key and Secret Key to the respective variables:

    ```env
    BINANCE_API_KEY="YOUR_API_KEY_HERE"
    BINANCE_API_SECRET="YOUR_SECRET_KEY_HERE"
    ```

4.  You can also choose whether to use the Binance Testnet by setting `USE_TESTNET` to `true` or `false`. It is highly recommended to start with `true`.

### 2. Install Dependencies

From the root directory of the project, run the following command. This will install both the Node.js dependencies for the frontend and the Python dependencies for the backend.

```bash
npm install
```

### 3. Run the Application

Once the installation is complete, you can start both the backend and frontend servers with a single command from the root directory:

```bash
npm run dev
```

This command will:
-   Start the Python backend server on port 8000.
-   Start the React frontend development server on port 3000.
-   Open the user interface in your default web browser.

You are now ready to start trading!
