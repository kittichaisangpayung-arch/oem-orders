from PIL import Image
import os

# Open the original logo
img = Image.open('logo.jpg')
print(f'Original size: {img.size[0]}x{img.size[1]} pixels')

# Target size: width 400px, maintain aspect ratio
target_width = 400
aspect_ratio = img.size[1] / img.size[0]
target_height = int(target_width * aspect_ratio)

# Resize with high quality
img_resized = img.resize((target_width, target_height), Image.Resampling.LANCZOS)

# Save as optimized JPEG
img_resized.save('logo_resized.jpg', 'JPEG', quality=95, optimize=True)
print(f'Resized to: {img_resized.size[0]}x{img_resized.size[1]} pixels')
print('Saved as: logo_resized.jpg')
