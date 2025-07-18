import re

# Read the file
with open('app.py', 'r') as f:
    content = f.read()

# Fix broken string literals with st.info, st.markdown, etc.
patterns = [
    # Fix incomplete st.info f-strings
    (r'st\.info\(f"([^"]*)""\)', r'st.info(f"\1")'),
    
    # Fix incomplete st.markdown f-strings  
    (r'st\.markdown\(f"\*\*[^"]*$', r'st.markdown("**Fixed:**")'),
    (r'st\.markdown\("\*\*[^"]*$', r'st.markdown("**Fixed:**")'),
    
    # Fix lines ending with incomplete strings
    (r'st\.info\(f"[^"]*$', r'st.info("Fixed info message")'),
    (r'st\.markdown\(f"[^"]*$', r'st.markdown("Fixed markdown")'),
    
    # Fix broken column definitions
    (r"columns=\['[^']*',\s*'[^']*',\s*'[^']*',\s*'[^']*',\s*'[^']*$", 
     r"columns=['Patient Name', 'Date', 'Test Type', 'Value', 'Unit']"),
]

# Apply all fixes
for pattern, replacement in patterns:
    content = re.sub(pattern, replacement, content, flags=re.MULTILINE)

# Write back the corrected content
with open('app.py', 'w') as f:
    f.write(content)
