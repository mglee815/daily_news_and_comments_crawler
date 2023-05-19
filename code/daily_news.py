# import
import pandas as pd

from bs4 import BeautifulSoup
import requests
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from tqdm import tqdm


from datetime import datetime, timedelta
import asyncio
import json
import nest_asyncio
import re

nest_asyncio.apply()


#웹드라이버 설정
options = webdriver.ChromeOptions()
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option("useAutomationExtension", False)

driver = webdriver.Chrome(ChromeDriverManager().install())
driver.implicitly_wait(3)


urls = []

prev = 'None'
i = 1
while True:
    if i == 200:
        break
    url = f'https://news.naver.com/main/main.naver?mode=LSD&mid=shm&sid1=100&page=2#&date=%2000:00:00&page={i}'
    driver.get(url)
    page_news = driver.find_element(By.CLASS_NAME, 'section_body').find_elements(By.TAG_NAME,'ul')
    driver.implicitly_wait(3)
    for chunck in page_news:
        try:
            for single_article in chunck.find_elements(By.TAG_NAME, 'li'):
                try:
                    urls.append(single_article.find_elements(By.TAG_NAME, 'a')[0].get_attribute('href'))
                except:
                    pass
        except:
            pass

    i += 1


urls_unique = list(set(urls))


def get_comments(refer_url, comment_url) : # 댓글 목록을 json 형태로 받아오는 함수
    comments = []
    next = None
    # 처음엔 댓글 개수를 모르므로 충분히 큰 수를 넣어 줌
    comment_count = 10e6
    headers = {
        'User-Agent' : 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_3) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.5 Safari/605.1.15',
        'referer': refer_url
    }
    
    # 수집한 댓글 수가 첫번째에 수집한 총 댓글 수 보다 많다면 반복을 종료합니다.
    while len(comments) < comment_count :
        comment_url_next = comment_url + '&moreParam.next=' + next if next else comment_url
        res = requests.get(comment_url_next, headers=headers)
        dic = json.loads(res.text[res.text.index('(')+1:-2])
        comments.extend(list(map(lambda x : {
            'url' : refer_url,
            'text': x['contents'],
            'reply_count' : x['replyCount'], 
            'uid': x['idNo'],
            'uname' : x['userName'],
            'like': x['sympathyCount'], 
            'dislike': x['antipathyCount'],
            'c_time' : x['modTime'],
            'cid': x['commentNo'],
            'pid' : x['parentCommentNo'] 
            }, dic['result']['commentList'])))
        comment_count = dic['result']['count']['comment']
        next = dic['result']['morePage']['next'] if comment_count else None
    # 필터로 삭제된 댓글을 걸러줍니다
    comments=list(filter(lambda x: len(x['text']), comments))
    return comments


def get_data(oid, aid) :
    try :
        # refer_url: 댓글 보기를 누르면 나오는 댓글 페이지 주소
        # comment_url: 네트워크 탭에서 확인 가능한 동적으로 생성되는 주소
        refer_url = f'https://n.news.naver.com/mnews/article/comment/{oid}/{aid}?sid=100'
        comment_url = f'https://apis.naver.com/commentBox/cbox/web_naver_list_jsonp.json?ticket=news&templateId=default_politics_m3&pool=cbox5&_cv=20220623185938&_callback=jQuery33103200637113167857_1656171100524&lang=ko&country=KR&objectId=news{oid}%2C{aid}&categoryId=&pageSize=100&indexSize=10&groupId=&listType=OBJECT&pageType=more&page=1&initialize=true&userType=&useAltSort=true&replyPageSize=20&followSize=100&sort=new&includeAllStatus=true&_=1656171100525'

        comments = get_comments(refer_url, comment_url)
        comments = pd.DataFrame(comments)
        # 댓글 수가 0개인 기사를 어떻게 할지 추후에 결정해야 함
        return comments
    except :
        return None
    
    
    
df = pd.DataFrame()
for url in tqdm(urls_unique):
    try:
        oid = re.findall('article/([^\*]*)/', str(url))[0]
        aid = re.findall(f'{oid}/([^\*]*)[?]', str(url))[0]
        sid = url[-3:]
        temp = get_data(oid, aid)
        temp['sid'] = sid
        df =pd.concat([df, temp])
    except:
        print(url)


now = datetime.now().date()
str(now)


df.reset_index(drop=True, inplace=True)
df['date'] = datetime.now().date()
print(f"{df.shape} of DATA is collected")
print('===' * 10)
print(f"Today : {str(now)}")


df.to_csv(f'./data/{str(now)}_naver_daily_news.csv', index=False)

print("DataFrame saved as csv file")