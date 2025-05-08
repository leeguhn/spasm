import cv2
import numpy as np
import os

def extract_and_save_lines(image_path, output_folder):
    """
    Extracts each line from the image, sorts them by area, and saves them as individual PNG files with transparent backgrounds, preserving original colors.
    """
    # Load the image in color
    original_image = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
    
    # Create a grayscale version for processing
    gray_image = cv2.cvtColor(original_image, cv2.COLOR_BGR2GRAY)

    # Apply Gaussian Blur to reduce noise and smooth the image
    blurred = cv2.GaussianBlur(gray_image, (5, 5), 0)

    # Apply Otsu's thresholding to create a binary image
    _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # Apply morphological closing to close gaps in lines
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

    # Find contours in the processed binary image
    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Filter out small contours that are likely noise
    min_contour_area = 500  # Adjust this value based on expected line size
    contours = [c for c in contours if cv2.contourArea(c) > min_contour_area]

    # Sort contours by area (descending order)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)

    # Ensure the output directory exists
    os.makedirs(output_folder, exist_ok=True)

    # Loop over the contours and save each as an individual image
    for i, contour in enumerate(contours):
        # Get the bounding box of the contour with a slight padding
        x, y, w, h = cv2.boundingRect(contour)
        padding = 5  # Adjust padding as needed
        x, y = max(x - padding, 0), max(y - padding, 0)
        w, h = min(w + 2 * padding, original_image.shape[1] - x), min(h + 2 * padding, original_image.shape[0] - y)

        # Extract the region of interest (ROI) containing the line
        line_image = original_image[y:y+h, x:x+w]

        # Create a mask for the contour
        mask = np.zeros((h, w), dtype=np.uint8)
        cv2.drawContours(mask, [contour], -1, 255, thickness=cv2.FILLED, offset=(-x, -y))

        # Smooth the contour edges to remove roughness
        mask = cv2.GaussianBlur(mask, (3, 3), 0)

        # Create a 4-channel (RGBA) image for transparency
        rgba_image = cv2.cvtColor(line_image, cv2.COLOR_BGR2BGRA)
        rgba_image[:, :, 3] = mask

        # Set alpha to 0 for non-line areas
        rgba_image[np.where(mask == 0)] = [0, 0, 0, 0]

        # Save the extracted line as a PNG file with a transparent background
        line_filename = os.path.join(output_folder, f'line_{i+1}.png')
        cv2.imwrite(line_filename, rgba_image)

    print(f"Extracted, sorted, and saved {len(contours)} lines to '{output_folder}'.")