from src.backend.downloader import DownloaderBackend
b = DownloaderBackend()
info = b.get_video_info('https://vww.animeflv.one/ver/aishiteru-game-wo-owarasetai-10')
print("INFO:")
print(info)
