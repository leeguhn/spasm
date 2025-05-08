import os
import datetime
import tkinter as tk
from tkinter import filedialog, messagebox, colorchooser
import platform
import subprocess
import cv2
import numpy as np
from PIL import Image, ImageTk
from maker import extract_lines_from_image, get_flickr_image, create_edge_based_composition

# Set your Flickr API key and secret here
FLICKR_API_KEY = 'a732c6eb5a00e2c2ab05b0080a511926'
FLICKR_API_SECRET = 'bd4a5acb5fa82c14'

class ContourImage:
    def __init__(self, image_path, low, high, master, max_size=300):
        self.image_path = image_path
        self.low = low
        self.high = high
        self.image = Image.open(image_path)
        
        # Resize the image while maintaining aspect ratio
        width, height = self.image.size
        if width > height:
            new_width = min(width, max_size)
            new_height = int(height * (new_width / width))
        else:
            new_height = min(height, max_size)
            new_width = int(width * (new_height / height))
        
        self.image = self.image.resize((new_width, new_height), Image.LANCZOS)
        self.photo = ImageTk.PhotoImage(self.image, master=master)

def show_contour_options(image, output_folder):
    def on_click(index):
        nonlocal selected
        selected = index
        window.quit()

    window = tk.Toplevel()
    window.title("Select Contour Version")
    window.geometry("800x600")  # Set a default window size

    canvas = tk.Canvas(window)
    scrollbar = tk.Scrollbar(window, orient="horizontal", command=canvas.xview)
    scrollable_frame = tk.Frame(canvas)

    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(
            scrollregion=canvas.bbox("all")
        )
    )

    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(xscrollcommand=scrollbar.set)

    thresholds = [(75, 200), (100, 250), (250, 400)]
    contour_images = []
    buttons = []

    # Create a folder for contour images
    contour_folder = os.path.join(output_folder, 'contours')
    os.makedirs(contour_folder, exist_ok=True)

    max_height = 0
    for i, (low, high) in enumerate(thresholds):
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Ensure low and high are integers
        low = int(low)
        high = int(high)

        # Apply threshold
        _, thresh = cv2.threshold(gray, low, high, cv2.THRESH_BINARY)
        
        # Save the contour image to the contour folder
        contour_image_path = os.path.join(contour_folder, f'contour_{low}_{high}.jpg')
        cv2.imwrite(contour_image_path, thresh)
        print(f"Saved contour image: {contour_image_path}")
        
        # Create a ContourImage object with resizing
        contour_image = ContourImage(contour_image_path, low, high, master=window, max_size=300)
        contour_images.append(contour_image)
        
        # Create a button for the contour image
        button = tk.Button(scrollable_frame, image=contour_image.photo, command=lambda idx=i: on_click(idx))
        button.image = contour_image.photo  # Keep a reference to the photo
        button.pack(side="left", padx=10, pady=10)
        buttons.append(button)

        max_height = max(max_height, contour_image.photo.height())

    canvas.pack(side="top", fill="both", expand=True)
    scrollbar.pack(side="bottom", fill="x")

    # Set the canvas height to match the tallest image
    canvas.configure(height=max_height + 40)  # Add some padding

    selected = None
    window.mainloop()
    window.destroy()

    return contour_images[selected].image_path if selected is not None else None

def process_local_image(image_path, output_folder):
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"Failed to load image from {image_path}")
    
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    thresholds = [(1, 200), (200, 350), (350, 500)]
    contour_images = []
    
    # Create a folder for contour images
    contour_folder = os.path.join(output_folder, 'contours')
    os.makedirs(contour_folder, exist_ok=True)
    
    for i, (low, high) in enumerate(thresholds):
        edges = cv2.Canny(gray, low, high)
        
        # Save the contour image to the contour folder
        contour_image_path = os.path.join(contour_folder, f'contour_{low}_{high}.jpg')
        cv2.imwrite(contour_image_path, edges)
        print(f"Saved contour image: {contour_image_path}")
        
        contour_images.append(contour_image_path)
    
    return contour_images

