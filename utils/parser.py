import re

def parse_response_files(raw_resp):
    if not raw_resp:
        return [], ""
    
    files = []
    
    # regex 1: === FILE: filename === \n code \n === END FILE ===
    re1 = re.compile(r'={3}\s*FILE:\s*([^\n=]+?)\s*={3}([\s\S]*?)={3}\s*END FILE\s*={3}', re.IGNORECASE)
    
    for match in re1.finditer(raw_resp):
        name = match.group(1).strip()
        code = match.group(2).strip()
        ext = name.split('.')[-1].lower() if '.' in name else 'txt'
        files.append({
            "name": name,
            "ext": ext,
            "code": code
        })
        
    if not files:
        # regex 2: ── filename ── \n ```ext\n code \n ```
        re2 = re.compile(r'\u2500\u2500\s+(\S+)\s+\u2500+\s*\n```(\w*)\n([\s\S]*?)```')
        for match in re2.finditer(raw_resp):
            name = match.group(1).strip()
            ext = match.group(2).strip() or "txt"
            code = match.group(3).strip()
            files.append({
                "name": name,
                "ext": ext,
                "code": code
            })
            
    # Find first index of === FILE: to separate the summary description from code block output
    first_match = re.search(r'={3}\s*FILE:', raw_resp, re.IGNORECASE)
    if first_match:
        summary_text = raw_resp[:first_match.start()].strip()
    else:
        summary_text = raw_resp.strip()
        
    return files, summary_text
