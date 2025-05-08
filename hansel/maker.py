import cv2
import numpy as np
import os
import random
import time
from tqdm import tqdm
from flickrapi import FlickrAPI
import requests
from io import BytesIO
from morphological_analysis import extract_and_save_lines

def extract_lines_from_image(image_path, output_folder):
    """
    Extracts lines from a local image and saves them as individual transparent PNGs.
    
    Args:
        image_path (str): Path to the local image.
        output_folder (str): Folder to save extracted line images.
    """
    extract_and_save_lines(image_path, output_folder)

def check_and_resize_image(image, max_dimension=10000):
        h, w = image.shape[:2]
        if max(h, w) > max_dimension:
            scale = max_dimension / max(h, w)
            new_size = (int(w * scale), int(h * scale))
            return cv2.resize(image, new_size, interpolation=cv2.INTER_AREA)
        return image

def get_flickr_image(api_key, api_secret, text_prompt):
    flickr = FlickrAPI(api_key, api_secret, format='parsed-json')
    extras = 'url_c,url_l,url_o,url_m'
    
    photos = flickr.photos.search(text=text_prompt, per_page=20, extras=extras, sort='relevance')
    
    if photos['photos']['total'] == '0':
        print("No photos found for the given prompt.")
        return None
    
    photo = random.choice(photos['photos']['photo'])
    
    url_keys = ['url_c', 'url_l', 'url_o', 'url_m']
    photo_url = next((photo[key] for key in url_keys if key in photo), None)
    
    if photo_url is None:
        print("No suitable URL found for the selected photo.")
        return None
    
    try:
        response = requests.get(photo_url)
        response.raise_for_status()
        image = cv2.imdecode(np.frombuffer(response.content, np.uint8), cv2.IMREAD_COLOR)
        return image
    except requests.exceptions.RequestException as e:
        print(f"Error downloading image: {e}")
        return None

def group_contour_segments(contour, segment_length=50):
    grouped_segments = []
    current_segment = []
    
    for point in contour:
        current_segment.append(point[0])
        if len(current_segment) >= segment_length:
            grouped_segments.append(np.array(current_segment))
            current_segment = [point[0]]
    
    if current_segment:
        grouped_segments.append(np.array(current_segment))
    
    return grouped_segments

def calibrate_parameters(flickr_image, selected_contour_image):
    # Calculate image sizes
    flickr_size = flickr_image.shape[0] * flickr_image.shape[1]
    contour_size = selected_contour_image.shape[0] * selected_contour_image.shape[1]

    # Calculate min and max total size for PNGs
    min_total_size = max(20, int(contour_size / 50000))
    max_total_size = max(500, int(contour_size / 5000))

    # Calculate min and max scales
    min_scale = 0.1
    max_scale = min(5.0, max_total_size / 100)  # Assuming average PNG size is around 100 pixels

    return min_total_size, max_total_size, min_scale, max_scale