def start_processing(local_image_path, contour_image_path, output_folder, num_drawings, background_color=(255, 255, 255), preextracted_folder=None, max_dots_limit=10000, png_size_multiplier=6.66):
    try:
        now = datetime.datetime.now().strftime("%m%d%Y_%I%M%p")
        final_output_folder = os.path.join(output_folder, now)
        
        counter = 1
        while os.path.exists(final_output_folder):
            final_output_folder = f"{os.path.join(output_folder, now)}_{counter}"
            counter += 1

        # Create the output folder
        os.makedirs(final_output_folder, exist_ok=True)
        print(f"Created output folder: {final_output_folder}")

        if preextracted_folder:
            line_images_folder = preextracted_folder
            print(f"Using pre-extracted images from: {line_images_folder}")
        else:
            # Extract lines from local image
            line_images_folder = os.path.join(final_output_folder, 'extracted_lines')
            extract_lines_from_image(local_image_path, line_images_folder)
            print(f"Extracted lines from local image to: {line_images_folder}")

        # Load the contour image
        contour_image = cv2.imread(contour_image_path, cv2.IMREAD_GRAYSCALE)

        # Create compositions
        create_edge_based_composition(
            cv2.imread(contour_image_path), 
            line_images_folder, 
            final_output_folder, 
            num_drawings, 
            contour_image, 
            background_color=background_color, 
            max_dots_limit=max_dots_limit, 
            png_size_multiplier=png_size_multiplier
        )

        # Open the output folder
        if platform.system() == "Windows":
            os.startfile(final_output_folder)
        elif platform.system() == "Darwin":  # macOS
            subprocess.run(["open", final_output_folder])
        elif platform.system() == "Linux":
            subprocess.run(["xdg-open", final_output_folder])

        messagebox.showinfo("Completed", "Processing completed and files saved!")
    except Exception as e:
        messagebox.showerror("Error", f"An error occurred: {e}")
        print(f"An error occurred: {e}")

