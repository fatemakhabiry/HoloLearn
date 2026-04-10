# Lecture_Agent/run_server.py — alternative if above still fails

import sys
import asyncio

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import uvicorn
from dotenv import load_dotenv

load_dotenv()

async def main():
    config = uvicorn.Config(
        "Lecture_Agent.api_server:app",
        host="127.0.0.1",
        port=8001,
        loop="asyncio",
    )
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(main())