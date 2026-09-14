"""
generate_msix_assets.py
Generates full set of unplated, targetsize, and scale variants for MSIX packaging.
This eliminates the colored plate (blue box/border) in the Windows taskbar right-click jump list.
"""

import os
from PIL import Image

def generate_assets():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    assets_dir = os.path.abspath(os.path.join(script_dir, "..", "assets"))
    src_icon = os.path.join(assets_dir, "icon.png")

    if not os.path.exists(src_icon):
        print(f"Error: Source icon not found at {src_icon}")
        return False

    im = Image.open(src_icon).convert("RGBA")
    print(f"Loaded master icon from {src_icon} ({im.size[0]}x{im.size[1]})")

    # 1. Square44x44Logo target sizes and unplated variants
    target_sizes = [16, 20, 24, 30, 32, 36, 40, 44, 48, 60, 64, 72, 80, 96, 256]
    for size in target_sizes:
        resized = im.resize((size, size), Image.Resampling.LANCZOS)
        
        # Standard targetsize
        p1 = os.path.join(assets_dir, f"Square44x44Logo.targetsize-{size}.png")
        resized.save(p1, "PNG")
        
        # Unplated variant (prevents blue background tile in taskbar right-click menu)
        p2 = os.path.join(assets_dir, f"Square44x44Logo.targetsize-{size}_altform-unplated.png")
        resized.save(p2, "PNG")

        # Alternate naming convention supported by Windows resource indexing
        p3 = os.path.join(assets_dir, f"Square44x44Logo.altform-unplated_targetsize-{size}.png")
        resized.save(p3, "PNG")

    # 2. Square44x44Logo scale variants
    scales_44 = {
        100: 44,
        125: 55,
        150: 66,
        200: 88,
        400: 176
    }
    for scale, size in scales_44.items():
        resized = im.resize((size, size), Image.Resampling.LANCZOS)
        p = os.path.join(assets_dir, f"Square44x44Logo.scale-{scale}.png")
        resized.save(p, "PNG")

    # 3. Square150x150Logo scale variants
    scales_150 = {
        100: 150,
        125: 188,
        150: 225,
        200: 300,
        400: 600
    }
    for scale, size in scales_150.items():
        resized = im.resize((size, size), Image.Resampling.LANCZOS)
        p = os.path.join(assets_dir, f"Square150x150Logo.scale-{scale}.png")
        resized.save(p, "PNG")

    # 4. StoreLogo scale variants
    scales_store = {
        100: 50,
        125: 63,
        150: 75,
        200: 100,
        400: 200
    }
    for scale, size in scales_store.items():
        resized = im.resize((size, size), Image.Resampling.LANCZOS)
        p = os.path.join(assets_dir, f"StoreLogo.scale-{scale}.png")
        resized.save(p, "PNG")

    # Ensure base 44x44 and 150x150 logos exist
    im.resize((44, 44), Image.Resampling.LANCZOS).save(os.path.join(assets_dir, "Square44x44Logo.png"), "PNG")
    im.resize((150, 150), Image.Resampling.LANCZOS).save(os.path.join(assets_dir, "Square150x150Logo.png"), "PNG")
    im.resize((50, 50), Image.Resampling.LANCZOS).save(os.path.join(assets_dir, "StoreLogo.png"), "PNG")

    print("All MSIX icon and unplated tile assets generated successfully!")
    return True

if __name__ == "__main__":
    generate_assets()