def create_gui():
    def select_line_image():
        file_path = filedialog.askopenfilename(filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp")])
        if file_path:
            line_image_path.set(file_path)

    def select_contour_image():
        file_path = filedialog.askopenfilename(filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp")])
        if file_path:
            contour_image_path.set(file_path)

    def select_output_folder():
        folder_path = filedialog.askdirectory(title="Select output folder")
        if folder_path:
            output_folder.set(folder_path)

    def select_preextracted_folder():
        folder_path = filedialog.askdirectory(title="Select folder with pre-extracted images")
        if folder_path:
            preextracted_folder.set(folder_path)

    def toggle_image_source():
        if use_preextracted.get():
            line_image_entry.config(state="disabled")
            line_image_button.config(state="disabled")
            preextracted_entry.config(state="normal")
            preextracted_button.config(state="normal")
        else:
            line_image_entry.config(state="normal")
            line_image_button.config(state="normal")
            preextracted_entry.config(state="disabled")
            preextracted_button.config(state="disabled")

    def toggle_contour_source():
        if use_flickr.get():
            flickr_prompt_entry.config(state="normal")
            contour_image_entry.config(state="disabled")
            contour_image_button.config(state="disabled")
        else:
            flickr_prompt_entry.config(state="disabled")
            contour_image_entry.config(state="normal")
            contour_image_button.config(state="normal")

    def choose_color():
        color = colorchooser.askcolor(title="Choose background color")
        if color[1]:
            background_color.set(color[1])
            color_button.config(bg=color[1])

    def run():
        if use_preextracted.get():
            if not preextracted_folder.get():
                messagebox.showerror("Error", "Please select a folder with pre-extracted images.")
                return
        else:
            if not line_image_path.get():
                messagebox.showerror("Error", "Please select a local image for line extraction.")
                return
        
        if not output_folder.get():
            messagebox.showerror("Error", "Please select an output folder.")
            return
        
        contour_image = None
        if use_flickr.get():
            if not flickr_prompt.get():
                messagebox.showerror("Error", "Please enter a Flickr search prompt.")
                return
            contour_image = get_flickr_image(FLICKR_API_KEY, FLICKR_API_SECRET, flickr_prompt.get())
            if contour_image is None:
                messagebox.showerror("Error", "Failed to retrieve image from Flickr.")
                return
        else:
            if not contour_image_path.get():
                messagebox.showerror("Error", "Please select a local image for contour structure.")
                return
            contour_image = cv2.imread(contour_image_path.get())
            if contour_image is None:
                messagebox.showerror("Error", "Failed to load local contour image.")
                return
        
        selected_contour_path = show_contour_options(contour_image, output_folder.get())
        
        if not selected_contour_path:
            messagebox.showerror("Error", "No contour image selected.")
            return
        
        # Convert hex color to RGB tuple
        bg_color = tuple(int(background_color.get()[1:][i:i+2], 16) for i in (0, 2, 4))
        
        try:
            max_dots = int(max_dots_limit.get())
            png_multiplier = float(png_size_multiplier.get())
        except ValueError:
            messagebox.showerror("Error", "Max Dots Limit or PNG Multiplier must be a valid integer.")
            return
        
        start_processing(
            line_image_path.get() if not use_preextracted.get() else None,
            selected_contour_path,
            output_folder.get(), 
            int(num_drawings.get()),
            background_color=bg_color,
            preextracted_folder=preextracted_folder.get() if use_preextracted.get() else None,
            max_dots_limit=max_dots,
            png_size_multiplier=png_multiplier  # Add this new parameter
        )

    root = tk.Tk()
    root.title("Drawing Disassembly Tool")

    # Variables
    line_image_path = tk.StringVar()
    contour_image_path = tk.StringVar()
    flickr_prompt = tk.StringVar()
    output_folder = tk.StringVar()
    num_drawings = tk.StringVar(value='5')
    use_flickr = tk.BooleanVar(value=True)
    background_color = tk.StringVar(value="#FFFFFF")  # Default white
    use_preextracted = tk.BooleanVar(value=False)
    preextracted_folder = tk.StringVar()
    max_dots_limit = tk.StringVar(value='10000')  # Default value

    # Layout
    tk.Label(root, text="Image Source:").grid(row=0, column=0, padx=5, pady=5)
    tk.Radiobutton(root, text="Use Single Image", variable=use_preextracted, value=False, command=toggle_image_source).grid(row=0, column=1, sticky="w", padx=5, pady=5)
    tk.Radiobutton(root, text="Use Pre-extracted Images", variable=use_preextracted, value=True, command=toggle_image_source).grid(row=0, column=1, sticky="e", padx=5, pady=5)

    tk.Label(root, text="Local Image for Line Extraction:").grid(row=1, column=0, padx=5, pady=5)
    line_image_entry = tk.Entry(root, textvariable=line_image_path, width=50)
    line_image_entry.grid(row=1, column=1, padx=5, pady=5)
    line_image_button = tk.Button(root, text="Browse", command=select_line_image)
    line_image_button.grid(row=1, column=2, padx=5, pady=5)

    tk.Label(root, text="Pre-extracted Images Folder:").grid(row=2, column=0, padx=5, pady=5)
    preextracted_entry = tk.Entry(root, textvariable=preextracted_folder, width=50, state="disabled")
    preextracted_entry.grid(row=2, column=1, padx=5, pady=5)
    preextracted_button = tk.Button(root, text="Browse", command=select_preextracted_folder, state="disabled")
    preextracted_button.grid(row=2, column=2, padx=5, pady=5)

    tk.Label(root, text="Contour Structure Source:").grid(row=3, column=0, padx=5, pady=5)
    tk.Radiobutton(root, text="Use Flickr", variable=use_flickr, value=True, command=toggle_contour_source).grid(row=3, column=1, sticky="w", padx=5, pady=5)
    tk.Radiobutton(root, text="Use Local Image", variable=use_flickr, value=False, command=toggle_contour_source).grid(row=3, column=1, sticky="e", padx=5, pady=5)

    tk.Label(root, text="Flickr Prompt:").grid(row=4, column=0, padx=5, pady=5)
    flickr_prompt_entry = tk.Entry(root, textvariable=flickr_prompt, width=50)
    flickr_prompt_entry.grid(row=4, column=1, padx=5, pady=5)

    tk.Label(root, text="Local Contour Image:").grid(row=5, column=0, padx=5, pady=5)
    contour_image_entry = tk.Entry(root, textvariable=contour_image_path, width=50, state="disabled")
    contour_image_entry.grid(row=5, column=1, padx=5, pady=5)
    contour_image_button = tk.Button(root, text="Browse", command=select_contour_image, state="disabled")
    contour_image_button.grid(row=5, column=2, padx=5, pady=5)

    tk.Label(root, text="Output Folder:").grid(row=6, column=0, padx=5, pady=5)
    tk.Entry(root, textvariable=output_folder, width=50).grid(row=6, column=1, padx=5, pady=5)
    tk.Button(root, text="Browse", command=select_output_folder).grid(row=6, column=2, padx=5, pady=5)

    tk.Label(root, text="Number of Drawings:").grid(row=7, column=0, padx=5, pady=5)
    tk.Entry(root, textvariable=num_drawings).grid(row=7, column=1, padx=5, pady=5)

    tk.Label(root, text="Background Color:").grid(row=8, column=0, padx=5, pady=5)
    color_button = tk.Button(root, text="Choose Color", command=choose_color, bg=background_color.get())
    color_button.grid(row=8, column=1, padx=5, pady=5)

    tk.Label(root, text="Max Dots Limit:").grid(row=9, column=0, padx=5, pady=5)
    max_dots_limit = tk.StringVar(value='10000')
    tk.Entry(root, textvariable=max_dots_limit).grid(row=9, column=1, padx=5, pady=5)

    tk.Label(root, text="Max Size Multiplier:").grid(row=10, column=0, padx=5, pady=5)
    png_size_multiplier = tk.StringVar(value='6.66')  # Default value
    tk.Entry(root, textvariable=png_size_multiplier).grid(row=10, column=1, padx=5, pady=5)

    tk.Button(root, text="Start Processing", command=run).grid(row=11, column=1, padx=5, pady=20)

    # Initialize GUI state
    toggle_image_source()
    toggle_contour_source()

    root.mainloop()

def main():
    create_gui()

if __name__ == "__main__":
    main()