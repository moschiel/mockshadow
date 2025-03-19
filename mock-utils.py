#!/usr/bin/env python3
#  Created on: 18 de mar de 2025
#      Author: roger moschiel

import os
import shutil
import sys

def validate_file_exists(file_path: str):
    if not os.path.isfile(file_path):
        print(f"Error: File '{file_path}' does not exist.")
        sys.exit(1)

def validate_directory_exists(directory: str):
    """Termina o script se o diretório não existir."""
    if not os.path.isdir(directory):
        print(f"Error: Directory '{directory}' does not exist.")
        sys.exit(1)

def remove_directory(directory: str):
    """
    Exibe uma mensagem e remove o diretório se ele existir, 
    replicando o comportamento de 'rm -rf DIR'.
    """
    print(f"Removing directory '{directory}'")
    if os.path.isdir(directory):
        shutil.rmtree(directory)

def copy_directory_content(src: str, dest: str):
    """
    Remove o diretório de destino (se existir), cria-o e copia recursivamente
    o conteúdo do diretório 'src' para 'dest', replicando:
      rm -rf "$DEST"
      mkdir -p "$DEST"
      cp -r "$SRC/"* "$DEST"
    """
    if os.path.exists(dest):
        shutil.rmtree(dest)
    os.makedirs(dest)
    for item in os.listdir(src):
        src_item = os.path.join(src, item)
        dest_item = os.path.join(dest, item)
        if os.path.isdir(src_item):
            shutil.copytree(src_item, dest_item)
        else:
            shutil.copy2(src_item, dest_item)

def clone_project_tree(dir_original_project: str, dir_shadow_mocks: str):
    """
    Verifica se o diretório de origem é válido e clona a árvore de
    diretórios (estrutura sem arquivos) de 'dir_original_project' para 'dir_shadow_mocks'.
    """
    if not os.path.isdir(dir_original_project):
        print(f"Erro: '{dir_original_project}' não é um diretório válido.")
        sys.exit(1)

    for root, dirs, _ in os.walk(dir_original_project):
        for d in dirs:
            # Calcula o caminho relativo do diretório em relação ao projeto original
            rel_path = os.path.relpath(os.path.join(root, d), dir_original_project)
            new_dir = os.path.join(dir_shadow_mocks, rel_path)
            os.makedirs(new_dir, exist_ok=True)
