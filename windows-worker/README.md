# Infinity Trader - Windows Compiler Worker

This worker process handles the compilation of `.mq5` EA files into `.ex5` files using MetaEditor.

## Requirements
1. A Windows machine (MetaEditor is a Windows executable).
2. MetaTrader 5 installed.
3. Python 3.10+

## Setup
1. Copy `.env.example` to `.env`
2. Update the `INFINITY_WORKER_API_KEY` to match the backend configuration.
3. Update `METAEDITOR_PATH` to point to your `metaeditor64.exe`.
4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running
```bash
python worker.py
```

## Testing Compilation
Set `WORKER_TEST_MODE=true` in your `.env` to skip actual MetaEditor execution and just upload dummy EAs.
