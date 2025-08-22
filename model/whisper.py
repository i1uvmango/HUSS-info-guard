# 구글 코랩에서 사용

'''!pip install git+https://github.com/openai/whisper.git

from google.colab import drive
drive.mount('/content/gdrive')


# 2번
# 작은 파일의 경우 직접 업로드. 앞의 구글 드라이드 업로드를 했다면 넘어가기.
from google.colab import files
uploaded = files.upload()
file_names = list(uploaded.keys())
print(file_names)
filepath = f'/content/{file_names[0]}'


#   --task translate 를 지정하면 영어로 번역 자막을 생성.
! whisper "{filepath}" --language Korean --model large '''