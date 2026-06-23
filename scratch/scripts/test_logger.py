import json
import os
def log_test(info, is_image):
    with open("c:/Users/sayan/Documents/GitHub/Any Downloader/test_log.txt", "w") as f:
        f.write(f"is_image: {is_image}\n")
        f.write(json.dumps(info, indent=2))
