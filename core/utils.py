import os
import subprocess
import socket

def copy_to_clipboard(text):
    try:
        import pyperclip
        pyperclip.copy(text)
        return True
    except ImportError:
        return False


def read_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError:
        return "[Binary file - cannot display content]"
    except Exception as e:
        return f"[Error reading file: {str(e)}]"


def is_git_repo(folder_path):
    if not folder_path or not os.path.exists(folder_path):
        return False
    return os.path.exists(os.path.join(folder_path, ".git"))


def get_git_diff(folder_path):
    if not folder_path or not os.path.exists(folder_path):
        return ""
    if not is_git_repo(folder_path):
        return "[Not a Git repository - cannot run git diff]"
    try:
        res_unstaged = subprocess.run(
            ["git", "diff"],
            cwd=folder_path, capture_output=True, text=True, check=True
        )
        res_staged = subprocess.run(
            ["git", "diff", "--cached"],
            cwd=folder_path, capture_output=True, text=True, check=True
        )
        diff_text = res_unstaged.stdout + "\\n" + res_staged.stdout
        return diff_text.strip()
    except Exception as e:
        return f"[Error running git diff: {str(e)}]"


def generate_project_mermaid_graph(active_files):
    import ast
    defs = {}
    calls = []
    
    for filepath in active_files:
        _, ext = os.path.splitext(filepath)
        if ext.lower() != ".py":
            continue
        try:
            import warnings
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", SyntaxWarning)
                tree = ast.parse(content, filename=filepath)
            current_file = os.path.basename(filepath)
            
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    defs[node.name] = current_file
                    
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    caller = f"{current_file}:{node.name}"
                    for subnode in ast.walk(node):
                        if isinstance(subnode, ast.Call):
                            func_name = None
                            if isinstance(subnode.func, ast.Name):
                                func_name = subnode.func.id
                            elif isinstance(subnode.func, ast.Attribute):
                                func_name = subnode.func.attr
                            if func_name and func_name in defs:
                                callee_file = defs[func_name]
                                callee = f"{callee_file}:{func_name}"
                                if caller != callee:
                                    calls.append((caller, callee))
        except Exception:
            pass
            
    unique_calls = sorted(list(set(calls)))
    mermaid_lines = ["graph TD"]
    files_nodes = {}
    
    for caller, callee in unique_calls:
        c_file, c_func = caller.split(":")
        ce_file, ce_func = callee.split(":")
        if c_file not in files_nodes:
            files_nodes[c_file] = set()
        if ce_file not in files_nodes:
            files_nodes[ce_file] = set()
        files_nodes[c_file].add(c_func)
        files_nodes[ce_file].add(ce_func)
        
    for filename, funcs in files_nodes.items():
        clean_file = filename.replace(".", "_").replace("-", "_")
        mermaid_lines.append(f"    subgraph {clean_file} [\"{filename}\"]")
        for func in funcs:
            mermaid_lines.append(f"        {clean_file}_{func}[\"{func}()\"]")
        mermaid_lines.append("    end")
        
    for caller, callee in unique_calls:
        c_file, c_func = caller.split(":")
        ce_file, ce_func = callee.split(":")
        clean_c_file = c_file.replace(".", "_").replace("-", "_")
        clean_ce_file = ce_file.replace(".", "_").replace("-", "_")
        mermaid_lines.append(f"    {clean_c_file}_{c_func} --> {clean_ce_file}_{ce_func}")
        
    if len(mermaid_lines) <= 1:
        return "```mermaid\\n% No internal function call connections detected.\\n```"
    return "```mermaid\\n" + "\\n".join(mermaid_lines) + "\\n```"


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"
