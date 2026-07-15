import os

from .compression import (
    remove_comments,
    compact_blank_lines,
)

class SkeletonGenerator:
    def generate(self, content, filepath):
        raise NotImplementedError

class PythonSkeleton(SkeletonGenerator):
    def generate(self, content, filepath):
        import os
        import warnings
        try:
            import ast
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", SyntaxWarning)
                tree = ast.parse(content, filename=filepath)
            skeleton_lines = []
            
            class SkeletonVisitor(ast.NodeVisitor):
                def __init__(self):
                    self.indent_level = 0
                    
                def visit_ClassDef(self, node):
                    indent = "    " * self.indent_level
                    for dec in node.decorator_list:
                        skeleton_lines.append(f"{indent}@decorator")
                    bases_str = ""
                    if node.bases:
                        bases_str = "(" + ", ".join(ast.unparse(b) for b in node.bases) + ")"
                    skeleton_lines.append(f"{indent}class {node.name}{bases_str}:")
                    
                    self.indent_level += 1
                    docstring = ast.get_docstring(node)
                    if docstring:
                        doc_indent = "    " * self.indent_level
                        skeleton_lines.append(f'{doc_indent}"""{docstring}"""')
                    self.generic_visit(node)
                    self.indent_level -= 1
                    
                def visit_FunctionDef(self, node):
                    indent = "    " * self.indent_level
                    for dec in node.decorator_list:
                        skeleton_lines.append(f"{indent}@decorator")
                    args_str = ast.unparse(node.args)
                    skeleton_lines.append(f"{indent}def {node.name}({args_str}):")
                    
                    self.indent_level += 1
                    doc_indent = "    " * self.indent_level
                    docstring = ast.get_docstring(node)
                    if docstring:
                        skeleton_lines.append(f'{doc_indent}"""{docstring}"""')
                    skeleton_lines.append(f"{doc_indent}pass")
                    self.indent_level -= 1
                    
                def visit_AsyncFunctionDef(self, node):
                    indent = "    " * self.indent_level
                    for dec in node.decorator_list:
                        skeleton_lines.append(f"{indent}@decorator")
                    args_str = ast.unparse(node.args)
                    skeleton_lines.append(f"{indent}async def {node.name}({args_str}):")
                    
                    self.indent_level += 1
                    doc_indent = "    " * self.indent_level
                    docstring = ast.get_docstring(node)
                    if docstring:
                        skeleton_lines.append(f'{doc_indent}"""{docstring}"""')
                    skeleton_lines.append(f"{doc_indent}pass")
                    self.indent_level -= 1
                    
            SkeletonVisitor().visit(tree)
            if not skeleton_lines:
                return "# No classes or functions defined in this file."
            return "\n".join(skeleton_lines)
        except Exception as e:
            return f"# [Error generating skeleton: {str(e)}]\n" + content

class CSkeleton(SkeletonGenerator):
    def generate(self, content, filepath):
        import os
        _, ext = os.path.splitext(filepath)
        ext = ext.lower()
        try:
            content = remove_comments(content, ext)
            skeleton = self.generate_c_style_skeleton(content)
            skeleton = compact_blank_lines(skeleton)
            if not skeleton.strip():
                return f"// No structural elements found in {os.path.basename(filepath)}"
            return skeleton
        except Exception as e:
            return f"// [Error generating skeleton: {str(e)}]\n" + content

    def generate_c_style_skeleton(self, content):
        out = []
        state = 'NORMAL'
        string_char = ''
        escape = False
        block_stack = []
        
        i = 0
        current_text_buffer = ""
        
        while i < len(content):
            c = content[i]
            
            if state == 'NORMAL':
                if c in ('"', "'", '`'):
                    state = 'STRING'
                    string_char = c
                    if not block_stack or block_stack[-1] == True:
                        out.append(c)
                elif c == '{':
                    buffer_stripped = current_text_buffer.strip()
                    import re as regex
                    words = regex.findall(r'\b\w+\b', buffer_stripped)
                    is_container = any(w in words for w in ['class', 'interface', 'struct', 'namespace', 'impl', 'trait'])
                    
                    block_stack.append(is_container)
                    
                    if len(block_stack) == 1 or block_stack[-2] == True:
                        out.append(c)
                        if not is_container:
                            out.append(" pass ")
                    current_text_buffer = ""
                elif c == '}':
                    if block_stack:
                        is_container = block_stack.pop()
                        if len(block_stack) == 0 or block_stack[-1] == True:
                            out.append(c)
                    else:
                        out.append(c)
                    current_text_buffer = ""
                elif c == ';':
                    if not block_stack or block_stack[-1] == True:
                        out.append(c)
                    current_text_buffer = ""
                else:
                    current_text_buffer += c
                    if not block_stack or block_stack[-1] == True:
                        out.append(c)
            elif state == 'STRING':
                if escape:
                    escape = False
                elif c == '\\':
                    escape = True
                elif c == string_char:
                    state = 'NORMAL'
                if not block_stack or block_stack[-1] == True:
                    out.append(c)
            i += 1
            
        return "".join(out)

class JavascriptSkeleton(CSkeleton):
    pass

class GoSkeleton(CSkeleton):
    pass

class RustSkeleton(CSkeleton):
    pass

class JavaSkeleton(CSkeleton):
    pass

class CSharpSkeleton(CSkeleton):
    pass

SKELETON_DISPATCH = {
    ".js": JavascriptSkeleton(),
    ".ts": JavascriptSkeleton(),
    ".jsx": JavascriptSkeleton(),
    ".tsx": JavascriptSkeleton(),
    ".java": JavaSkeleton(),
    ".cs": CSharpSkeleton(),
    ".go": GoSkeleton(),
    ".rs": RustSkeleton(),
    ".py": PythonSkeleton(),
}

def generate_skeleton(content, filepath):
    import os
    _, ext = os.path.splitext(filepath)
    ext = ext.lower()
    
    generator = SKELETON_DISPATCH.get(ext)
    if generator:
        return generator.generate(content, filepath)
        
    return f"# [Skeleton only available for Python and C-style files. Filename: {os.path.basename(filepath)}]"
