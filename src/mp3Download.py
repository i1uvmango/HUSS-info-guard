import yt_dlp

def download_youtube_audio(url: str, output_dir: str = '.', filename_template: str = '%(title)s.%(ext)s'):
    ydl_opts = {
        'outtmpl': f'{output_dir}/{filename_template}',
        'format': 'bestaudio/best',
        'extractaudio': True,
        'audioformat': 'mp3',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

if __name__ == "__main__":
    video_url = "https://www.youtube.com/watch?v=t_Y9OKb2Wts"
    download_youtube_audio(video_url, output_dir='.', filename_template='%(title)s.%(ext)s')
    print("MP3 다운로드가 완료되었습니다.")
