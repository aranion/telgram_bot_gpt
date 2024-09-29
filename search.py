import logging
import requests

from util import get_gpt_response


def get_search_result(GOOGLE_API_KEY, GOOGLE_SEARCH_ENGINE_ID, query, pages=1):
    res_str = ''

    for p in range(1, pages + 1):
        start = (p - 1) * 10 + 1

        url = f'https://www.googleapis.com/customsearch/v1?key={GOOGLE_API_KEY}&cx={GOOGLE_SEARCH_ENGINE_ID}&q={query}&start={start}'

        response = requests.get(url)

        if response.ok:
            data = response.json()

            search_items = data.get('items')

            if search_items:
                for i, search_item in enumerate(search_items, start=1):
                    try:
                        long_description = search_item['pagemap']['metatags'][0]['og:description']
                    except KeyError:
                        logging.info('Не найден long_description (og:description)!')
                        long_description = 'N/A'

                    title = search_item.get('title')
                    snippet = search_item.get('snippet')

                    res_str += f'Result {i}:\n' \
                               f'title: {title}\n'

                    if long_description != 'N/A':
                        res_str += f'Long description: {long_description}\n'
                    else:
                        res_str += f'description: {snippet}'

                    res_str += '\n'
            else:
                logging.info('Не найден items в ответе!')
        else:
            logging.error(f'Ошибка при получении данных по URL {url}')

    return res_str


def process_search_openai(GOOGLE_API_KEY, GOOGLE_SEARCH_ENGINE_ID, question, pages=1):
    logging.info('Старт поиска...')

    context = [
        {'role': 'system', 'content': f'generate google search query in english for this question\n{question}'}
    ]
    res = get_gpt_response(messages=context, max_tokens=20, temperature=0.9)
    query = res['msg'] if res['success'] else question
    search_res = get_search_result(GOOGLE_API_KEY, GOOGLE_SEARCH_ENGINE_ID, query, pages)

    logging.info(search_res)

    context = [
        {'role': 'system', 'content': f'Interpret information to suit answer for this question: {question}'},
        {'role': 'system', 'content': search_res},
        {'role': 'system', 'content': 'Write a simple and useful answer.'}
    ]
    res = get_gpt_response(messages=context, max_tokens=100, temperature=0.9)
    text_response = res['msg'] if res['success'] else search_res

    return text_response
