from PIL import Image, ImageDraw, ImageFont

img = Image.new('RGB', (1080, 1080), color=(40, 40, 48))
d = ImageDraw.Draw(img)

try:
    f = ImageFont.truetype('C:/Windows/Fonts/simhei.ttf', 72)
except:
    f = ImageFont.load_default()

d.text((80, 300), '草台就是', fill=(255, 200, 60), font=f)
d.text((80, 420), '最好的班子', fill=(255, 90, 70), font=f)
d.text((80, 560), '办公室的草台', fill=(180, 180, 180), font=f)
d.text((80, 640), '比舞台上的', fill=(180, 180, 180), font=f)
d.text((80, 720), '精彩多了', fill=(180, 180, 180), font=f)

img.save('ai_cover_草台.jpg', 'JPEG', quality=95)
print('Cover created: ai_cover_草台.jpg')
