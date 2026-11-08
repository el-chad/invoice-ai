import logging
from fastapi import FastAPI
from invoice_ai.api.documents import router

logging.basicConfig(
    filemode="w",
    filename="app.log",
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
app = FastAPI()
app.include_router(router)