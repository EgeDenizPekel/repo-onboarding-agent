import os

# Set a placeholder API key so langchain-openai can instantiate ChatOpenAI at module
# import time without requiring a real key in the environment. Tests that exercise
# LLM calls mock the client, so this value is never sent to OpenAI.
os.environ.setdefault("OPENAI_API_KEY", "test-key-placeholder")
