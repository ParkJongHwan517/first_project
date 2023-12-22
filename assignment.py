from flask import Flask, jsonify, request
import requests
from bs4 import BeautifulSoup
import re

app = Flask(__name__)
a = {}

@app.route("/webhook/", methods=["POST"])
def webhook():
    global a
    request_data = request.get_json()
    a[request_data['user']] = request_data['result']['choices'][0]['message']['content']
    return 'OK'

@app.route("/question", methods=["POST"])
def get_question():
    global a
    try:
        request_data = request.get_json()
        response = {
            "version": "2.0",
            "template": {
                "outputs": [
                    {
                        "simpleText": {
                            "text": f"질문을 받았습니다. 적절한 답을 찾고 있어요!: {request_data['action']['params']['question']}"
                        }
                    }
                ]
            }
        }
        a[request_data['userRequest']['user']['id']] = '적절한 답을 찾고 있는 중입니다!'
        api = requests.post('https://api.asyncia.com/v1/api/request/', json={
            "apikey": "<open ai api key>",
            "messages": [{"role": "user", "content": request_data['action']['params']['question']}],
            "userdata": [["user", request_data['userRequest']['user']['id']]]
        }, headers={"apikey": "<api key>"}, timeout=0.3)
        return jsonify(response)
    except Exception as e:
        app.logger.error("An error occurred in /question endpoint: %s", str(e))
        return jsonify({"error": str(e)})

@app.route("/ans", methods=["POST"])
def hello2():
    request_data = request.get_json()
    response = {
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "simpleText": {
                        "text": f"답변: {a.get(request_data['userRequest']['user']['id'], '질문을 하신 적이 없어보여요. 질문부터 해주세요')}"
                    }
                }
            ]
        }
    }
    return jsonify(response)

############################크롤링 부분########################

def get_video_links(query):
    url = f'https://search.naver.com/search.naver?where=video&sm=tab_jum&query={query}'
    response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    video_list = []

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')

        video_link_elements = soup.select('li.video_item')[:3]

        for video_links in video_link_elements:
            video_title_tag = video_links.select_one('a.info_title')
            video_url_tag = video_links.select_one('a.link._svp_trigger')
            video_thumbnail_tag = video_links.select_one('img.thumb.api_get.api_img')

            if not video_title_tag or not video_url_tag or not video_thumbnail_tag:
                print("Error: Video information not found.")
                continue

            video_title = video_title_tag.text.strip() if video_title_tag else 'No title'
            video_url = video_url_tag.get('href', '') if video_url_tag else ''
            video_thumbnail = video_thumbnail_tag.get('src', '') if video_thumbnail_tag else ''

            video_item = {
                "title": video_title,
                "description": f"{video_title} description",
                "imageUrl": video_thumbnail,
                "link": {
                    "web": video_url
                }
            }

            video_list.append(video_item)
    else:
        print(f"Error: {response.status_code}")

    return video_list

############################동영상 검색어########################

@app.route('/api/Search', methods=['POST', 'GET'])
def Search():
    body = request.get_json()
    print(body)

    utt = body['userRequest']['utterance']

    speech = '동영상 검색어를 입력하세요 : '

    responseBody = {
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "simpleText": {
                        "text": speech
                    }
                }
            ]
        }
    }

    return jsonify(responseBody)

@app.route('/api/SearchWord', methods=['POST'])
def SearchWord():
    body = request.get_json()
    print(body)

    video_list = get_video_links(body['userRequest']['utterance'])

    list_card_items = []
    for video_item in video_list:
        list_card_item = {
            "title": video_item["title"],
            "description": video_item["description"],
            "imageUrl": video_item["imageUrl"],
            "link": {
                "web": video_item["link"]["web"]
            }
        }
        list_card_items.append(list_card_item)

    responseBody = {
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "listCard": {
                        "header": {
                            "title": "동영상 목록"
                        },
                        "items": list_card_items,
                    }
                }
            ]
        }
    }

    return jsonify(responseBody)


############################쇼핑 검색어########################



def get_shopping_results(shop):
    url = f'https://browse.auction.co.kr/search?keyword={shop}' # 사이트

    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        items = soup.select('a.link--itemcard')[:6]
        print(items)

        results = []
        for item in items:
            title = item.text.strip()
            link = item.get('href', '')

            # "구매 1천+"와 같은 패턴을 가진 제목은 무시합니다.
            if not re.search(r'구매\s*\d+', title):
                result_item = {
                    'title': title,
                    'link': link
                }
                # title이 비어있지 않은 경우에만 결과에 추가합니다.
                if title:
                    results.append(result_item)

        return results
    except requests.exceptions.RequestException as e:
        print(f'Error: {e}')
        return []


@app.route('/api/shopping/search', methods=['POST', 'GET'])
def search():
    body = request.get_json()
    print(body)

    utt = body['userRequest']['utterance']

    speech = '운동기구 관련 쇼핑 검색어를 입력하세요: ' # 검색어 

    responseBody = {
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "simpleText": {
                        "text": speech
                    }
                }
            ]
        }
    }

    return jsonify(responseBody)

@app.route('/api/shopping/SearchWord', methods=['POST'])
def search_word():
    body = request.get_json()
    print(body)

    shopping_results = get_shopping_results(body['userRequest']['utterance'])

    list_card_items = []
    for result_item in shopping_results:
        list_card_item = {
            "title": result_item["title"],
            "link": {
                "web": result_item["link"]
            }
        }
        list_card_items.append(list_card_item)

    responseBody = {
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "listCard": {
                        "header": {
                            "title": "쇼핑 목록"
                        },
                        "items": list_card_items,
                    }
                }
            ]
        }
    }
    return jsonify(responseBody)



if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)