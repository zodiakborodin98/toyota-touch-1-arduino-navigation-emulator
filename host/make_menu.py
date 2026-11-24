"""Generate the neutral 480×234 source menu. Requires Pillow and a Cyrillic font."""
from argparse import ArgumentParser
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def make_menu(font_path):
    image = Image.new('RGB', (480, 234), '#182028')
    draw = ImageDraw.Draw(image)
    title = ImageFont.truetype(font_path, 25)
    label = ImageFont.truetype(font_path, 17)
    draw.text((8, 4), 'Источник', fill='#f1f3f1', font=title)
    buttons = [('Назад', 350, 5, 120, 33)]
    for i, name in enumerate(('FM', 'AM', 'CD', 'AUX', 'CarPlay')):
        buttons.append((name, 8 + (i % 3) * 156, 45 + (i // 3) * 56, 147, 48))
    for name, x, y, width, height in buttons:
        draw.rounded_rectangle((x, y, x + width - 1, y + height - 1),
                               radius=5, fill='#222d38', outline='#dcab52', width=2)
        draw.text((x + width / 2, y + height / 2), name,
                  anchor='mm', fill='#f1f3f1', font=label)
    return image


if __name__ == '__main__':
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('--font', default='DejaVuSans.ttf')
    parser.add_argument('--output', type=Path, default=Path(__file__).with_name('source-menu.bmp'))
    args = parser.parse_args()
    make_menu(args.font).save(args.output)
