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
        """Return full document page showing the test result."""
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
                # Return full page with highlighted areas
                full_page = image.copy()
                draw = ImageDraw.Draw(full_page)
                
                # Highlight the found areas on the full page
                for coord in found_coords:
                    x, y, w, h = coord
                    # Draw rectangle around found text
                    draw.rectangle([(x, y), (x + w, y + h)], outline='red', width=3)
                
                # Convert to bytes
                img_buffer = io.BytesIO()
                full_page.save(img_buffer, format='PNG')
                return img_buffer.getvalue()
        
        return None
    
    def get_context_snippet(self, search_text: str) -> bytes:
        """Return full document page showing the search text."""
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
                # Return full page with highlighted areas
                full_page = image.copy()
                draw = ImageDraw.Draw(full_page)
                
                # Highlight all found text occurrences
                for coord in found_coords:
                    x, y, w, h = coord
                    draw.rectangle([(x, y), (x + w, y + h)], outline='blue', width=3)
                
                # Convert to bytes
                img_buffer = io.BytesIO()
                full_page.save(img_buffer, format='PNG')
                return img_buffer.getvalue()
        
        return None