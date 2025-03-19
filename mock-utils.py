#!/usr/bin/env python3
#  Created on: 18 de mar de 2025
#      Author: roger moschiel

import os
import shutil
import sys
import env # Variaveis de ambiente env.py


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

def list_mocks():
    print("Mock List")
    
    # Percorre recursivamente o diretório DIR_SHADOW_MOCKS
    for root, dirs, files in os.walk(env.DIR_SHADOW_MOCKS):
        for filename in files:
            if filename.startswith("__mock__") or filename.startswith("__additional__"):
                # Obtém o caminho completo do arquivo
                file_path = os.path.join(root, filename)
                # Calcula o caminho relativo a partir de DIR_MOCK_SHADOW_PROJECT
                relative_path = os.path.relpath(file_path, env.DIR_MOCK_SHADOW_PROJECT)
                print(f"  {relative_path}")
    
    print("Mock List Complete!")

def clone_project():
    print(f"Cloning Project {env.DIR_ORIGINAL_PROJECT} to {env.DIR_TEMP_PROJECT}")
    copy_directory_content(env.DIR_ORIGINAL_PROJECT, env.DIR_TEMP_PROJECT)
    
    print("Cloning FreeRTOS")
    print(" ***** TODO: DEPENDENCIA DO PROJETO NAO PODE FICAR AQUI ****")
    print(" ***** TODO: DEPENDENCIA DO PROJETO NAO PODE FICAR AQUI ****")
    print(" ***** TODO: DEPENDENCIA DO PROJETO NAO PODE FICAR AQUI ****")
    
    src_freertos = os.path.join(env.DIR_MOCK_SHADOW_PROJECT, "FreeRTOS")
    dest_freertos = os.path.join(env.DIR_TEMP_PROJECT, "FreeRTOS")
    copy_directory_content(src_freertos, dest_freertos)
    
    #echo "Cloning FreeRTOS+FAT"
    #copy_directory_content "$SCRIPT_MOCKSHADOW_DIR/FreeRTOS+FAT" "$SCRIPT_MOCKSHADOW_DIR/MOCKED_PROJECT/FreeRTOS+FAT"
    
    print("Cloning Complete")

def mount_extractor_extra_args(custom_extra_args: str) -> str:
    # Remove espaços à esquerda dos argumentos customizados
    custom_extra_args = custom_extra_args.lstrip()
    
    # Define o caminho para o arquivo de extra args
    file_path = os.path.join(env.DIR_MOCK_SHADOW_PROJECT, "extractor-global-cflags.txt")
    extra_args_list = []
    
    # Lê o arquivo linha por linha
    try:
        with open(file_path, "r") as f:
            for line in f:
                # Remove quebras de linha e espaços no início/fim
                line = line.replace('\r', '').replace('\n', '').strip()
                if line:  # Se a linha não estiver vazia, adiciona à lista
                    extra_args_list.append(line)
    except FileNotFoundError:
        # Se o arquivo não existir, não adiciona nada
        pass
    
    # Combina os custom_extra_args com os extra args lidos do arquivo
    combined_args = f"{custom_extra_args} " + " ".join(extra_args_list)
    # Remove espaços extras no início
    combined_args = combined_args.lstrip()
    
    return combined_args

def check_file_mock_mode(file_path: str) -> str:
    """
    Verifica o modo de mock do arquivo.
    
    Se o arquivo não existir, retorna "none".
    Se a primeira linha do arquivo for:
      - "//__MOCK_COPY_FILE_CONTENT__" → retorna "copy"
      - "//__MOCK_DISCARD_FILE_CONTENT__" → retorna "discard"
    Caso contrário, retorna "discard" (padrão).
    """
    if not os.path.isfile(file_path):
        return "none"
    
    # Abre o arquivo e lê a primeira linha, removendo quebras de linha e carriage returns
    with open(file_path, 'r', encoding='utf-8') as f:
        first_line = f.readline().rstrip('\r\n')
    
    if first_line == "//__MOCK_COPY_FILE_CONTENT__":
        return "copy"
    elif first_line == "//__MOCK_DISCARD_FILE_CONTENT__":
        return "discard"
    else:
        return "discard"
    
def mock_err_msg(line_number, file, cmd, msg):
    """
    Exibe mensagens de erro com informações sobre o arquivo, linha, comando e mensagem.
    
    Parâmetros:
      line_number: Número da linha onde ocorreu o erro.
      file: Caminho do arquivo onde ocorreu o erro.
      cmd: Comando ou instrução de mock que gerou o erro.
      msg: Mensagem de erro adicional.
    """
    print(f"Error at {file}:{line_number}")
    print(f"Mock instruction: {cmd}")
    print(msg)

mock_err_msg(8, "mock-utils.py", "//__MOCK_START: BLAUS", "deu merda")