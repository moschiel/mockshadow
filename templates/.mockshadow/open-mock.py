import os
import sys
import subprocess
import tkinter as tk

paste_clipboard_content=False

def get_clipboard_content():
    try:
        root = tk.Tk()
        root.withdraw()
        content = root.clipboard_get()
        root.destroy()
        return content
    except Exception as e:
        return ""

def main():
    if len(sys.argv) < 2:
        print("Uso: python script.py <caminho/para/o/arquivo>")
        sys.exit(1)
    
    # Caminho do arquivo original
    original_file = sys.argv[1]
    if not os.path.isfile(original_file):
        print(f"Arquivo '{original_file}' não encontrado.")
        sys.exit(1)
    
    # Verifica se a extensão do arquivo é .c ou .h
    valid_extensions = ['.c', '.h']
    _, ext = os.path.splitext(original_file)
    if ext.lower() not in valid_extensions:
        print("O arquivo deve ser .c ou .h para prosseguir.")
        sys.exit(1)
    
    # Define os diretórios do workspace
    workspace_root = os.getcwd()
    temp_project_root = os.path.join(workspace_root, "TEMP_PROJECT")
    mock_tree_root = os.path.join(workspace_root, "MOCK_TREE")
    
    # Verifica se o arquivo está dentro do TEMP_PROJECT
    isInsideValidDir = True
    try:
        rel_path = os.path.relpath(original_file, temp_project_root)
    except ValueError:
        isInsideValidDir = False
        #print("Erro: o arquivo não está dentro do diretório TEMP_PROJECT.")
        #sys.exit(1)

    # ou se o arquivo está dentro do MOCK_TREE
    if isInsideValidDir == False:
        try:
            rel_path = os.path.relpath(original_file, mock_tree_root)
        except ValueError:
            print("Erro: o arquivo não está dentro do diretório TEMP_PROJECT ou do diretório MOCK_TREE.")
            sys.exit(1)
    
    if rel_path.startswith(".."):
        print("Erro: o arquivo não está dentro do diretório TEMP_PROJECT ou do diretório MOCK_TREE.")
        sys.exit(1)
    
    # Obtém o caminho relativo (ex.: "path/to/file.c")
    rel_dir = os.path.dirname(rel_path)
    original_filename = os.path.basename(original_file)
    
    # Cria a mesma estrutura de diretórios em MOCK_TREE
    target_dir = os.path.join(mock_tree_root, rel_dir)
    os.makedirs(target_dir, exist_ok=True)
    
    # Define o nome do arquivo mock com prefixo "__mock__"
    mock_filename = "__mock__" + original_filename
    mock_file_path = os.path.join(target_dir, mock_filename)
    
    # Se o arquivo mock não existir, cria-o
    if not os.path.exists(mock_file_path):
        with open(mock_file_path, "w", encoding="utf-8") as f:
            f.write("")
        with open(mock_file_path, "a", encoding="utf-8") as f:
            f.write("//__MOCK_COPY_FILE_CONTENT__")

    if paste_clipboard_content:
        # Lê o conteúdo do clipboard (seleção ou o que foi copiado)
        clipboard_content = get_clipboard_content().strip()
        if clipboard_content:
            # Monta o bloco a ser inserido (com uma linha em branco antes)
            block="\n\n//__MOCK_REPLACE_START: function name\n" + clipboard_content + "\n//__MOCK_REPLACE_END\n"
            # Abre o arquivo mock em modo append e insere o bloco
            with open(mock_file_path, "a", encoding="utf-8") as f:
                f.write(block)
    
    # Abre o arquivo mock no VS Code e garante que a aba seja selecionada
    subprocess.run(["code", "--goto", mock_file_path])

if __name__ == "__main__":
    main()
