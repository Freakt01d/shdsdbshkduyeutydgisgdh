from PIL import Image, ImageDraw, ImageFont

# Example coordinates (replace with actual values)
latitude = 45.49
longitude = -122.67
date_time = "2024-05-22 14:30"

# Load your base image
base_image = Image.open("your_image.jpg")

# Create an overlay image with transparent background
overlay = Image.new("RGBA", base_image.size, (255, 255, 255, 0))
draw = ImageDraw.Draw(overlay)

# Add text to the overlay
font = ImageFont.truetype("arial.ttf", 20)
text_color = (255, 255, 255)  # White color
draw.text((10, 10), f"Location: {latitude:.2f}, {longitude:.2f}", fill=text_color, font=font)
draw.text((10, 40), f"Date & Time: {date_time}", fill=text_color, font=font)

# Merge the overlay with the base image
combined_image = Image.alpha_composite(base_image.convert("RGBA"), overlay)

# Save the modified image
combined_image.save("output_image.jpg")

print("Overlay applied successfully!")
