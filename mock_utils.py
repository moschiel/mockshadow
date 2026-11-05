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
import json
from source_types import SOURCE_EXTENSIONS, HEADER_EXTENSIONS

ENCODING="latin-1"
script_dir = os.path.dirname(os.path.abspath(__file__))

def get_user_configs():
    """
    Reads the .mockshadow/config.json and returns the configuration dictionary.
    Exits the application if the file is missing or contains invalid JSON.
    """
    import runtime
    file_config_json = os.path.join(runtime.DIR_MOCK_SHADOW_PROJECT, ".mockshadow/config.json")

    if not os.path.isfile(file_config_json):
        sys.exit("fatal: not a mockshadow project (missing .mockshadow/config.json)")

    try:
        with open(file_config_json, "r", encoding="utf-8") as f:
            config = json.load(f)
        from recipes import validate_config
        validate_config(config)
        return config
    except json.JSONDecodeError:
        sys.exit("fatal: invalid JSON in .mockshadow/config.json")

def get_user_env():
    """
    Reads the .mockshadow/env.json and returns the configuration dictionary.
    Creates if the file is missing.
    """
    import runtime
    file_env_json = os.path.join(runtime.DIR_MOCK_SHADOW_PROJECT, ".mockshadow/env.json")

    if not os.path.isfile(file_env_json):
        sys.exit("fatal: missing file .mockshadow/env.json")

    try:
        with open(file_env_json, "r", encoding="utf-8") as f:
            env_data = json.load(f)
    except json.JSONDecodeError:
        sys.exit("fatal: invalid JSON in .mockshadow/env.json")

    if "originalProject" not in env_data:
        sys.exit("fatal: missing 'originalProject' key in .mockshadow/env.json")

    original_project_path = env_data["originalProject"]

    if not isinstance(original_project_path, str) or not os.path.isdir(original_project_path):
        sys.exit(f"fatal: 'originalProject' path does not exist or is not a directory: {original_project_path}")

    return env_data

def update_user_env_param(key, value):
    """
    Atualiza um parâmetro específico no .mockshadow/env.json.
    Cria a chave se ela não existir.
    """
    import runtime
    file_env_json = os.path.join(runtime.DIR_MOCK_SHADOW_PROJECT, ".mockshadow/env.json")

    if not os.path.isfile(file_env_json):
        sys.exit("fatal: not a mockshadow project (missing .mockshadow/env.json)")

    try:
        with open(file_env_json, "r", encoding=ENCODING) as f:
            env_data = json.load(f)
    except json.JSONDecodeError:
        sys.exit("fatal: invalid JSON in .mockshadow/env.json")

    env_data[key] = value

    with open(file_env_json, "w", encoding=ENCODING) as f:
        json.dump(env_data, f, indent=4)

def mount_extractor_extra_args(custom_extra_args: str) -> str:
    import runtime
    # Remove espaços à esquerda dos argumentos customizados
    custom_extra_args = custom_extra_args.lstrip()
    
    # Adiciona flags extras a partir da chave 'extractorCFlags' do JSON de env
    extra_args_list = []
    for Cflag in runtime.USER_CONFIGS.get("extractorCFlags", []):
        if isinstance(Cflag, str) and Cflag.strip():
            extra_args_list.append(Cflag.strip())
    
    # Combina os custom_extra_args com os extra args lidos do arquivo
    combined_args = f"{custom_extra_args} " + " ".join(extra_args_list)
    # Remove espaços extras no início
    combined_args = combined_args.lstrip()
    
    return combined_args

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
                with open_shadow_file(mock_file_to_create, 'r', encoding=ENCODING) as mf:
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
                with open_shadow_file(mock_file_to_create, 'w', encoding=ENCODING) as mf:
                    mf.writelines(new_lines)

