from PIL import Image

img = Image.open('assets/icon.png')
img.save('assets/icon.ico')
print('Converted icon.png to icon.ico')
