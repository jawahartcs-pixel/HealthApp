"""
Image Snippet Extractor for OCR Results
Extracts specific portions of images based on OCR coordinates.
"""

import io
from PIL import Image, ImageDraw
import pytesseract
from pdf2image import convert_from_bytes

class ImageSnippetExtractor:
    def __init__(self):
        self.ocr_data = []
        self.ocr_images = []
    
    def process_pdf_for_snippets(self, pdf_bytes: bytes):
        """Process PDF and store OCR data for snippet extraction."""
        try:
            # Configure tesseract for better accuracy
            custom_config = r'--oem 3 --psm 6'
            
            # Convert PDF to images with high DPI
            images = convert_from_bytes(pdf_bytes, dpi=300, fmt='PNG')
            self.ocr_images = images
            self.ocr_data = []
            
            for i, image in enumerate(images):
                # Get OCR data with position information
                ocr_data = pytesseract.image_to_data(image, config=custom_config, output_type=pytesseract.Output.DICT)
                
                # Store OCR data for this page
                page_ocr_data = {
                    'page_num': i,
                    'image': image,
                    'text_data': ocr_data
                }
                self.ocr_data.append(page_ocr_data)
            
            return True
        except Exception as e:
            print(f"Error processing PDF for snippets: {str(e)}")
            return False
    
    def get_image_snippet_for_test(self, test_name: str, test_value: str) -> bytes:
        """Extract image snippet showing the specific test result from OCR data."""
        if not self.ocr_data:
            return None
        
        for page_data in self.ocr_data:
            image = page_data['image']
            text_data = page_data['text_data']
            
            # Find the test name and value in OCR data
            found_coords = []
            
            # Search for test name (partial matches)
            test_name_lower = test_name.lower()
            for i, text in enumerate(text_data['text']):
                if text.strip() and any(word in text.lower() for word in test_name_lower.split() if len(word) > 2):
                    x, y, w, h = text_data['left'][i], text_data['top'][i], text_data['width'][i], text_data['height'][i]
                    if w > 0 and h > 0:  # Valid coordinates
                        found_coords.append((x, y, w, h))
            
            # Search for test value
            for i, text in enumerate(text_data['text']):
                if text.strip() and str(test_value) in text:
                    x, y, w, h = text_data['left'][i], text_data['top'][i], text_data['width'][i], text_data['height'][i]
                    if w > 0 and h > 0:  # Valid coordinates
                        found_coords.append((x, y, w, h))
            
            if found_coords:
                # Find bounding box for all found coordinates
                min_x = min(coord[0] for coord in found_coords)
                min_y = min(coord[1] for coord in found_coords)
                max_x = max(coord[0] + coord[2] for coord in found_coords)
                max_y = max(coord[1] + coord[3] for coord in found_coords)
                
                # Add padding around the found area
                padding = 100  # Increased padding for better context
                crop_x1 = max(0, min_x - padding)
                crop_y1 = max(0, min_y - padding)
                crop_x2 = min(image.width, max_x + padding)
                crop_y2 = min(image.height, max_y + padding)
                
                # Ensure minimum snippet size
                min_width, min_height = 200, 100
                if crop_x2 - crop_x1 < min_width:
                    center_x = (crop_x1 + crop_x2) // 2
                    crop_x1 = max(0, center_x - min_width // 2)
                    crop_x2 = min(image.width, crop_x1 + min_width)
                
                if crop_y2 - crop_y1 < min_height:
                    center_y = (crop_y1 + crop_y2) // 2
                    crop_y1 = max(0, center_y - min_height // 2)
                    crop_y2 = min(image.height, crop_y1 + min_height)
                
                # Crop the image
                snippet = image.crop((crop_x1, crop_y1, crop_x2, crop_y2))
                
                # Highlight the found areas in the snippet
                snippet_copy = snippet.copy()
                draw = ImageDraw.Draw(snippet_copy)
                
                for coord in found_coords:
                    x, y, w, h = coord
                    # Adjust coordinates to snippet space
                    adj_x = x - crop_x1
                    adj_y = y - crop_y1
                    adj_x2 = adj_x + w
                    adj_y2 = adj_y + h
                    
                    # Draw rectangle around found text
                    if 0 <= adj_x < snippet.width and 0 <= adj_y < snippet.height:
                        draw.rectangle([(adj_x, adj_y), (adj_x2, adj_y2)], outline='red', width=2)
                
                # Convert to bytes
                img_buffer = io.BytesIO()
                snippet_copy.save(img_buffer, format='PNG')
                return img_buffer.getvalue()
        
        return None
    
    def get_context_snippet(self, search_text: str) -> bytes:
        """Get a snippet for any search text in the document."""
        if not self.ocr_data:
            return None
        
        for page_data in self.ocr_data:
            image = page_data['image']
            text_data = page_data['text_data']
            
            # Find search text in OCR data
            found_coords = []
            search_lower = search_text.lower()
            
            for i, text in enumerate(text_data['text']):
                if text.strip() and search_lower in text.lower():
                    x, y, w, h = text_data['left'][i], text_data['top'][i], text_data['width'][i], text_data['height'][i]
                    if w > 0 and h > 0:
                        found_coords.append((x, y, w, h))
            
            if found_coords:
                # Get first found occurrence
                x, y, w, h = found_coords[0]
                
                # Create snippet around the found text
                padding = 150
                crop_x1 = max(0, x - padding)
                crop_y1 = max(0, y - padding)
                crop_x2 = min(image.width, x + w + padding)
                crop_y2 = min(image.height, y + h + padding)
                
                # Crop and highlight
                snippet = image.crop((crop_x1, crop_y1, crop_x2, crop_y2))
                snippet_copy = snippet.copy()
                draw = ImageDraw.Draw(snippet_copy)
                
                # Highlight found text
                adj_x = x - crop_x1
                adj_y = y - crop_y1
                draw.rectangle([(adj_x, adj_y), (adj_x + w, adj_y + h)], outline='blue', width=3)
                
                # Convert to bytes
                img_buffer = io.BytesIO()
                snippet_copy.save(img_buffer, format='PNG')
                return img_buffer.getvalue()
        
        return None