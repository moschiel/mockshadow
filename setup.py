#!/usr/bin/python3
import os
import subprocess
import sys
import platform
import shutil
import urllib.request
import zipfile

def run_command(cmd, shell=False):
    """Executa um comando com subprocess.run e check=True."""
    print("Running:", " ".join(cmd) if not shell else cmd)
    subprocess.run(cmd, shell=shell, check=True)

def make_scripts_executable(root_dir):
    """
    Percorre recursivamente o diretório 'root_dir' e define permissões executáveis
    para todos os arquivos com extensão '.py' que possuem shebang.
    (No Windows, isso geralmente não é necessário.)
    """
    for current_root, _, files in os.walk(root_dir):
        for file in files:
            if file.endswith(".py"):
                filepath = os.path.join(current_root, file)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        first_line = f.readline()
                    # Se o arquivo começa com shebang, definir permissão executável
                    if first_line.startswith("#!"):
                        os.chmod(filepath, 0o755)
                except Exception as e:
                    print(f"Warning: cannot change permission for {filepath}: {e}")

def download_clang_code_extractor():
    is_windows = platform.system().lower() == "windows"
    
    # Download clang-code-extractor
    zip_file = "clang-code-extractor.zip"
    clang_extractor_dir = "clang-code-extractor"
    if is_windows:
        url = "https://github.com/moschiel/clang-code-extractor/releases/download/v1.0.0/clang-code-extractor-windows-x64.zip"
    else:
        url = "https://github.com/moschiel/clang-code-extractor/releases/download/v1.0.0/clang-code-extractor-ubuntu-x64.zip"

    # Download the ZIP file
    print(f"Downloading 'clang-code-extractor' from {url}...")
    urllib.request.urlretrieve(url, zip_file)
    
    # Remove old clang-code-extractor directory
    if os.path.exists(clang_extractor_dir):
        shutil.rmtree(clang_extractor_dir)

    # Extract the ZIP file
    print(f"Extracting {zip_file}...")
    with zipfile.ZipFile(zip_file, 'r') as zip_ref:
        zip_ref.extractall(clang_extractor_dir)

    # Remove ZIP file
    os.remove(zip_file)
        

def main():
    # Obtém o diretório onde o script está (raiz do projeto)
    script_dir = os.path.dirname(os.path.realpath(__file__))
    is_windows = platform.system().lower() == "windows"

    if is_windows:
        print("Setting execution permission for scripts")
        make_scripts_executable(script_dir)

    mockshadow_path = os.path.join(script_dir, "mockshadow.py")

    # Cria link simbólico para "mockshadow" de forma que possa ser chamado de qualquer diretório
    if is_windows:
        # No Windows, tente criar um symlink (pode ser necessário executar como administrador ou habilitar o Developer Mode)
        symlink_path = os.path.join(script_dir, "mockshadow_link")
        try:
            if os.path.exists(symlink_path):
                os.remove(symlink_path)
            os.symlink(mockshadow_path, symlink_path)
            print(f"Created symbolic link: {symlink_path}")
            print("Please add this directory to your PATH to use 'mockshadow' from any location.")
        except Exception as e:
            print("Failed to create symbolic link on Windows:", e)
            print("Please add the project directory to your PATH manually.")
    else:
        # Em Linux/Unix, cria o link em /usr/local/bin
        symlink_path = "/usr/local/bin/mockshadow"
        print(f"Adding symbolic link for '{mockshadow_path}' into '{symlink_path}'")
        run_command(["sudo", "rm", "-f", symlink_path])
        run_command(["sudo", "ln", "-s", mockshadow_path, symlink_path])

        #apt update
        run_command(["sudo", "apt", "update"])
        #CMake
        run_command(["sudo", "apt", "install", "cmake"])
        #CLang
        run_command(["sudo", "apt", "install", "clang"])
        # Reinstall libclang-18-dev para corrigir o erro do CMake
        run_command(["sudo", "apt", "install", "--reinstall", "libclang-18-dev"])


    download_clang_code_extractor()

    print("mockshadow setup complete!")

if __name__ == "__main__":
    main()
