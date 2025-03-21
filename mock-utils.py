#!/usr/bin/env python3
#  Created on: 18 de mar de 2025
#      Author: roger moschiel

import os
import shutil
import sys
import re
import subprocess
import env # Variaveis de ambiente env.py

script_dir = os.path.dirname(os.path.abspath(__file__))

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

def mock_remove_content(mock_file_cmds: str, mock_file_to_create: str, show_details: bool = False):
    """
    Processa o arquivo de comandos de mock (mock_file_cmds) para remover conteúdo
    do arquivo de mock (mock_file_to_create) de acordo com as instruções.
    
    Para cada linha que corresponda a:
      __MOCK_REMOVE: <EXTRACT_TYPE> <EXTRACT_NAME> [extra-args]
    a função:
      - Adiciona "lines" e os extra args processados via mount_extractor_extra_args().
      - Chama o extractor (a versão Python, extract.py) no diretório SCRIPT_MOCKSHADOW_DIR/clang-code-extractor.
      - Se o extractor retornar erro, chama mock_err_msg() e encerra.
      - Se bem-sucedido, a saída deverá ser "<START_LINE>;<END_LINE>".
      - Atualiza o arquivo de mock, substituindo as linhas entre START_LINE e END_LINE
        pela instrução de mock (a linha atual).
    """
    # Verifica se os arquivos existem
    if not os.path.isfile(mock_file_cmds):
        print(f"Error: Not Found Source File '{mock_file_cmds}'")
        sys.exit(1)
    if not os.path.isfile(mock_file_to_create):
        print(f"Error: Mock File '{mock_file_to_create}'")
        sys.exit(1)
    
    count = 0
    with open(mock_file_cmds, 'r', encoding='utf-8') as f:
        for line in f:
            # Remove a quebra de linha no final, se houver
            line = line.rstrip('\n')
            count += 1

            # Regex para capturar: __MOCK_REMOVE: <EXTRACT_TYPE> <EXTRACT_NAME> [extra-args]
            pattern = r"__MOCK_REMOVE:\s+(\S+)\s+(\S+)(\s+.*)?"
            m = re.search(pattern, line)
            if m:
                extract_type = m.group(1)
                extract_name = m.group(2)
                extra_args = m.group(3) if m.group(3) is not None else ""
                # Adiciona "lines" e processa os extra args
                extra_args = "lines " + mount_extractor_extra_args(extra_args)
                
                if show_details:
                    print(f"      Remove original {extract_type} '{extract_name}'")
                
                # Define o diretório do extractor a partir da variável de ambiente SCRIPT_MOCKSHADOW_DIR
                extractor_dir = os.path.join(script_dir, "clang-code-extractor")
                # Monta o comando usando a versão Python do extractor (extract.py)
                # Usamos sys.executable para invocar o Python atual
                cmd = [sys.executable, "extract.py", extract_type, extract_name, mock_file_to_create] + extra_args.split()
                
                try:
                    result = subprocess.run(cmd, cwd=extractor_dir, capture_output=True, text=True)
                    text_extracted = (result.stdout + result.stderr).strip()
                    status = result.returncode
                except Exception as e:
                    print(f"Error executing extractor: {e}")
                    sys.exit(1)
                
                if status != 0:
                    mock_err_msg(count, mock_file_cmds, line, text_extracted)
                    sys.exit(status)
                
                # A saída deve estar no formato "<START_LINE>;<END_LINE>"
                parts = text_extracted.split(";")
                if len(parts) < 2:
                    print(f"Error: Could not parse extractor output: {text_extracted}")
                    sys.exit(1)
                try:
                    start_line = int(parts[0].strip())
                    end_line = int(parts[1].strip())
                except ValueError:
                    print(f"Error: Invalid line numbers extracted: {text_extracted}")
                    sys.exit(1)
                
                # Lê o conteúdo do arquivo de mock
                with open(mock_file_to_create, 'r', encoding='utf-8') as mf:
                    file_lines = mf.readlines()
                
                # Monta o novo conteúdo:
                # - Linhas antes de start_line: mantêm
                # - Linha start_line: substituída pela instrução de mock (a linha atual)
                # - Linhas de start_line+1 até end_line: descartadas
                # - Linhas após end_line: mantidas
                new_lines = []
                for i, content in enumerate(file_lines, start=1):
                    if i < start_line:
                        new_lines.append(content)
                    elif i == start_line:
                        new_lines.append(line + "\n")
                    elif i > end_line:
                        new_lines.append(content)
                # Escreve o novo conteúdo de volta para o arquivo
                with open(mock_file_to_create, 'w', encoding='utf-8') as mf:
                    mf.writelines(new_lines)

mock_remove_content(
    "/home/moschiel/Development/EmulandoMSC/MSC_Simulator/MOCK_TREE/src/Include/__mock__FreeRTOSConfig.h",
    "/home/moschiel/Development/EmulandoMSC/MSC_Simulator/MOCK_TREE/src/Include/FreeRTOSConfig.h",
    True
)