import aiohttp
import json
import logging
import os
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def get_result(text, id):
    load_dotenv()
    print(os.getenv('folder_id'))
    headers = {"Authorization": f"Api-Key {os.getenv('api_token_search')}"}

    data = {
        "messages": [{"content": f"{text}", "role": "user"}],
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(
                f"https://ya.ru/search/xml/generative?folderid={os.getenv('folder_id')}",
                headers=headers, json=data
            ) as response:
                if response.status != 200:
                    logger.error(f"Ошибка при запросе к поиску: {response.status}")
                    return {"error": "Ошибка при запросе к поиску", "status": response.status}

                response_json = await response.json()
                logger.info(f"Поисковый API вернул: {response_json}")

                content = response_json.get('message', {}).get('content', "")
                titles = response_json.get('titles', [])
                links = response_json.get('links', [])

                if not content:
                    logger.warning("Контент из поиска пустой")
                    return {"error": "Поиск не вернул контент"}

                context2 = f"Content:\n{content}\n\nTitles:\n" + "\n".join(titles) + "\n\nLinks:\n" + "\n".join(links)

        except aiohttp.ClientError as e:
            logger.error(f"Ошибка при запросе к поиску: {str(e)}")
            return {"error": "Ошибка сети при запросе к поиску"}

        try:
            gpt_data = {
                "modelUri": f"gpt://{os.getenv('folder_id')}/yandexgpt/latest",
                "completionOptions": {"temperature": 0.3, "maxTokens": 1000},
                "messages": [
                    {"role": "system",
                     "text": "ТЫ ОТВЕЧАЕШЬ НА ВОПРОСЫ СВЯЗАННЫЕ С ПРЕДОСТАВЛЕНИЕ ИНФОРМАЦИИ О УНИВЕРСИТЕТЕ ИТМО."},
                    {"role": "user", "text": f"""
                        ### ИНСТРУКЦИЯ ###
                        Предоставьте подробную информацию об Университете ИТМО, ответьте на вопрос на русском языке и дайте полный ответ с обоснованием. 
                        Если даны варианты ответов, выберите правильный и объясните причину. Если вариантов нет, дайте ТОЛЬКО развернутый ответ с обоснованием. Не вкоем случае не пиши слово ответ.
                        ИНФОРМАЦИЯ: {context2}
                        ВОПРОС: {text}"""}
                ]
            }

            async with session.post(
                "https://llm.api.cloud.yandex.net/foundationModels/v1/completion",
                headers={"Accept": "application/json", "Authorization": f"Api-Key {os.getenv('api_token_gpt')}"},
                json=gpt_data
            ) as response:
                if response.status != 200:
                    logger.error(f"Ошибка при запросе к YandexGPT: {response.status}")
                    return {"error": "Ошибка при запросе к YandexGPT", "status": response.status}

                result = await response.json()
                logger.info(f"Ответ от YandexGPT: {result}")

                gpt_response = result.get('result', {}).get('alternatives', [{}])[0].get('message', {}).get('text', "")
                if not gpt_response:
                    logger.warning("GPT не вернул текст")
                    return {"error": "GPT не дал ответа"}

        except aiohttp.ClientError as e:
            logger.error(f"Ошибка сети при запросе к YandexGPT: {str(e)}")
            return {"error": "Ошибка сети при запросе к YandexGPT"}

        try:
            if gpt_response[:2].isdigit():
                answer = int(gpt_response[:2])
            elif gpt_response[:1].isdigit():
                answer = int(gpt_response[:1])
            else:
                answer = None
        except Exception as e:
            logger.error(f"Ошибка при разборе ответа: {str(e)}")
            answer = None

        result_data = {
            "id": id,
            "answer": answer,
            "reasoning": gpt_response + "\nСделано в YandexGPT.",
            "sources": links[:3]
        }

        logger.info(f"Итоговый результат: {result_data}")
        return result_data
