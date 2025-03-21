#!/usr/bin/env python3
import os
import subprocess
import sys
import platform

def run_command(cmd, shell=False):
    """Executa um comando com subprocess.run e check=True."""
    print("Running:", " ".join(cmd) if not shell else cmd)
    subprocess.run(cmd, shell=shell, check=True)

def main():
    # Obtém o diretório onde o script está (raiz do projeto)
    script_dir = os.path.dirname(os.path.realpath(__file__))
    system = platform.system()

    # Inicializa submódulos
    print("Initializing submodules")
    if system == "Windows":
        run_command(["git", "submodule", "update", "--init", "--recursive"])
    else:
        run_command(["sudo", "git", "submodule", "update", "--init", "--recursive"])

    # Como todos os scripts foram convertidos para Python, não há necessidade de ajustar permissões de arquivos .sh
    print("No need to adjust script permissions; all scripts are now in Python.")

    # Cria link simbólico para "mockshadow" de forma que possa ser chamado de qualquer diretório
    mockshadow_path = os.path.join(script_dir, "mockshadow")
    if system == "Windows":
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

    # Build do clang-code-extractor usando a versão Python (build.py)
    print("Building clang-code-extractor")
    clang_dir = os.path.join(script_dir, "clang-code-extractor")
    os.chdir(clang_dir)
    # Executa o build.py; se necessário, adicione sudo conforme seu ambiente
    run_command([sys.executable, "build.py"])
    os.chdir(script_dir)

    print("mockshadow setup complete!")

if __name__ == "__main__":
    main()
