import os
from config import IMAGE_FOLDER

def get_image_path(filename):
    path = os.path.join(IMAGE_FOLDER, filename)
    if os.path.exists(path):
        return path
    return None
