#!/usr/bin/env python3
#  Created on: 18 de mar de 2025
#      Author: roger moschiel

import os
import shutil
import sys
import re
import subprocess
import tempfile
import time
import env # Variaveis de ambiente env.py

script_dir = os.path.dirname(os.path.abspath(__file__))
ENCODING="latin-1"

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

def clone_project_tree():
    """
    Verifica se o diretório de origem é válido e clona a árvore de
    diretórios (estrutura sem arquivos) de 'dir_original_project' para 'dir_shadow_mocks'.
    """
    print("Cloning Project Tree")
    if not os.path.isdir(env.DIR_ORIGINAL_PROJECT):
        print(f"Erro: '{env.DIR_ORIGINAL_PROJECT}' não é um diretório válido.")
        sys.exit(1)

    for root, dirs, _ in os.walk(env.DIR_ORIGINAL_PROJECT):
        for d in dirs:
            # Calcula o caminho relativo do diretório em relação ao projeto original
            rel_path = os.path.relpath(os.path.join(root, d), env.DIR_ORIGINAL_PROJECT)
            new_dir = os.path.join(env.DIR_SHADOW_MOCKS, rel_path)
            os.makedirs(new_dir, exist_ok=True)
    print("Cloning Project Tree Complete!")

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
    with open(file_path, 'r', encoding=ENCODING) as f:
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
    with open(mock_file_cmds, 'r', encoding=ENCODING) as f:
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
                with open(mock_file_to_create, 'r', encoding=ENCODING) as mf:
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
                with open(mock_file_to_create, 'w', encoding=ENCODING) as mf:
                    mf.writelines(new_lines)

