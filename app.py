import asyncio
import time
import logging
from quart import Quart, request, jsonify
from pydantic import ValidationError, BaseModel
from gptsearch import get_result

app = Quart(__name__)
semaphore = asyncio.Semaphore(7)


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PredictionRequest(BaseModel):
    id: int

@app.before_request
async def log_request_info():
    start_time = time.time()
    request_body = await request.get_data(as_text=True)
    logger.info(
        f"Incoming request: {request.method} {request.url}\n"
        f"Request body: {request_body}"
    )
    request.start_time = start_time

@app.after_request
async def log_response_info(response):
    process_time = time.time() - request.start_time
    response_body = await response.get_data(as_text=True)
    logger.info(
        f"Request completed: {request.method} {request.url}\n"
        f"Status: {response.status_code}\n"
        f"Response body: {response_body}\n"
        f"Duration: {process_time:.3f}s"
    )
    return response

@app.route('/api/request', methods=['POST'])
async def predict():
    body = PredictionRequest.model_validate(await request.get_json())
    try:
        data = await request.get_json()
        text = data.get("query")

        if not text:
            return jsonify({"error": "Поле 'query' обязательно"}), 400

        logger.info(f"Processing request with text: {text}")


        async with semaphore:
            result = await get_result(text, body.id)

        return jsonify(result), 200

    except ValidationError as e:
        error_msg = e.json()
        logger.error(f"Validation error: {error_msg}")
        return jsonify({"error": error_msg}), 400
    except Exception as e:
        logger.error(f"Internal server error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
