import os
import base64
from PIL import Image

def get_local_creatives(directory="input_images"):
    """
    Scans the directory for images and returns a list of dictionaries with 
    metadata and base64 encoded content.
    """
    creatives = []
    supported_extensions = ('.png', '.jpg', '.jpeg', '.webp', '.gif')
    
    if not os.path.exists(directory):
        os.makedirs(directory)
        return []

    for filename in os.listdir(directory):
        if filename.lower().endswith(supported_extensions):
            path = os.path.join(directory, filename)
            try:
                with Image.open(path) as img:
                    width, height = img.size
                
                # Convert to base64 for injection into browser
                with open(path, "rb") as image_file:
                    encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
                
                creatives.append({
                    "name": filename,
                    "width": width,
                    "height": height,
                    "base64": f"data:image/{img.format.lower()};base64,{encoded_string}"
                })
            except Exception as e:
                print(f"[IMAGE-UTILS] Error loading {filename}: {e}")
                
    print(f"[IMAGE-UTILS] Loaded {len(creatives)} creatives from {directory}")
    return creatives

def find_best_match(ad_slot, creatives, tolerance=20):
    """
    Finds a creative that fits the ad slot dimensions within a given tolerance.
    """
    for creative in creatives:
        w_diff = abs(creative['width'] - ad_slot['width'])
        h_diff = abs(creative['height'] - ad_slot['height'])
        
        if w_diff <= tolerance and h_diff <= tolerance:
            return creative
    return None