def mock_replace_content(mock_file_cmds: str, mock_file_to_create: str, show_details: bool = False) -> None:
    """
    Processa o arquivo de comandos de mock (mock_file_cmds) e substitui blocos de conteúdo
    no arquivo de mock (mock_file_to_create) conforme instruções do tipo:
    
      __MOCK_REPLACE_(START|LINE): <EXTRACT_TYPE> <EXTRACT_NAME> [extra-args]
      ... (linhas intermediárias) ...
      //__MOCK_REPLACE_END
      
    Para cada bloco, a função:
      - Determina o bloco (linhas SRC_START_LINE a SRC_END_LINE) no arquivo de comandos;
      - Chama o extractor (versão Python, extract.py) para obter DEST_START_LINE e DEST_END_LINE
        no arquivo de mock a ser atualizado;
      - Extrai o conteúdo do bloco do arquivo de comandos e insere esse conteúdo
        no arquivo de mock, substituindo as linhas entre DEST_START_LINE e DEST_END_LINE.
    
    Se ocorrer algum erro (como instrução aninhada ou falta de __MOCK_REPLACE_END),
    a função chama mock_err_msg() e encerra.
    """
    # Verifica se os arquivos existem
    if not os.path.isfile(mock_file_cmds):
        print(f"Error: Not Found Source File '{mock_file_cmds}'")
        sys.exit(1)
    if not os.path.isfile(mock_file_to_create):
        print(f"Error: Mock File '{mock_file_to_create}'")
        sys.exit(1)
    
    inside_mock_block = False
    MOCK_CMD = ""
    count = 0
    SRC_START_LINE = 0
    SRC_END_LINE = 0
    REPLACE_MODE = ""
    
    # Lê todas as linhas do arquivo de comandos (preservando quebras de linha)
    with open(mock_file_cmds, "r", encoding=ENCODING) as f:
        cmds_lines = f.readlines()
    
    # Itera sobre cada linha (contabilizando o número da linha)
    for line in cmds_lines:
        count += 1
        line = line.rstrip("\n")
        
        # Procura instruções do tipo __MOCK_REPLACE_(START|LINE): <EXTRACT_TYPE> <EXTRACT_NAME> [extra-args]
        pattern = r"__MOCK_REPLACE_(START|LINE):\s+(\S+)\s+(\S+)(\s+.*)?"
        m = re.search(pattern, line)
        if m:
            if inside_mock_block:
                mock_err_msg(count, mock_file_cmds, line, "Nested instruction, expected __MOCK_REPLACE_END")
                sys.exit(1)
            inside_mock_block = True
            MOCK_CMD = line
            SRC_START_LINE = count
            
            REPLACE_MODE = m.group(1)  # "START" ou "LINE"
            EXTRACT_TYPE = m.group(2)
            EXTRACT_NAME = m.group(3)
            EXTRA_ARGS = m.group(4) if m.group(4) is not None else ""
            # Adiciona o argumento "lines" e processa os extra args
            EXTRA_ARGS = "lines " + mount_extractor_extra_args(EXTRA_ARGS)
            
            if show_details:
                print(f"      replace original {EXTRACT_TYPE} '{EXTRACT_NAME}'")
        
        # Verifica se a linha marca o fim do bloco ou, no modo LINE, finaliza imediatamente
        elif (line.strip() == "//__MOCK_REPLACE_END" or REPLACE_MODE == "LINE"):
            if not inside_mock_block:
                mock_err_msg(count, mock_file_cmds, line, "Missing initial __MOCK_REPLACE_START:")
                sys.exit(1)
            REPLACE_MODE = ""  # Reseta o modo
            inside_mock_block = False
            SRC_END_LINE = count
            
            # Chama o extractor (versão Python, extract.py) para obter DEST_START_LINE e DEST_END_LINE
            extractor_dir = os.path.join(script_dir, "clang-code-extractor")
            cmd = [sys.executable, "extract.py", EXTRACT_TYPE, EXTRACT_NAME, mock_file_to_create] + EXTRA_ARGS.split()
            try:
                result = subprocess.run(cmd, cwd=extractor_dir, capture_output=True, text=True)
            except Exception as e:
                print(f"Error executing extractor: {e}")
                sys.exit(1)
            text_extracted = (result.stdout + result.stderr).strip()
            status = result.returncode
            if status != 0:
                mock_err_msg(count, mock_file_cmds, MOCK_CMD, text_extracted)
                sys.exit(status)
            
            # Espera-se que a saída seja do formato "<DEST_START_LINE>;<DEST_END_LINE>"
            parts = text_extracted.split(";")
            if len(parts) < 2:
                print(f"Error: Could not parse extractor output: {text_extracted}")
                sys.exit(1)
            try:
                DEST_START_LINE = int(parts[0].strip())
                DEST_END_LINE = int(parts[1].strip())
            except ValueError:
                print(f"Error: Invalid destination line numbers: {text_extracted}")
                sys.exit(1)
            
            # Extrai o conteúdo do arquivo de comandos entre SRC_START_LINE e SRC_END_LINE
            extracted_content = cmds_lines[SRC_START_LINE - 1:SRC_END_LINE]
            # Garante que tenha um '\n' no final
            if extracted_content and not extracted_content[-1].endswith('\n'):
                extracted_content[-1] += '\n'
            # Escreve esse conteúdo em um arquivo temporário
            with tempfile.NamedTemporaryFile(delete=False, mode="w", encoding=ENCODING) as tmp_file:
                tmp_file.writelines(extracted_content)
                temp_file_path = tmp_file.name
            
            # Atualiza o arquivo de mock (mock_file_to_create):
            # - Mantém as linhas antes de DEST_START_LINE
            # - Insere o conteúdo do arquivo temporário no lugar das linhas de DEST_START_LINE até DEST_END_LINE
            # - Mantém as linhas após DEST_END_LINE
            with open(mock_file_to_create, "r", encoding=ENCODING) as mf:
                mock_file_lines = mf.readlines()
            new_content = []
            new_content.extend(mock_file_lines[:DEST_START_LINE - 1])
            with open(temp_file_path, "r", encoding=ENCODING) as tf:
                temp_lines = tf.readlines()
            new_content.extend(temp_lines)
            new_content.extend(mock_file_lines[DEST_END_LINE:])
            with open(mock_file_to_create, "w", encoding=ENCODING) as mf:
                mf.writelines(new_content)
            
            # Remove o arquivo temporário
            os.remove(temp_file_path)
    
    # Verifica se algum bloco ficou aberto sem encerramento
    if inside_mock_block:
        mock_err_msg(count, mock_file_cmds, MOCK_CMD, "Missing __MOCK_REPLACE_END")
        sys.exit(1)

