# Python Executor App

This project is a web application that allows users to execute multiple Python functions dynamically. It is built using Flask and provides a simple interface for inputting function names and parameters.

## Project Structure

```
python-executor-app
├── src
│   ├── app.py                # Entry point of the application
│   ├── routes
│   │   └── executor.py       # Defines the route for executing functions
│   ├── services
│   │   └── runner.py         # Contains the FunctionRunner class for executing functions
│   ├── functions
│   │   └── sample_function.py # Sample function to be executed
│   └── templates
│       └── index.html        # HTML template for the web interface
├── requirements.txt           # Lists project dependencies
└── README.md                  # Documentation for the project
```

## Setup Instructions

1. Clone the repository:
   ```
   git clone <repository-url>
   cd python-executor-app
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Run the application:
   ```
   python src/app.py
   ```

4. Open your web browser and navigate to `http://127.0.0.1:5000` to access the application.

## Usage

- Enter the name of the function you want to execute in the input field.
- Provide any necessary parameters for the function.
- Click the "Execute" button to run the function and view the result.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any improvements or features you would like to add.