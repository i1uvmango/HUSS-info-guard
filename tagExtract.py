
from bs4 import BeautifulSoup
import requests

def extract_youtube_tags(video_url):
    """
    유튜브 영상 URL에서 meta 태그에 있는 keywords 추출
    """
    headers = {"User-Agent": "Mozilla/5.0"}  
    response = requests.get(video_url, headers=headers)
    
    if response.status_code != 200:
        print("영상 페이지 접근 실패")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    keywords_tag = soup.find("meta", {"name": "keywords"})
    
    if keywords_tag:
        tags = keywords_tag["content"].split(", ")
        return tags
    else:
        print("태그가 존재하지 않거나 추출 불가")
        return []

# 링크
video_url = "https://www.youtube.com/watch?v=IFszIL4ubCQ"  
tags = extract_youtube_tags(video_url)

print("추출된 태그:", tags)