def insert_mock_top_bottom(mock_file_cmds: str, mock_file_to_create: str, show_details: bool = False) -> None:
    """
    Insere conteúdo de blocos de mock em um arquivo de destino, de acordo com marcadores
    no arquivo de comandos (mock_file_cmds). São suportados dois tipos de blocos:

      - MOCK_TOP: Bloco que deve ser inserido no topo do arquivo de destino.
      - MOCK_BOTTOM: Bloco que deve ser inserido no fundo do arquivo de destino.

    Para arquivos com extensão .h, o código tenta identificar os "include guards":
      - Para MOCK_BOTTOM, procura a última ocorrência de "#endif" e insere logo antes.
      - Para MOCK_TOP, procura a primeira linha que inicia com "#define" e insere logo depois.

    Se ocorrer algum erro (por exemplo, bloco aninhado ou ausência do marcador de fim),
    o script exibe uma mensagem e encerra.
    """
    # Verifica se os arquivos existem
    if not os.path.isfile(mock_file_cmds):
        print(f"Error: Not Found Source File '{mock_file_cmds}'")
        sys.exit(1)
    if not os.path.isfile(mock_file_to_create):
        print(f"Error: Mock File '{mock_file_to_create}'")
        sys.exit(1)
    
    inside_block = False
    block_type = ""
    MOCK_CMD = ""
    count = 0
    SRC_START_LINE = 0
    SRC_END_LINE = 0
    DEST_START_LINE = 0

    # Lê todas as linhas do arquivo de comandos
    with open(mock_file_cmds, "r", encoding=ENCODING) as f:
        cmds_lines = f.readlines()
    
    for line in cmds_lines:
        count += 1
        line_stripped = line.rstrip("\n")
        
        # Verifica se a linha indica início de um bloco (MOCK_TOP ou MOCK_BOTTOM)
        m_start = re.match(r"^//__(MOCK_TOP|MOCK_BOTTOM)_START$", line_stripped)
        if m_start:
            if inside_block:
                print(f"Erro: Bloco aninhado detectado em linha {count}. Não permitido.")
                sys.exit(1)
            inside_block = True
            block_type = m_start.group(1)  # "MOCK_TOP" ou "MOCK_BOTTOM"
            MOCK_CMD = line_stripped
            SRC_START_LINE = count
            if show_details:
                if block_type == "MOCK_BOTTOM":
                    print("      insert content at the BOTTOM")
                elif block_type == "MOCK_TOP":
                    print("      insert content at the TOP")
            continue
        
        # Verifica se a linha indica fim de bloco
        m_end = re.match(r"^//__(MOCK_TOP|MOCK_BOTTOM)_END$", line_stripped)
        if m_end:
            if not inside_block:
                print(f"Erro: Marcador de fim encontrado sem bloco iniciado (linha {count}).")
                sys.exit(1)
            expected_end = f"//__{block_type}_END"
            if line_stripped != expected_end:
                print(f"Erro: Marcador de fim '{line_stripped}' não corresponde ao início '{MOCK_CMD}' (linha {count}).")
                sys.exit(1)
            inside_block = False
            SRC_END_LINE = count

            # Extrai o conteúdo do bloco do arquivo de comandos (linhas do início ao fim do bloco)
            block_content = cmds_lines[SRC_START_LINE - 1 : SRC_END_LINE]
            # Garante que tenha um '\n' no final
            if block_content and not block_content[-1].endswith('\n'):
                block_content[-1] += '\n'
            
            # Determina a linha de destino para a inserção no arquivo de destino
            # Para arquivos .h, tenta identificar os include guards
            if block_type == "MOCK_BOTTOM":
                if mock_file_to_create.endswith(".h"):
                    with open(mock_file_to_create, "r", encoding=ENCODING) as f:
                        dest_lines = f.readlines()
                    # Procura a última ocorrência de "#endif"
                    endif_lines = [i + 1 for i, l in enumerate(dest_lines) if "#endif" in l]
                    if endif_lines:
                        DEST_START_LINE = endif_lines[-1] - 1  # insere antes do #endif
                    else:
                        print("Aviso: Nenhum #endif encontrado. Inserindo no final do arquivo.")
                        DEST_START_LINE = len(dest_lines)
                else:
                    with open(mock_file_to_create, "r", encoding=ENCODING) as f:
                        dest_lines = f.readlines()
                    DEST_START_LINE = len(dest_lines)
            elif block_type == "MOCK_TOP":
                if mock_file_to_create.endswith(".h"):
                    with open(mock_file_to_create, "r", encoding=ENCODING) as f:
                        dest_lines = f.readlines()
                    # Procura a primeira linha que inicia com "#define"
                    define_lines = [i + 1 for i, l in enumerate(dest_lines) if l.lstrip().startswith("#define")]
                    if define_lines:
                        DEST_START_LINE = define_lines[0] + 1  # insere logo após
                    else:
                        DEST_START_LINE = 1
                else:
                    DEST_START_LINE = 1
            
            # Insere o conteúdo extraído no arquivo de destino
            with open(mock_file_to_create, "r", encoding=ENCODING) as f:
                target_lines = f.readlines()
            new_content = target_lines[:DEST_START_LINE - 1] + block_content + target_lines[DEST_START_LINE - 1:]
            with open(mock_file_to_create, "w", encoding=ENCODING) as f:
                f.writelines(new_content)
            continue
    # Final do loop de leitura
    
    if inside_block:
        print(f"Erro: Bloco iniciado com '{MOCK_CMD}' não foi encerrado corretamente.")
        sys.exit(1)

