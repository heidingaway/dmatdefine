from typing import List, Tuple
import math

# Define the legend with hex codes and their associated statuses
legend = {
    "00B050": "Green: Collection completed for 2025–26",
    "FF0000": "Red: At risk of being discontinued",
    "FFFF00": "Yellow: Delayed collection",
    "7030A0": "Purple: Ready to start collection",
    "FFC000": "Orange: Waiting for financial confirmation",
    "D0CECE": "Gray: In-kind contribution"
}

# Convert hex color to RGB tuple
def hex_to_rgb(hex_code: str) -> Tuple[int, int, int]:
    hex_code = hex_code.strip("#")
    return tuple(int(hex_code[i:i+2], 16) for i in (0, 2, 4))

# Compute Euclidean distance between two RGB colors
def color_distance(rgb1: Tuple[int, int, int], rgb2: Tuple[int, int, int]) -> float:
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(rgb1, rgb2)))

# Find the closest match from the legend for each color in the dataset
def find_closest_colors(dataset_colors: List[str]) -> List[Tuple[str, str, float]]:
    legend_rgb = {k: hex_to_rgb(k) for k in legend}
    results = []

    for color in dataset_colors:
        color_rgb = hex_to_rgb(color)
        closest_match = None
        min_distance = float('inf')
        for legend_hex, legend_rgb_val in legend_rgb.items():
            dist = color_distance(color_rgb, legend_rgb_val)
            if dist < min_distance:
                min_distance = dist
                closest_match = legend_hex
        results.append((color, closest_match, legend[closest_match]))

    return results

# Example usage
dataset_colors = ["00AF50", "FE0001", "FFFF10", "7130A1", "FFBF00", "D1CECE"]
matches = find_closest_colors(dataset_colors)

for original, match, status in matches:
    print(f"Color {original} is closest to {match} → {status}")