def draw_dot_plot(contour_image, max_dots):
    # Invert the image so that black areas become white
    inverted_image = cv2.bitwise_not(contour_image)
    
    # Find contours of both the original and inverted image
    contours, _ = cv2.findContours(contour_image, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    inner_contours, _ = cv2.findContours(inverted_image, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    
    all_contours = contours + inner_contours
    
    dot_plot = np.zeros_like(contour_image)
    
    total_length = sum(cv2.arcLength(contour, True) for contour in all_contours)
    spacing = total_length / max_dots
    
    all_dots = []
    for contour in all_contours:
        contour_length = cv2.arcLength(contour, True)
        num_dots = int(contour_length / spacing)
        if num_dots > 0:
            for i in range(num_dots):
                index = int((i / num_dots) * len(contour))
                x, y = contour[index][0]
                all_dots.append((x, y))
    
    # If we have more dots than max_dots, evenly sample them
    if len(all_dots) > max_dots:
        indices = np.linspace(0, len(all_dots) - 1, max_dots, dtype=int)
        all_dots = [all_dots[i] for i in indices]
    
    for x, y in all_dots:
        cv2.circle(dot_plot, (x, y), 1, 255, -1)
    
    return dot_plot, all_dots

def estimate_required_dots(binary_mask, fill_percentage=0.8, sample_factor=0.1):
    total_black_pixels = np.sum(binary_mask == 255)
    estimated_dots = int(total_black_pixels * fill_percentage * sample_factor)
    return max(estimated_dots, 1000)  # Ensure a minimum number of dots

def fill_black_areas(contour_image, max_dots):
    # Create a mask of the black areas
    _, black_mask = cv2.threshold(contour_image, 1, 255, cv2.THRESH_BINARY_INV)
    
    # Calculate the total area of black regions
    black_area = np.sum(black_mask == 255)
    
    # Calculate the number of dots to place inside black areas
    num_dots = min(max_dots, black_area // 100)  # Adjust this factor as needed
    
    # Create an empty image for the dots
    dot_plot = np.zeros_like(contour_image)
    
    # Get coordinates of all black pixels
    black_coords = np.column_stack(np.where(black_mask == 255))
    
    # Randomly sample from these coordinates
    if len(black_coords) > num_dots:
        selected_coords = black_coords[np.random.choice(len(black_coords), num_dots, replace=False)]
    else:
        selected_coords = black_coords
    
    # Place dots at the selected coordinates
    for y, x in selected_coords:
        cv2.circle(dot_plot, (x, y), 1, 255, -1)
    
    return dot_plot, selected_coords.tolist()

def place_line_on_canvas(canvas, line_image, start_point, end_point):
    start_point = np.array(start_point)
    end_point = np.array(end_point)
    edge_vector = end_point - start_point
    edge_length = np.linalg.norm(edge_vector)
    edge_angle = np.arctan2(edge_vector[1], edge_vector[0])

    line_length = max(line_image.shape[:2])
    scale = min(edge_length / line_length, 1.0)
    scale = max(scale, 0.1)

    if scale < 1.0:
        new_size = tuple(max(1, int(dim * scale)) for dim in line_image.shape[:2])
        line_image = cv2.resize(line_image, new_size[::-1], interpolation=cv2.INTER_AREA)

    rotation_matrix = cv2.getRotationMatrix2D((line_image.shape[1] / 2, line_image.shape[0] / 2), np.degrees(edge_angle), 1)
    rotated_line = cv2.warpAffine(line_image, rotation_matrix, line_image.shape[1::-1])

    overlap = 0.2  # 20% overlap
    step = rotated_line.shape[1] * (1 - overlap)
    
    for i in np.arange(0, 1, step / edge_length):
        position = (start_point + edge_vector * i).astype(int)
        x = position[0] - rotated_line.shape[1] // 2
        y = position[1] - rotated_line.shape[0] // 2

        x = max(0, min(x, canvas.shape[1] - rotated_line.shape[1]))
        y = max(0, min(y, canvas.shape[0] - rotated_line.shape[0]))

        mask = rotated_line[:, :, 3:] / 255.0
        canvas_roi = canvas[y:y+rotated_line.shape[0], x:x+rotated_line.shape[1]]
        if canvas_roi.shape[:2] == rotated_line.shape[:2]:
            canvas_roi[:] = (1 - mask) * canvas_roi + mask * rotated_line[:, :, :3]

import concurrent.futures
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading 

# Define place_png_piece in the global scope
import random
import math

def place_png_piece(canvas, x, y, line_image, min_total_size, max_total_size, min_scale, max_scale, png_size_multiplier):
    # Get original dimensions
    orig_height, orig_width = line_image.shape[:2]
    
    # Calculate the size of the canvas
    canvas_size = canvas.shape[0] * canvas.shape[1]
    
    # Adjust min_total_size and max_total_size based on canvas size
    size_factor = math.sqrt(canvas_size / (2300 * 2300))  # Using 2300x2300 as a reference size
    adjusted_min_size = max(20, int(min_total_size * size_factor))
    adjusted_max_size = max(100, int((max_total_size * size_factor) * png_size_multiplier))
    
    # Generate a random scale factor (keep this part as it was)
    distribution_choice = random.random()
    if distribution_choice < 0.4:
        random_scale = min_scale + (max_scale - min_scale) * random.expovariate(2)
    elif distribution_choice < 0.7:
        random_scale = random.uniform(min_scale, max_scale)
    elif distribution_choice < 0.9:
        random_scale = min_scale + (max_scale - min_scale) * (random.random() ** 2)
    else:
        random_scale = min_scale + (1 - min_scale) * random.random()
    
    random_scale = max(min_scale, min(max_scale, random_scale))
    
    # Calculate new size based on the adjusted min_total_size and max_total_size
    total_size = random.randint(adjusted_min_size, adjusted_max_size)
    aspect_ratio = orig_width / orig_height
    new_height = int(math.sqrt(total_size / aspect_ratio))
    new_width = int(new_height * aspect_ratio)
    
    resized_line_image = cv2.resize(line_image, (new_width, new_height), interpolation=cv2.INTER_AREA)

    # The rest of the function remains the same
    h, w = resized_line_image.shape[:2]
    x_start, y_start = max(0, x - w // 2), max(0, y - h // 2)
    x_end, y_end = min(x_start + w, canvas.shape[1]), min(y_start + h, canvas.shape[0])

    canvas_roi = canvas[y_start:y_end, x_start:x_end]
    png_roi = resized_line_image[:y_end-y_start, :x_end-x_start]

    if canvas_roi.shape[:2] != png_roi.shape[:2]:
        min_height = min(canvas_roi.shape[0], png_roi.shape[0])
        min_width = min(canvas_roi.shape[1], png_roi.shape[1])
        canvas_roi = canvas_roi[:min_height, :min_width]
        png_roi = png_roi[:min_height, :min_width]

    if canvas_roi.shape[0] > 0 and canvas_roi.shape[1] > 0:
        alpha = png_roi[:, :, 3:] / 255.0
        canvas_roi[:] = (1 - alpha) * canvas_roi + alpha * png_roi[:, :, :3]

    return new_width, new_height

def create_contour_probability_map(image, contour_weight=0.7, pixel_weight=0.3, threshold=128):
    if len(image.shape) == 3:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Create a binary mask of dark areas
    _, binary_mask = cv2.threshold(image, threshold, 255, cv2.THRESH_BINARY_INV)
    
    # Find contours on the binary mask
    contours, _ = cv2.findContours(binary_mask, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    
    contour_map = np.zeros_like(image, dtype=float)
    cv2.drawContours(contour_map, contours, -1, 1, 1)
    
    # Use the binary mask for pixel map
    pixel_map = binary_mask.astype(float) / 255.0
    
    combined_map = contour_weight * contour_map + pixel_weight * pixel_map
    
    # Apply the binary mask to the combined map
    combined_map *= (binary_mask / 255.0)
    
    # Normalize probabilities to sum to 1
    total = combined_map.sum()
    if total > 0:
        combined_map /= total
    else:
        print("Warning: No dark areas found in the image.")
    
    return combined_map, contours, binary_mask

def sample_contour_points(contours, prob_map, binary_mask, num_points):
    total_length = sum(cv2.arcLength(contour, True) for contour in contours)
    points_per_unit_length = num_points / total_length
    
    sampled_points = []
    for contour in contours:
        contour_length = cv2.arcLength(contour, True)
        num_contour_points = int(contour_length * points_per_unit_length)
        
        for i in range(num_contour_points):
            t = i / num_contour_points
            point = contour[int(t * len(contour))][0]
            x, y = point
            
            # Only add the point if it's within the binary mask
            if binary_mask[y, x] > 0 and np.random.random() < prob_map[y, x]:
                sampled_points.append((x, y))
    
    return sampled_points

def sample_points(prob_map, binary_mask, num_points):
    # Flatten the probability map and get cumulative probabilities
    flat_prob = prob_map.flatten()
    cumulative_prob = np.cumsum(flat_prob)
    
    # Sample points
    sampled_points = []
    while len(sampled_points) < num_points:
        sampled_index = np.searchsorted(cumulative_prob, np.random.random())
        y, x = np.unravel_index(sampled_index, prob_map.shape)
        
        # Only add the point if it's within the binary mask
        if binary_mask[y, x] > 0:
            sampled_points.append((x, y))
    
    return sampled_points

# MAXX DOT LIMIT

def create_edge_based_composition(flickr_image, line_images_folder, output_folder, num_drawings, selected_contour_image, max_dots_limit=15000, background_color=(255, 255, 255), png_size_multiplier=6.66):
    """
    ...
    Args:
        flickr_image: ...
        line_images_folder (str): Path to the folder containing line images (either extracted or pre-extracted)
        ...
    """

    start_time = time.time()
    print("Starting composition creation...")

    os.makedirs(output_folder, exist_ok=True)

    cv2.imwrite(os.path.join(output_folder, 'flickr_reference.jpg'), flickr_image)
    cv2.imwrite(os.path.join(output_folder, 'flickr_contours.jpg'), selected_contour_image)

    # Load line images
    line_images = []
    for file in os.listdir(line_images_folder):
        if file.lower().endswith('.png'):
            img = cv2.imread(os.path.join(line_images_folder, file), cv2.IMREAD_UNCHANGED)
            if img is not None and img.shape[2] == 4:  # Ensure it's RGBA
                line_images.append(img)

    print(f"Loaded {len(line_images)} line images.")
    if not line_images:
        print("Error: No valid line images found.")
        return

    # Call calibrate_parameters to get size-related parameters
    min_total_size, max_total_size, min_scale, max_scale = calibrate_parameters(flickr_image, selected_contour_image)
    print(f"Calibrated parameters: min_total_size={min_total_size}, max_total_size={max_total_size}, min_scale={min_scale:.2f}, max_scale={max_scale:.2f}")

    # Create combined probability map and get contours
    prob_map, contours, binary_mask = create_contour_probability_map(selected_contour_image)
    
    # Estimate initial number of dots
    initial_dots = estimate_required_dots(binary_mask)
    print(f"Initial estimation of required dots: {initial_dots}")

    # Calculate the scale factor to ensure output is at least 8 times larger
    flickr_max_dim = max(flickr_image.shape[:2])
    contour_max_dim = max(selected_contour_image.shape[:2])
    min_scale_factor = (24 * flickr_max_dim) / contour_max_dim
    scale_factor = max(min_scale_factor, contour_max_dim // 150)
    print(f"Using scale factor: {scale_factor}")

    # Initialize variables for iterative dot placement
    all_dots = []
    coverage = 0
    target_coverage = 0.8  # Adjust this value to control the desired coverage
    max_iterations = 10  # Prevent infinite loop

    for iteration in range(max_iterations):
        # Calculate remaining dots
        remaining_dots = max_dots_limit - len(all_dots)
        if remaining_dots <= 0:
            break

        # Sample points along contours
        num_contour_points = min(int(initial_dots * 0.7), remaining_dots)  # 70% of points on contours
        contour_points = sample_contour_points(contours, prob_map, binary_mask, num_contour_points)
        
        # Sample remaining points from dark areas
        num_area_points = min(initial_dots - len(contour_points), remaining_dots - len(contour_points))
        area_points = sample_points(prob_map, binary_mask, num_area_points)
        
        # Combine contour and area points
        new_dots = contour_points + area_points
        all_dots.extend(new_dots)

        # Calculate coverage
        dot_mask = np.zeros_like(binary_mask)
        for x, y in all_dots:
            dot_mask[y, x] = 255
        coverage = np.sum((binary_mask > 0) & (dot_mask > 0)) / np.sum(binary_mask > 0)

        print(f"Iteration {iteration + 1}: Added {len(new_dots)} dots. Total dots: {len(all_dots)}. Coverage: {coverage:.2f}")

        if coverage >= target_coverage:
            break

        # If coverage is not met, add more dots in the next iteration
        initial_dots = min(int(initial_dots * 0.5), remaining_dots)  # Add 50% more dots in the next iteration, but don't exceed the limit

    # Ensure we don't exceed the maximum limit
    if len(all_dots) > max_dots_limit:
        all_dots = all_dots[:max_dots_limit]

    total_dots = len(all_dots)
    print(f"Final number of dots: {total_dots}. Final coverage: {coverage:.2f}")

    cv2.imwrite(os.path.join(output_folder, 'probability_map.jpg'), (prob_map * 255).astype(np.uint8))
    cv2.imwrite(os.path.join(output_folder, 'binary_mask.jpg'), binary_mask)
    cv2.imwrite(os.path.join(output_folder, 'dot_mask.jpg'), dot_mask)

    total_dots = len(all_dots)
    print(f"Final number of dots: {total_dots}. Final coverage: {coverage:.2f}")

    if total_dots == 0:
        print("Error: No points sampled from the probability map.")
        return
    
    # Create a progress bar
    pbar = tqdm(total=num_drawings, desc="Creating compositions")
    last_update = time.time()

    # Set the maximum number of concurrent threads
    max_concurrent_threads = 2  # Adjust this based on your system's capabilities

    # Create a semaphore to limit concurrent threads
    semaphore = threading.Semaphore(max_concurrent_threads)

    def create_single_composition_with_semaphore(iteration, scale_factor):
        with semaphore:
            result = create_single_composition(iteration, scale_factor)
        
        nonlocal last_update
        current_time = time.time()
        if current_time - last_update >= 2:  # Update every 2 seconds
            pbar.update(1)
            last_update = current_time
        
        return result

    def create_single_composition(iteration, scale_factor):
        canvas_width = int(selected_contour_image.shape[1] * scale_factor)
        canvas_height = int(selected_contour_image.shape[0] * scale_factor)
        canvas = np.full((canvas_height, canvas_width, 3), background_color, dtype=np.uint8)

        print(f"Composition {iteration + 1}: Processing {total_dots} pixels.")
        print(f"Canvas size: {canvas_width}x{canvas_height}")

        for x, y in all_dots:
            # Only place a PNG if the corresponding pixel in the binary mask is non-zero
            if binary_mask[y, x] > 0:
                line_image = random.choice(line_images)
                scaled_x = int(x * scale_factor)
                scaled_y = int(y * scale_factor)
                place_png_piece(canvas, scaled_x, scaled_y, line_image, min_total_size, max_total_size, min_scale, max_scale, png_size_multiplier)
        
        # Check and resize the canvas if necessary
        canvas = check_and_resize_image(canvas)

        # Check if the canvas is empty or uniform
        if np.std(canvas) < 1e-5:
            print(f"Warning: Composition {iteration + 1} appears to be empty or uniform.")
        else:
            print(f"Composition {iteration + 1} created successfully.")

        output_path = os.path.join(output_folder, f'composition_{iteration + 1:03d}.jpg')
        success = cv2.imwrite(output_path, canvas, [cv2.IMWRITE_JPEG_QUALITY, 85])

        if success:
            print(f"Saved composition {iteration + 1} to {output_path}")
            # Verify the saved file
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                print(f"Verified: Composition {iteration + 1} saved successfully.")
            else:
                print(f"Error: Composition {iteration + 1} file is missing or empty.")
        else:
            print(f"Error: Failed to save composition {iteration + 1}")
    
        nonlocal last_update
        current_time = time.time()
        if current_time - last_update >= 2:  # Update every 2 seconds
            pbar.update(1)
            last_update = current_time

        return iteration

    # Use a thread pool to create compositions with limited concurrency
    with ThreadPoolExecutor(max_workers=max_concurrent_threads) as executor:
        futures = [executor.submit(create_single_composition_with_semaphore, i, scale_factor) for i in range(num_drawings)]
        
        for future in concurrent.futures.as_completed(futures):
            try:
                iteration = future.result()
            except Exception as e:
                print(f"Error in composition creation: {e}")

    pbar.close()
    print(f"All compositions created in {time.time() - start_time:.2f} seconds")