def insert_mock_original_content(original_file: str, mock_file_to_create: str, show_details: bool):
    print("TODO: insert_mock_original_content")

def unmock_project():
    """
    Remove todos os arquivos com extensão .c ou .h dentro de DIR_SHADOW_MOCKS,
    exceto aqueles cujo nome comece com "__mock__" ou "__additional__". Após a limpeza,
    chama clone_project().

    Para arquivos removidos, exibe o caminho relativo a partir de DIR_MOCK_SHADOW_PROJECT.
    """
    print("Cleaning", os.path.basename(env.DIR_SHADOW_MOCKS), "...")
    
    # Percorre recursivamente o diretório DIR_SHADOW_MOCKS
    for root, dirs, files in os.walk(env.DIR_SHADOW_MOCKS):
        for file in files:
            # Filtra arquivos com extensão .c ou .h, mas exclui os que começam com "__mock__" ou "__additional__"
            if (file.endswith(".c") or file.endswith(".h")) and not (file.startswith("__mock__") or file.startswith("__additional__")):
                file_path = os.path.join(root, file)
                try:
                    os.remove(file_path)
                    # Calcula o caminho relativo a partir de DIR_MOCK_SHADOW_PROJECT
                    relative_path = os.path.relpath(file_path, env.DIR_MOCK_SHADOW_PROJECT)
                    print("  Removed", relative_path)
                except Exception as e:
                    print(f"Error removing file {file_path}: {e}", file=sys.stderr)
    
    print("Cleaning Complete!")
    
    # Chama a função clone_project para recriar a árvore de diretórios
    clone_project()