def mock_replace_code(mock_file_cmds: str, mock_file_to_create: str, show_details: bool = False) -> None:
    """
    Processa o arquivo de comandos de mock (mock_file_cmds) e substitui blocos de conteúdo
    no arquivo de mock (mock_file_to_create) conforme instruções do tipo:
    
      __MOCK_REPLACE_CODE_START: <EXTRACT_TYPE> <EXTRACT_NAME> [extra-args]
      ... (conteudo multilinha que irá sobrescrever o conteudo original ) ...
      //__MOCK_REPLACE_CODE_END

      __MOCK_REPLACE_CODE_LINE: <EXTRACT_TYPE> <EXTRACT_NAME> [extra-args]
      ... (conteudo com uma unica linha que irá sobrescrever o conteudo original) ...
      
    Para cada bloco, a função:
      - Determina o bloco (linhas SRC_START_LINE a SRC_END_LINE) no arquivo de comandos;
      - Chama o extractor (versão Python, extract.py) para obter DEST_START_LINE e DEST_END_LINE
        no arquivo de mock a ser atualizado;
      - Extrai o conteúdo do bloco do arquivo de comandos e insere esse conteúdo
        no arquivo de mock, substituindo as linhas entre DEST_START_LINE e DEST_END_LINE.
    
    Se ocorrer algum erro (como instrução aninhada ou falta de __MOCK_REPLACE_CODE_END),
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
        
        # Procura instruções do tipo __MOCK_REPLACE_CODE_(START|LINE): <EXTRACT_TYPE> <EXTRACT_NAME> [extra-args]
        pattern = r"__MOCK_REPLACE_CODE_(START|LINE):\s+(\S+)\s+(\S+)(\s+.*)?"
        m = re.search(pattern, line)
        if m:
            if inside_mock_block:
                mock_err_msg(count, mock_file_cmds, line, "Nested instruction, expected __MOCK_REPLACE_CODE_END")
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
                print(f"      replace code {EXTRACT_TYPE} '{EXTRACT_NAME}'")
        
        # Verifica se a linha marca o fim do bloco ou, no modo LINE, finaliza imediatamente
        elif (line.strip() == "//__MOCK_REPLACE_CODE_END" or REPLACE_MODE == "LINE"):
            if not inside_mock_block:
                mock_err_msg(count, mock_file_cmds, line, "Missing initial __MOCK_REPLACE_CODE_START:")
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
            with open_shadow_file(mock_file_to_create, "r", encoding=ENCODING) as mf:
                mock_file_lines = mf.readlines()
            new_content = []
            new_content.extend(mock_file_lines[:DEST_START_LINE - 1])
            with open(temp_file_path, "r", encoding=ENCODING) as tf:
                temp_lines = tf.readlines()
            new_content.extend(temp_lines)
            new_content.extend(mock_file_lines[DEST_END_LINE:])
            with open_shadow_file(mock_file_to_create, "w", encoding=ENCODING) as mf:
                mf.writelines(new_content)
            
            # Remove o arquivo temporário
            os.remove(temp_file_path)
    
    # Verifica se algum bloco ficou aberto sem encerramento
    if inside_mock_block:
        mock_err_msg(count, mock_file_cmds, MOCK_CMD, "Missing __MOCK_REPLACE_CODE_END")
        sys.exit(1)

def insert_mock_top_or_bottom(mock_file_cmds: str, mock_file_to_create: str, show_details: bool = False) -> None:
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
                if mock_file_to_create.endswith(HEADER_EXTENSIONS):
                    with open_shadow_file(mock_file_to_create, "r", encoding=ENCODING) as f:
                        dest_lines = f.readlines()
                    # Procura a última ocorrência de "#endif"
                    endif_lines = [i + 1 for i, l in enumerate(dest_lines) if "#endif" in l]
                    if endif_lines:
                        DEST_START_LINE = endif_lines[-1]  # indice de insercao: antes do #endif
                    else:
                        print("Aviso: Nenhum #endif encontrado. Inserindo no final do arquivo.")
                        DEST_START_LINE = len(dest_lines) + 1
                else:
                    with open_shadow_file(mock_file_to_create, "r", encoding=ENCODING) as f:
                        dest_lines = f.readlines()
                    DEST_START_LINE = len(dest_lines) + 1
            elif block_type == "MOCK_TOP":
                if mock_file_to_create.endswith(HEADER_EXTENSIONS):
                    with open_shadow_file(mock_file_to_create, "r", encoding=ENCODING) as f:
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
            with open_shadow_file(mock_file_to_create, "r", encoding=ENCODING) as f:
                target_lines = f.readlines()
            if DEST_START_LINE > 1 and target_lines and not target_lines[DEST_START_LINE - 2].endswith('\n'):
                target_lines[DEST_START_LINE - 2] += '\n'
            new_content = target_lines[:DEST_START_LINE - 1] + block_content + target_lines[DEST_START_LINE - 1:]
            with open_shadow_file(mock_file_to_create, "w", encoding=ENCODING) as f:
                f.writelines(new_content)
            continue
    # Final do loop de leitura
    
    if inside_block:
        print(f"Erro: Bloco iniciado com '{MOCK_CMD}' não foi encerrado corretamente.")
        sys.exit(1)

def mock_add_content_before_or_after(mock_file_cmds: str, mock_file_to_create: str, show_details: bool = False) -> None:
    """
    Processa o arquivo de comandos de mock (mock_file_cmds) e insere blocos de conteúdo
    no arquivo de mock (mock_file_to_create) conforme as instruções:

      __MOCK_ADD_BEFORE_START: <EXTRACT_TYPE> <EXTRACT_NAME> [extra-args]
      //multine content to add before
      __MOCK_ADD_BEFORE_END

      __MOCK_ADD_AFTER_START: <EXTRACT_TYPE> <EXTRACT_NAME> [extra-args]
      //multiline content to add after
      __MOCK_ADD_AFTER_END

      __MOCK_ADD_BEFORE_LINE: <EXTRACT_TYPE> <EXTRACT_NAME> [extra-args]
      //sigle line content to add before

      __MOCK_ADD_AFTER_LINE: <EXTRACT_TYPE> <EXTRACT_NAME> [extra-args]
      //single line content to add after

    Para cada comando, a função:
      - Identifica o bloco (para comandos START, do marcador inicial até o marcador de fim;
        para comandos LINE, a linha imediatamente após o comando);
      - Chama o extractor (extract.py) para obter DEST_START_LINE e DEST_END_LINE
        no arquivo de mock a ser atualizado;
      - Insere o conteúdo extraído (incluindo os próprios marcadores) no arquivo de mock:
          - Para comandos BEFORE, insere logo acima da linha DEST_START_LINE;
          - Para comandos AFTER, insere logo após a linha DEST_END_LINE.
    """

    # Verifica se os arquivos existem
    if not os.path.isfile(mock_file_cmds):
        print(f"Error: Not Found Source File '{mock_file_cmds}'")
        sys.exit(1)
    if not os.path.isfile(mock_file_to_create):
        print(f"Error: Mock File '{mock_file_to_create}' not found.")
        sys.exit(1)
    
    # Lê todas as linhas do arquivo de comandos
    with open(mock_file_cmds, "r", encoding=ENCODING) as f:
        cmds_lines = f.readlines()
    
    line_count = 0
    inside_block = False
    command_position = ""  # "BEFORE" ou "AFTER"
    replace_mode = ""      # "START" ou "LINE"
    EXTRACT_TYPE = ""
    EXTRACT_NAME = ""
    EXTRA_ARGS = ""
    block_content = []  # conteúdo do bloco, incluindo marcadores

    while line_count < len(cmds_lines):
        current_line = cmds_lines[line_count].rstrip("\n")
        line_count += 1

        if not inside_block:
            # Verifica comandos multi-linha (START)
            pattern_block = r"__MOCK_ADD_(BEFORE|AFTER)_START:\s+(\S+)\s+(\S+)(\s+.*)?"
            m_block = re.search(pattern_block, current_line)
            if m_block:
                inside_block = True
                command_position = m_block.group(1)  # BEFORE ou AFTER
                replace_mode = "START"
                EXTRACT_TYPE = m_block.group(2)
                EXTRACT_NAME = m_block.group(3)
                EXTRA_ARGS = m_block.group(4) if m_block.group(4) is not None else ""
                EXTRA_ARGS = "lines " + mount_extractor_extra_args(EXTRA_ARGS)
                # Guarda o marcador inicial como parte do bloco
                block_content = [current_line + "\n"]
                if show_details:
                    print(f"      add content {command_position} {EXTRACT_TYPE} '{EXTRACT_NAME}'")
                continue

            # Verifica comandos de linha única (LINE)
            pattern_line = r"__MOCK_ADD_(BEFORE|AFTER)_LINE:\s+(\S+)\s+(\S+)(\s+.*)?"
            m_line = re.search(pattern_line, current_line)
            if m_line:

                command_position = m_line.group(1)  # BEFORE ou AFTER
                replace_mode = "LINE"
                EXTRACT_TYPE = m_line.group(2)
                EXTRACT_NAME = m_line.group(3)
                EXTRA_ARGS = m_line.group(4) if m_line.group(4) is not None else ""
                EXTRA_ARGS = "lines " + mount_extractor_extra_args(EXTRA_ARGS)
                # Guarda o comando e a próxima linha (conteúdo a adicionar)
                block_content = [current_line + "\n"]
                if line_count < len(cmds_lines):
                    content_line = cmds_lines[line_count]
                    line_count += 1
                    block_content.append(content_line)
                else:
                    mock_err_msg(line_count, mock_file_cmds, current_line, "Expected content line after __MOCK_ADD_LINE marker")
                    sys.exit(1)
                if show_details:
                    print(f"      add content {command_position} {EXTRACT_TYPE} '{EXTRACT_NAME}'")
                # Processa imediatamente o comando de linha única
                process_add_command(mock_file_to_create, EXTRACT_TYPE, EXTRACT_NAME, EXTRA_ARGS, block_content, command_position, show_details)
                block_content = []
                continue

        else:
            # Estamos dentro de um bloco multi-linha iniciado por __MOCK_ADD_?_START
            if command_position == "BEFORE":
                if current_line.strip() == "//__MOCK_ADD_BEFORE_END":
                    block_content.append(current_line + "\n")
                    inside_block = False
                    process_add_command(mock_file_to_create, EXTRACT_TYPE, EXTRACT_NAME, EXTRA_ARGS, block_content, command_position, show_details)
                    block_content = []
                    continue
                else:
                    block_content.append(current_line + "\n")
            elif command_position == "AFTER":
                # Observação: conforme o padrão fornecido, o marcador de fim é "__MOCK_ADD_AFTER_END"
                if current_line.strip() == "//__MOCK_ADD_AFTER_END":
                    block_content.append(current_line + "\n")
                    inside_block = False
                    process_add_command(mock_file_to_create, EXTRACT_TYPE, EXTRACT_NAME, EXTRA_ARGS, block_content, command_position, show_details)
                    block_content = []
                    continue
                else:
                    block_content.append(current_line + "\n")
    
    if inside_block:
        mock_err_msg(line_count, mock_file_cmds, block_content[0].strip(), "Block not terminated properly.")
        sys.exit(1)

def process_add_command(mock_file_to_create: str, EXTRACT_TYPE: str, EXTRACT_NAME: str, EXTRA_ARGS: str,
                        block_content: list, command_position: str, show_details: bool = False) -> None:
    """
    Processa um comando de adição (antes ou depois), chamando o extractor para obter a posição
    de destino e inserindo o conteúdo (incluindo os marcadores) no arquivo de mock.
    """

    # Define o diretório do extractor (supondo que 'script_dir' e 'extract.py' existam)
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
        mock_err_msg(0, "", f"Extractor command for {EXTRACT_TYPE} '{EXTRACT_NAME}'", text_extracted)
        sys.exit(status)
    
    # A saída do extractor deve estar no formato "<DEST_START_LINE>;<DEST_END_LINE>"
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
    
    # Lê o conteúdo atual do arquivo de mock a ser atualizado
    with open_shadow_file(mock_file_to_create, "r", encoding=ENCODING) as mf:
        target_lines = mf.readlines()
    
    # Define a posição de inserção com base no tipo do comando:
    # - BEFORE: insere logo acima de DEST_START_LINE
    # - AFTER: insere logo após DEST_END_LINE
    if command_position == "BEFORE":
        insert_index = DEST_START_LINE - 1
    elif command_position == "AFTER":
        insert_index = DEST_END_LINE
    else:
        print("Error: Invalid command position.")
        sys.exit(1)
    
    # Garante que a última linha do bloco tenha '\n'
    if block_content and not block_content[-1].endswith('\n'):
        block_content[-1] += '\n'

    # Constrói o novo conteúdo do arquivo
    new_content = target_lines[:insert_index] + block_content + target_lines[insert_index:]
    with open_shadow_file(mock_file_to_create, "w", encoding=ENCODING) as mf:
        mf.writelines(new_content)
    
    #if show_details:
    #    pos_desc = "before" if command_position == "BEFORE" else "after"
    #    print(f"Inserted content {pos_desc} line {insert_index+1} in '{mock_file_to_create}'")

def mock_text_replace(mock_file_cmds: str, mock_file_to_create: str, show_details: bool = False) -> None:
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
    REPLACE_MODE = ""
    NEW_TEXT = ""
    CURR_TEXT = ""
    
    # Lê todas as linhas do arquivo de comandos (preservando quebras de linha)
    with open(mock_file_cmds, "r", encoding=ENCODING) as f:
        cmds_lines = f.readlines()
    
    # Itera sobre cada linha (contabilizando o número da linha)
    for line in cmds_lines:
        count += 1
        line = line.rstrip("\n")
        
        pattern = r"__MOCK_REPLACE_TEXT_(START|LINE): \s*(.*)"
        m = re.search(pattern, line)
        if m:
            if inside_mock_block:
                mock_err_msg(count, mock_file_cmds, MOCK_CMD, "Nested instruction, expected text to replace")
                sys.exit(1)
            
            inside_mock_block = True
            REPLACE_MODE = m.group(1)  # "START" ou "LINE"
            CURR_TEXT = m.group(2)
            MOCK_CMD = line
            
            if show_details:
                print(f"      replace text [${CURR_TEXT}]")        
        elif (line.strip() == "//__MOCK_REPLACE_TEXT_END" or REPLACE_MODE == "LINE"):
            if not inside_mock_block:
                mock_err_msg(count, mock_file_cmds, line, "Missing initial __MOCK_REPLACE_TEXT_START:")
                sys.exit(1)
                
            if REPLACE_MODE == "LINE":
                NEW_TEXT += line
            NEW_TEXT = NEW_TEXT.rstrip()
            content = ""
            with open_shadow_file(mock_file_to_create, "r", encoding=ENCODING) as f:
                content = f.read()
            if content.count(CURR_TEXT) == 0:
                mock_err_msg(count, mock_file_cmds, MOCK_CMD, f"Not found text to replace '${CURR_TEXT}'")
                sys.exit(1)
            content = content.replace(CURR_TEXT, NEW_TEXT)
            with open_shadow_file(mock_file_to_create, 'w', encoding=ENCODING) as f:
                f.write(content)
        
            NEW_TEXT = "" # reseta o conteúdo
            REPLACE_MODE = ""  # Reseta o modo
            inside_mock_block = False
        elif inside_mock_block:
            NEW_TEXT += line + "\n"

    if inside_mock_block:
        mock_err_msg(count, mock_file_cmds, MOCK_CMD, "Block not terminated properly.")
        sys.exit(1)

def create_mockshadow_project(project_name):
    # Verifica se o nome do projeto é válido
    if not project_name or not project_name.strip():
        print("Error: Project name cannot be empty.")
        sys.exit(1)

    # Evita nomes com caracteres inválidos (ex: / \ ? * etc.)
    if re.search(r'[<>:"/\\|?*\x00-\x1F]', project_name):
        print("Error: Project name contains invalid characters.")
        sys.exit(1)

    # Caminho absoluto para a pasta onde o script foi executado
    exec_dir = os.getcwd()
    project_path = os.path.join(exec_dir, project_name.strip())

    # Caminhos das pastas/arquivos do template
    template_root = os.path.join(os.path.dirname(__file__), "templates")
    template_dot_mockshadow = os.path.join(template_root, ".mockshadow")
    template_dot_vscode = os.path.join(template_root, ".vscode")
    template_gitignore = os.path.join(template_root, ".gitignore_template")

    try:
        # Cria a pasta do projeto
        os.makedirs(project_path, exist_ok=False)

        # Copia .mockshadow
        dst_dot_mockshadow = os.path.join(project_path, ".mockshadow")
        shutil.copytree(template_dot_mockshadow, dst_dot_mockshadow, dirs_exist_ok=True)

        # Copia .vscode
        dst_dot_vscode = os.path.join(project_path, ".vscode")
        shutil.copytree(template_dot_vscode, dst_dot_vscode, dirs_exist_ok=True)

        # Copia .gitignore
        dst_gitignore = os.path.join(project_path, ".gitignore")
        shutil.copyfile(template_gitignore, dst_gitignore)

        # Cria o diretório MOCK_TREE
        mock_tree_path = os.path.join(project_path, "mocks")
        os.makedirs(mock_tree_path, exist_ok=True)

        print(f"MockShadow project created at: {project_path}")

    except Exception as e:
        print(f"Error while creating project: {e}")
        sys.exit(1)


def open_shadow_file(*args, **kwargs):
    """Retry Windows locks before opening a shadow file, not a whole recipe."""
    from pipeline import retry_io
    return retry_io(open, *args, **kwargs)
