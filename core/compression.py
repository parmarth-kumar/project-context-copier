import os

def remove_python_comments(content):
    lines = content.splitlines()
    new_lines = []
    in_multiline_comment = False
    
    for line in lines:
        stripped = line.strip()
        if in_multiline_comment:
            if '"""' in line or "'''" in line:
                in_multiline_comment = False
            continue
        else:
            if stripped.startswith('"""') or stripped.startswith("'''"):
                if (stripped.count('"""') == 2) or (stripped.count("'''") == 2):
                    continue
                else:
                    in_multiline_comment = True
                    continue
                    
        if "#" in line:
            if stripped.startswith("#"):
                continue
            else:
                parts = line.split("#", 1)
                before = parts[0]
                if (before.count('"') % 2 == 0) and (before.count("'") % 2 == 0):
                    line = before
        new_lines.append(line)
    return "\n".join(new_lines)

def remove_c_comments(content):
    lines = content.splitlines()
    new_lines = []
    in_multiline_comment = False
    
    for line in lines:
        stripped = line.strip()
        if in_multiline_comment:
            if "*/" in line:
                in_multiline_comment = False
                parts = line.split("*/", 1)
                if len(parts) > 1 and parts[1].strip():
                    line = parts[1]
                else:
                    continue
            else:
                continue
        else:
            if "/*" in line:
                if "*/" in line:
                    parts = line.split("/*", 1)
                    rest = parts[1].split("*/", 1)
                    line = parts[0] + (rest[1] if len(rest) > 1 else "")
                else:
                    in_multiline_comment = True
                    parts = line.split("/*", 1)
                    if parts[0].strip():
                        line = parts[0]
                    else:
                        continue
                        
        stripped = line.strip()
        if stripped.startswith("//"):
            continue
        elif "//" in line:
            parts = line.split("//", 1)
            before = parts[0]
            if (before.count('"') % 2 == 0) and (before.count("'") % 2 == 0):
                line = before
                
        new_lines.append(line)
    return "\n".join(new_lines)

def remove_js_comments(content):
    return remove_c_comments(content)

def remove_css_comments(content):
    lines = content.splitlines()
    new_lines = []
    in_multiline_comment = False
    
    for line in lines:
        stripped = line.strip()
        if in_multiline_comment:
            if "*/" in line:
                in_multiline_comment = False
                parts = line.split("*/", 1)
                if len(parts) > 1 and parts[1].strip():
                    line = parts[1]
                else:
                    continue
            else:
                continue
        else:
            if "/*" in line:
                if "*/" in line:
                    parts = line.split("/*", 1)
                    rest = parts[1].split("*/", 1)
                    line = parts[0] + (rest[1] if len(rest) > 1 else "")
                else:
                    in_multiline_comment = True
                    parts = line.split("/*", 1)
                    if parts[0].strip():
                        line = parts[0]
                    else:
                        continue
        new_lines.append(line)
    return "\n".join(new_lines)

REMOVE_COMMENTS_DISPATCH = {
    ".py": remove_python_comments,
    ".js": remove_js_comments,
    ".ts": remove_js_comments,
    ".jsx": remove_js_comments,
    ".tsx": remove_js_comments,
    ".kt": remove_c_comments,
    ".java": remove_c_comments,
    ".cpp": remove_c_comments,
    ".css": remove_css_comments,
}

def remove_comments(content, ext):
    handler = REMOVE_COMMENTS_DISPATCH.get(ext)
    if handler:
        return handler(content)
    return content

def compact_indent(content):
    lines = content.splitlines()
    new_lines = []
    for line in lines:
        if line.startswith(" "):
            leading_spaces = len(line) - len(line.lstrip(' '))
            scaled_spaces = (leading_spaces // 4) * 2 + (leading_spaces % 4)
            line = " " * scaled_spaces + line.lstrip(' ')
        new_lines.append(line)
    return "\\n".join(new_lines)

def compact_blank_lines(content):
    lines = content.splitlines()
    compacted_lines = []
    consecutive_empty = 0
    for line in lines:
        if not line.strip():
            consecutive_empty += 1
            if consecutive_empty <= 1:
                compacted_lines.append("")
        else:
            consecutive_empty = 0
            compacted_lines.append(line)
    return "\\n".join(compacted_lines)

def compress_comments_whitespace(content, filepath):
    _, ext = os.path.splitext(filepath)
    ext = ext.lower()
    
    content = remove_comments(content, ext)
    content = compact_indent(content)
    content = compact_blank_lines(content)
    
    return content
