import re
content = open('src/backend/downloader.py', encoding='utf-8').read()
content = content.replace('                if str(e) == "Download cancelled by user":', '                if str(e) == "Download cancelled by user" or self.active_tasks.get(task_id, False):')
open('src/backend/downloader.py', 'w', encoding='utf-8').write(content)
print("Done")