def mock_project(*args):
    # Parse arguments
    show_details = False
    is_remock = False
    for arg in args:
        if arg == "details":
            show_details = True
        elif arg == "remock":
            is_remock = True

    proj_basename = os.path.basename(env.DIR_ORIGINAL_PROJECT)

    # Antes de mockar, se "remock" for solicitado, chama unmock_project()
    if is_remock:
        unmock_project()

    print("Creating Mock Files ...")
    file_last_mock_timestamp = os.path.join(env.DIR_MOCK_SHADOW_PROJECT, "last_mock_timestamp.txt")
    if os.path.isfile(file_last_mock_timestamp):
        with open(file_last_mock_timestamp, "r", encoding=ENCODING) as f:
            last_mock_timestamp = int(f.read().strip())
    else:
        last_mock_timestamp = 0

    # Itera sobre todos os arquivos .c e .h que iniciam com "__mock__" em DIR_SHADOW_MOCKS
    for root, dirs, files in os.walk(env.DIR_SHADOW_MOCKS):
        for filename in files:
            if (filename.endswith(".c") or filename.endswith(".h")) and filename.startswith("__mock__"):
                mock_file = os.path.join(root, filename)
                mock_dir = os.path.dirname(mock_file)
                mock_basename = os.path.basename(mock_file)
                original_basename = mock_basename.replace("__mock__", "")
                mock_file_to_create = os.path.join(mock_dir, original_basename)

                # Se o arquivo a ser criado não existe ou se o arquivo __mock__ foi modificado após o último mock
                if (not os.path.isfile(mock_file_to_create)) or (os.stat(mock_file).st_mtime > last_mock_timestamp):
                    mock_mode = check_file_mock_mode(mock_file)
                    rel_path = os.path.relpath(mock_file_to_create, env.DIR_MOCK_SHADOW_PROJECT)
                    print(f"  Creating {rel_path} (MOCK_MODE: {mock_mode})")

                    # Remove DIR_SHADOW_MOCKS do caminho e junta com DIR_ORIGINAL_PROJECT para obter o arquivo original
                    partial_dir = os.path.relpath(mock_dir, env.DIR_SHADOW_MOCKS)
                    original_file = os.path.join(env.DIR_ORIGINAL_PROJECT, partial_dir, original_basename)
                    validate_file_exists(original_file)

                    if mock_mode == "copy":
                        # Cria o arquivo de mock como cópia do arquivo original
                        shutil.copy2(original_file, mock_file_to_create)
                        # Processa as seções: remove, substitui e insere conteúdo
                        mock_remove_content(mock_file, mock_file_to_create, show_details)
                        mock_replace_content(mock_file, mock_file_to_create, show_details)
                        insert_mock_top_bottom(mock_file, mock_file_to_create, show_details)
                    else:
                        # Cria o arquivo de mock com o conteúdo do arquivo __mock__
                        shutil.copy2(mock_file, mock_file_to_create)
                        # Insere seções do conteúdo original no arquivo mockado
                        insert_mock_original_content(original_file, mock_file_to_create, show_details)

    # Atualiza o timestamp do último mock
    last_mock_timestamp = int(time.time())
    with open(file_last_mock_timestamp, "w", encoding=ENCODING) as f:
        f.write(str(last_mock_timestamp))
    print("Creating Mock Files Complete!")

    print(f"Mocking {os.path.basename(env.DIR_TEMP_PROJECT)} ...")
    # Itera sobre os mocks em DIR_SHADOW_MOCKS que são .c ou .h, mas não começam com "__mock__"
    for root, dirs, files in os.walk(env.DIR_SHADOW_MOCKS):
        for filename in files:
            if (filename.endswith(".c") or filename.endswith(".h")) and not filename.startswith("__mock__"):
                mock_file = os.path.join(root, filename)
                proj_file = os.path.relpath(mock_file, env.DIR_SHADOW_MOCKS)
                project_file_to_replace = os.path.join(env.DIR_TEMP_PROJECT, proj_file)

                basename_project_to_mock = os.path.basename(env.DIR_TEMP_PROJECT)
                print(f"  Mocking {os.path.join(basename_project_to_mock, proj_file)}")
                file_basename = os.path.basename(proj_file)
                if file_basename.startswith("__additional__"):
                    # Arquivos __additional__ são copiados para o projeto
                    os.makedirs(os.path.dirname(project_file_to_replace), exist_ok=True)
                    shutil.copy2(mock_file, project_file_to_replace)
                else:
                    original_file = os.path.join(env.DIR_ORIGINAL_PROJECT, proj_file)
                    validate_file_exists(original_file)
                    # Substitui o arquivo original pela versão mockada
                    shutil.copy2(mock_file, project_file_to_replace)
    print(f"Mocking {os.path.basename(env.DIR_TEMP_PROJECT)} Complete!")
