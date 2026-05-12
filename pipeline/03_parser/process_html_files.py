import os
from html_text import extract_text

def is_coffee_related(text):
    keywords = ["coffee", "caffeine", "espresso", "latte", "cappuccino", "cà phê", "robusta", "arabica", "giá cà phê", "thị trường cà phê", "hạt cà phê", "trồng cà phê", "xuất khẩu cà phê", "pha cà phê"]
    return any(keyword in text.lower() for keyword in keywords)

def process_html_files(input_dir, output_dir):
    for root, dirs, files in os.walk(input_dir):
        for file in files:
            if file.endswith(".html"):
                input_file_path = os.path.join(root, file)
                relative_path = os.path.relpath(root, input_dir)
                output_folder = os.path.join(output_dir, relative_path)
                os.makedirs(output_folder, exist_ok=True)

                output_file_path = os.path.join(output_folder, file)
                with open(input_file_path, "r", encoding="utf-8") as f:
                    html_content = f.read()

                clean_text = extract_text(html_content)

                # Filter: Check if the text is coffee-related and not too short
                if len(clean_text) >= 200 and is_coffee_related(clean_text):
                    with open(output_file_path, "w", encoding="utf-8") as f:
                        f.write(clean_text)

if __name__ == "__main__":
    input_directory = "data/02_rawhtml"
    output_directory = "data/03_articles"
    process_html_files(input_directory, output_directory)